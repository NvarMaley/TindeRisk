"""Verify downloaded file fingerprints and publish only aggregate coverage to the local app."""

from datetime import date
import gzip
import hashlib
import json
from pathlib import Path
import tempfile

from fetch_public_universe_data import ROOT

RAW = ROOT / "data/raw"
DERIVED = ROOT / "data/processed/universe"


def latest(folder, pattern="receipt-*.json"):
    paths = list(folder.glob(pattern))
    if not paths:
        return None, None
    path = max(paths, key=lambda p: p.stat().st_mtime_ns)
    return path.parent, json.loads(path.read_text())


def check(folder, entry):
    name = entry["file"]
    if Path(name).name != name:
        raise ValueError("Invalid receipt path")
    path = folder / name
    with path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != entry["sha256"]:
            raise ValueError("Stored data fingerprint mismatch")
    return path


def main():
    summary = {"audited_on": date.today().isoformat()}
    folder, r = latest(RAW / "research_futures", "*/receipt-*.json")
    if r:
        for row in r["rows"]:
            check(folder, row["file"])
        summary["futures"] = {
            "roots": len(r["rows"]),
            "months": sum(row["contract_months"] for row in r["rows"]),
            "last": min(row["last"] for row in r["rows"]),
        }
    folder, r = latest(RAW / "issuer_nav")
    if r:
        for row in r["funds"]:
            check(folder, row["file"])
        summary["nav"] = {"funds": len(r["funds"]), "last": min(row["last"] for row in r["funds"])}
    folder, r = latest(RAW / "issuer_performance")
    if r and r["funds"]:
        for row in r["funds"]:
            check(folder, row["file"])
        summary["issuer_returns"] = {
            "funds": len(r["funds"]),
            "last": min(row["last"] for row in r["funds"]),
        }
    folder, r = latest(RAW / "public_equity_refresh")
    if r:
        check(folder, r["file"])
        summary["stock_sample"] = {"matches": r["ticker_matches"], "last": r["last"]}
    folder, r = latest(RAW / "public_market_history", "*/receipt-*.json")
    if r:
        check(folder, r["file"])
        summary["bars"] = {
            k: r[k]
            for k in (
                "rows",
                "days",
                "cohort_any",
                "cohort_all_sessions",
                "first",
                "last",
                "etf_days",
            )
        }
        for key in ("expected_days", "missing_days", "unexpected_days", "cohort_last", "invalid"):
            if key in r:
                summary["bars"][key] = r[key]
    folder, r = latest(RAW / "benchmark_membership")
    if r:
        check(folder, r["file"])
        summary["index_membership"] = {k: r[k] for k in ("snapshots", "first", "last")}
    folder, r = latest(RAW / "macro_vintages")
    if r:
        for row in r["series"]:
            check(folder, row["file"])
        summary["macro_vintages"] = {row["series"]: row["vintage_columns"] for row in r["series"]}
    folder, r = latest(RAW / "fund_fees")
    if r:
        for row in r["tables"].values():
            check(folder, row["file"])
        summary["fees"] = {
            "funds": r["tables"]["fund-fees"]["funds"],
            "changes": r["tables"]["fee-changes"]["rows"],
            "issuer_mdy": r["tables"].get("MDY", {}).get("as_of"),
        }
    folder, r = latest(RAW / "public_actions", "*/receipt-*.json")
    if r:
        for row in r["tables"].values():
            check(folder, row["file"])
        summary["actions"] = {
            k: {"rows": v["rows"], "invalid": v["invalid_factors"]} for k, v in r["tables"].items()
        }
    folder, r = latest(RAW / "nport_research_mirror")
    if r:
        seen = set()
        for fund in r["funds"]:
            check(folder, fund["filings"]["file"])
            with gzip.open(check(folder, fund["holdings"]["file"])) as f:
                seen.update((v["accession_number"], str(v["holding_id"])) for v in json.load(f))
        summary["holdings"] = {
            "funds": len(r["funds"]),
            "filings": sum(v["filings"]["rows"] for v in r["funds"]),
            "positions": len(seen),
        }
        qfolder, q = latest(RAW / "nport_accession_positions", "*/receipt-*.json")
        if q:
            verified = set()
            non_treasury = set()
            for chunk in q["quarters"]:
                if "file" not in chunk:
                    continue
                with gzip.open(check(qfolder, chunk["file"])) as f:
                    for v in json.load(f):
                        verified.add((v["accession_number"], str(v["holding_id"])))
                        if (
                            v["issuer_type"] != "UST"
                            and v["asset_cat"] == "STIV"
                            and float(v["percentage"] or 0) > 0
                        ):
                            non_treasury.add(v["accession_number"])
            summary["holdings"].update(
                verified_filings=len({a for a, _ in verified}),
                verified_positions=len(verified),
                filings_with_non_ust_short_term_vehicle=len(non_treasury),
            )
    folder, r = latest(DERIVED / "filing_dates")
    if r:
        for row in r["match"].values():
            check(folder, row["file"])
        summary["as_filed"] = {
            "filings": r["rows"],
            "last": r["last"],
            "annual_matches": r["match"]["annual"]["matched"],
            "quarterly_matches": r["match"]["quarterly"]["matched"],
        }
    folder, r = latest(DERIVED / "filing_dates", "facts-*.json")
    if r:
        for entry in r["tables"].values():
            check(folder, entry["file"])
        summary["original_facts"] = {
            k: {"filings": v["filings"], "rows": v["rows"]} for k, v in r["tables"].items()
        }
    folder, r = latest(DERIVED / "filing_reference")
    if r:
        for row in r["match"].values():
            check(folder, row["file"])
        summary["reference_dates"] = {
            "rows": r["rows"],
            "last": r["last"],
            "periods": {k: v["matched"] for k, v in r["match"].items()},
        }
    folder, r = latest(DERIVED / "market_matches", "identity-*.json")
    if r:
        check(folder, r["file"])
        summary["identity"] = {
            k: r[k] for k in ("cohort", "unique_cik", "unchanged_ticker_confirmed")
        }
    folder, r = latest(DERIVED / "nport_acceptance")
    if r:
        check(folder, r["file"])
        summary["holdings_acceptance"] = {"filings": r["filings"], "supported": r["supported"]}
    folder, receipt = latest(RAW / "crypto_bars")
    if receipt:
        for row in receipt["products"]:
            check(folder, row["file"])
        summary["crypto"] = {
            r["product"]: {"days": r["days"], "last": r["last"], "missing": len(r["missing_days"])}
            for r in receipt["products"]
        }
    folder, receipt = latest(RAW / "issuer_assets")
    if receipt:
        for row in receipt["funds"]:
            check(folder, row["file"])
        summary["issuer_assets"] = {
            "funds": len(receipt["funds"]),
            "dates": sorted({r["as_of"] for r in receipt["funds"]}),
        }
    folder, receipt = latest(DERIVED / "etf_liquidity")
    if receipt:
        check(folder, receipt["file"])
        summary["liquidity"] = {
            k: receipt[k]
            for k in (
                "funds",
                "as_of",
                "window_sessions",
                "above_turnover_proxy",
                "matched_issuer_nav",
                "above_aum",
                "max_abs_nav_gap_pct",
            )
        }
    folder, receipt = latest(RAW / "delisting_reference")
    if receipt:
        check(folder, receipt["file"])
        check(DERIVED / "market_matches", receipt["local_leads_file"])
        summary["delistings"] = {
            "events": receipt["rows"],
            "cohort_leads": receipt["candidate_leads"],
        }
    folder, receipt = latest(RAW / "cash_reference")
    if receipt:
        for row in receipt["series"]:
            check(folder, row["file"])
        summary["cash_reference"] = {
            r["symbol"]: {"days": r["days"], "last": r["last"], "unit": r["unit"]}
            for r in receipt["series"]
        }
    out = DERIVED / "research_extensions.json"
    with tempfile.NamedTemporaryFile(mode="w", dir=out.parent, delete=False) as stream:
        json.dump(summary, stream, indent=2)
    Path(stream.name).replace(out)
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
