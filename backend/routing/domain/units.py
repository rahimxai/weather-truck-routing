# Exact by definition (international yard and pound agreement, 1959).
KG_PER_LB = 0.45359237
M_PER_MI = 1609.344
MM_PER_IN = 25.4


def lb_to_kg(lb):
    return lb * KG_PER_LB


def kg_to_lb(kg):
    return kg / KG_PER_LB


def m_to_mi(m):
    return m / M_PER_MI


def mi_to_m(mi):
    return mi * M_PER_MI


def kmh_to_mph(kmh):
    return kmh * 1000 / M_PER_MI


def mm_to_in(mm):
    return mm / MM_PER_IN


def cm_to_in(cm):
    return cm * 10 / MM_PER_IN
