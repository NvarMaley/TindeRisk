"""Offline conditional futures ledger. Contract months are source labels, not expiry dates."""
from dataclasses import dataclass
from datetime import datetime
import math
import numpy as np

VERSION='futures-v1'


@dataclass(frozen=True)
class Spec:
    root:str
    multiplier:float
    tick:float
    unit:str

    def __post_init__(self):
        if not np.isfinite([self.multiplier,self.tick]).all() or self.multiplier<=0 or self.tick<=0:raise ValueError('Invalid contract specification')


@dataclass(frozen=True)
class Mark:
    stamp:datetime
    contract:str
    price:float
    quotes:dict
    roll_from:str|None=None
    old_price:float|None=None
    new_price:float|None=None
    roll_stamp:datetime|None=None


def valid_month(contract,stamp):
    """Conservative month identity check, not actual last trading date."""
    return len(contract)==8 and contract.isdigit() and 1<=int(contract[4:6])<=12 and int(contract[:6])>=stamp.year*100+stamp.month


def variation(q,multiplier,old,new):
    if isinstance(q,bool) or not isinstance(q,(int,np.integer)) or multiplier<=0 or not np.isfinite([multiplier,old,new]).all():raise ValueError('Invalid variation margin')
    return float(q*multiplier*(new-old))


def integer_position(price,spec,nav,target,gross_limit,initial_margin,reserve):
    """Integer signed exposure, shrinking toward zero; never round upward to leverage."""
    if not np.isfinite([price,nav,target,gross_limit,initial_margin,reserve]).all() or nav<=0 or gross_limit<=0 or not 0<initial_margin<=1 or not 0<=reserve<1:raise ValueError('Invalid sizing input')
    notional=abs(price)*spec.multiplier
    if notional<spec.tick*spec.multiplier:return 0
    limit=min(abs(target),gross_limit,(1-reserve)/initial_margin);q=math.floor(nav*limit/notional+1e-12)*int(np.sign(target))
    return q


def continuous_changes(marks):
    """Causal additive differences excluding roll gap. Return None on missing overlap."""
    if not marks:return []
    out=[{'date':str(marks[0].stamp.date()),'change':None,'causal_index':0.}];level=0.
    for a,b in zip(marks,marks[1:]):
        if b.contract==a.contract:delta=b.price-a.price
        elif b.roll_from==a.contract and b.old_price is not None and b.new_price is not None:delta=b.old_price-a.price+b.price-b.new_price
        else:delta=None
        if delta is None or (b.stamp.date()-a.stamp.date()).days>7:level=0.;delta=None
        else:level+=delta
        out.append({'date':str(b.stamp.date()),'change':delta,'causal_index':level})
    return out


