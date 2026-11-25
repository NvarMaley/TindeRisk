"""Precompute only non-client default BL research settings."""
from datetime import date
from pathlib import Path
import sys,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from riskmatch.optimization.black_litterman_report import cached_report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--as-of',default=str(date.today()));a=p.parse_args()
    for currency in ('USD','CHF'):
        for scope in ('cohort','core'):
            r=cached_report(ROOT,{'as_of':a.as_of,'currency':currency,'scope':scope});print(currency,scope,r['assets'],r['anchor'],{k:v['status'] for k,v in r['models'].items()},flush=True)
