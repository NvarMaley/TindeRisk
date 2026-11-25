"""Source acquisition readiness; no source availability grants investability or rights."""

from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
import stat
from pathlib import Path

from .source_inventory import inventory_counts, inventory_snapshot
from .local_sources import new_data_root, monthly_audit, daily_audit, audit_available_for_as_of, treasury_identity_summary, issuer_holdings_summary, fedinvest_summary

ROOT=Path(__file__).resolve().parents[3]


def catalog():
    result=json.loads((ROOT/"configs/source_catalog.json").read_text())
    if len({r["id"] for r in result["entries"]})!=len(result["entries"]):raise ValueError("Duplicate source ID")
    return result


@dataclass(frozen=True)
class ProviderRequest:
    provider: str
    dataset_version: str
    as_of: date

    def __post_init__(self):
        if not self.provider or not self.dataset_version:raise ValueError("Missing provider/version")


def request_snapshot(request, adapters=None, *, root=ROOT):
    """Explicit adapters only. Unavailable providers return a diagnostic, never synthetic substitutes."""
    if adapters is None:
        return inventory_snapshot(Path(root)/"data/processed/universe/source_inventory.duckdb", request)
    adapter=adapters.get(request.provider)
    if adapter is None:return {"status":"provider_unavailable","provider":request.provider,"dataset_version":request.dataset_version,"as_of":request.as_of.isoformat()}
    return adapter(request)


def public_receipts(root=ROOT, as_of=None):
    """Verify the small immutable local public-download receipts, not raw WRDS data."""
    as_of=as_of or date.today();found={};base=Path(root)/"data/raw/public_universe"
    if not base.is_dir():return found
    for path in sorted(base.glob("*/receipt-*.json")):
        try:
            if getattr(path.stat(),"st_flags",0)&getattr(stat,"SF_DATALESS",0x40000000):continue
            receipt=json.loads(path.read_text());stamp=datetime.fromisoformat(receipt["acquired_at_utc"])
            if receipt["schema"]!="public-source-receipt-v1" or stamp.date()>as_of:continue
            for row in receipt["datasets"]:
                if row["status"]!="downloaded_schema_checked_not_normalized":continue
                verified=True
                for file in row["files"]:
                    if Path(file["file"]).name!=file["file"]:raise ValueError("Invalid receipt path")
                    p=path.parent/file["file"]
                    info=p.stat()
                    if info.st_size!=file["size"] or file["size"]>20_000_000:raise ValueError("Public receipt size mismatch")
                    if getattr(info,"st_flags",0)&getattr(stat,"SF_DATALESS",0x40000000):
                        verified=False;continue
                    if hashlib.sha256(p.read_bytes()).hexdigest()!=file["sha256"]:raise ValueError("Public receipt fingerprint mismatch")
                previous=found.get(row["dataset"])
                if previous is None or stamp.isoformat()>previous["acquired_at"]:
                    found[row["dataset"]]={"rows":row["rows"],"first":row["first_record"],"last":row["last_record"],"acquired_at":stamp.isoformat(),"status":row["status"],"kind":row["kind"],"verification":"hash_checked" if verified else "receipt_only_cloud_placeholder"}
        except (OSError,ValueError,KeyError,TypeError):continue
    return found