def simulate(marks,spec,*,capital=250000.,target=.5,gross_limit=1.5,initial_margin=.10,maintenance_margin=.075,reserve=.20,commission=2.,slippage_ticks=1.,cash_rate=0.,margin_shock=1.5,strategy='long',margin_schedule=None,spec_schedule=None):
    """Daily sampled mark-to-market, integer sizing and separate roll trades.

    Price-role transitions are observed retrospectively; simultaneous overlap
    is mandatory. No unrealized roll-gap P&L, no funded purchase of notional.
    Optional dated margin schedule is a research scenario, not exchange data.
    """
    nums=[capital,target,gross_limit,initial_margin,maintenance_margin,reserve,commission,slippage_ticks,cash_rate,margin_shock]
    if len(marks)<2 or not np.isfinite(nums).all() or capital<=0 or not 0<=target<=gross_limit<=5 or not 0<maintenance_margin<=initial_margin<=1 or not 0<=reserve<1 or commission<0 or slippage_ticks<0 or not -.1<=cash_rate<=.2 or not 1<=margin_shock<=5 or strategy not in ('long','short','trend'):raise ValueError('Invalid futures simulation settings')
    if any(not np.isfinite(m.price) or not valid_month(m.contract,m.stamp) or (i and m.stamp.date()<=marks[i-1].stamp.date()) for i,m in enumerate(marks)):raise ValueError('Invalid dated marks or expired delivery month')
    schedule=margin_schedule or {};spec_schedule=spec_schedule or {};changes=continuous_changes(marks);nav=float(capital);q=0;rows=[];rolls=[];cost_unit=commission+slippage_ticks*spec.tick*spec.multiplier;total_cost=0.;total_vm=0.;total_interest=0.;blocked=None
    for i,m in enumerate(marks):
        revised=spec_schedule.get(m.stamp.date(),spec)
        if revised!=spec:
            if revised.root!=spec.root:raise ValueError('Wrong root in dated specification')
            if q:blocked='Contract size/specification changed while position open: conversion unavailable';break
            spec=revised;cost_unit=commission+slippage_ticks*spec.tick*spec.multiplier
        im,mm=schedule.get(m.stamp.date(),(initial_margin,maintenance_margin))
        if not 0<mm<=im<=1:raise ValueError('Invalid dated margin assumption')
        vm=0.;interest=0.;fee=0.;roll=False;oldq=q;reason=None
        if i:
            prev=marks[i-1];gap=(m.stamp.date()-prev.stamp.date()).days
            if gap>7:blocked='Missing observations: source gap exceeds seven calendar days';break
            prior_nav=nav;interest=max(nav,0)*cash_rate*gap/365;nav+=interest
            if m.contract!=prev.contract:
                roll=True
                if m.roll_from!=prev.contract or m.old_price is None or m.new_price is None or m.roll_stamp is None:blocked='Missing simultaneous old/new quote on roll';break
                if not valid_month(prev.contract,m.roll_stamp) or not valid_month(m.contract,m.roll_stamp):blocked='Roll beyond source delivery month';break
                vm=variation(q,spec.multiplier,prev.price,m.old_price);nav+=vm
                old_notional=abs(q*m.old_price*spec.multiplier)
                if nav<=0:reason='equity_exhausted_at_roll'
                elif old_notional and nav<old_notional*mm:reason='maintenance_margin_call_at_roll'
                elif old_notional and nav*(1-reserve)<old_notional*im:reason='initial_margin_or_reserve_shortfall_at_roll'
                # Close old contract before opening new; transaction costs per side.
                close_fee=abs(q)*cost_unit;nav-=close_fee;fee+=close_fee
                if nav<=0:reason='equity_exhausted_at_roll'
                direction=1 if strategy=='long' else -1 if strategy=='short' else int(np.sign(sum(x['change'] or 0 for x in changes[max(1,i-252):i]))) if i>=253 and all(x['change'] is not None for x in changes[i-252:i]) else 0
                q=0 if reason else integer_position(m.new_price,spec,nav,target*direction,gross_limit,im,reserve)
                while q and (abs(q)*cost_unit+abs(q*m.new_price*spec.multiplier)*im>nav*(1-reserve) or abs(q*m.new_price*spec.multiplier)>gross_limit*(nav-abs(q)*cost_unit)):q-=int(np.sign(q))
                open_fee=abs(q)*cost_unit;fee+=open_fee;nav-=open_fee
                post=variation(q,spec.multiplier,m.new_price,m.price);vm+=post;nav+=post
                rolls.append({'date':str(m.stamp.date()),'timestamp':str(m.roll_stamp),'old_contract':prev.contract,'new_contract':m.contract,'old_price':m.old_price,'new_price':m.new_price,'old_quantity':oldq,'new_quantity':q,'curve_gap':m.new_price-m.old_price,'cost':fee,'old_contract_vm':variation(oldq,spec.multiplier,prev.price,m.old_price),'new_contract_vm':post})
            else:vm=variation(q,spec.multiplier,prev.price,m.price);nav+=vm
        else:prior_nav=nav
        if nav<=0:
            reason='equity_exhausted'
        notional=abs(q*m.price*spec.multiplier);required=notional*mm
        if notional and nav<required:reason='maintenance_margin_call'
        if reason is None and notional and nav*(1-reserve)<notional*im:reason='initial_margin_or_reserve_shortfall'
        if reason is None and roll and notional>gross_limit*nav:reason='gross_limit_after_roll'
        if reason is not None:
            # Close at observed mark for scenario; never pretend additional capital arrived.
            fee+=abs(q)*cost_unit;nav-=abs(q)*cost_unit;q=0
        elif i==0 or not roll:
            direction=1 if strategy=='long' else -1 if strategy=='short' else int(np.sign(sum(x['change'] or 0 for x in changes[max(1,i-252):i]))) if i>=253 and all(x['change'] is not None for x in changes[i-252:i]) else 0
            # At day close, trend uses only preceding marks, sizing uses observed current price.
            new=integer_position(m.price,spec,nav,target*direction,gross_limit,im,reserve)
            while new and (abs(new-q)*cost_unit+abs(new*m.price*spec.multiplier)*im>nav*(1-reserve) or abs(new*m.price*spec.multiplier)>gross_limit*(nav-abs(new-q)*cost_unit)):new-=int(np.sign(new))
            trade_fee=abs(new-q)*cost_unit;fee+=trade_fee;nav-=trade_fee;q=new
        if nav<=0 and reason is None:
            reason='equity_exhausted_after_costs'
            fee+=abs(q)*cost_unit;nav-=abs(q)*cost_unit;q=0
        total_cost+=fee;total_vm+=vm;total_interest+=interest;notional=abs(q*m.price*spec.multiplier);initial=notional*im;maintenance=notional*mm;stress=notional*min(1,im*margin_shock);signed=q*abs(m.price)*spec.multiplier
        if not np.isclose(nav,prior_nav+vm+interest-fee,rtol=1e-10,atol=1e-7):raise ArithmeticError('Variation margin ledger not reconciled')
        rows.append({'date':str(m.stamp.date()),'contract':m.contract,'price':m.price,'quantity':q,'nav':nav,'variation_margin':vm,'interest':interest,'fees':fee,'gross_notional':notional,'signed_notional':signed,'gross_exposure':notional/nav if nav>0 else None,'initial_margin':initial,'maintenance_margin':maintenance,'collateral_free':nav-initial,'stressed_margin':stress,'stressed_reserve_shortfall':max(0.,stress+reserve*max(nav,0)-nav),'margin_call':reason})
        if reason:blocked=reason;break
    return {'status':'computed' if blocked is None else 'stopped','reason':blocked,'ledger':rows,'rolls':rolls,'final_nav':rows[-1]['nav'] if rows else capital,'total_variation_margin':total_vm,'total_interest':total_interest,'total_cost':total_cost,'initial_capital':capital,'completed_marks':len(rows)}
