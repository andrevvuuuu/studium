"""litpipe.models - modello Pydantic v2 + motore di validazione delle dimensioni d'effetto.

Convenzioni:
  n          = numero di PARTECIPANTI (coppie) e mai di arti, salvo spread.n_basis == "limbs".
  md         = mean_a - mean_b (differenza fra le due condizioni confrontate).
  r          = correlazione fra le due misure appaiate (arto A/arto B, pre/post).
  J(df)      = correzione di Hedges esatta (funzione Gamma); df = n-1 (appaiato), n1+n2-2 (indipendente).
"""
from __future__ import annotations

import itertools
import math
import re
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _betacf(a: float, b: float, x: float) -> float:
    """Frazione continua della beta incompleta (Numerical Recipes, Lentz)."""
    tiny, qab, qap, qam = 1e-300, a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-14:
            break
    return h


def _betainc(a: float, b: float, x: float) -> float:
    """Beta incompleta regolarizzata I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1.0 - x)
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(lbt) * _betacf(a, b, x) / a
    return 1.0 - math.exp(lbt) * _betacf(b, a, 1.0 - x) / b


def t_sf(t: float, df: float) -> float:
    """P(T > t) per la t di Student con df gradi di liberta'."""
    tail = 0.5 * _betainc(df / 2.0, 0.5, df / (df + t * t))
    return tail if t >= 0 else 1.0 - tail


def t_isf(q: float, df: float) -> float:
    """t tale che P(T > t) = q (0 < q < 1), per bisezione."""
    if not 0.0 < q < 1.0:
        raise ValueError("q deve essere in (0, 1)")
    if q > 0.5:
        return -t_isf(1.0 - q, df)
    lo, hi = 0.0, 1.0
    while t_sf(hi, df) > q:
        hi *= 2.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if t_sf(mid, df) > q:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0

# --------------------------------------------------------------------------------------
# 1. Primitive statistiche
# --------------------------------------------------------------------------------------


def hedges_j(df: float) -> float:
    """J(df) = sqrt(2/df) * Gamma(df/2) / Gamma((df-1)/2). Richiede df > 1."""
    if df <= 1:
        raise ValueError("df deve essere > 1 per J di Hedges")
    return math.exp(math.lgamma(df / 2) - math.lgamma((df - 1) / 2)) / math.sqrt(df / 2)


def hedges_j_approx(df: float) -> float:
    """Approssimazione 1 - 3/(4*df - 1); errore < 0.002 per df >= 5."""
    return 1.0 - 3.0 / (4.0 * df - 1.0)


def t_crit(df: float, level: float = 0.95) -> float:
    return t_isf((1 - level) / 2, df)


def sd_from_sem(sem: float, n: int) -> float:
    """SD = SEM * sqrt(n); n = osservazioni indipendenti dietro la SEM (partecipanti)."""
    return sem * math.sqrt(n)


def sd_from_ci(lower: float, upper: float, n: int, level: float = 0.95) -> float:
    """SD = sqrt(n) * (U - L) / (2 * t_{1-alpha/2, n-1}); vale per l'IC di UNA media."""
    return math.sqrt(n) * (upper - lower) / (2.0 * t_crit(n - 1, level))


def sd_diff_from_t(md: float, t: float, n: int) -> float:
    """t = md / (sdd / sqrt(n))  =>  sdd = |md| * sqrt(n) / |t|."""
    return abs(md) * math.sqrt(n) / abs(t)


def sd_diff_from_p(md: float, p_two_sided: float, n: int) -> float:
    """p ESATTO bilaterale (non 'p<0.05'): t = isf(p/2, n-1)."""
    return sd_diff_from_t(md, t_isf(p_two_sided / 2.0, n - 1), n)


def sd_diff_from_ci(lower: float, upper: float, n: int, level: float = 0.95) -> float:
    """IC della DIFFERENZA appaiata -> sdd (non l'SD di un braccio)."""
    return math.sqrt(n) * (upper - lower) / (2.0 * t_crit(n - 1, level))


def r_from_sds(sd1: float, sd2: float, sd_diff: float) -> float:
    """Cochrane 6.5.2.8: r = (sd1^2 + sd2^2 - sdd^2) / (2 sd1 sd2)."""
    return (sd1**2 + sd2**2 - sd_diff**2) / (2.0 * sd1 * sd2)


def sd_diff_from_r(sd1: float, sd2: float, r: float) -> float:
    return math.sqrt(max(sd1**2 + sd2**2 - 2.0 * r * sd1 * sd2, 1e-12))


def var_dz_exact(d_z: float, n: int) -> Optional[float]:
    """Varianza esatta di d_z (t non centrale), n coppie, richiede n > 3.
    V = ((n-1)/(n-3)) * (1/n) * (1 + n*delta^2) - delta^2 / J(n-1)^2,  delta = d_z / J."""
    if n <= 3:
        return None
    j = hedges_j(n - 1)
    delta = d_z / j
    return ((n - 1) / (n - 3)) * (1.0 / n) * (1.0 + n * delta**2) - delta**2 / j**2


