"""What moved Blood PhenoAge between two draws, using only the original PLSI formula.

Same method as PLSI's `plsi calc derive --set marker=value`: start from the previous draw, replace one input with
its new value and recompute. No outside benchmarks or reference ranges are involved. Because the formula is not
linear, the single effects do not add up exactly; the remainder is reported as combined effects so the total
always matches the real change.
"""
from datetime import datetime, timezone
from .plsi_kernel import chronological_age, phenoage


def _age(result):
    at=datetime.fromisoformat(result['measured_at']).replace(tzinfo=timezone.utc)
    return chronological_age(result['birth_year'],at)


def explain_change(previous, current):
    before=dict(previous['values']); age_before=_age(previous)
    base=phenoage(before,age_before)
    total=phenoage(current['values'],_age(current))-base
    effects=[]
    for marker in before:
        if current['values'][marker]==before[marker]:continue
        changed={**before,marker:current['values'][marker]}
        effects.append({'kind':'marker','marker':marker,'from':before[marker],'to':current['values'][marker],
                        'years':phenoage(changed,age_before)-base})
    age_effect=phenoage(before,_age(current))-base
    if abs(age_effect)>0:
        effects.append({'kind':'age','from':age_before,'to':_age(current),'years':age_effect})
    rest=total-sum(e['years'] for e in effects)
    if abs(rest)>=0.05:
        effects.append({'kind':'combined','years':rest})
    effects.sort(key=lambda e:-abs(e['years']))
    return {'from_id':previous['id'],'to_id':current['id'],'total':total,'effects':effects}


def previous_draw(history, current):
    earlier=[r for r in history if (r['measured_at'],r['draw_id'])<(current['measured_at'],current['draw_id'])]
    return earlier[-1] if earlier else None
