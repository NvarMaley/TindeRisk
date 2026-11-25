"""Conditional, asset-specific estimates, never mixed with validated forecasts."""
from math import isfinite
import calendar
import numpy as np
from scipy.optimize import brentq


def _coupon_date(maturity, months):
    month=maturity.month-1-months
    year=maturity.year+month//12
    month=month%12+1
    end=calendar.monthrange(year,month)[1]
    day=end if maturity.day==calendar.monthrange(maturity.year,maturity.month)[1] else min(maturity.day,end)
    return maturity.replace(year=year,month=month,day=day)


def bond_yield(mark, maturity, coupon, price, instrument_type):
    """Indicative yield assuming a clean mark per 100 face, actual coupon fractions.

    Bills use effective annual yield ACT/365; notes/bonds/TIPS use nominal
    semiannual bond-equivalent yield. TIPS estimate is real, not nominal.
    No claim of executable market price or realized holding-period return.
    """
    if maturity<=mark or not isfinite(price) or price<=0 or not 0<=coupon<=.25:
        raise ValueError("Invalid bond inputs")
    if instrument_type=="treasury_bill":
        return (100/price)**(365/(maturity-mark).days)-1
    dates=[]
    i=0
    while _coupon_date(maturity,6*i)>mark:
        dates.append(_coupon_date(maturity,6*i))
        i+=1
    prev=_coupon_date(maturity,6*i)
    dates.reverse()
    fraction=(dates[0]-mark).days/(dates[0]-prev).days
    coupon_cash=100*coupon/2
    dirty=price+coupon_cash*(1-fraction)
    def objective(y):
        return sum((coupon_cash+(100 if j==len(dates)-1 else 0))/(1+y/2)**(fraction+j)
                   for j in range(len(dates)))-dirty
    return brentq(objective,-.5,5)


def fallback(item, outcome, db, returns_folder, pit_folder, as_of):
    """For unavailable assets only, produce separate estimates or explicit reasons."""
    category=item["category"]
    if category=="treasury":
        cusip=item["id"].split(":",1)[1]
        row=db.execute("""select a.instrument_type,a.maturity,a.coupon_rate_decimal,b.observation_date,b.eod_price
          from read_parquet(?) a join read_parquet(?) b using(instrument)
          where a.instrument=? and a.issue_date<=? and b.observation_date<=? and b.observation_date<a.maturity
          order by b.observation_date desc limit 1""",[str(pit_folder/"treasury_identity.parquet"),
          str(pit_folder/"fedinvest_marks.parquet"),cusip,as_of,as_of]).fetchone()
        if row:
            kind,maturity,coupon,mark,price=row
            try:
                if coupon is None or (as_of-mark).days>31:
                    raise ValueError("Missing coupon or current mark")
                y=bond_yield(mark,maturity,coupon,price,kind)
                return outcome | {"status":"fallback","estimate":{"method":"real_ytm" if kind=="tips" else "indicative_ytm",
                    "value":y,"units":"annual yield","as_of":str(mark),"maturity":str(maturity),
                    "currency":"USD","source":"FedInvest / U.S. Treasury",
                    "limitations":"Conditional clean-mark convention; yield to maturity, not a one-period return; TIPS real yield."}}
            except (ValueError,OverflowError,ZeroDivisionError):
                pass
    if category=="cash":
        row=db.execute("""select observation_date,observed_value from read_parquet(?) where observation_date<=?
            order by observation_date desc limit 1""",[str(pit_folder/"sofr.parquet"),as_of]).fetchone()
        if row and (as_of-row[0]).days<=7:
            return outcome | {"status":"fallback","estimate":{"method":"sofr","value":row[1]/100,
              "units":"annual overnight rate, ACT/360","as_of":str(row[0]),"currency":"USD",
              "source":"Federal Reserve Bank of New York","limitations":"Indicative overnight reference rate, not a guaranteed annual return or tradeable cash product."}}
    if category=="stock":
        for attempt in outcome.get("attempts",[]):
            series=next((s for s in item["series"] if s["source"]==attempt["source"]),None)
            if not series: continue
            kind=attempt["kind"]
            rows=db.execute(f"""select end_date,{kind} from read_parquet(?) where instrument=? and end_date<=?
              and {kind} is not null order by end_date desc limit 60""",
              [str(returns_folder/f"{series['source']}.parquet"),series["instrument"],as_of]).fetchall()
            valid=[(d,v) for d,v in rows if isfinite(v) and v>=-1]
            if len(valid)>=3:
                values=np.array([v for _,v in valid])
                return outcome | {"status":"fallback","estimate":{"method":"short_history_mean","value":float(values.mean()),
                    "units":"decimal per "+series["frequency"],"as_of":str(valid[0][0]),"currency":"USD",
                    "frequency":series["frequency"],"kind":kind,"observations":len(valid),"source":series["source"],
                    "limitations":"Observed interval mean only; gaps not filled, no held-out model validation; low confidence."}}
    return outcome