def paired_effect_sizes(
    mean_a: float,
    mean_b: float,
    n: int,
    *,
    sd_std_a: float,
    sd_std_b: float,
    sd_qty_a: Optional[float] = None,
    sd_qty_b: Optional[float] = None,
    sd_diff: Optional[float] = None,
    t: Optional[float] = None,
    p_exact: Optional[float] = None,
    ci_diff: Optional[tuple[float, float]] = None,
    r_reported: Optional[float] = None,
    r_imputed: float = 0.5,
) -> dict:
    """Metriche per un contrasto appaiato (arto A vs B, pre vs post) su n COPPIE.

    sd_std_*  : SD del metrica raw (SD pre, o SD post se non c'e' pre) -> standardizzatore di d_av/d_rm.
    sd_qty_*  : SD della quantita' confrontata (es. SD del cambiamento); servono solo per ricavare r.
    Ritorna un dict con d_z, d_av, d_rm, g_*, J, varianze, r, r_source e avvisi.
    """
    if n < 2:
        raise ValueError("n coppie deve essere >= 2")
    warnings: list[str] = []
    md = mean_a - mean_b
    df = n - 1
    j = hedges_j(df)

    # 1) sdd: priorita' esplicita > t > p esatto > IC > r riportato > r imputato
    sdd: Optional[float] = None
    r: Optional[float] = None
    r_source = "none"
    if sd_diff is not None:
        sdd, r_source = sd_diff, "sd_diff"
    elif t is not None and t != 0:
        sdd, r_source = sd_diff_from_t(md, t, n), "t"
    elif p_exact is not None and 0 < p_exact < 1:
        sdd, r_source = sd_diff_from_p(md, p_exact, n), "p_exact"
    elif ci_diff is not None:
        sdd, r_source = sd_diff_from_ci(ci_diff[0], ci_diff[1], n), "ci_diff"

    qa = sd_qty_a if sd_qty_a is not None else sd_std_a
    qb = sd_qty_b if sd_qty_b is not None else sd_std_b
    can_derive_r = sd_qty_a is not None and sd_qty_b is not None

    if sdd is not None and can_derive_r:
        r = r_from_sds(qa, qb, sdd)
        lo, hi = abs(qa - qb), qa + qb
        if not (lo - 1e-9 <= sdd <= hi + 1e-9):
            warnings.append("sd_diff incompatibile con gli SD dei bracci (|r|>1): input incoerente")
        if r < 0 or r > 1:
            warnings.append(f"r implicito {r:.3f} fuori da [0,1]")
        r = max(min(r, 0.999), -0.999)
    elif sdd is None and r_reported is not None:
        r, r_source = r_reported, "reported"
        sdd = sd_diff_from_r(qa, qb, r)
    elif sdd is None:
        r, r_source = r_imputed, "imputed"
        warnings.append("r imputato: d_z e d_rm NON calcolati; d_av e' indipendente da r, r agisce solo sulla varianza")
    # sdd noto ma r non derivabile: r_source resta quello di sdd, r = None

    sd_av = math.sqrt((sd_std_a**2 + sd_std_b**2) / 2.0)  # media quadratica (forma 'average variance')
    d_av = md / sd_av
    out: dict = {
        "n_pairs": n, "df": df, "J": j, "md": md, "sd_diff": sdd, "r": r, "r_source": r_source,
        "d_av": d_av, "g_av": j * d_av, "sd_av": sd_av, "warnings": warnings,
        "d_z": None, "g_z": None, "d_rm": None, "g_rm": None,
        "var_d_z": None, "var_g_z": None, "var_d_av": None, "var_g_av": None,
        "se_g_av": None, "ci95_g_av": None,
    }
    if sdd is not None:
        d_z = md / sdd
        out["d_z"], out["g_z"] = d_z, j * d_z
        v = var_dz_exact(d_z, n)
        out["var_d_z"] = v
        out["var_g_z"] = None if v is None else j**2 * v
        # d_rm = d_z * sqrt(2(1-r)) quando r e' noto
        if r is not None:
            d_rm = d_z * math.sqrt(2.0 * (1.0 - r))
            out["d_rm"], out["g_rm"] = d_rm, j * d_rm
    # Varianza di d_av (approssimazione tipo Borenstein/Becker):
    #   V = (sdd/sd_av)^2 / n + d_av^2 / (2n)  ==  2(1-r)/n + d^2/(2n) a SD uguali
    ratio2 = (sdd / sd_av) ** 2 if sdd is not None else 2.0 * (1.0 - (r if r is not None else r_imputed))
    v_av = ratio2 / n + d_av**2 / (2.0 * n)
    out["var_d_av"], out["var_g_av"] = v_av, j**2 * v_av
    se = j * math.sqrt(v_av)
    out["se_g_av"] = se
    out["ci95_g_av"] = (j * d_av - 1.96 * se, j * d_av + 1.96 * se)
    return out


