import numpy as np
import pandas as pd
import pytest

from src.estimation import (ledoit_wolf_constant_corr, rolling_covariances,
                            sample_cov, validate_returns)
from src.correlation import correlation_diagnostics


@pytest.fixture
def panel():
    rng = np.random.default_rng(42)
    values=rng.normal(0, .01, (80, 4))
    values[:,1]=.8*values[:,0]+.3*values[:,1]
    values[:,2]=-.4*values[:,0]+values[:,2]
    return pd.DataFrame(values,
        index=pd.bdate_range('2020-01-01', periods=80), columns=list('ABCD'))


def test_sample_covariance_units(panel):
    np.testing.assert_allclose(sample_cov(panel), np.cov(panel.to_numpy().T, ddof=1)*252)
    pd.testing.assert_frame_equal(sample_cov(panel, 1)*252, sample_cov(panel))


def test_constant_correlation_matches_scalar_moments(panel):
    # Independent scalar Appendix-B calculation on population-denominator moments.
    x = panel.to_numpy(); x = x-x.mean(axis=0); n,p=x.shape
    s=np.cov(x.T,ddof=0); sd=np.sqrt(np.diag(s))
    r=sum(s[i,j]/(sd[i]*sd[j]) for i in range(p) for j in range(p) if i!=j)/(p*(p-1))
    f=np.array([[s[i,i] if i==j else r*sd[i]*sd[j] for j in range(p)] for i in range(p)])
    pi=rho=0.
    for i in range(p):
        for j in range(p):
            v=np.mean((x[:,i]*x[:,j]-s[i,j])**2); pi+=v
            if i==j: rho+=v
            else: rho+=r*sd[j]/sd[i]*(np.mean(x[:,i]**3*x[:,j])-s[i,i]*s[i,j])
    delta=np.clip((pi-rho)/(n*np.sum((s-f)**2)),0,1)
    cov,d=ledoit_wolf_constant_corr(panel)
    assert 0 < delta < 1
    assert d==pytest.approx(delta)
    np.testing.assert_allclose(cov,(delta*f+(1-delta)*s)*n/(n-1)*252)
    np.testing.assert_allclose(np.diag(cov),np.diag(sample_cov(panel)))
    assert np.linalg.eigvalsh(cov).min()>=-1e-12
    pd.testing.assert_frame_equal(cov,cov.T)


def test_target_equal_to_sample_is_finite(panel):
    cov,delta=ledoit_wolf_constant_corr(panel[['A','B']])
    assert delta==1
    np.testing.assert_allclose(cov,sample_cov(panel[['A','B']]))


@pytest.mark.parametrize('kind',['nan','constant','duplicate','unsorted','bad_return'])
def test_invalid_panel_rejected(panel,kind):
    if kind=='nan': panel.iloc[0,0]=np.nan
    elif kind=='constant': panel['A']=0.
    elif kind=='duplicate': panel.columns=['A','A','C','D']
    elif kind=='unsorted': panel=panel.iloc[::-1]
    else: panel.iloc[0,0]=-1.
    with pytest.raises(ValueError): validate_returns(panel)


def test_rolling_covariance_has_no_future_dependence(panel):
    dates=panel.index[[29,49]]
    cov,diag=rolling_covariances(panel,dates,window=20)
    changed=panel.copy(); changed.loc[panel.index>dates[-1]]*=10
    other,other_diag=rolling_covariances(changed,dates,window=20)
    pd.testing.assert_frame_equal(cov,other)
    pd.testing.assert_frame_equal(diag,other_diag)
    assert (diag.observations==20).all()
    assert diag.loc[(dates[0],'sample'),'window_start']==panel.index[10]
    np.testing.assert_allclose(cov.loc[(dates[0],'sample')], sample_cov(panel.iloc[10:30]))
    with pytest.raises(ValueError,match='insufficient'): rolling_covariances(panel,panel.index[:1],window=20)


def test_correlations_match_manual_window_without_future_dependence(panel):
    corr,roll=correlation_diagnostics(panel,benchmark='A',diversifiers=['B'],window=20)
    np.testing.assert_allclose(corr,np.corrcoef(panel.to_numpy().T))
    assert roll.iloc[:19].isna().all().all()
    assert roll.iloc[19,0]==pytest.approx(np.corrcoef(panel.A.iloc[:20],panel.B.iloc[:20])[0,1])
    changed=panel.copy(); changed.iloc[20:]*=5
    _,other=correlation_diagnostics(changed,benchmark='A',diversifiers=['B'],window=20)
    pd.testing.assert_frame_equal(roll.iloc[:20],other.iloc[:20])
    with pytest.raises(ValueError,match='belong'): correlation_diagnostics(panel,benchmark='SPY',diversifiers=['B'])


def test_builder_exports_verified_samples_and_omits_partial_month(tmp_path,monkeypatch):
    import json
    import yaml
    import pandas_market_calendars as mcal
    import src.build_dependence as builder
    from src.provenance import sha256_file
    processed=tmp_path/'processed'; processed.mkdir()
    config={'tickers':{'sectors':['A','B'],'diversifiers':['C']}, 'benchmark':'SPY',
            'portfolio':{'estimation_window_years':1},'validation':{'periods':{'main':{}}}}
    (tmp_path/'config.yaml').write_text(yaml.safe_dump(config,sort_keys=False))
    dates=mcal.get_calendar('NYSE').valid_days('2022-01-03','2023-03-15',tz=None)
    data=pd.DataFrame(np.random.default_rng(7).normal(0,.01,(len(dates),4)),index=dates,columns=['A','B','C','SPY'])
    manifest={'files':{}}
    for key,table in [('warmup_returns',data.iloc[:252]),('returns',data.iloc[252:])]:
        path=processed/f'common_main_{key}.parquet'; table.to_parquet(path)
        manifest['files'][path.name]={'sha256':sha256_file(path)}
    (processed/'common_sample_manifest.json').write_text(json.dumps(manifest))
    monkeypatch.setattr(builder,'ROOT',tmp_path)
    monkeypatch.setattr(builder,'PROCESSED_DATA',processed)
    monkeypatch.setattr(builder,'RESULTS',tmp_path/'results')
    builder.main()
    result=json.loads((tmp_path/'results/2_1b_2_2_manifest.json').read_text())
    assert result['periods']['main']['last_estimate']=='2023-02-28'
    cov=pd.read_parquet(tmp_path/'results/2_2_main_covariances.parquet')
    assert list(cov.columns)==['A','B','C']
    for name,info in result['files'].items(): assert sha256_file(tmp_path/'results'/name)==info['sha256']
    (processed/'common_main_returns.parquet').write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='checksum mismatch'): builder.main()
