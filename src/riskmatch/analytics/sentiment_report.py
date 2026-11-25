"""Local aggregate sentiment artifacts, never interpreted as current predictions."""
from datetime import date
from pathlib import Path
import hashlib
import json
from riskmatch.analytics.sentiment import VERSION


def sentiment_report(root,as_of):
    base=Path(root)/'data/processed/sentiment'
    try:
        r=json.loads((base/'report.json').read_text());up=json.loads((Path(root)/'data/processed/returns/report.json').read_text());key=r['run_id']
        if r['version']!=VERSION or r['return_id']!=up['return_id'] or date.fromisoformat(r['as_of'])>as_of or len(key)!=64 or any(c not in '0123456789abcdef' for c in key):return {'status':'unavailable','current_signal_available':False}
        with (base/key/'assets.json').open('rb') as f:
            if hashlib.file_digest(f,'sha256').hexdigest()!=r['file_hash']:return {'status':'unavailable','current_signal_available':False}
        return r
    except (OSError,ValueError,KeyError,TypeError):return {'status':'unavailable','current_signal_available':False}


def sentiment_asset(root,as_of,asset_id):
    if not isinstance(asset_id,str) or len(asset_id)>100:raise ValueError('Invalid asset')
    r=sentiment_report(root,as_of)
    if r['status']!='historical_only':return r
    a=json.loads((Path(root)/'data/processed/sentiment'/r['run_id']/'assets.json').read_text()).get(asset_id)
    return a or {'status':'unavailable','current_signal':None}
