"""Bridge the confirmed interview to a decision using its dated eligibility register."""
from datetime import date
from ..risk_review import assess


def account_gate(snapshot, register, as_of):
    if snapshot["as_of"]!=as_of[:10]:
        return dict(status="date of mandate to be updated", ids=[])
    if not len(register) or not (register.date==as_of).all() or register.id.duplicated().any():
        return dict(status="incomplete decision register", ids=[])
    review=snapshot.get("risk_review")
    if not review:
        return dict(status="request to be confirmed", ids=[])
    current=assess(snapshot,review["choice"],accept=review["accepted"],bills=review["bills"],comfort=review["comfort"])
    if not current["ready_for_feasibility"]:
        return dict(status=current["state"], ids=[])
    choice=current["choice"]
    share=current["household_invested_share"]
    factor=1 if choice["basis"]=="investment sleeve" else share
    if not factor or current["investable_chf"]["low"]<=0:
        return dict(status="no investment sleeve invested",ids=[])
    high=choice["high"]/factor if choice["high"] is not None else None
    if high is not None and choice["high_exclusive"]:
        high=max(0.,high-2e-6)  # Keep the verified numeric solution inside the open edge.
    ids=register.loc[register.eligible,"id"].tolist()
    return dict(status="oversight of the mandate to be implemented" if ids else "no eligible instrument",
                ids=ids, pocket_chf=current["investable_chf"]["low"],reserve_chf=current["reserve_chf"]["high"],
                mode=choice["mode"], low=(choice["low"] or 0)/factor,high=high)
