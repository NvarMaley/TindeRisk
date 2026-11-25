"""Download public FedInvest valuation snapshots; never substitute for executable quotes."""
import argparse
from collections import Counter
import csv
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
import http.cookiejar
import io
import json
import re
import time
from urllib.parse import urlencode
from urllib.request import build_opener, HTTPCookieProcessor, Request
from urllib.error import HTTPError

from fetch_public_universe_data import ROOT, immutable_save

URL = "https://www.treasurydirect.gov/GA-FI/FedInvest/selectSecurityPriceDate"
HEADER = ["CUSIP", "SECURITY TYPE", "RATE", "MATURITY DATE", "CALL DATE", "BUY", "SELL", "END OF DAY"]


class Tables(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows=[]; self.row=None; self.cell=None
    def handle_starttag(self, tag, attrs):
        if tag == 'tr': self.row=[]
        elif tag in {'td','th'} and self.row is not None: self.cell=[]
    def handle_data(self, data):
        if self.cell is not None: self.cell.append(data)
    def handle_endtag(self, tag):
        if tag in {'td','th'} and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split())); self.cell=None
        elif tag == 'tr' and self.row is not None:
            self.rows.append(self.row); self.row=None


def parse(raw, day):
    page=raw.decode('latin1'); parser=Tables(); parser.feed(page)
    if HEADER not in parser.rows: raise ValueError('Pricing table missing')
    rows=[]; seen=set()
    for row in parser.rows[parser.rows.index(HEADER)+1:]:
        if len(row)!=8 or not re.fullmatch(r'[0-9A-Z]{9}', row[0]): continue
        if row[0] in seen: raise ValueError('Duplicate CUSIP within date')
        seen.add(row[0]); rows.append(row)
    if not rows: raise ValueError('No security prices')
    # Verify the report date from descriptive page text, not from a maturity cell.
    stripped=re.sub(r'<[^>]+>', ' ', page)
    flat=' '.join(stripped.split())
    date_strings={day.isoformat(),day.strftime('%B %d, %Y'),day.strftime('%b %d, %Y'),f'{day.strftime("%B")} {day.day}, {day.year}',f'{day.strftime("%b")} {day.day}, {day.year}'}
    date_strings.update(f'{m}/{d}/{y}' for m in {str(day.month),f'{day.month:02}'} for d in {str(day.day),f'{day.day:02}'} for y in {str(day.year),f'{day.year%100:02}'})
    if not any(re.search(r'(?:prices?\s+(?:as\s+of|for|on)|(?:as\s+of|price|requested)\s+date)\s*:?\s*'+re.escape(s),flat,re.I) for s in date_strings):
        # Preserve diagnostic text on mismatch without accepting a wrongly dated report.
        idx=flat.lower().find('security prices'); raise ValueError('Report date not verified: '+flat[max(0,idx-20):idx+200])
    return rows


def fetch(day):
    opener=build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
    headers={'User-Agent':'RiskMatch academic local research/1.0'}
    with opener.open(Request(URL,headers=headers),timeout=30) as response:
        page=response.read(2_000_000).decode('latin1')
    token=re.search(r'name="_csrf" value="([^"]+)"',page)
    if not token: raise ValueError('Form schema changed')
    data=urlencode({'priceDate':day.isoformat(),'submit':'Show Prices','_csrf':token.group(1)}).encode()
    time.sleep(1)
    with opener.open(Request(URL,data=data,headers={**headers,'Referer':URL}),timeout=30) as response:
        if 'securityPriceDetail' not in response.url: raise ValueError('Unexpected pricing response')
        raw=response.read(2_000_001)
    if len(raw)>2_000_000: raise ValueError('Oversized report')
    return raw


def main():
    p=argparse.ArgumentParser(); p.add_argument('--date',action='append',type=date.fromisoformat,default=[]); p.add_argument('--start',type=date.fromisoformat); p.add_argument('--end',type=date.fromisoformat); p.add_argument('--limit',type=int,default=20); a=p.parse_args()
    days=set(a.date)
    if a.start and a.end:
        days.update(a.start+timedelta(days=n) for n in range((a.end-a.start).days+1) if (a.start+timedelta(days=n)).weekday()<5)
    if not days or min(days)<date(2008,9,2) or max(days)>=date.today() or not 1<=a.limit<=100: p.error('Supply dates from 2008-09-02 through yesterday; limit 1–100')
    root=ROOT/'data/raw/fedinvest'; processed=0
    for day in sorted(days,reverse=True):
        target=root/day.isoformat()
        if list(target.glob('receipt-*.json')): continue
        if processed>=a.limit: break
        processed+=1
        try:
            raw=fetch(day); rows=parse(raw,day)
            out=io.StringIO(); w=csv.writer(out); w.writerow(['date',*HEADER]); w.writerows([[day.isoformat(),*r] for r in rows])
            receipt={'date':day.isoformat(),'source':URL,'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),'rows':len(rows),'types':dict(Counter(r[1] for r in rows)),'file':immutable_save(target,'prices',out.getvalue().encode(),'csv'),'kind':'government valuation marks, not executable quotes'}
            immutable_save(target,'receipt',json.dumps(receipt,indent=2).encode(),'json'); print(day,len(rows),receipt['types'],flush=True)
        except HTTPError as e:
            print(day,'HTTP',e.code,flush=True); break
        except (OSError,ValueError) as e:
            print(day,'not acquired',str(e)[:350],flush=True)
        time.sleep(2)


if __name__=='__main__': main()
