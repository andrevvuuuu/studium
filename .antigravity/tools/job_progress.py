"""Weighted progress bands shared with the Studium HUD."""
BANDS = {"prep": (0, 3), "sources": (3, 15), "context": (15, 20), "writing": (20, 85), "verify": (85, 97), "final": (97, 100)}

def phase_plan(op, strict):
    plan = ["prep", "sources", "context", "writing"]
    if op == "moc" or (op == "normal" and strict): plan.append("verify")
    plan.append("final")
    return plan

def compute_overall(phase, fraction, plan):
    lo, hi = BANDS.get(phase, (0, 3))
    if phase == "final" and "verify" not in plan: lo, hi = (85, 100)
    if phase not in plan: return lo
    f = 0 if fraction is None else max(0, min(1, float(fraction)))
    return round(lo + (hi - lo) * f)