def independent_effect_sizes(m1: float, sd1: float, n1: int, m2: float, sd2: float, n2: int) -> dict:
    """d_s con SD pooled; g_s con J(df = n1+n2-2). Varianza: (n1+n2)/(n1 n2) + d^2/(2(n1+n2))."""
    df = n1 + n2 - 2
    sp = math.sqrt(((n1 - 1) * sd1**2 + (n2 - 1) * sd2**2) / df)
    d = (m1 - m2) / sp
    j = hedges_j(df)
    v = (n1 + n2) / (n1 * n2) + d**2 / (2.0 * (n1 + n2))
    return {"df": df, "J": j, "d_s": d, "g_s": j * d, "var_d_s": v, "var_g_s": j**2 * v, "sd_pooled": sp}


def ppc2_effect_size(
    pre_t: float, post_t: float, sdpre_t: float, n_t: int,
    pre_c: float, post_c: float, sdpre_c: float, n_c: int, rho: float,
) -> dict:
    """Morris (2008) d_ppc2. Standardizzatore = SD pre pooled; c = 1 - 3/(4 df - 1), df = nT+nC-2.
    Varianza come in MDMA::dPPC2 (Morris 2008 eq. 25), con rho comune ai due bracci."""
    df = n_t + n_c - 2
    sd_pre = math.sqrt(((n_t - 1) * sdpre_t**2 + (n_c - 1) * sdpre_c**2) / df)
    c = hedges_j_approx(df)
    d = c * ((post_t - pre_t) - (post_c - pre_c)) / sd_pre
    nt = n_t * n_c / (n_t + n_c)  # n tilde
    var = (2 * c**2 * (1 - rho) / nt) * (df / (df - 2)) * (1 + nt * d**2 / (2 * (1 - rho))) - d**2 if df > 2 else None
    return {"df": df, "c": c, "d_ppc2": d, "g_ppc2": d, "var": var, "sd_pre_pooled": sd_pre}


# --------------------------------------------------------------------------------------
# 2. Enum e tipi (valori brevi in snake_case: Dataview-safe, niente parentesi)
# --------------------------------------------------------------------------------------


class Design(str, Enum):
    parallel = "parallel_group"
    within = "within_subject_unilateral"
    crossover = "crossover"
    single_group = "single_group_prepost"
    other = "other"


class TrainingStatus(str, Enum):
    untrained = "untrained"
    recreational = "recreational"
    trained = "trained"
    advanced = "advanced"
    ambiguous = "ambiguous"


class Effort(str, Enum):
    failure = "momentary_failure"
    rir = "rir_or_velocity_loss"
    volitional = "volitional_fatigue"
    fixed_buffer = "fixed_prescription"
    unclear = "unclear"


class VolumeMatching(str, Enum):
    sets = "sets_equated"
    tonnage = "tonnage_equated"
    work = "work_equated"
    unmatched = "unmatched"
    not_reported = "not_reported"


class Tool(str, Enum):
    bia = "bia"
    dexa = "dexa"
    us_single = "ultrasound_single_point"
    imaging_fcsa = "mri_ct_panoramic"
    biopsy = "biopsy_fcsa"


class EsLabel(str, Enum):
    d_z = "d_z"; g_z = "g_z"; d_av = "d_av"; g_av = "g_av"; d_rm = "d_rm"; g_rm = "g_rm"
    d_s = "d_s"; g_s = "g_s"; d_ppc2 = "d_ppc2"; unknown = "unknown"


class Tier(str, Enum):
    PASS = "pass"
    NOTE = "note"
    WARN = "warn"
    FAIL = "fail"


_TIER_ORDER = {Tier.PASS: 0, Tier.NOTE: 1, Tier.WARN: 2, Tier.FAIL: 3}

# --------------------------------------------------------------------------------------
# 3. Blocchi di input statistico
# --------------------------------------------------------------------------------------


class Spread(BaseModel):
    """Misura di dispersione come riportata; la conversione in SD avviene qui e solo qui."""

    kind: Literal["sd", "sem", "ci95"]
    value: Optional[float] = Field(None, gt=0)       # SD o SEM
    lower: Optional[float] = None                     # IC95 di una media
    upper: Optional[float] = None
    n_basis: Literal["participants", "limbs"] = "participants"

    @model_validator(mode="after")
    def _shape(self) -> "Spread":
        if self.kind in ("sd", "sem") and self.value is None:
            raise ValueError(f"spread.kind={self.kind} richiede 'value'")
        if self.kind == "ci95":
            if self.lower is None or self.upper is None or self.upper <= self.lower:
                raise ValueError("spread.kind=ci95 richiede lower < upper")
        return self

    def to_sd(self, n_participants: int, n_limbs: Optional[int] = None) -> float:
        n = n_limbs if (self.n_basis == "limbs" and n_limbs) else n_participants
        if self.kind == "sd":
            return float(self.value)  # type: ignore[arg-type]
        if self.kind == "sem":
            return sd_from_sem(float(self.value), n)  # type: ignore[arg-type]
        return sd_from_ci(float(self.lower), float(self.upper), n)  # type: ignore[arg-type]


