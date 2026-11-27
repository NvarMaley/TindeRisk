"""Exploratory choice likelihoods; not a calibrated person-level risk estimate."""

import numpy as np

from .discovery import canonical_choice, session


def crra(wealth, gamma):
    w=np.asarray(wealth,dtype=float)
    if np.any(w<=0):
        raise ValueError("CRRA requires positive wealth")
    return np.log(w) if abs(gamma-1)<1e-10 else np.expm1((1-gamma)*np.log(w))/(1-gamma)


def prospect(outcomes, alpha, loss_aversion):
    x=np.asarray(outcomes,dtype=float)
    return np.where(x>=0,np.abs(x)**alpha,-loss_aversion*np.abs(x)**alpha)


def _utility(card, alternative, model, parameters):
    x=np.array(alternative["outcomes"],dtype=float)/card["reference_wealth"]
    p=np.array(alternative["probabilities"],dtype=float)
    if model=="crra":
        values=crra(1+x,parameters[0])
    else:
        values=prospect(x,parameters[0],parameters[1])
    return float(p @ values)


def explore_likelihoods(seed, currency, responses, temperature=10.0):
    """Fixed-temperature grid comparison, no score mapping or risk-budget changes.

    Only known-probability monetary choices enter. No probability
    weighting fit; parameters are exploratory and may be weakly identified.
    """
    if not np.isfinite(temperature) or temperature<=0:
        raise ValueError("Invalid temperature")
    items=[]
    for card in session(seed,currency)["cards"]:
        choice=canonical_choice(card,responses.get(card["id"]))
        if card["block_id"] in {"mixed","gains","losses","rare"} and choice:
            items.append((card,choice=="A"))
    if len(items)<7:
        return {"status":"insufficient_choices","n":len(items)}

    def likelihood(model,parameters):
        nll=0.0
        for card,a_selected in items:
            delta=temperature*(_utility(card,card["canonical_a"],model,parameters)-_utility(card,card["canonical_b"],model,parameters))
            nll+=float(np.logaddexp(0,-delta if a_selected else delta))
        return nll

    gamma_grid=[0,.5,1,2,3,5,8,10]
    prospect_grid=[(a,l) for a in (.5,.7,.88,1.0) for l in (1,1.5,2,2.5,3,4)]
    crra_results=sorted((likelihood("crra",(g,)),g) for g in gamma_grid)
    prospect_results=sorted((likelihood("prospect",p),p) for p in prospect_grid)
    c,p=crra_results[0],prospect_results[0]
    return {"status":"experimental_weak_identification","n":len(items),"temperature":temperature,
            "crra":{"gamma_grid_best":c[1],"nll":c[0],"grid_within_2_nll":[g for nll,g in crra_results if nll<=c[0]+2]},
            "prospect":{"alpha_grid_best":p[1][0],"loss_aversion_grid_best":p[1][1],"nll":p[0],
                        "grid_within_2_nll":[list(params) for nll,params in prospect_results if nll<=p[0]+2]},
            "limitations":["fixed_temperature","objective_probabilities","not_calibrated","not_a_score_mapping"]}
