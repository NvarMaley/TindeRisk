from datetime import date
import json
import numpy as np
import pytest
from riskmatch.analytics.sentiment import polarity,chronological_split,factor_returns,paired_uncertainty
from riskmatch.analytics.sentiment_report import sentiment_report


def test_labelled_denominator_and_missing():
    p,share=polarity([3,0],[1,0],[10,2]);assert p[0]==pytest.approx(.5) and share[0]==pytest.approx(.4);assert np.isnan(p[1]) and share[1]==0
    with pytest.raises(ValueError):polarity([2],[1],[1])


def test_chronological_date_split_and_paired_interval():
    dates=np.repeat(np.arange(40),3);train,val,test=chronological_split(dates);assert dates[train].max()<dates[val].min()<dates[test].min();assert np.all(train.astype(int)+val.astype(int)+test.astype(int)==1)
    y=np.zeros(24);d=np.repeat(np.arange(8),3);r=paired_uncertainty(y,np.ones(24)*.1,np.ones(24)*.05,d);assert r['conditional_block_interval']==pytest.approx([.05,.05])


def test_factor_quintiles_and_missing_report(tmp_path):
    r=factor_returns(np.repeat('2020-01-31',20),np.arange(20).astype(str),np.arange(20),np.arange(20)*.01);assert r[0]['spread']==pytest.approx(.16);assert r[0]['rank_ic']==pytest.approx(1)
    assert sentiment_report(tmp_path,date.today())=={'status':'unavailable','current_signal_available':False}