class Stat(BaseModel):
    mean: float
    spread: Spread
    dec_mean: int = Field(1, ge=0, le=6)    # decimali con cui la media e' stampata (per l'intervallo di arrotondamento)
    dec_spread: int = Field(1, ge=0, le=6)


class ConditionData(BaseModel):
    label: str
    n_participants: int = Field(..., ge=2)
    n_limbs: Optional[int] = Field(None, ge=2)
    pre: Optional[Stat] = None
    post: Optional[Stat] = None
    change: Optional[Stat] = None   # media/SD del cambiamento pre->post, se riportati

    @model_validator(mode="after")
    def _at_least_one(self) -> "ConditionData":
        # Ammesso anche senza statistiche (paper che riportano solo stime da modello): niente ricalcolo per l'outcome.
        return self

    @property
    def has_stats(self) -> bool:
        return any(x is not None for x in (self.pre, self.post, self.change))


class PairedSummary(BaseModel):
    """Statistiche inferenziali del contrasto appaiato (A-B), se riportate. Solo valori ESATTI."""

    t: Optional[float] = None
    p_exact: Optional[float] = Field(None, gt=0, lt=1)
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    sd_diff: Optional[float] = Field(None, gt=0)
    r_reported: Optional[float] = Field(None, ge=-1, le=1)
    r_imputed: float = Field(0.5, ge=-0.99, le=0.99)


class ReportedEffect(BaseModel):
    value: float
    label: EsLabel = EsLabel.unknown
    decimals: int = Field(2, ge=0, le=4)
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None


class EffectAudit(BaseModel):
    tier: Tier
    label_compared: str
    reported: float
    recomputed: Optional[float] = None
    abs_diff: Optional[float] = None
    rel_diff: Optional[float] = None
    rounding_interval: Optional[tuple[float, float]] = None
    diagnosis: Optional[str] = None
    notes: list[str] = Field(default_factory=list)
    primary: dict = Field(default_factory=dict)   # metriche ricalcolate (primary + secondarie)


# --------------------------------------------------------------------------------------
# 4. Outcome con audit dell'effetto
# --------------------------------------------------------------------------------------


class Outcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    muscle_region: str
    measurement_tool: Tool
    tem_or_cv_reported: bool = False
    blinded_analyst: Optional[bool] = None
    condition_a: ConditionData
    condition_b: Optional[ConditionData] = None
    paired: Optional[PairedSummary] = None
    reported_effect: Optional[ReportedEffect] = None
    p_value: Optional[float] = Field(None, ge=0, le=1)
    p_kind: Literal["interaction", "between_group", "within_group", "not_reported"] = "not_reported"
    individual_data_reported: bool = False
    audit: Optional[EffectAudit] = None   # popolato dal validatore di documento; NON dall'LLM


class SubjectDemographics(BaseModel):
    enrolled_count: int = Field(..., ge=1)
    completed_count: int = Field(..., ge=1)
    n_limbs: Optional[int] = Field(None, ge=2)
    sex: Literal["male", "female", "mixed", "not_reported"]
    mean_age: Optional[float] = Field(None, ge=10, le=100)
    training_status: TrainingStatus
    exact_inclusion_criteria: str


class ResistanceProtocol(BaseModel):
    exercise_name: str
    target_muscle_groups: list[str]
    weekly_frequency: int = Field(..., ge=1, le=14)
    sets_per_session: int = Field(..., ge=1)
    prescribed_rep_range: str
    effort: Effort
    volume_matching: VolumeMatching
    velocity_loss_threshold_pct: Optional[float] = Field(None, ge=0, le=100)


class SpinAudit(BaseModel):
    abstract_claim: str
    unsupported_claim_detected: bool
    spin_severity: Literal["none", "low", "moderate", "high"]
    spin_justification: str


_DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")
_URN_RE = re.compile(r"^urn:sha256:[0-9a-f]{64}$")


def normalize_doi(raw: str) -> str:
    s = raw.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "doi:"):
        if s.startswith(prefix):
            s = s[len(prefix):]
    return s


class StudyAnalysisDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doi: str
    study_design: Design
    demographics: SubjectDemographics
    protocol: ResistanceProtocol
    outcomes: list[Outcome] = Field(default_factory=list)
    spin_analysis: Optional[SpinAudit] = None
    methodological_quality_score: int = Field(..., ge=0, le=10)
    cross_education_risk: Optional[bool] = None
    audit_statistical_discrepancy: bool = False   # derivato: l'LLM non lo imposta

    @field_validator("doi")
    @classmethod
    def _doi(cls, v: str) -> str:
        v = normalize_doi(v)
        if not (_DOI_RE.match(v) or _URN_RE.match(v)):
            raise ValueError("DOI non valido e non e' un URN sha256 (urn:sha256:<64 hex>)")
        return v

    @property
    def is_unilateral(self) -> bool:
        return self.study_design == Design.within

    @model_validator(mode="after")
    def _structure(self) -> "StudyAnalysisDocument":
        d = self.demographics
        if d.completed_count > d.enrolled_count:
            raise ValueError("completed_count > enrolled_count")
        if self.is_unilateral:
            if d.n_limbs is not None and d.n_limbs != 2 * d.completed_count:
                raise ValueError(
                    f"n_limbs={d.n_limbs} incoerente con 2*N={2 * d.completed_count}: "
                    "in un disegno unilaterale l'unita' statistica e' il partecipante"
                )
            self.cross_education_risk = True if self.cross_education_risk is None else self.cross_education_risk
        elif d.n_limbs is not None:
            raise ValueError("n_limbs ha senso solo per disegni within-subject unilaterali")
        for i, o in enumerate(self.outcomes):
            for c in filter(None, (o.condition_a, o.condition_b)):
                if self.is_unilateral:
                    if c.n_participants == 2 * d.completed_count:
                        raise ValueError(f"outcomes[{i}].{c.label}: n={c.n_participants} = 2N (arti conteggiati come "
                                         f"partecipanti). Usare n_participants={d.completed_count}, n_limbs=2N")
                    if c.n_participants != d.completed_count:
                        raise ValueError(f"outcomes[{i}].{c.label}: n_participants={c.n_participants} != "
                                         f"completed_count={d.completed_count} in un disegno within-subject")
                elif c.n_participants > d.completed_count:
                    raise ValueError(f"outcomes[{i}].{c.label}: n del braccio > completed_count")
            try:
                o.audit = audit_outcome(self.study_design, o)
            except (ValueError, ZeroDivisionError):
                o.audit = None   # statistiche insufficienti per il ricalcolo: l'outcome resta, senza audit
        self.audit_statistical_discrepancy = any(
            o.audit is not None and _TIER_ORDER[o.audit.tier] >= _TIER_ORDER[Tier.WARN] for o in self.outcomes
        )
        return self


# --------------------------------------------------------------------------------------
# 5. Audit dell'effetto: ricalcolo, intervallo di arrotondamento, tier, diagnosi
# --------------------------------------------------------------------------------------

_PAIRED_DESIGNS = {Design.within, Design.crossover, Design.single_group}


def _half_unit(dec: int) -> float:
    return 0.5 * 10 ** (-dec)


def _paired_inputs(design: Design, o: Outcome) -> dict:
    """Costruisce gli argomenti di paired_effect_sizes dall'outcome."""
    a, b = o.condition_a, o.condition_b
    n = a.n_participants
    pr = o.paired or PairedSummary()
    kw = dict(
        sd_diff=pr.sd_diff, t=pr.t, p_exact=pr.p_exact,
        ci_diff=(pr.ci_lower, pr.ci_upper) if pr.ci_lower is not None and pr.ci_upper is not None else None,
        r_reported=pr.r_reported, r_imputed=pr.r_imputed,
    )
    if design == Design.single_group:
        s_pre, s_post = a.pre, a.post
        if not (s_pre and s_post):
            raise ValueError("single_group richiede pre e post")
        sd_pre = s_pre.spread.to_sd(n)
        return dict(mean_a=s_post.mean, mean_b=s_pre.mean, n=n, sd_std_a=sd_pre, sd_std_b=sd_pre,
                    sd_qty_a=s_post.spread.to_sd(n), sd_qty_b=sd_pre, **kw), \
            [(s_post.mean, s_post.dec_mean), (s_pre.mean, s_pre.dec_mean)], [(sd_pre, s_pre.dec_spread)] * 2
    if b is None:
        raise ValueError("disegno appaiato a due condizioni richiede condition_b")
    use_change = all(c.pre is not None and c.post is not None for c in (a, b))
    if use_change:
        ma, mb = a.post.mean - a.pre.mean, b.post.mean - b.pre.mean            # type: ignore[union-attr]
        sa, sb = a.pre.spread.to_sd(n), b.pre.spread.to_sd(n)                  # type: ignore[union-attr]
        qa = a.change.spread.to_sd(n) if a.change else None
        qb = b.change.spread.to_sd(n) if b.change else None
        means = [(a.post.mean, a.post.dec_mean), (a.pre.mean, a.pre.dec_mean),
                 (b.post.mean, b.post.dec_mean), (b.pre.mean, b.pre.dec_mean)]  # type: ignore[union-attr]
        sds = [(sa, a.pre.dec_spread), (sb, b.pre.dec_spread)]                   # type: ignore[union-attr]
    else:
        if a.post is None or b.post is None:
            raise ValueError("servono post (e idealmente pre) per entrambe le condizioni")
        ma, mb = a.post.mean, b.post.mean
        sa, sb = a.post.spread.to_sd(n), b.post.spread.to_sd(n)
        qa = qb = None
        means = [(ma, a.post.dec_mean), (mb, b.post.dec_mean)]
        sds = [(sa, a.post.dec_spread), (sb, b.post.dec_spread)]
    return dict(mean_a=ma, mean_b=mb, n=n, sd_std_a=sa, sd_std_b=sb, sd_qty_a=qa, sd_qty_b=qb, **kw), means, sds


