"""Local audited marks and FRED par-rate receipts; no trade execution."""
from datetime import date,timedelta,datetime
from pathlib import Path
from functools import lru_cache
import csv,hashlib,json
from collections import Counter
import duckdb
import numpy as np
from riskmatch.analytics.treasury import VERSION,bootstrap,discount,schedule,yield_metrics,curve_metrics,holding_return,ladder,shift_month

SERIES={'DGS1MO':1/12,'DGS3MO':.25,'DGS2':2.,'DGS5':5.,'DGS10':10.,'DGS30':30.,'DFII5':5.,'DFII10':10.,'DFII30':30.}


@lru_cache(maxsize=16)
def hashsum(path,size,mtime):
    with open(path,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def verify(path,expected):
    stat=path.stat()
    if hashsum(str(path),stat.st_size,stat.st_mtime_ns)!=expected:raise ValueError('Source hash mismatch: '+path.name)
    return str(path)


def inputs(root):
    base=Path(root)/'data/processed/pit';r=json.loads((base/'report.json').read_text());folder=base/r['snapshot_id'];names=('treasury_identity','fedinvest_marks','tips_daily_index_ratios','tips_payments');files={}
    for name in names:
        e=next(x for x in r['datasets'] if x['dataset']==name);files[name]=verify(folder/(name+'.parquet'),e['file_hash'])
    return files,r['snapshot_id']


def par_curves(root,as_of):
    files={}
    for receipt in sorted((Path(root)/'data/raw/public_universe').glob('*/receipt-*.json')):
        r=json.loads(receipt.read_text());stamp=datetime.fromisoformat(r['acquired_at_utc']).date()
        if stamp>as_of:continue
        for d in r['datasets']:
            if d.get('series') in SERIES and d.get('status')=='downloaded_schema_checked_not_normalized':
                f=d['files'][0];s=d['series'];old=files.get(s)
                if old is None or stamp>=old[0]:files[s]=(stamp,receipt.parent/Path(f['file']).name,f['sha256'])
    if set(files)!=set(SERIES):raise ValueError('Missing dated curve receipts')
    data={}
    for s,(_,p,h) in files.items():
        verify(p,h)
        with p.open() as f:data[s]={date.fromisoformat(row['observation_date']):float(row[s])/100 for row in csv.DictReader(f) if row[s] not in ('','.','NaN') and date.fromisoformat(row['observation_date'])<=as_of}
    common=set.intersection(*(set(v) for v in data.values()))
    if not common:raise ValueError('No common curve observation')
    day=max(common);nom={SERIES[s]:data[s][day] for s in SERIES if s.startswith('DGS')};real={SERIES[s]:data[s][day] for s in SERIES if s.startswith('DFII')};curves={'nominal':bootstrap(nom),'real':bootstrap(real)}
    def rows(par,c):
        nodes=sorted(set(par)|{.5,1.,2.,5.,10.,20.,30.});out=[];last=0.;old=1.
        for t in nodes:
            df=float(discount(c,t));out.append({'tenor':t,'par_yield':par.get(t),'spot_continuous':float(-np.log(df)/t),'discount_factor':df,'forward_continuous':float(np.log(old/df)/(t-last))});last=t;old=df
        return out
    return curves,{'date':str(day),'age_days':(as_of-day).days,'nominal':rows(nom,curves['nominal']),'real':rows(real,curves['real']),'breakeven':[{'tenor':t,'par_breakeven':nom[t]-real[t],'spot_breakeven_continuous':float(np.log(discount(curves['real'],t)/discount(curves['nominal'],t))/t)} for t in sorted(real)],'slope_10y_2y':nom[10.]-nom[2.],'curvature_2_5_10':2*nom[5.]-nom[2.]-nom[10.],'warning':'Sparse latest-vintage par yield proxy: interpolated semiannual par bootstrap, real short end extrapolated, short nominal money-market proxy. Not official zero curve or PIT release series.'}


def auction_dates(root,as_of):
    """Only original normal-period auction records with matching coupon dates."""
    out={};conflicts=set()
    for receipt in (Path(root)/'data/raw/public_universe').glob('*/receipt-*.json'):
        r=json.loads(receipt.read_text())
        if datetime.fromisoformat(r['acquired_at_utc']).date()>as_of:continue
        for item in r['datasets']:
            if item['dataset']!='auctions_query' or item['status']!='downloaded_schema_checked_not_normalized':continue
            for f in item['files']:
                p=receipt.parent/Path(f['file']).name;verify(p,f['sha256'])
                for q in json.loads(p.read_text())['data']:
                    if q.get('reopening')!='No' or q.get('first_int_period')!='Normal':continue
                    try:
                        d,first,record=map(date.fromisoformat,(q['dated_date'],q['first_int_payment_date'],q['record_date']));issue=date.fromisoformat(q['issue_date']);mat=date.fromisoformat(q['maturity_date'])
                    except (ValueError,TypeError,KeyError):continue
                    if record>as_of or not d<=issue<first or first!=shift_month(d,6):continue
                    # EOM anchored at final maturity; check first date strictly.
                    months=(mat.year-first.year)*12+mat.month-first.month
                    if months<0 or months%6 or shift_month(mat,-months)!=first:continue
                    key=q['cusip'];v=(d,first)
                    if key in out and out[key]!=v:conflicts.add(key)
                    out[key]=v
    return {k:v for k,v in out.items() if k not in conflicts}


def valuation(row,curves,as_of,auction=None):
    cusip,kind,issue,maturity,coupon,mark,price,buy,sell,ratio=row
    out={'cusip':cusip,'type':kind,'issuer':'US Treasury','issue_date':str(issue),'maturity':str(maturity),'coupon_rate':coupon,'mark_date':str(mark) if mark else None,'status':'unavailable','day_count':'ACT/365 bill' if kind=='treasury_bill' else 'Actual/Actual coupon period','settlement':'mark date (research assumption, not actual trade settlement)','index_ratio':ratio if kind=='tips' else 1.}
    try:
        if mark is None or (as_of-mark).days>7 or mark>=maturity or price is None or price<=0:raise ValueError('Missing or stale valuation mark')
        if kind=='tips' and (ratio is None or ratio<=0):raise ValueError('Missing exact-date TIPS index ratio')
        ratio=ratio if kind=='tips' else 1.;flows,accrued=schedule(issue,maturity,mark,coupon,kind,auction[0] if auction else None);m=yield_metrics(flows,price,accrued,ratio);c=curve_metrics(flows,mark,m['dirty_per_100'],curves['real' if kind=='tips' else 'nominal'],ratio);spread=abs(buy-sell)*ratio if buy is not None and sell is not None and buy>0 and sell>0 else None
        out.update(m|c|{'status':'computed','yield_kind':'real (floor excluded)' if kind=='tips' else 'nominal semiannual equivalent','spread_per_100':spread,'spread_bps_of_dirty':spread/m['indexed_dirty_per_100']*10000 if spread is not None else None,'days_to_maturity':(maturity-mark).days,'flows':flows,'rate_shock_kind':'real' if kind=='tips' else 'nominal'})
        if kind=='treasury_bill':out['bill_discount_yield']=(100-price)/100*360/(maturity-mark).days;out['bill_investment_simple_yield']=(100/price-1)*365/(maturity-mark).days
        if kind=='tips':out['indexation_shock_1pct']=.01;out['maturity_floor']='max(100, 100 × future index ratio); future ratio unknown, real valuation excludes floor';out['indexed_principal_now']=100*ratio
        if auction:out['dated_date'],out['first_coupon_date']=map(str,auction)
    except (ValueError,TypeError,OverflowError) as e:out['reason']=str(e)
    return out


def history(db,files,row,auction=None):
    cid,kind,issue,maturity,coupon,mark,*_=row
    rows=db.execute('''select m.observation_date,m.eod_price,t.index_ratio from read_parquet(?) m left join read_parquet(?) t on m.instrument=t.instrument and m.observation_date=t.observation_date where m.instrument=? and m.observation_date<=? and m.observation_date<? order by m.observation_date desc limit 120''',[files['fedinvest_marks'],files['tips_daily_index_ratios'],cid,mark,maturity]).fetchall();rows=rows[::-1]
    paid={d:(c or 0)+(r or 0) for d,c,r in db.execute('select observation_date,indexed_coupon_per_100,redemption_per_100 from read_parquet(?) where instrument=? and observation_date<=?',[files['tips_payments'],cid,mark]).fetchall()} if kind=='tips' else {}
    out=[];prev=None
    for d,p,ratio in rows:
        try:
            if d<issue or p is None or p<=0 or kind=='tips' and (ratio is None or ratio<=0):raise ValueError('Missing mark')
            ratio=ratio if kind=='tips' else 1.;flows,a=schedule(issue,maturity,d,coupon,kind,auction[0] if auction else None);dirty=(p+a)*ratio;ret=None;cash=None
            if prev:
                pd,pp,pf=prev;events=[(t,cf) for t,cf,_ in pf if t<=d]
                if kind!='tips' or all(t in paid for t,_ in events):cash=sum(paid[t] if kind=='tips' else cf for t,cf in events);ret=holding_return(pp,dirty,cash)
            out.append({'date':str(d),'clean':p,'dirty_indexed':dirty,'cash':cash,'return':ret});prev=(d,dirty,flows)
        except (ValueError,TypeError):prev=None
    return out


def run_report(root,data):
    as_of=date.fromisoformat(data['as_of']);cid=data.get('cusip');capital=data.get('capital',10000.);cap=data.get('max_weight',.25);cost=data.get('cost_bps',10.);raw=data.get('liabilities');min_maturity=data.get('min_maturity_years',0.);max_maturity=data.get('max_maturity_years',30.);max_spread=data.get('max_spread_bps',100.)
    if as_of>date.today() or any(isinstance(v,bool) or not isinstance(v,(float,int)) or not np.isfinite(v) for v in (capital,cap,cost,min_maturity,max_maturity,max_spread)) or not 0<capital<=1e9 or not 0<cap<=1 or not 0<=cost<=200 or not 0<=min_maturity<=max_maturity<=30 or not 0<=max_spread<=1000:raise ValueError('Invalid Treasury settings')
    if cid is not None and (not isinstance(cid,str) or len(cid)!=9 or not cid.isalnum()):raise ValueError('Invalid CUSIP')
    duration_target=data.get('duration_target');duration_tolerance=data.get('duration_tolerance',.25);max_dv01=data.get('max_dv01')
    for v,maximum in ((duration_target,30),(duration_tolerance,30),(max_dv01,1e9)):
        if v is not None and (isinstance(v,bool) or not isinstance(v,(int,float)) or not np.isfinite(v) or not 0<=v<=maximum):raise ValueError('Invalid duration/DV01 constraint')
    if duration_tolerance is None:raise ValueError('Invalid duration tolerance')
    files,version=inputs(root);curves,curve=par_curves(root,as_of);auction=auction_dates(root,as_of)
    with duckdb.connect() as db:
        rows=db.execute('''with i as (select * from read_parquet(?) where issue_date<=? and maturity>? and (? is null or instrument=?)), m as (select * from read_parquet(?) where observation_date<=? and (availability_time is null or cast(availability_time as date)<=?) qualify row_number() over(partition by instrument order by observation_date desc)=1) select i.instrument,i.instrument_type,i.issue_date,i.maturity,i.coupon_rate_decimal,m.observation_date,m.eod_price,m.buy_mark,m.sell_mark,t.index_ratio from i left join m on i.instrument=m.instrument left join read_parquet(?) t on i.instrument=t.instrument and m.observation_date=t.observation_date order by i.maturity,i.instrument''',[files['treasury_identity'],as_of,as_of,cid,cid,files['fedinvest_marks'],as_of,as_of,files['tips_daily_index_ratios']]).fetchall();bonds=[valuation(r,curves,as_of,auction.get(r[0])) for r in rows]
        if cid:
            if not rows:return {'status':'unavailable','reason':'CUSIP not active or identity unavailable'}
            b=bonds[0];h=history(db,files,rows[0],auction.get(cid)) if b['status']=='computed' else [];b['history']=h;valid_history=len(h)>1 and all(q['return'] is not None for q in h[1:]);b['conditional_cumulative_return']=holding_return(h[0]['dirty_indexed'],h[-1]['dirty_indexed'],sum(q['cash'] for q in h[1:])) if valid_history else None;b['conditional_reinvested_return']=float(np.prod([1+q['return'] for q in h[1:]])-1) if valid_history else None
            b['cashflows']=[{'date':str(d),'real_or_nominal_per_100':v,'indexed_constant_ratio_scenario':(v-100)*b['index_ratio']+max(100,100*b['index_ratio']) if b['type']=='tips' and d==rows[0][3] else v*b['index_ratio']} for d,v,_ in b.pop('flows',[])];return {'status':'experimental','approved':False,'data_version':version,'curve':curve,'bond':b,'warning':'Government valuation marks assumed clean, settlement at observed date, not tradable prices. Historical cash held without interest; TIPS cash uses published payments, future indexation conditional.'}
    # Use one common valuation date for allocation instead of mixing stale marks.
    valid=[b for b in bonds if b['status']=='computed'];mark=max((b['mark_date'] for b in valid),default=None);candidates=[b for b in valid if b['type']!='tips' and b['mark_date']==mark and b['spread_bps_of_dirty'] is not None and b['spread_bps_of_dirty']<=max_spread and min_maturity<=b['days_to_maturity']/365.25<=max_maturity];settle=date.fromisoformat(mark) if mark else as_of
    if raw is None:liabilities=[(shift_month(settle,12*i),capital*v) for i,v in [(1,.35),(3,.35),(5,.35)]]
    else:
        if not isinstance(raw,list) or not 1<=len(raw)<=20:raise ValueError('Invalid liability list')
        liabilities=[(date.fromisoformat(q['date']),float(q['amount'])) for q in raw]
        if any(d<=settle or (d-settle).days>30*365.25 or not np.isfinite(v) or not 0<v<=1e9 for d,v in liabilities):raise ValueError('Invalid liability date/amount')
    variants={}
    for mode in ('cashflow','key_rate','combined'):
        try:variants[mode]=ladder(candidates,settle,capital,liabilities,cap,cost,curves['nominal'],mode,duration_target,duration_tolerance,max_dv01)
        except ValueError as e:variants[mode]={'status':'unavailable','reason':str(e)}
    for b in bonds:b.pop('flows',None)
    return {'status':'experimental','approved':False,'version':VERSION,'data_version':version,'as_of':str(as_of),'valuation_date':mark,'curve':curve,'count':len(bonds),'computed':len(valid),'counts_by_type':dict(Counter(b['type'] for b in bonds)),'computed_by_type':dict(Counter(b['type'] for b in valid)),'unavailable_reasons':dict(Counter(b.get('reason') for b in bonds if b['status']!='computed')),'bonds':bonds,'ladder_eligible':len(candidates),'liabilities':[{'date':str(d),'amount':v} for d,v in liabilities],'ladders':variants,'configuration':{'capital':capital,'max_weight':cap,'cost_bps':cost,'min_maturity_years':min_maturity,'max_maturity_years':max_maturity,'max_spread_bps':max_spread},'warning':'Government valuation marks assumed clean; no verified executable quotes, settlement calendar, borrow or live liquidity. Nominal and real curves on latest common FRED date; no PIT publication guarantee. Ladder uses fractional face units, nominal securities only, indicative spread plus cost, cash at zero interest. Independent mandate certification not provided.'}
