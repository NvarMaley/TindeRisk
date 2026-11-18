import json

import numpy as np
import pandas as pd
import pytest

from src.expected_returns import rolling_expected_returns, shrink_expected_mean


@pytest.fixture
def means_and_cov():
    labels = pd.Index(['A', 'B'])
    return (pd.Series([-.001, .003], index=labels),
            pd.DataFrame(np.diag([.0001, .0004]), index=labels, columns=labels))


def test_known_diagonal_covariance_formula(means_and_cov):
    mean, cov = means_and_cov
    shrunk, info = shrink_expected_mean(mean, cov, 100)
    target = .8*(-.001) + .2*.003
    distance = ((-.001-target)**2/.0001 + (.003-target)**2/.0004)
    intensity = 4/(4+100*distance)
    assert info['target'] == pytest.approx(target)
    assert info['shrinkage'] == pytest.approx(intensity)
    np.testing.assert_allclose(shrunk, (1-intensity)*mean + intensity*target)
    assert shrunk.std() == pytest.approx((1-intensity)*mean.std())


def test_identical_means_have_no_division_by_zero(means_and_cov):
    mean, cov = means_and_cov
    mean[:] = -.002
    result, info = shrink_expected_mean(mean, cov, 100)
    np.testing.assert_allclose(result, mean)
    assert info['shrinkage'] == 1


def test_translation_scale_and_permutation_invariance(means_and_cov):
    mean, cov = means_and_cov
    result, info = shrink_expected_mean(mean, cov, 100)
    shifted, shifted_info = shrink_expected_mean(mean+.001, cov, 100)
    np.testing.assert_allclose(shifted, result+.001)
    assert shifted_info['shrinkage'] == pytest.approx(info['shrinkage'])
    scaled, scaled_info = shrink_expected_mean(mean*100, cov*100**2, 100)
    np.testing.assert_allclose(scaled, result*100)
    assert scaled_info['shrinkage'] == pytest.approx(info['shrinkage'])
    order=['B','A']
    permuted, _ = shrink_expected_mean(mean.loc[order], cov.loc[order,order], 100)
    pd.testing.assert_series_equal(permuted.loc[mean.index],result)


@pytest.mark.parametrize('bad', ['nan','asymmetric','singular','indefinite','labels','observations'])
def test_invalid_inputs_fail(means_and_cov,bad):
    mean, cov = means_and_cov
    n=100
    if bad=='nan': mean.iloc[0]=np.nan
    elif bad=='asymmetric': cov.iloc[0,1]=.001
    elif bad=='singular': cov[:]=0.
    elif bad=='indefinite': cov.iloc[0,0]=-.001
    elif bad=='labels': cov=cov.iloc[::-1]
    else: n=1
    with pytest.raises(ValueError): shrink_expected_mean(mean,cov,n)


def test_rolling_windows_units_and_future_invariance():
    dates=pd.bdate_range('2020-01-01',periods=60)
    returns=pd.DataFrame(np.random.default_rng(4).normal(0,.01,(60,3)),index=dates,columns=list('ABC'))
    excess=returns-.0001
    decisions=dates[[29,49]]
    mu, raw, diag=rolling_expected_returns(returns,excess,decisions,window=20)
    changed=returns.copy(); changed.iloc[50:]*=5
    other,other_raw,other_diag=rolling_expected_returns(changed,changed-.0001,decisions,window=20)
    pd.testing.assert_frame_equal(mu,other)
    pd.testing.assert_frame_equal(raw,other_raw)
    pd.testing.assert_frame_equal(diag,other_diag)
    np.testing.assert_allclose(raw.iloc[0],excess.iloc[10:30].mean()*252)
    daily,_,_=rolling_expected_returns(returns,excess,decisions,window=20,annualize=1)
    np.testing.assert_allclose(mu,daily*252)
    assert diag.iloc[0].window_start==dates[10]
    assert (diag.observations==20).all()
    with pytest.raises(ValueError,match='matching'): rolling_expected_returns(returns,excess.iloc[1:],decisions,window=20)
    with pytest.raises(ValueError,match='insufficient'): rolling_expected_returns(returns,excess,dates[:1],window=20)


def test_builder_hashes_partial_month_and_benchmark_exclusion(tmp_path,monkeypatch):
    import yaml
    import pandas_market_calendars as mcal
    import src.build_expected_returns as builder
    from src.provenance import sha256_file

    processed=tmp_path/'processed'; processed.mkdir()
    settings={'method':'regularized_bayes_stein','target':'gmv_mean','covariance':'lw_constcorr',
              'units':'annualized_excess_arithmetic','status':'implementation_default_not_final_oos_validated'}
    config={'tickers':{'sectors':['A','B'],'diversifiers':['C']},'benchmark':'SPY',
            'portfolio':{'estimation_window_years':1},'validation':{'periods':{'main':{}}},
            'expected_returns':settings}
    (tmp_path/'config.yaml').write_text(yaml.safe_dump(config,sort_keys=False))
    dates=mcal.get_calendar('NYSE').valid_days('2022-01-03','2023-03-15',tz=None)
    data=pd.DataFrame(np.random.default_rng(7).normal(0,.01,(len(dates),4)),index=dates,columns=['A','B','C','SPY'])
    source=processed/'excess_returns.parquet'; (data-.0001).to_parquet(source)
    manifest={'inputs':{'excess_returns':sha256_file(source)},'files':{}}
    for key,table in [('warmup_returns',data.iloc[:252]),('returns',data.iloc[252:])]:
        path=processed/f'common_main_{key}.parquet';table.to_parquet(path)
        manifest['files'][path.name]={'sha256':sha256_file(path)}
    (processed/'common_sample_manifest.json').write_text(json.dumps(manifest))
    monkeypatch.setattr(builder,'ROOT',tmp_path)
    monkeypatch.setattr(builder,'PROCESSED_DATA',processed)
    monkeypatch.setattr(builder,'RESULTS',tmp_path/'results')
    builder.main()
    output=tmp_path/'results'
    result=json.loads((output/'2_3_manifest.json').read_text())
    assert result['periods']['main']['last_estimate']=='2023-02-28'
    mu=pd.read_csv(output/'2_3_main_mu.csv',index_col=0)
    assert list(mu.columns)==['A','B','C']
    assert result['periods']['main']['all_dispersion_reduced']
    for name,info in result['files'].items(): assert sha256_file(output/name)==info['sha256']
    source.write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='source checksum'):builder.main()
