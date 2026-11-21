"""CHF demonstration rules. Reserves and invested positions are accounted for separately."""
from math import sqrt


def example():
    return dict(project="Down payment", currency="CHF", capital=50000, horizon=8,
                goal=None, wish=None, contribution=0, withdraw=15000, due=24, flexible=False,
                external=0, saving=0, household="Covered elsewhere", safety=0, variable=False,
                employer=False, ethics="", strict=False, cap=12.)


def reserve(m, months=None, saving=None):
    months = m["due"] if months is None else months
    saving = m["saving"] if saving is None else saving
    return max(0., m["withdraw"]-m["external"]-months*saving)


def capacity(m, answers):
    missing = any(m[k] is None for k in ("capital","withdraw","horizon","external","saving","due","safety","cap"))
    reasons = []
    if missing or m["household"] == "Unknown":
        reasons.append("Specify the amounts, deadline, risk cap and household reserve.")
    if m["currency"] != "CHF":
        reasons.append("This catalogue covers CHF goals only.")
    if m["strict"] or answers.get("F06")==0:
        reasons.append("The available dated ETF holdings cannot verify your exclusion.")
    if answers.get("F03") in (1,2) and not m["safety"]:
        reasons.append("Enter the amount of the investment needed for household expenses.")
    if m["saving"] and answers.get("F04") in (1,2,3,-1):
        reasons.append("Confirm the contributions you can rely on for the withdrawal or set them to zero.")
    if answers.get("B03")==0 and m["withdraw"] == 0:
        reasons.append("An expense is coming up. Enter its amount and date.")
    if not missing and m["withdraw"] > 0 and m["due"] > 12*m["horizon"]:
        reasons.append("The withdrawal falls after your investment horizon. Check both dates.")
    if answers.get("F01") in (0,1,2) and m["capital"] and m["withdraw"] is not None:
        fraction = m["withdraw"]/m["capital"]
        band = 0 if fraction < .25 else 1 if fraction <= .5 else 2
        if band != answers["F01"]:
            reasons.append("The withdrawal share on the card differs from the amount you entered.")
    if missing:
        return dict(reasons=reasons, reserve=None, free=None)
    needed = reserve(m)+m["safety"]
    free = m["capital"]-needed
    if free <= 0:
        reasons.append("Your reserves use all available capital.")
    return dict(reasons=reasons, reserve=needed, free=max(0., free))


def growth_value(initial, monthly, years, rate):
    factor = (1+rate)**(1/12)
    months = years*12
    annuity = months if abs(rate)<1e-12 else ((1+rate)**years-1)/(factor-1)
    return initial*(1+rate)**years + monthly*annuity


def required_rate(initial, monthly, years, target):
    if target is None or target <= 0 or initial is None or (initial<=0 and not monthly) or not years or monthly is None:
        return None
    low, high = -.99, 1.
    if not growth_value(initial,monthly,years,low) <= target <= growth_value(initial,monthly,years,high):
        return None
    for _ in range(60):
        mid = (low+high)/2
        if growth_value(initial,monthly,years,mid)<target:
            low = mid
        else:
            high = mid
    return (low+high)/2


def compare(m, cap, profile, catalogue):
    if cap["reasons"] or profile["lo"] is None:
        return []
    allowed = [r for r in catalogue["frontier"] if r["risk"] <= m["cap"]/100+1e-6]
    if not allowed:
        return []
    # A clear advantage allows for a caution as steadfast as cash.
    def select(phi):
        return max(allowed, key=lambda r: r["net"]-phi*r["risk"]**2/2)
    low = select(profile["hi"]) if profile["hi"] is not None else allowed[0]
    high = select(profile["lo"])
    if low is high:
        # Show an explicit compromise below the chosen point if the two boundaries coincide.
        lower = [r for r in allowed if r["risk"] <= high["risk"]*.75]
        if lower:
            low = lower[-1]
    return [low] if low is high else [low,high]


def positions(amount, row, fee):
    invested = amount/(1+fee*sum(row["weights"][:3]))
    return [invested*w for w in row["weights"]]


def review(m, cap, row, market, month, new_due):
    if not 0 <= month <= new_due <= m["due"] or month >= len(market["replay"]):
        raise ValueError("Withdrawal date incompatible with the review")
    prices = market["replay"][month]["relative"]
    initial = positions(cap["free"], row, market["fee"])
    before = [q*p for q,p in zip(initial,prices,strict=True)]
    extra = reserve(m,new_due)-reserve(m)
    cash = min(extra,before[-1])
    etfs = sum(before[:3])
    sale = min(etfs,(extra-cash)/(1-market["fee"]))
    cost = sale*market["fee"]
    secured = cash+sale-cost
    after = [x*(1-sale/etfs) if etfs else 0. for x in before[:3]]+[before[-1]-cash]
    def risk(assets, restricted):
        denom = sum(assets)+restricted
        variance = sum(x*y*market["cov"][i][j] for i,x in enumerate(assets) for j,y in enumerate(assets))
        return sqrt(max(0.,variance))/denom if denom else 0.
    return dict(date=market["replay"][month]["date"], before=before, after=after,
                reserve_before=cap["reserve"], reserve_after=cap["reserve"]+secured, extra=extra,
                cash=cash,sale=sale,cost=cost,uncovered=max(0.,extra-secured),
                risk_before=risk(before,cap["reserve"]),risk_after=risk(after,cap["reserve"]+secured))
