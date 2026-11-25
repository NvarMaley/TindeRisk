"""Precompute non-personal default research configurations locally."""
import argparse
from datetime import date
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from riskmatch.optimization.mean_variance_report import cached_report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--as-of',default=str(date.today()));p.add_argument('--scope',choices=('core','cohort','all'),default='all');p.add_argument('--currency',choices=('USD','CHF','all'),default='all');a=p.parse_args()
    for currency in ('USD','CHF') if a.currency=='all' else (a.currency,):
        for scope in ('cohort','core') if a.scope=='all' else (a.scope,):
            r=cached_report(ROOT,{'as_of':a.as_of,'scope':scope,'currency':currency});print(currency,scope,r['status'],r.get('asset_count'),{k:v['status'] for k,v in r.get('models',{}).items()},flush=True)
