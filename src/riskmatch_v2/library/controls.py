"""Shared point-in-time, valuation, admission and exposure controls."""
import math
import numpy as np
import pandas as pd


def visible(frame, instant, keys, observed="day", available="available"):
    cutoff = pd.Timestamp(instant)
    if cutoff.tz is None:
        raise ValueError("Explicit UTC time stamping required")
    known = frame[(pd.to_datetime(frame[observed], utc=True) <= cutoff)
                  & (pd.to_datetime(frame[available], utc=True) <= cutoff)].copy()
    if known.duplicated([*keys, observed, available]).any():
        raise ValueError("Two competing versions without publication order")
    return known.sort_values([observed, available]).drop_duplicates(keys, keep="last")


def chf_return(local, fx_start, fx_end, direction="CHF/USD"):
    if direction not in ("CHF/USD","USD/CHF"):
        raise ValueError("Unknown currency exchange agreement")
    if not (fx_start > 0 and fx_end > 0 and math.isfinite(fx_start) and math.isfinite(fx_end)):
        return np.nan
    ratio = fx_end / fx_start if direction == "CHF/USD" else fx_start / fx_end
    return (1 + local) * ratio - 1


def identity_at(identifiers, ticker, day):
    day=pd.Timestamp(day)
    rows=identifiers[(identifiers.ticker==ticker) & (pd.to_datetime(identifiers.id_from)<=day)
                     & (pd.to_datetime(identifiers.id_to)>=day)]
    ids=rows.permno.unique()
    return int(ids[0]) if len(ids)==1 else None


def align_sessions(frame, sessions, fx):
    if not frame.index.is_unique or not frame.index.difference(sessions).empty:
        raise ValueError("Duplicated or non-scheduled dates")
    aligned=frame.reindex(sessions)
    aligned["fx"]=fx.reindex(sessions)
    aligned["return_usd"]=aligned.adjusted.pct_change(fill_method=None)
    aligned["return_chf"]=(aligned.adjusted*aligned.fx).pct_change(fill_method=None)
    aligned["reason"]=np.select([aligned.adjusted.isna(),aligned.fx.isna(),aligned.return_usd.isna(),
                                  aligned.return_chf.isna()],
                                 ["PRIX_ABSENT","FX_ABSENT","BASE_PRIX_ABSENTE","BASE_FX_ABSENTE"],default="OK")
    return aligned


def disposition(row, policy):
    """Every positive assertion must be documented for the portfolio and date."""
    reasons = []
    if row["role"] != "instrument":
        return ["ROLE_NON_INVESTISSABLE"]
    if row.get("available") is None or pd.isna(row["available"]) or pd.Timestamp(row["available"]) > pd.Timestamp(policy["decision_utc"]):
        reasons.append("SOURCE_INDISPONIBLE")
    if row.get("ended"):
        reasons.append("SORTIE_OBSERVEE")
    checks = {"identified":"IDENTITE", "mandate_scope":"PERIMETRE_US", "listed":"NEGOCIABILITE",
              "access":"ACCES_COMPTE","lot":"LOT","settlement":"REGLEMENT","liquid":"LIQUIDITE_ORDRE",
              "fees":"FRAIS","distinct":"DOUBLON", "class_terms":"CONDITIONS_CLASSE"}
    reasons.extend(code for field,code in checks.items() if row.get(field) is not True)
    if row.get("price_day") != policy["last_closed_us_session"]:
        reasons.append("PRIX_NON_FRAIS")
    if row.get("currency") != "CHF" and row.get("fx_day") != policy["last_closed_us_session"]:
        reasons.append("FX_NON_FRAIS")
    if row.get("history", 0) < policy["risk_months_required"]:
        reasons.append("HISTORIQUE_RISQUE")
    return reasons


def exposure(weights, holdings, direct, instant):
    if any(not math.isfinite(w) or w < 0 for w in weights.values()) or not math.isclose(sum(weights.values()),1):
        raise ValueError("Long weight of sum one required")
    totals = {}
    unknown_gross = residual = 0.
    for asset, weight in weights.items():
        if asset in direct:
            issuer = direct[asset]
            totals[issuer] = totals.get(issuer,0) + weight
            continue
        subset = holdings[holdings.fund == asset]
        editions = subset[["fund","day","available"]].drop_duplicates()
        snapshot = visible(editions, instant, ["fund"])
        if snapshot.empty:
            unknown_gross += weight
            residual += weight
            continue
        chosen = snapshot.iloc[0]
        lines = subset[(subset.day == chosen.day) & (subset.available == chosen.available)]
        balance = 1 - lines.weight.sum()
        unknown_gross += weight * (abs(balance) + lines.loc[lines.issuer.isna(),"weight"].abs().sum())
        residual += weight * (balance + lines.loc[lines.issuer.isna(),"weight"].sum())
        for issuer, part in lines.dropna(subset=["issuer"]).groupby("issuer").weight.sum().items():
            totals[issuer] = totals.get(issuer,0) + weight * part
    return dict(issuers=totals, unknown_net=residual, unknown_gross=unknown_gross)


def exclusion_status(result, forbidden, mandatory):
    if any(result["issuers"].get(i,0) > 1e-12 for i in forbidden):
        return "excluded" if mandatory else "preference not satisfied"
    if forbidden and result["unknown_gross"] > 1e-10:
        return "suspendu" if mandatory else "partial coverage"
    return "verified"


def corporate_return(previous, closing, dividend, shares_per_old):
    """Unadjusted prices, cash dividend per new share, split effective first."""
    if previous <= 0 or shares_per_old <= 0:
        raise ValueError("Invalid event base")
    return (closing + dividend) * shares_per_old / previous - 1