def source_report(as_of, root=ROOT):
    root=Path(root);meta=catalog();new=new_data_root(root);monthly=audit_available_for_as_of(monthly_audit(root),as_of);daily=audit_available_for_as_of(daily_audit(root),as_of)
    public=public_receipts(root,as_of)
    treasury=treasury_identity_summary(as_of,root);holdings=issuer_holdings_summary(as_of,root);fed=fedinvest_summary(as_of,root)
    def present(path):return bool(new and (new/path).is_file())
    available={
      "ETF_DAILY":("local_partial" if daily or present("data_plus/raw/wrds/crsp_dsf.csv") else "missing", f"CRSP daily {daily['observed_etfs']}/{len(daily['etf'])}; no volume field; ends 2025" if daily else "Daily CRSP audit pending"),
      "ETF_MONTHLY":("local_partial" if monthly or present("data_plus/raw/wrds/crsp_msf.csv") else "missing",f"{monthly['observed_etfs']}/{len(monthly['etf'])} monthly ETF histories through 2025" if monthly else "Monthly audit pending"),
      "EQUITY_MASTER":("local_partial" if monthly or present("data_plus/raw/wrds/crsp_msf.csv") else "missing",f"{monthly['stock_candidate_count']} raw classified candidates; {monthly['selected_count']} ranked locally at {monthly['snapshot_date']}" if monthly else "Monthly audit pending"),
      "ETF_HOLDINGS":("local_partial" if holdings else "missing", f"{len(holdings)}/5 current issuer snapshots audited; strict rule blocks reported money-market shares; historical holdings still missing" if holdings else "No verified dated Treasury ETF holding snapshots"),
      "FUNDAMENTALS":("local_partial" if present("data_plus/raw/wrds/comp_funda.csv") else "missing","Annual export lacks verified release/revision history"),
      "LINKS":("local_partial" if present("data_plus/raw/wrds/ccm_lnkhist.csv") else "missing","CCM dated links present; validate types and overlaps"),
      "TREASURY_MASTER":("public_downloaded" if treasury or any(k in public for k in ("auctions_query","treasury_securities_auctions_v2")) else "missing",f"{sum(treasury['historical_by_type'].values())} historical CUSIPs; {sum(treasury['not_matured_by_type'].values())} non-matured candidates; no secondary prices" if treasury else "Auction identity metadata, not secondary-market quotes"),
      "TREASURY_DAILY":("local_partial" if fed else "missing",f"FedInvest: {fed['days']} dated snapshots, {fed['scope_positive_eod']} positive in-scope valuation observations; historical completeness and execution pricing unverified" if fed else "No individual daily secondary-market prices verified"),
      "RATES_FX":("public_downloaded" if any(k.startswith("fred_rates") for k in public) else "local_partial","Latest-vintage rates/FX; PIT lag and cash conversion not validated"),
      "MACRO_VINTAGES":("local_partial","Existing local macro/vintage inputs; complete release and revision coverage pending"),
      "FACTORS":("local_partial" if new and (new/"data_plus/raw/factors").is_dir() else "missing","Local factor archives; definitions and final dates require validation"),
      "BENCHMARKS":("local_partial","Local CRSP index columns and ETF proxies; historical index weights missing"),
      "FUTURES":("missing","No verified contract-level settlement/volume/OI/margin history"),
      "COSTS_LIQUIDITY":("local_partial" if daily or present("data_plus/raw/wrds/crsp_dsf.csv") else "missing","Bid/ask present; daily volume, dated fund expenses and execution assumptions missing"),
      "SENTIMENT":("local_partial" if present("data1/processed/sentiment_firm_daily.parquet") else "missing","Historical course StockTwits archive 2009–2020; strictly lagged historical research only; no current signal"),
    }
    audit_dir = root / "data/processed/universe"
    def local_audit(name):
        try:
            return audit_available_for_as_of(json.loads((audit_dir / name).read_text()), as_of) or {}
        except (OSError, ValueError):
            return {}

    delivery = local_audit("wrds_delivery.json").get("tables", {})
    folders = [p for p in (root / "data").glob("telecharger*") if p.name.strip() == "telecharger"]
    def current(table):
        item = delivery.get(table, {})
        if len(folders) != 1 or not item or Path(item["file"]).name != item["file"]:
            return None
        try:
            info = (folders[0] / item["file"]).stat()
            if (info.st_size, info.st_mtime_ns) == (item["size"], item["mtime_ns"]):
                return item
        except OSError:
            pass
        return None

    supplement = current("daily_supplement")
    if supplement:
        evidence = f"{supplement['rows']:,} WRDS supplement rows through {supplement['last']}; {supplement['populated_volume']:,} populated volume fields. PERMNO/date reconciliation pending."
        available["ETF_DAILY"] = ("local_partial", evidence)
        available["COSTS_LIQUIDITY"] = ("local_partial", evidence)
    joined = local_audit("etf_daily_volume.json")
    if supplement and joined and (audit_dir / "etf_daily_volume.csv.gz").is_file():
        detail = f"{joined['matched']:,} daily ETF keys matched across {len(joined['by_ticker'])} funds with return agreement and volume. Ends {supplement['last']}."
        available["ETF_DAILY"] = ("local_partial", detail)
        available["COSTS_LIQUIDITY"] = ("local_partial", detail + " Dated expenses and AUM pending.")
    treasury_data = local_audit("treasury_supplements.json")
    if treasury_data:
        available["TREASURY_MASTER"] = ("local_partial", f"{treasury_data['monthly_statements']} monthly statements; {treasury_data['latest_positive_issues']} issues with positive balances at {treasury_data['latest_statement']}.")
        available["TREASURY_DAILY"] = ("local_partial", available["TREASURY_DAILY"][1] + f". {treasury_data['tips_issues']} TIPS with ratios; {len(treasury_data['archives'])} separately archived third-party historical sources.")
    quarter = current("quarterly")
    if quarter:
        available["FUNDAMENTALS"] = ("local_partial", f"{quarter['rows']:,} quarterly rows. Release dates and restatements require validation.")
    if current("links"):
        available["LINKS"] = ("local_partial", "Dated CCM links audited; historical overlap checks pending.")
    ranking = local_audit("monthly_stock_candidates.json")
    if ranking and (audit_dir / "monthly_stock_candidates.csv.gz").is_file():
        available["EQUITY_MASTER"] = ("local_partial", f"{ranking['months']} month-end candidate rankings ({ranking['first']} to {ranking['last']}); execution and PIT validation pending.")
    if "cftc_legacy_futures_only" in public:
        count = public["cftc_legacy_futures_only"]["rows"]
        available["FUTURES"] = ("local_partial", f"{count:,} weekly CFTC market observations across ten families. Settlement histories by expiry still required.")
    spot = [public[key] for key in ("CBBTCUSD", "CBETHUSD") if key in public]
    available["CRYPTO_SPOT"] = ("local_partial" if spot else "missing", f"{len(spot)}/2 spot series acquired. Research candidates only.")
    extensions = local_audit("research_extensions.json")
    translations = {}
    def research(category, english, french):
        available[category] = ("local_partial", english)
        translations[category] = french

    futures = extensions.get("futures")
    if futures:
        fields = (futures["roots"], futures["months"], futures["last"])
        research("FUTURES",
                 "%s roots, %s selected contract months through %s. Settlement, volume, open interest and margins remain incomplete." % fields,
                 "%s familles, %s mois de contrat distincts jusqu’au %s. Cours de compensation, volumes, positions ouvertes et marges restent incomplets." % fields)
    positions = extensions.get("holdings")
    if positions:
        fields = (positions["filings"], positions["funds"], positions.get("verified_filings", 0))
        research("ETF_HOLDINGS",
                 "%s filing records across %s funds. Holdings retrieved from quarterly files for %s filings. Treasury-only eligibility requires dated review." % fields,
                 "%s déclarations pour %s ETF. Positions retrouvées dans les archives trimestrielles pour %s déclarations. Le filtre obligations d’État reste à vérifier à chaque date." % fields)
        flagged = positions.get("filings_with_non_ust_short_term_vehicle")
        if flagged is not None:
            research("ETF_HOLDINGS",available["ETF_HOLDINGS"][1] + f" {flagged} filings include non-Treasury short-term vehicles.",
                     translations["ETF_HOLDINGS"] + f" {flagged} déclarations contiennent un placement à court terme émis par un tiers.")
    nav = extensions.get("nav")
    if nav:
        fields = (nav["funds"], nav["last"])
        research("ETF_DAILY",
                 available["ETF_DAILY"][1] + " Daily issuer NAV for %s ETFs through %s." % fields,
                 "Valeur liquidative quotidienne de %s ETF jusqu’au %s. Les cours de marché et les distributions se contrôlent séparément." % fields)
    bars = extensions.get("bars")
    if bars:
        fields = (bars["cohort_any"], bars["days"], bars["first"], bars["last"])
        research("EQUITY_MASTER",
                 available["EQUITY_MASTER"][1] + " Public ticker matches for %s candidates over %s sessions (%s to %s). Identifier continuity remains open." % fields,
                 "%s candidats retrouvés par symbole sur %s séances dans l’archive (%s au %s). La continuité des identifiants reste à vérifier." % fields)
        baseline = available["ETF_DAILY"][1]
        minimum = min(bars["etf_days"].values(),default=0)
        fields = (len(bars["etf_days"]),minimum,bars["days"])
        research("ETF_DAILY",baseline + " Market bars: %s ETFs, minimum %s of %s observed sessions per ETF." % fields,
                 (translations.get("ETF_DAILY") or "") + " Cours et volumes : %s ETF, au moins %s séances sur %s par ETF." % fields)
    fees = extensions.get("fees")
    if fees:
        fields = (fees["funds"],fees["changes"])
        en = "%s ETF fee readings and %s dated changes. " % fields
        fr = "%s ETF avec relevé de frais et %s changements datés. " % fields
        if fees.get("issuer_mdy"):
            en += "Separate MDY gross fee at " + fees["issuer_mdy"] + "."
            fr += "Frais bruts de MDY vérifiés séparément au " + fees["issuer_mdy"] + "."
        research("COSTS_LIQUIDITY", en, fr)
    benchmark = extensions.get("index_membership")
    if benchmark:
        fields = (benchmark["snapshots"],benchmark["first"],benchmark["last"])
        research("BENCHMARKS","%s public S&P 500 membership snapshots, %s to %s. Timing, weights and other indices require review." % fields,
                 "%s compositions historiques du S&P 500, du %s au %s. Horaires, pondérations et autres indices à vérifier." % fields)
    valuations = local_audit("treasury_sessions.json")
    if valuations:
        fields = (valuations["observed_ends"],valuations["expected_ends"],valuations["days"],valuations["last"])
        research("TREASURY_DAILY","%s/%s curve month ends with identified positive Treasury marks; %s official dates through %s. Cash flows and executable spreads pending." % fields,
                 "%s/%s fins de mois avec valorisation positive d’un titre identifié ; %s dates officielles jusqu’au %s. Coupons et fourchettes exécutables à valider." % fields)
    macro = extensions.get("macro_vintages")
    if macro:
        fields = (sum(macro.values()),len(macro))
        research("MACRO_VINTAGES",
                 "%s vintage columns for %s US indicators from the Philadelphia Fed. Release cutoffs require validation." % fields,
                 "%s versions datées pour %s indicateurs américains de la Fed de Philadelphie. Les horaires de publication restent à vérifier." % fields)
    filings = extensions.get("as_filed")
    if filings:
        fields = (filings["annual_matches"], filings["quarterly_matches"], filings["last"])
        research("FUNDAMENTALS",
                 "%s annual and %s quarterly periods matched to SEC filing timestamps through %s. Original Compustat value vintages unverified." % fields,
                 "%s périodes annuelles et %s trimestrielles reliées aux dates de dépôt SEC jusqu’au %s. Les versions historiques des valeurs Compustat restent à vérifier." % fields)
    facts = extensions.get("original_facts")
    if facts and filings:
        count = sum(r["rows"] for r in facts.values())
        research("FUNDAMENTALS",available["FUNDAMENTALS"][1] + f" {count:,} linked original XBRL fact rows.",
                 translations["FUNDAMENTALS"] + f" {count:,} valeurs XBRL originales reliées aux dépôts.")
    liquidity = extensions.get("liquidity")
    if liquidity:
        fields = (liquidity["above_turnover_proxy"],liquidity["funds"],liquidity["as_of"])
        english = "%s/%s ETFs above the USD 1m last-20-session turnover proxy at %s." % fields
        french = "%s/%s ETF dépassent le seuil de 1 M USD échangé par séance sur 20 séances au %s." % fields
        if fees:
            english += " " + available["COSTS_LIQUIDITY"][1]
            french += " " + translations["COSTS_LIQUIDITY"]
        research("COSTS_LIQUIDITY",english,french)
    crypto = extensions.get("crypto")
    if crypto and all(t in crypto for t in ("BTC-USD","ETH-USD")):
        fields = (crypto["BTC-USD"]["days"],crypto["ETH-USD"]["days"],crypto["ETH-USD"]["missing"])
        research("CRYPTO_SPOT","Coinbase Exchange spot OHLCV: %s BTC/USD and %s ETH/USD UTC days; %s missing ETH days." % fields,
                 "Coinbase Exchange au comptant : %s jours BTC/USD et %s jours ETH/USD en UTC, dont %s dates ETH absentes du calendrier." % fields)
    windows = local_audit("research_window_summary.json")
    if windows:
        for category,english,french in [
            ("ETF_DAILY",f"{windows['bridge']}/{windows['products']} closing prices reconciled on the December 2025 boundary.",f"{windows['bridge']}/{windows['products']} cours de clôture concordent au raccord de décembre 2025."),
            ("EQUITY_MASTER",f"{windows['stock_gaps']} missing next-month returns among {windows['stock_rows']} ranked observations.",f"{windows['stock_gaps']} rendements du mois suivant manquent sur {windows['stock_rows']} observations classées."),
            ("TREASURY_DAILY",f"{windows['issues_with_marks']} issues have official marks. {windows['schedules']} nominal issues have contractual schedules.",f"{windows['issues_with_marks']} titres ont des valorisations officielles. {windows['schedules']} titres nominaux ont un échéancier contractuel.")
        ]:
            research(category,available[category][1]+" "+english,(translations.get(category) or "")+" "+french)
    rows=[]
    for row in meta["entries"]:
        status,evidence=available[row["id"]];rows.append(row|{"status":status,"evidence":evidence,"evidence_fr":translations.get(row["id"]),"allocation_approved":False})
    return {"inventory":inventory_counts(Path(root)/"data/processed/universe/source_inventory.duckdb",as_of), "version":meta["version"],"as_of":as_of.isoformat(),"rows":rows,"public_receipts":public,"treasury_identity":treasury,"issuer_holdings":holdings,
            "rights_policy":"local_only_pending_entitlement_and_redistribution_review","approved_for_allocation":0}
