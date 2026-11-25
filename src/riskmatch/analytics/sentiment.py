"""Optional historical sentiment diagnostics; no live-signal inference from stale data."""
import numpy as np
from scipy.stats import spearmanr
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression,Ridge,Lasso,ElasticNet
from sklearn.ensemble import RandomForestRegressor
from sklearn.neural_network import MLPRegressor

VERSION='sentiment-v1'


def polarity(bull,bear,total):
    b=np.asarray(bull,float);s=np.asarray(bear,float);n=np.asarray(total,float)
    if b.shape!=s.shape or b.shape!=n.shape or not np.isfinite([b,s,n]).all() or np.any(b<0)|np.any(s<0)|np.any(n<b+s):raise ValueError('Invalid sentiment counts')
    labels=b+s;return np.divide(b-s,labels,out=np.full_like(labels,np.nan),where=labels>0),np.divide(labels,n,out=np.full_like(labels,np.nan),where=n>0)


def chronological_split(dates):
    unique=np.unique(dates)
    if len(unique)<36:raise ValueError('Insufficient monthly history')
    a=unique[int(.6*len(unique))];b=unique[int(.8*len(unique))]
    return np.asarray(dates)<a,(np.asarray(dates)>=a)&(np.asarray(dates)<b),np.asarray(dates)>=b


def factor_returns(dates,ids,score,returns):
    out=[];dates=np.asarray(dates);ids=np.asarray(ids);score=np.asarray(score);returns=np.asarray(returns)
    for d in np.unique(dates):
        ix=np.flatnonzero(dates==d)
        if len(ix)<20:continue
        ix=ix[np.lexsort((ids[ix],score[ix]))];k=len(ix)//5;low=ix[:k];high=ix[-k:];ic=spearmanr(score[ix],returns[ix]).statistic if np.ptp(score[ix]) and np.ptp(returns[ix]) else None
        out.append({'date':str(d),'assets':len(ix),'long':float(returns[high].mean()),'short':float(returns[low].mean()),'spread':float(returns[high].mean()-returns[low].mean()),'rank_ic':float(ic) if ic is not None and np.isfinite(ic) else None})
    return out


def score(y,p):
    e=np.asarray(y)-np.asarray(p);return {'rmse':float(np.sqrt(np.mean(e**2))),'mae':float(np.mean(abs(e))),'directional_accuracy':float(np.mean((np.asarray(y)>0)==(np.asarray(p)>0)))}


def paired_uncertainty(y,baseline,augmented,dates,seed=17):
    """Resample calendar blocks, preserving cross-sectional dependence per month."""
    dates=np.asarray(dates);y=np.asarray(y);b=np.asarray(baseline);a=np.asarray(augmented);unique=np.unique(dates);n=len(unique)
    if n<6:return None
    monthly=np.array([[(np.mean((y[dates==d]-b[dates==d])**2)),np.mean((y[dates==d]-a[dates==d])**2)] for d in unique]);rng=np.random.default_rng(seed);block=3;starts=rng.integers(0,n-block+1,(1000,(n+block-1)//block));ix=(starts[:,:,None]+np.arange(block)).reshape(1000,-1)[:,:n];draw=monthly[ix].mean(1);gain=np.sqrt(draw[:,0])-np.sqrt(draw[:,1]);return {'monthly_equal_weight_rmse_gain':float(np.sqrt(monthly[:,0].mean())-np.sqrt(monthly[:,1].mean())),'conditional_block_interval':np.quantile(gain,[.025,.975]).tolist(),'block_months':block,'months':n}


def compare_models(X,S,y,dates):
    """Pooled, chronological fixed parameters; baseline and augmented identical rows."""
    X=np.asarray(X,float);S=np.asarray(S,float);y=np.asarray(y,float);dates=np.asarray(dates)
    if X.ndim!=2 or S.ndim!=2 or len(X)!=len(S) or len(X)!=len(y) or not np.isfinite(X).all() or not np.isfinite(S).all() or not np.isfinite(y).all():raise ValueError('Invalid aligned feature panel')
    train,val,test=chronological_split(dates);fit=train|val;out={};predictions={}
    for key,factory in {'ols':lambda:LinearRegression(),'ridge':lambda:Ridge(alpha=10),'lasso':lambda:Lasso(alpha=.001,max_iter=3000),'elastic_net':lambda:ElasticNet(alpha=.001,l1_ratio=.5,max_iter=3000),'random_forest':lambda:RandomForestRegressor(n_estimators=60,max_depth=5,min_samples_leaf=30,n_jobs=1,random_state=17),'neural_network':lambda:MLPRegressor(hidden_layer_sizes=(16,),alpha=.01,max_iter=200,random_state=17)}.items():
        rows={}
        for label,z in [('baseline',X),('sentiment',np.column_stack((X,S)))]:
            m=make_pipeline(StandardScaler(),factory());m.fit(z[fit],y[fit]);p=m.predict(z[test]);rows[label]=score(y[test],p);predictions[(key,label)]=p
        rows['rmse_improvement']=rows['baseline']['rmse']-rows['sentiment']['rmse'];rows['uncertainty']=paired_uncertainty(y[test],predictions[(key,'baseline')],predictions[(key,'sentiment')],dates[test]);out[key]=rows
    try:
        from xgboost import XGBRegressor
        rows={}
        for label,z in [('baseline',X),('sentiment',np.column_stack((X,S)))]:
            m=XGBRegressor(n_estimators=60,max_depth=3,learning_rate=.05,n_jobs=1,random_state=17,objective='reg:squarederror');m.fit(z[fit],y[fit]);p=m.predict(z[test]);rows[label]=score(y[test],p);predictions[('xgboost',label)]=p
        rows['rmse_improvement']=rows['baseline']['rmse']-rows['sentiment']['rmse'];rows['uncertainty']=paired_uncertainty(y[test],predictions[('xgboost','baseline')],predictions[('xgboost','sentiment')],dates[test]);out['xgboost']=rows
    except ImportError:out['xgboost']={'status':'unavailable'}
    test_dates=np.unique(dates[test]);return out,predictions,test,{'train_months':len(np.unique(dates[train])),'validation_months':len(np.unique(dates[val])),'test_months':len(test_dates),'train_rows':int(train.sum()),'validation_rows':int(val.sum()),'test_rows':int(test.sum()),'test_start':str(test_dates[0]),'test_end':str(test_dates[-1])}
