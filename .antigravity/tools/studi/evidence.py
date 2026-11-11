"""studi.evidence - schemi LLM, pesi di evidenza deterministici, gate di utilizzabilita', verifica delle affermazioni."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from pathlib import Path
from .models import Effort, StudyAnalysisDocument, Tool, TrainingStatus, recompute_primary

# ------------------------------------------------------------------ schemi di I/O con l'LLM

class Narrative(BaseModel):
    model_config = ConfigDict(extra="forbid")
    takeaway: str = Field(..., min_length=10, max_length=900)
    practical_implications: list[str] = Field(default_factory=list, max_length=4)
    methods_summary: str = Field(..., max_length=1200)
    limitations: list[str] = Field(default_factory=list, max_length=10)


class Envelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document: StudyAnalysisDocument
    narrative: Narrative


class Claim(BaseModel):
    text: str
    strength: Literal["solid", "moderate", "tentative", "insufficient"]
    supporting: list[str] = Field(default_factory=list)
    contradicting: list[str] = Field(default_factory=list)


class PracticalRule(BaseModel):
    rule: str
    claim_ids: list[int] = Field(default_factory=list)   # 1-based


class Synthesis(BaseModel):
    headline: str
    claims: list[Claim]
    conflicts: list[str] = Field(default_factory=list)
    practical_rules: list[PracticalRule] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


# ------------------------------------------------------------------ pesi

TOOL_W = {Tool.imaging_fcsa: 1.0, Tool.us_single: 0.6, Tool.biopsy: 0.5, Tool.dexa: 0.35, Tool.bia: 0.15}
STATUS_W = {TrainingStatus.advanced: 1.0, TrainingStatus.trained: 0.7, TrainingStatus.recreational: 0.4,
            TrainingStatus.untrained: 0.25, TrainingStatus.ambiguous: 0.2}
EFFORT_W = {Effort.failure: 1.0, Effort.rir: 0.7, Effort.fixed_buffer: 0.5, Effort.volitional: 0.4, Effort.unclear: 0.3}
SPIN_F = {"none": 1.0, "low": 0.9, "moderate": 0.6, "high": 0.3, "unassessed": 0.8}
TIER_F = {"pass": 1.0, "note": 0.95, "warn": 0.7, "fail": 0.4}
TIER_ORDER = ["pass", "note", "warn", "fail"]
MIN_N = 8
_RANK = {"insufficient": 0, "tentative": 1, "moderate": 2, "solid": 3}


@dataclass
class EvidenceCard:
    citekey: str
    label: str
    title: str
    year: Optional[int]
    doi: str
    design: str
    n_participants: int
    n_limbs: Optional[int]
    best_tool: Optional[str]
    training_status: str
    advanced_verified: bool
    effort: str
    spin_severity: str
    worst_tier: Optional[str]
    quality: int
    weight: float
    level: Literal["high", "moderate", "low", "insufficient"]
    usable: bool
    gates: list[str] = field(default_factory=list)
    takeaway: str = ""
    findings: list[str] = field(default_factory=list)

    def for_prompt(self) -> dict:
        d = asdict(self)
        d.pop("doi")
        return d


def surname(author: str) -> str:
    a = author.strip()
    return (a.split(",")[0] if "," in a else a.split()[-1]).strip() if a else "Anon"


def label_for(meta: dict) -> str:
    authors = meta.get("authors") or []
    s = surname(authors[0]) if authors else "Anon"
    if len(authors) > 2:
        s += " et al."
    elif len(authors) == 2:
        s += f" & {surname(authors[1])}"
    return f"{s} {meta.get('year') or 'n.d.'}"


def build_card(ck: str, doc: StudyAnalysisDocument, meta: dict, takeaway: str = "") -> EvidenceCard:
    d = doc.demographics
    tools = [o.measurement_tool for o in doc.outcomes]
    best = max(tools, key=lambda t: TOOL_W[t]) if tools else None
    verified = d.training_status == TrainingStatus.advanced and len(d.exact_inclusion_criteria.strip()) >= 15
    status_w = STATUS_W[d.training_status]
    if d.training_status == TrainingStatus.advanced and not verified:
        status_w = min(status_w, STATUS_W[TrainingStatus.trained])
    spin = doc.spin_analysis.spin_severity if doc.spin_analysis else "unassessed"
    tiers = [o.audit.tier.value for o in doc.outcomes if o.audit]
    worst = max(tiers, key=TIER_ORDER.index) if tiers else None
    tool_w = TOOL_W[best] if best else 0.0
    base = 0.4 * tool_w + 0.3 * status_w + 0.3 * EFFORT_W[doc.protocol.effort]
    weight = round(base * (0.5 + 0.05 * doc.methodological_quality_score) * SPIN_F[spin] * TIER_F.get(worst or "pass", 1.0), 3)

    gates: list[str] = []
    if not doc.outcomes:
        gates.append("nessun_outcome_estratto")
    if spin in ("moderate", "high"):
        gates.append(f"spin_{spin}")
    if spin == "unassessed":
        gates.append("spin_non_valutato")
    if d.training_status == TrainingStatus.ambiguous:
        gates.append("stato_allenamento_ambiguo")
    if doc.protocol.effort == Effort.unclear:
        gates.append("sforzo_non_chiaro")
    if worst in ("warn", "fail"):
        gates.append(f"audit_statistico_{worst}")
    if best == Tool.bia:
        gates.append("solo_BIA")
    if d.completed_count < MIN_N:
        gates.append(f"n<{MIN_N}")
    if doc.study_design.value == "other":
        gates.append("disegno_non_standard")
    usable = not gates
    level = "insufficient" if not usable else ("high" if weight >= 0.75 else "moderate" if weight >= 0.5 else "low")

    findings = []
    for o in doc.outcomes:
        a = o.audit
        if a and a.recomputed is not None:
            eff = f"{a.label_compared}={a.recomputed:.2f} (audit {a.tier.value})"
        else:
            rp = recompute_primary(doc.study_design, o)
            eff = f"{rp[0]}={rp[1]:.2f} (ricalcolato; il paper non riporta un effect size)" if rp else "effetto non ricalcolabile (solo stime da modello)"
        p = f", {o.p_kind} p={o.p_value:.3g}" if o.p_value is not None else ""
        findings.append(f"{o.muscle_region} [{o.measurement_tool.value}] {eff}{p}")
    return EvidenceCard(
        citekey=ck, label=label_for(meta), title=meta.get("title") or doc.doi, year=meta.get("year"), doi=doc.doi,
        design=doc.study_design.value, n_participants=d.completed_count,
        n_limbs=(d.n_limbs or 2 * d.completed_count) if doc.is_unilateral else None,
        best_tool=best.value if best else None, training_status=d.training_status.value, advanced_verified=verified,
        effort=doc.protocol.effort.value, spin_severity=spin, worst_tier=worst, quality=doc.methodological_quality_score,
        weight=weight, level=level, usable=usable, gates=gates, takeaway=takeaway, findings=findings[:8],
    )


def load_card(data_dir: Path, ck: str) -> Optional[EvidenceCard]:
    """None se manca il sidecar (nota non estratta da questo strumento)."""
    p = data_dir / f"{ck}.json"
    if not p.exists():
        return None
    sc = json.loads(p.read_text(encoding="utf-8"))
    if "document" not in sc:                      # sidecar legacy (render_note): dump piatto del documento
        sc = {"document": sc, "meta": {}, "narrative": {}}
    doc = StudyAnalysisDocument.model_validate(sc["document"])
    return build_card(ck, doc, sc.get("meta", {}), (sc.get("narrative") or {}).get("takeaway", ""))


@dataclass
class CheckedClaim:
    claim: Claim
    final: str
    notes: list[str] = field(default_factory=list)


def enforce_claims(claims: list[Claim], cards: dict[str, EvidenceCard]) -> list[CheckedClaim]:
    """Il tetto di forza di ogni affermazione dipende dagli studi citati, non dall'LLM."""
    out: list[CheckedClaim] = []
    for c in claims:
        notes: list[str] = []
        sup = [k for k in dict.fromkeys(c.supporting) if k in cards]
        con = [k for k in dict.fromkeys(c.contradicting) if k in cards]
        if len(set(c.supporting)) != len(sup) or len(set(c.contradicting)) != len(con):
            notes.append("citazioni non presenti nell'insieme di studi rimosse")
        good = [k for k in sup if cards[k].usable and cards[k].level in ("high", "moderate")]
        high = [k for k in good if cards[k].level == "high"]
        cap = "insufficient"
        if sup:
            cap = "tentative"
        if good:
            cap = "moderate"
        if len(good) >= 2 and high:
            cap = "solid"
        if cap == "solid" and any(cards[k].usable and cards[k].level == "high" for k in con):
            cap = "moderate"
            notes.append("contraddetta da studio ad alto peso")
        final = c.strength if _RANK[c.strength] <= _RANK[cap] else cap
        if final != c.strength:
            notes.append(f"declassata {c.strength}->{final}: studi citati insufficienti per il livello dichiarato")
        out.append(CheckedClaim(c.model_copy(update={"supporting": sup, "contradicting": con}), final, notes))
    return out
