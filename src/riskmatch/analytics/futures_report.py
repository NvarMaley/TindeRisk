"""Audit the ten archived source families; never promote to the active universe."""
from datetime import datetime,date
from pathlib import Path
from functools import lru_cache
from collections import defaultdict,Counter
import csv,gzip,hashlib,json,math,zipfile
import numpy as np
from riskmatch.analytics.futures import VERSION,Spec,Mark,valid_month,simulate,continuous_changes

ROOTS=('ES','NQ','RTY','ZT','ZF','ZN','ZB','CL','GC','6S')


def verified(folder,entry):
    name=entry['file'];p=folder/name
    if Path(name).name!=name or p.stat().st_size!=entry['size']:raise ValueError('Invalid source receipt')
    with p.open('rb') as f:
        if hashlib.file_digest(f,'sha256').hexdigest()!=entry['sha256']:raise ValueError('Source hash mismatch')
    return p


def month(s):return str(s).split('.')[0]


@lru_cache(maxsize=20)
def parse_source(path,mtime,size):
    """Use chronological snapshots, preserve negative prices and isolate quote conflicts."""
    grouped=defaultdict(list);months=set();negatives=0;conflicts=0
    with gzip.open(path,'rt',encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            stamp=datetime.fromisoformat(row['DATETIME']);quotes={};bad=set()
            for role in ('PRICE','FORWARD','CARRY'):
                c=month(row[role+'_CONTRACT']);raw=row[role]
                if not raw or not valid_month(c,stamp):continue
                try:p=float(raw)
                except ValueError:continue
                if not math.isfinite(p):continue
                months.add(c);negatives+=int(p<0)
                if c in quotes and not math.isclose(quotes[c],p,rel_tol=0,abs_tol=1e-9):bad.add(c)
                quotes[c]=p
            for c in bad:quotes.pop(c,None)
            conflicts+=len(bad);selected=month(row['PRICE_CONTRACT'])
            if selected in quotes:grouped[stamp.date()].append((stamp,selected,quotes))
    marks=[];unresolved=0;duplicates=0
    for day,items in sorted(grouped.items()):
        items.sort(key=lambda q:q[0]);stamp,c,quotes=items[-1]
        if len(items)>1 and items[-2][0]==stamp and items[-2][1:]!=items[-1][1:]:duplicates+=1;continue
        old=None;op=np_=rs=None
        if marks and marks[-1].contract!=c:
            old=marks[-1].contract
            # Latest same-day simultaneous quotes before observed switch to final role.
            first=next((k for k,x in enumerate(items) if x[1]==c),len(items));eligible=[x for x in items[:first] if x[1]==old and old in x[2] and c in x[2]]
            if eligible:
                rs,_,q=eligible[-1];op=q[old];np_=q[c]
            else:unresolved+=1
        marks.append(Mark(stamp,c,quotes[c],quotes,old,op,np_,rs))
    return tuple(marks),{'source_month_labels':len(months),'source_negative_role_quotes':negatives,'conflicting_role_quotes':conflicts,'conflicting_final_timestamps':duplicates,'unresolved_rolls_all_history':unresolved}


def source_calendar(folder,entry):
    if not entry or not entry.get('file'):return set()
    p=verified(folder,entry['file'])
    with p.open() as f:return {(datetime.fromisoformat(r['DATE_TIME']).date(),month(r['current_contract']),month(r['next_contract'])) for r in csv.DictReader(f)}


def summary(result):
    rows=result['ledger'];nav=np.array([result['initial_capital'],*[r['nav'] for r in rows]]);peak=np.maximum.accumulate(nav);dd=nav/peak-1
    return {k:v for k,v in result.items() if k not in ('ledger','rolls')}|{'return':float(nav[-1]/nav[0]-1),'max_drawdown':float(-dd.min()),'roll_count':len(result['rolls']),'maximum_gross_exposure':max((r['gross_exposure'] or 0 for r in rows),default=0.),'max_stressed_reserve_shortfall':max((r['stressed_reserve_shortfall'] for r in rows),default=0.),'margin_calls':sum(r['margin_call'] is not None for r in rows),'last':rows[-1]['date'] if rows else None,'nonzero_position_days':sum(r['quantity']!=0 for r in rows)}


def report(root,data):
    root=Path(root);as_of=date.fromisoformat(data['as_of']);start=date.fromisoformat(data.get('start','2022-01-01'));end=date.fromisoformat(data.get('end',str(as_of)));requested=data.get('root','ES');strategy=data.get('strategy','long');settings={k:data.get(k,v) for k,v in {'capital':1000000.,'target':.5,'gross_limit':1.5,'initial_margin':.10,'maintenance_margin':.075,'reserve':.20,'commission':2.,'slippage_ticks':1.,'cash_rate':0.,'margin_shock':1.5}.items()}
    if as_of>date.today() or not date(2010,1,1)<=start<end<=as_of or requested not in ROOTS or strategy not in ('long','short','trend') or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not np.isfinite(v) for v in settings.values()):raise ValueError('Invalid futures research request')
    if not 0<settings['capital']<=1e9 or not 0<=settings['target']<=settings['gross_limit']<=5 or not 0<settings['maintenance_margin']<=settings['initial_margin']<=1 or not 0<=settings['reserve']<1 or not 0<=settings['commission']<=1000 or not 0<=settings['slippage_ticks']<=100 or not -.1<=settings['cash_rate']<=.2 or not 1<=settings['margin_shock']<=5:raise ValueError('Invalid futures research settings')
    receipts=[]
    for p in (root/'data/raw/research_futures').glob('*/receipt-*.json'):
        r=json.loads(p.read_text());stamp=datetime.fromisoformat(r['acquired_at_utc']).date()
        if stamp<=as_of:receipts.append((stamp,p,r))
    if not receipts:raise ValueError('Archived local futures receipts unavailable')
    _,receipt,r=max(receipts,key=lambda v:(v[0],str(v[1])));folder=receipt.parent;rolls={}
    for p in sorted(folder.glob('roll-audit-*.json')):
        ra=json.loads(p.read_text())
        if datetime.fromisoformat(ra['acquired_at_utc']).date()<=as_of:rolls.update({q['root']:q for q in ra['rows']})
    with (root/'configs/futures_reference_specs.csv').open() as f:specs={q['root']:q for q in csv.DictReader(f)}
    sources={q['root']:q for q in r['rows']};families={};selected=None;returns={}
    for key in ROOTS:
        q=sources.get(key);s=specs.get(key)
        if not q or not s:families[key]={'status':'unavailable','reason':'Missing reference source'};continue
        p=verified(folder,q['file']);stat=p.stat();all_marks,audit=parse_source(str(p),stat.st_mtime_ns,stat.st_size);calendar=source_calendar(folder,rolls.get(key));spec=Spec(key,float(s['usd_per_price_unit']),float(s['outright_tick']),s['price_unit']);marks=[m for m in all_marks if start<=m.stamp.date()<=end];changes=continuous_changes(marks);roll_changes=[m for m in marks if m.roll_from];matched=sum((m.stamp.date(),m.roll_from,m.contract) in calendar for m in roll_changes);supported=sum(m.roll_stamp is not None for m in roll_changes)
        returns[key]={(a.stamp.date(),b.stamp.date()):changes[i]['change']/abs(a.price) for i,(a,b) in enumerate(zip(marks,marks[1:]),1) if changes[i]['change'] is not None and abs(a.price)>=spec.tick}
        meta={'status':'research_only','active':False,'source_first':q['first'],'source_last':q['last'],'source_contract_months':q['contract_months'],'sampled_marks':len(marks),'source_calendar_rows':len(calendar),'observed_roll_changes':len(roll_changes),'same_day_overlap_rolls':supported,'calendar_confirmed_rolls':matched,'reference_spec':{'multiplier':spec.multiplier,'tick':spec.tick,'tick_value':spec.multiplier*spec.tick,'price_unit':spec.unit,'source':s['source'],'review_date':s['reference_review_date'],'settlement_currency':'USD','actual_expiry':None,'last_trade_date':None,'historical_multiplier_verified':False},'audit':audit,'missing':['exchange settlement history','actual last trade and expiry dates','dated multiplier/spec history','per-expiry volume/open interest','historical initial/maintenance margin','executable bid/ask','delivery/CTD data']}
        if len(marks)<2:meta['simulation']={'status':'unavailable','reason':'Fewer than two archived marks in selected dates'};families[key]=meta;continue
        try:
            sim=simulate(marks,spec,**settings,strategy=strategy);meta['simulation']=summary(sim)
            if key==requested:
                doubled=simulate(marks,spec,**(settings|{'commission':settings['commission']*2,'slippage_ticks':settings['slippage_ticks']*2}),strategy=strategy);stress_margin={m.stamp.date():(min(1,settings['initial_margin']*settings['margin_shock']),min(1,settings['maintenance_margin']*settings['margin_shock'])) for m in marks};stress=simulate(marks,spec,**settings,strategy=strategy,margin_schedule=stress_margin);last=marks[-1];contracts=[{'contract_month':c[:6],'source_label':c,'contract_id':key+':'+c,'price':v,'notional_per_contract':abs(v)*spec.multiplier,'actual_expiry':None} for c,v in sorted(last.quotes.items())];selected={'root':key,'summary':summary(sim),'ledger':sim['ledger'],'rolls':sim['rolls'],'continuous_signal':changes,'latest_source_date':str(last.stamp.date()),'curve_contracts':contracts,'curve_gap':contracts[-1]['price']-contracts[0]['price'] if len(contracts)>1 else None,'cost_shock':summary(doubled),'margin_shock':summary(stress),'dv01':None,'beta':None,'basis':None,'risk_explanation':'Actual CTD/conversion factor and verified per-expiry settlement and synchronized spot reference unavailable. No certified DV01, beta or spot basis.'}
                if len(contracts)>1:
                    a,b=contracts[0]['contract_month'],contracts[-1]['contract_month'];months=(int(b[:4])-int(a[:4]))*12+int(b[4:])-int(a[4:]);selected['annualized_curve_gap_price_units']=selected['curve_gap']*12/months if months>0 else None
        except (ValueError,ArithmeticError) as e:meta['simulation']={'status':'unavailable','reason':str(e)}
        families[key]=meta
    if selected and 'ES' in returns:
        common=sorted(set(returns[requested])&set(returns['ES']));a=np.array([returns[requested][i] for i in common]);b=np.array([returns['ES'][i] for i in common]);var=float(np.var(b,ddof=1)) if len(b)>1 else 0.
        selected['conditional_beta_vs_es']=float(np.cov(a,b,ddof=1)[0,1]/var) if len(common)>=30 and var>1e-12 else None;selected['beta_observations']=len(common)
    # Separately verify the one-day licensed sample metadata; do not parse or use tick trades as settlements.
    sample=None
    for p in sorted((root/'data/raw/futures_samples').glob('receipt-*.json')):
        receipt_sample=json.loads(p.read_text())
        if datetime.fromisoformat(receipt_sample['acquired_at_utc']).date()<=as_of:
            verified(p.parent,receipt_sample['file']);sample={'date':receipt_sample['trade_sample_date'],'contracts':receipt_sample['contracts'],'status':'one_day_trade_sample_not_settlement_history'}
    return {'status':'experimental','approved':False,'version':VERSION,'as_of':str(as_of),'requested_start':str(start),'requested_end':str(end),'source_revision':r['revision'],'families':families,'selected':selected,'settings':settings,'strategy':strategy,'active_futures_count':0,'sample':sample,'warning':'Retrospective source-labelled research quotes, not certified exchange settlements or executable rolls. Present reference multipliers assumed historically stable, actual expiry/margin/liquidity not verified. Simulated collateral and costs are assumptions, archived marks end in 2024. No futures eligible for client portfolios or current hedging.'}