def _rounding_interval(kw: dict, means: list, sds: list, label: str, es_dec: int, scale: float = 1.0,
                       mode: str = "worst") -> tuple[float, float]:
    """Intervallo del valore ricalcolato dovuto SOLO all'arrotondamento dei dati stampati.

    mode="worst" : estremi massimi (somma delle semi-unita'); mode="prob": ~95% probabile
    (errori di arrotondamento uniformi indipendenti: 1.96 * sqrt(sum(u^2) / 3)).
    `scale` moltiplica il risultato (es. J_indipendente per g_s)."""
    us_m = [_half_unit(d) for _, d in means]
    us_s = [_half_unit(d) for _, d in sds]
    if mode == "worst":
        u_md = sum(us_m)
        u_sd = us_s
    else:
        u_md = 1.96 * math.sqrt(sum(u * u for u in us_m) / 3.0)
        u_sd = [1.96 * u / math.sqrt(3.0) for u in us_s]
    vals = []
    for s_md, s_a, s_b in itertools.product((-1, 1), repeat=3):
        k = dict(kw)
        k["mean_a"] = kw["mean_a"] + s_md * u_md
        k["sd_std_a"] = max(kw["sd_std_a"] + s_a * u_sd[0], 1e-9)
        k["sd_std_b"] = max(kw["sd_std_b"] + s_b * u_sd[1], 1e-9)
        try:
            v = paired_effect_sizes(**k).get(label)
        except Exception:  # corner degenere
            continue
        if v is not None:
            vals.append(v * scale)
    if not vals:
        return (float("nan"), float("nan"))
    u_es = _half_unit(es_dec)
    return (min(vals) - u_es, max(vals) + u_es)


def _known_factors(r: Optional[float], n: int, df: int) -> dict[str, float]:
    f: dict[str, float] = {
        "g_vs_d: ratio = J(n-1)": hedges_j(df),
        "d_vs_g: ratio = 1/J(n-1)": 1.0 / hedges_j(df),
        "ricetta indipendente su t appaiato: ratio = sqrt(2) sul d_z": math.sqrt(2.0),
        "SD scambiata con SEM: ratio = 1/sqrt(n)": 1.0 / math.sqrt(n),
        "SEM scambiata con SD: ratio = sqrt(n)": math.sqrt(n),
        "J con df indipendente (2n-2) al posto di n-1": hedges_j(2 * n - 2) / hedges_j(df),
    }
    if r is not None and r < 0.999:
        f["d_z riportato al posto di d_av: ratio = 1/sqrt(2(1-r))"] = 1.0 / math.sqrt(2.0 * (1.0 - r))
        f["d_av riportato al posto di d_z: ratio = sqrt(2(1-r))"] = math.sqrt(2.0 * (1.0 - r))
        if r > 0:
            f["ricetta indipendente su t appaiato vs d_rm: ratio = 1/sqrt(1-r)"] = 1.0 / math.sqrt(1.0 - r)
    return f


def _tier(abs_diff: float, rel: float, in_prob: bool, in_worst: bool) -> Tier:
    """PASS: dentro l'intervallo probabile di arrotondamento o |diff| <= 0.01.
    NOTE: dentro l'intervallo di arrotondamento al caso peggiore, oppure rel <= 5% e |diff| <= 0.05.
    WARN: rel <= 10%.  FAIL: oltre."""
    if in_prob or abs_diff <= 0.01:
        return Tier.PASS
    if in_worst or (rel <= 0.05 and abs_diff <= 0.05):
        return Tier.NOTE
    if rel <= 0.10:
        return Tier.WARN
    return Tier.FAIL


def _max_tier(a: Tier, b: Tier) -> Tier:
    return a if _TIER_ORDER[a] >= _TIER_ORDER[b] else b


_COMPARABLE = {"d_av", "g_av", "d_rm", "g_rm", "d_s", "g_s", "d_ppc2"}


