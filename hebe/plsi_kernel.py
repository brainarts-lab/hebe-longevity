# Unchanged definitions from PLSI v0.2.1; see NOTICE.md and vendor/LICENSE.
import calendar
import math
from datetime import datetime

PHENOAGE_WEIGHTS = {
    "albumin": -0.0336, "creatinine": 0.0095, "glucose": 0.1953, "lymphocyte_pct": -0.0120, "mcv": 0.0268,
    "rdw": 0.3306, "alp": 0.00188, "wbc": 0.0554,
}

def chronological_age(birth_year: int, at: datetime) -> float:
    """Age at the draw = year_fraction(at) - (birth_year + 0.5), year_fraction = year + (day_of_year - 1)/days_in_year."""
    days = 366 if calendar.isleap(at.year) else 365
    return at.year + (at.timetuple().tm_yday - 1) / days - (birth_year + 0.5)

def phenoage(inputs: dict[str, float], age: float) -> float:
    """Blood PhenoAge from canonical-unit inputs keyed albumin, creatinine, glucose, crp, lymphocyte_pct, mcv, rdw,
    alp, wbc. Raises ValueError for crp <= 0 or a math domain error."""
    if inputs["crp"] <= 0:
        raise ValueError("PhenoAge needs CRP > 0 (ln CRP)")
    xb = -19.907 + 0.0954 * math.log(inputs["crp"]) + 0.0804 * age
    xb += sum(w * inputs[k] for k, w in PHENOAGE_WEIGHTS.items())
    gamma = 0.0076927
    mortality = 1 - math.exp(-math.exp(xb) * (math.exp(120 * gamma) - 1) / gamma)
    return 141.50225 + math.log(-0.00553 * math.log(1 - mortality)) / 0.090165
