"""Precompute public non-client strategy research configurations."""
from datetime import date
from pathlib import Path
import sys,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from riskmatch.strategies.long_only_report import cached_report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--as-of',default=str(date.today()));a=p.parse_args()
    for currency in ('USD','CHF'):
        for scope in ('cohort','core'):
            r=cached_report(ROOT,{'as_of':a.as_of,'currency':currency,'scope':scope});print(currency,scope,r['status'],{k:v['status'] for k,v in r.get('strategies',{}).items()},r.get('fundamental_rows'),flush=True)