def _audit_paired(design: Design, o: Outcome) -> tuple[float, str, Optional[tuple], Optional[tuple], dict, dict, list[str], list[str]]:
    rep = o.reported_effect
    assert rep is not None
    kw, means, sds = _paired_inputs(design, o)
    res = paired_effect_sizes(**kw)
    notes = list(res["warnings"])
    n, df = kw["n"], kw["n"] - 1
    j_ind = hedges_j(2 * n - 2)
    cands: dict[str, Optional[float]] = {
        "d_z": res["d_z"], "g_z": res["g_z"], "d_av": res["d_av"], "g_av": res["g_av"],
        "d_rm": res["d_rm"], "g_rm": res["g_rm"],
        "d_s": res["d_av"],            # ricetta indipendente: SD pooled = media quadratica a n uguali
        "g_s": j_ind * res["d_av"],    # ... con J(df=2n-2): la correzione sbagliata per dati appaiati
    }
    key = rep.label.value
    if rep.label in (EsLabel.d_s, EsLabel.g_s):
        notes.append("ricetta per campioni indipendenti usata su dati appaiati: usare g_av con J(df=n-1)")
    if rep.label == EsLabel.d_ppc2:
        notes.append("d_ppc2 incoerente con un disegno appaiato")
    if key == "unknown" or cands.get(key) is None:
        if key != "unknown":
            notes.append(f"{key} non ricostruibile (servono sd_diff/t/p esatto/IC appaiato e SD del cambiamento)")
        key = "g_av"
        notes.append("etichetta metrica assente/non verificabile: confronto con il primario g_av")
    recomputed = float(cands[key])  # type: ignore[arg-type]
    base, scale = {"d_s": ("d_av", 1.0), "g_s": ("d_av", j_ind)}.get(key, (key, 1.0))
    worst = _rounding_interval(kw, means, sds, base, rep.decimals, scale, "worst")
    prob = _rounding_interval(kw, means, sds, base, rep.decimals, scale, "prob")
    factors = _known_factors(res["r"], n, df)
    others = [k for k, v in cands.items() if v is not None and k != key and abs(rep.value - v) <= max(0.01, 0.02 * abs(v))]
    info = {k: v for k, v in res.items() if k != "warnings"}
    return recomputed, key, worst, prob, factors, info, notes, others


def _audit_independent(o: Outcome) -> tuple[float, str, None, None, dict, dict, list[str], list[str]]:
    rep = o.reported_effect
    assert rep is not None
    a, b = o.condition_a, o.condition_b
    if b is None:
        raise ValueError("disegno a gruppi indipendenti richiede condition_b")
    notes: list[str] = []
    na, nb = a.n_participants, b.n_participants
    if all(c.pre is not None and c.post is not None for c in (a, b)):
        sp_a, sp_b = a.pre.spread.to_sd(na), b.pre.spread.to_sd(nb)            # type: ignore[union-attr]
        if a.change is not None and b.change is not None:
            rho_a = r_from_sds(sp_a, a.post.spread.to_sd(na), a.change.spread.to_sd(na))  # type: ignore[union-attr]
            rho_b = r_from_sds(sp_b, b.post.spread.to_sd(nb), b.change.spread.to_sd(nb))  # type: ignore[union-attr]
            rho, src = float(min(max((rho_a + rho_b) / 2, -0.99), 0.99)), "derived"
        else:
            rho, src = (o.paired.r_imputed if o.paired else 0.5), "imputed"
            notes.append("rho pre-post imputato: il punto d_ppc2 non dipende da rho, la varianza si'")
        res = ppc2_effect_size(a.pre.mean, a.post.mean, sp_a, na, b.pre.mean, b.post.mean, sp_b, nb, rho)  # type: ignore[union-attr]
        res["rho"], res["rho_source"] = rho, src
        recomputed, key = res["g_ppc2"], "d_ppc2"
        if rep.label not in (EsLabel.d_ppc2, EsLabel.unknown, EsLabel.d_s, EsLabel.g_s):
            notes.append(f"etichetta {rep.label.value} non standard per pre-post-control: confronto con d_ppc2")
    else:
        if a.post is None or b.post is None:
            raise ValueError("servono i valori post (o pre+post) di entrambi i bracci")
        res = independent_effect_sizes(a.post.mean, a.post.spread.to_sd(na), na,
                                       b.post.mean, b.post.spread.to_sd(nb), nb)
        recomputed, key = res["g_s"], "g_s"
    if rep.label in (EsLabel.d_z, EsLabel.g_z, EsLabel.d_rm, EsLabel.d_av):
        notes.append("metrica da disegno appaiato dichiarata in un disegno a gruppi indipendenti")
    nmin = min(na, nb)
    j = res.get("J", res.get("c", 1.0))
    factors = {"g_vs_d: ratio = J": j, "d_vs_g: ratio = 1/J": 1.0 / j,
               "SD scambiata con SEM: ratio = 1/sqrt(n)": 1.0 / math.sqrt(nmin),
               "SEM scambiata con SD: ratio = sqrt(n)": math.sqrt(nmin)}
    return recomputed, key, None, None, factors, dict(res), notes, []


