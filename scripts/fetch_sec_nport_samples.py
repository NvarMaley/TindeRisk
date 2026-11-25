"""Targeted public SEC N-PORT examples, not a complete historical download.

An actual contact is required for declared SEC fair-access User-Agent.
"""
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import time
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from fetch_public_universe_data import immutable_save

ROOT=Path(__file__).resolve().parents[1]


def main():
    contact=os.getenv("SEC_CONTACT_EMAIL","").strip()
    if "@" not in contact or any(c.isspace() for c in contact):raise SystemExit("Set a real SEC_CONTACT_EMAIL for fair-access User-Agent; no requests made.")
    catalog=json.loads((ROOT/"configs/sec_nport_targets.json").read_text())
    root=ROOT/"data/raw/sec_nport"/date.today().isoformat();results=[]
    for t in catalog["targets"]:
        url=f"https://www.sec.gov/Archives/edgar/data/{t['cik']}/{t['sample_accession']}/primary_doc.xml"
        try:
            with urlopen(Request(url,headers={"User-Agent":f"RiskMatch research {contact}"}),timeout=30) as response:raw=response.read(5_000_001)
            if len(raw)>5_000_000:raise ValueError("Response exceeds bound")
            xml=ET.fromstring(raw);series={v.text.strip() for v in xml.iter() if v.tag.split("}")[-1].lower()=="seriesid" and v.text}
            if t["series_id"] not in series:raise ValueError("Wrong series identity")
            results.append({**t,"source":url,"status":"xml_identity_checked_not_historical_coverage","file":immutable_save(root,t['ticker']+"-"+t["sample_accession"],raw,"xml")});print(t["ticker"],"received",flush=True)
        except (OSError,ValueError,ET.ParseError) as exc:
            results.append({"ticker":t["ticker"],"status":"unavailable","error_type":type(exc).__name__});print(t["ticker"],"unavailable",type(exc).__name__,flush=True)
        time.sleep(1)
    immutable_save(root,"receipt",json.dumps({"schema":"sec-nport-sample-v1","acquired_at_utc":datetime.now(timezone.utc).isoformat(),"results":results},indent=2).encode(),"json")


if __name__=="__main__":main()