def recompute_primary(design: Design, o: Outcome) -> Optional[tuple[str, float]]:
    """Effetto primario ricalcolato anche quando il paper non ne stampa uno: g_av (appaiati), d_ppc2 o g_s (gruppi)."""
    try:
        if design in _PAIRED_DESIGNS:
            kw, _, _ = _paired_inputs(design, o)
            return "g_av", float(paired_effect_sizes(**kw)["g_av"])
        a, b = o.condition_a, o.condition_b
        if b is None:
            return None
        na, nb = a.n_participants, b.n_participants
        if all(c.pre is not None and c.post is not None for c in (a, b)):
            r = ppc2_effect_size(a.pre.mean, a.post.mean, a.pre.spread.to_sd(na), na,           # type: ignore[union-attr]
                                 b.pre.mean, b.post.mean, b.pre.spread.to_sd(nb), nb, 0.5)       # type: ignore[union-attr]
            return "d_ppc2", float(r["d_ppc2"])
        if a.post is not None and b.post is not None:
            r = independent_effect_sizes(a.post.mean, a.post.spread.to_sd(na), na, b.post.mean, b.post.spread.to_sd(nb), nb)
            return "g_s", float(r["g_s"])
    except (ValueError, ZeroDivisionError):
        return None
    return None


def audit_outcome(design: Design, o: Outcome) -> Optional[EffectAudit]:
    """Ricalcola l'effetto con la formula CORRETTA PER IL DISEGNO e lo confronta con quello riportato."""
    rep = o.reported_effect
    if rep is None:
        return None
    if design in _PAIRED_DESIGNS:
        recomputed, key, worst, prob, factors, info, notes, others = _audit_paired(design, o)
    else:
        recomputed, key, worst, prob, factors, info, notes, others = _audit_independent(o)

    def inside(iv: Optional[tuple]) -> bool:
        return iv is not None and not math.isnan(iv[0]) and iv[0] <= rep.value <= iv[1]

    abs_diff = abs(rep.value - recomputed)
    rel = abs_diff / abs(recomputed) if recomputed else float("inf")
    tier = _tier(abs_diff, rel, inside(prob), inside(worst))
    label_used = key
    if design in _PAIRED_DESIGNS and rep.label in (EsLabel.d_s, EsLabel.g_s):
        tier = _max_tier(tier, Tier.NOTE)   # ricetta indipendente su dati appaiati: sempre da segnalare
    # etichetta assente + coincidenza con un'altra metrica: il numero e' giusto, la metrica e' un'altra
    if rep.label == EsLabel.unknown and others and tier != Tier.PASS:
        label_used = others[0]
        tier = Tier.NOTE
        notes.append(f"valore coerente con {others[0]}, non con il primario {key}")
        if others[0] in ("d_z", "g_z"):
            notes.append("d_z/g_z NON e' comparabile con d indipendenti: conservare l'etichetta, non aggregare in meta-analisi")
    diag: Optional[str] = None
    if tier != Tier.PASS and recomputed and rep.value > 0 and recomputed > 0:
        ratio = rep.value / recomputed
        name, f = min(factors.items(), key=lambda kv: abs(math.log(ratio / kv[1])))
        if abs(math.log(ratio / f)) <= 0.03:
            diag = f"rapporto {ratio:.3f} compatibile con: {name}"
            if label_used == key and abs(ratio - 1) > 0.05:
                tier = _max_tier(tier, Tier.WARN)   # errore sistematico riconoscibile, anche se dentro l'arrotondamento
    # Metrica non dichiarata (es. SMD da modello misto/bayesiano con standardizzatore proprio): senza un errore
    # riconoscibile il confronto e' solo indicativo e non costituisce una discrepanza.
    if rep.label == EsLabel.unknown and diag is None and _TIER_ORDER[tier] > _TIER_ORDER[Tier.NOTE]:
        tier = Tier.NOTE
        notes.append(f"metrica non dichiarata: confronto indicativo con {key} (standardizzatore del paper ignoto)")
    if rep.ci_lower is not None and rep.ci_upper is not None and not (rep.ci_lower <= rep.value <= rep.ci_upper):
        notes.append("valore riportato fuori dal proprio IC")
        tier = _max_tier(tier, Tier.WARN)
    return EffectAudit(tier=tier, label_compared=label_used, reported=rep.value, recomputed=recomputed,
                       abs_diff=abs_diff, rel_diff=rel, rounding_interval=worst, diagnosis=diag,
                       notes=notes, primary=info)


def validate_extraction_payload(payload: dict) -> dict:
    """Valida un payload LLM e ritorna un report serializzabile (usato dal tool MCP validate_extraction)."""
    from pydantic import ValidationError

    try:
        doc = StudyAnalysisDocument.model_validate(payload)
    except ValidationError as e:
        return {"ok": False, "errors": [{"loc": list(x["loc"]), "msg": x["msg"]} for x in e.errors()],
                "audit_statistical_discrepancy": None, "audits": []}
    audits = [{"outcome": i, "tier": o.audit.tier.value, "diagnosis": o.audit.diagnosis, "notes": o.audit.notes,
               "recomputed": o.audit.recomputed, "reported": o.audit.reported}
              for i, o in enumerate(doc.outcomes) if o.audit]
    return {"ok": True, "errors": [], "audit_statistical_discrepancy": doc.audit_statistical_discrepancy,
            "audits": audits, "document": doc.model_dump(mode="json")}
