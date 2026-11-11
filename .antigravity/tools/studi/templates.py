"""studi.templates - Nota Studio Standalone, blocco di evidenza per note di concetto, linking al vocabolario controllato."""
from __future__ import annotations

import datetime as dt
import re
from typing import Any, Iterable

import yaml

from .evidence import CheckedClaim, EvidenceCard, Narrative, Synthesis, build_card
from .models import Design, Effort, StudyAnalysisDocument, Tool, TrainingStatus
from .notefs import content_hash, dump_frontmatter, make_citekey

CONTROLLED_VOCABULARY: dict[str, str] = {
    r"\b(rectus femoris|vastus lateralis|vastus medialis|quadriceps?)\b": "Quadriceps",
    r"\b(biceps brachii|brachialis|elbow flexors?)\b": "Biceps Brachii",
    r"\b(triceps brachii|elbow extensors?)\b": "Triceps Brachii",
    r"\b(gastrocnemius|soleus|calves|calf|triceps surae)\b": "Triceps Surae",
    r"\b(gluteus maximus|gluteals?)\b": "Gluteus Maximus",
    r"\b(hamstrings?|biceps femoris|semitendinosus)\b": "Hamstrings",
    r"\b(stretch[- ]mediated hypertrophy|passive tension|titin)\b": "Stretch-Mediated Hypertrophy",
    r"\b(long muscle lengths?|lengthened position|extended length|full ROM)\b": "Long Muscle Lengths",
    r"\b(regional hypertrophy|distal hypertrophy|proximal hypertrophy)\b": "Regional Hypertrophy",
    r"\b(mechanical tension|mechanosensing|mechanotransduction)\b": "Mechanical Tension",
    r"\b(repetitions? in reserve|RIR)\b": "Repetitions in Reserve (RIR)",
    r"\b(momentary (?:concentric )?failure|task failure|volitional failure)\b": "Concentric Failure",
    r"\b(volume matching|equated sets?|work[- ]matched)\b": "Volume Matching",
    r"\b(cross[- ]education|contralateral strength transfer)\b": "Cross-Education",
    r"\b(range of motion|partial ROM|ROM)\b": "Range of Motion",
    r"\b(velocity loss)\b": "Velocity Loss",
}
_VOCAB_RX = [(re.compile(p, re.I), t) for p, t in CONTROLLED_VOCABULARY.items()]
_PROTECT = re.compile(r"(\[\[.*?\]\]|`[^`\n]*`|\[[^\]\n]*\]\([^)\n]*\)|https?://\S+)")
_TABLE = re.compile(r"^\s*(?:>\s*)*\|")


def link_vocabulary(text: str) -> str:
    """Prima occorrenza di ogni concetto -> [[Target|testo originale]]. Protegge link, codice, URL, titoli, frontmatter
    e usa '\\|' dentro le tabelle."""
    seen: set[str] = set()
    out: list[str] = []
    in_code = False
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("```"):
            in_code = not in_code
        if in_code or s.startswith(("#", "<!--", "---")):
            out.append(line)
            continue
        pipe = "\\|" if _TABLE.match(line) else "|"
        parts = _PROTECT.split(line)
        for i in range(0, len(parts), 2):
            seg = parts[i]
            hits = sorted((m.start(), m.end(), t) for rx, t in _VOCAB_RX if t not in seen for m in [rx.search(seg)] if m)
            res, pos, last = [], 0, -1
            for a, b, t in hits:
                if a < last:
                    continue
                res += [seg[pos:a], f"[[{t}{pipe}{seg[a:b]}]]"]
                seen.add(t)
                pos = last = b
            res.append(seg[pos:])
            parts[i] = "".join(res)
        out.append("".join(parts))
    return "\n".join(out)


# ------------------------------------------------------------------ utilita' Markdown / blocchi gestiti

def callout(kind: str, title: str, lines: Iterable[str], fold: str = "") -> str:
    return "\n".join([f"> [!{kind}]{fold} {title}"] + [("> " + l) if l else ">" for l in lines])


def wrap(name: str, content: str) -> str:
    return f"<!-- LIT:BEGIN {name} -->\n{content}\n<!-- LIT:END {name} -->"


def upsert_block(body: str, name: str, block: str) -> str:
    rx = re.compile(rf"<!-- LIT:BEGIN {re.escape(name)} -->.*?<!-- LIT:END {re.escape(name)} -->", re.S)
    if rx.search(body):
        return rx.sub(lambda _: block, body, count=1)
    return body.rstrip("\n") + "\n\n" + block + "\n"


def strip_block(body: str, name: str) -> str:
    return re.sub(rf"<!-- LIT:BEGIN {re.escape(name)} -->.*?<!-- LIT:END {re.escape(name)} -->", "", body, flags=re.S)


def split_note(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end < 0:
        return {}, text
    return (yaml.safe_load(text[4:end]) or {}), text[end + 4:].lstrip("\n")


def join_note(fm: dict[str, Any], body: str) -> str:
    return dump_frontmatter(fm) + "\n" + body.lstrip("\n")


_EFFORT_IT = {"momentary_failure": "cedimento concentrico oggettivo", "rir_or_velocity_loss": "RIR / velocity loss",
              "volitional_fatigue": "cedimento volizionale", "fixed_prescription": "prescrizione fissa (no cedimento)",
              "unclear": "non chiaro"}
_TOOL_IT = {"mri_ct_panoramic": "MRI/CT/eco panoramica (fCSA)", "ultrasound_single_point": "ecografia punto singolo",
            "biopsy_fcsa": "biopsia (fCSA fibre)", "dexa": "DEXA", "bia": "BIA"}
_LEVEL_IT = {"high": "alto", "moderate": "medio", "low": "basso", "insufficient": "insufficiente"}


def _f(x: Any, nd: int = 2) -> str:
    return "-" if x is None else f"{x:.{nd}f}"


def _cell(s: Any) -> str:
    return str(s).replace("|", "/").replace("\n", " ")


def auto_limitations(doc: StudyAnalysisDocument, flags: Iterable[str] = ()) -> list[str]:
    d, p = doc.demographics, doc.protocol
    L: list[str] = []
    if doc.is_unilateral:
        L.append(f"Disegno unilaterale: unita' statistica = partecipante (N={d.completed_count}, arti={2 * d.completed_count}); "
                 "gli arti non sono osservazioni indipendenti. Rischio di cross-education: i dati di forza non sono attribuibili al solo arto allenato.")
    ts = d.training_status
    if ts == TrainingStatus.ambiguous:
        L.append("Stato di allenamento non definito: esito non generalizzabile.")
    elif ts in (TrainingStatus.untrained, TrainingStatus.recreational):
        L.append(f"Campione {ts.value}: non estrapolabile ad atleti avanzati (risposta e finestra di adattamento diverse).")
    elif ts == TrainingStatus.advanced and len(d.exact_inclusion_criteria.strip()) < 15:
        L.append("'Avanzato' dichiarato senza criteri oggettivi verificabili.")
    if p.effort == Effort.volitional:
        L.append("Sforzo = fatica volizionale (interruzione soggettiva): intensita' effettiva non standardizzata.")
    elif p.effort == Effort.rir:
        L.append("Sforzo = RIR/velocity loss: la stima del RIR e' soggettiva e meno accurata dal cedimento reale.")
    elif p.effort in (Effort.fixed_buffer, Effort.unclear):
        L.append("Sforzo non portato a cedimento o non descritto: volume efficace non confrontabile.")
    tools = {o.measurement_tool for o in doc.outcomes}
    if tools & {Tool.bia, Tool.dexa}:
        L.append("BIA/DEXA: stima indiretta della massa magra (idratazione, glicogeno, edema), non dell'ipertrofia regionale.")
    if Tool.us_single in tools:
        L.append("Ecografia a punto singolo: spessore muscolare != fCSA/volume; sensibile a edema e posizione della sonda.")
    if doc.outcomes and not any(o.tem_or_cv_reported for o in doc.outcomes):
        L.append("Errore tecnico di misura (TEM/CV/ICC) non riportato.")
    if doc.outcomes and not all(o.blinded_analyst for o in doc.outcomes):
        L.append("Analista della misura non in cieco o non riportato.")
    if doc.outcomes and not any(o.individual_data_reported for o in doc.outcomes):
        L.append("Nessun dato individuale (responder/non-responder non valutabili).")
    if any(o.p_kind == "within_group" for o in doc.outcomes):
        L.append("Almeno un p-value e' intra-gruppo: non prova differenza fra condizioni.")
    if d.completed_count < d.enrolled_count:
        L.append(f"Drop-out: {d.enrolled_count - d.completed_count}/{d.enrolled_count} ({100 * (1 - d.completed_count / d.enrolled_count):.0f}%).")
    if doc.audit_statistical_discrepancy:
        L.append("Discrepanza statistica: effetto riportato incompatibile col ricalcolo (tier warn/fail). Verifica manuale prima dell'uso.")
    names = {"methods_only_in_supplement": "Metodologia dettagliata solo nel materiale supplementare.",
             "methods_unavailable_do_not_infer": "Metodologia non disponibile nel testo: campi non dedotti.",
             "no_doi_found_using_sha256_urn": "DOI non trovato: identificatore = hash del PDF.",
             "segmentation_failed_full_text_fallback": "Segmentazione fallita: estrazione dal testo intero, affidabilita' ridotta."}
    L += [names[f] for f in flags if f in names]
    return L


def _n_cell(doc: StudyAnalysisDocument, o) -> str:
    a, b = o.condition_a, o.condition_b
    if doc.is_unilateral:
        return f"N={a.n_participants} ({2 * a.n_participants} arti)"
    return f"{a.n_participants}/{b.n_participants}" if b else f"N={a.n_participants}"


def _outcome_table(doc: StudyAnalysisDocument) -> list[str]:
    rows = ["| Regione | Strumento | N | Metrica | Riportato | Ricalcolato | Audit | p |", "|---|---|---|---|---|---|---|---|"]
    for o in doc.outcomes:
        a = o.audit
        p = f"{o.p_kind}: {o.p_value:.3g}" if o.p_value is not None else "-"
        rows.append(f"| {_cell(o.muscle_region)} | {_TOOL_IT[o.measurement_tool.value]} | {_n_cell(doc, o)} | "
                    f"{a.label_compared if a else '-'} | {_f(a.reported) if a else '-'} | {_f(a.recomputed) if a else '-'} | "
                    f"{a.tier.value if a else '-'} | {p} |")
    return rows


def render_paper_note(doc: StudyAnalysisDocument, nar: Narrative, meta: dict, job_id: str,
                      parse_flags: Iterable[str] = (), concepts: Iterable[str] = ()) -> tuple[str, str, dict]:
    """Ritorna (citekey, markdown, sidecar). Frontmatter piatto (scalari + liste atomiche) per Dataview."""
    flags, concepts = list(parse_flags), list(dict.fromkeys(concepts))
    ck = make_citekey(meta.get("authors", []), meta.get("year"), meta.get("title", ""), doc.doi)
    card = build_card(ck, doc, meta, nar.takeaway)
    d, p = doc.demographics, doc.protocol
    title = meta.get("title") or doc.doi
    spin = doc.spin_analysis
    fm = {
        "Disciplina": "Bodybuilding", "Type": ["Studio"], "citekey": ck, "aliases": [card.label, title], "doi": doc.doi, "pmid": meta.get("pmid"),
        "title": title, "year": meta.get("year"), "journal": meta.get("journal") or None,
        "authors": (meta.get("authors") or [])[:8] or None,
        "study_design": doc.study_design.value, "is_unilateral": doc.is_unilateral,
        "n_participants": d.completed_count, "n_enrolled": d.enrolled_count,
        "n_limbs": card.n_limbs, "sex": d.sex, "mean_age": d.mean_age,
        "training_status": d.training_status.value, "advanced_verified": card.advanced_verified,
        "effort": p.effort.value, "volume_matching": p.volume_matching.value,
        "weekly_frequency": p.weekly_frequency, "sets_per_session": p.sets_per_session,
        "target_muscles": p.target_muscle_groups,
        "measurement_tools": sorted({o.measurement_tool.value for o in doc.outcomes}), "best_tool": card.best_tool,
        "n_outcomes": len(doc.outcomes), "quality_score": doc.methodological_quality_score,
        "spin_detected": bool(spin and spin.unsupported_claim_detected),
        "spin_severity": spin.spin_severity if spin else "unassessed",
        "cross_education_risk": doc.cross_education_risk,
        "audit_statistical_discrepancy": doc.audit_statistical_discrepancy, "audit_worst_tier": card.worst_tier,
        "evidence_weight": card.weight, "evidence_level": card.level, "usable_for_conclusions": card.usable,
        "evidence_gates": card.gates, "parse_flags": flags or None, "concepts": concepts or None,
        "status": "needs_review" if (doc.audit_statistical_discrepancy or not card.usable) else "extracted",
        "ingest_job": job_id,
        "tags": ["bodybuilding", "personale", "studio-scientifico", f"evidenza-{card.level}"],
    }
    inc = d.exact_inclusion_criteria.strip().replace("\n", " ")
    meth = [
        f"**Disegno:** {doc.study_design.value}" + (" - unita' statistica = partecipante" if doc.is_unilateral else ""),
        f"**Campione:** N={d.completed_count}/{d.enrolled_count}" + (f" (arti: {2 * d.completed_count})" if doc.is_unilateral else "")
        + f" - {d.sex}" + (f", {d.mean_age:.1f} anni" if d.mean_age else ""),
        f"**Stato allenamento:** {d.training_status.value}" + (" (criteri oggettivi presenti)" if card.advanced_verified else "")
        + f" - criteri: \"{inc}\"",
        f"**Protocollo:** {p.exercise_name}; {p.weekly_frequency}x/sett; {p.sets_per_session} serie/sessione; {p.prescribed_rep_range}",
        f"**Sforzo:** {_EFFORT_IT[p.effort.value]}" + (f" (velocity loss {p.velocity_loss_threshold_pct:g}%)" if p.velocity_loss_threshold_pct else "")
        + f"; **Volume:** {p.volume_matching.value}",
        "**Misura:** " + ", ".join(_TOOL_IT[t] for t in fm["measurement_tools"]) + f"; analista in cieco: "
        + ("si" if doc.outcomes and all(o.blinded_analyst for o in doc.outcomes) else "no/n.r.")
        + "; TEM/CV: " + ("riportato" if any(o.tem_or_cv_reported for o in doc.outcomes) else "n.r."),
        f"**Qualita':** {doc.methodological_quality_score}/10; **peso evidenza:** {card.weight:.2f} ({_LEVEL_IT[card.level]})"
        + (f"; gate: {', '.join(card.gates)}" if card.gates else ""),
        "", nar.methods_summary,
    ]
    meth = [f"- {x}" if x and not x.startswith("- ") and x != nar.methods_summary else x for x in meth]
    lim = auto_limitations(doc, flags) + [x for x in nar.limitations if x not in auto_limitations(doc, flags)]
    diag = [f"{o.muscle_region}: {o.audit.diagnosis or '; '.join(o.audit.notes[:2])}" for o in doc.outcomes
            if o.audit and o.audit.tier.value != "pass" and (o.audit.diagnosis or o.audit.notes)]
    spin_block = (
        callout("danger" if spin.unsupported_claim_detected else "success", f"Spin: {spin.spin_severity}",
                [f"- **Claim abstract:** {spin.abstract_claim}", f"- {spin.spin_justification}"]) if spin
        else callout("warning", "Spin non valutato", ["Abstract non disponibile o non analizzato."]))
    concepts_block = wrap("concepts", "\n".join(f"- [[{c}]]" for c in concepts))
    body = "\n\n".join([
        f"# {title}",
        callout("summary", "Takeaway", [nar.takeaway] + [f"- {x}" for x in nar.practical_implications]),
        callout("info", "Metodologia", meth),
        callout("example", "Dati tabulari (ricalcolo deterministico)", _outcome_table(doc) + (["", "**Audit:**"] + [f"- {x}" for x in diag] if diag else [])),
        callout("warning", "Limiti metodologici", [f"- {x}" for x in lim] or ["- nessuno rilevato"]),
        spin_block,
        "## Concetti collegati\n" + concepts_block,
    ]) + "\n"
    body = link_vocabulary(body)
    fm["content_hash"] = content_hash(body)
    sidecar = {"document": doc.model_dump(mode="json"), "narrative": nar.model_dump(mode="json"),
               "meta": {k: v for k, v in meta.items() if k != "abstract_inverted"}, "parse_flags": flags}
    return ck, dump_frontmatter(fm) + "\n" + body, sidecar


# ------------------------------------------------------------------ blocco di evidenza per le note di concetto

_CLAIM_CALLOUT = {"solid": "success", "moderate": "info", "tentative": "question", "insufficient": "failure"}
_STRENGTH_IT = {"solid": "SOLIDA", "moderate": "MODERATA", "tentative": "PROVVISORIA", "insufficient": "INSUFFICIENTE"}


def _lk(card: EvidenceCard, table: bool = False) -> str:
    return f"[[{card.citekey}{chr(92) + '|' if table else '|'}{card.label}]]"


def render_evidence_block(concept: str, kind: str, syn: Synthesis, checked: list[CheckedClaim],
                          cards: dict[str, EvidenceCard]) -> str:
    ordered = sorted(cards.values(), key=lambda c: (-c.usable, -c.weight))
    usable = [c for c in ordered if c.usable]
    out: list[str] = [
        "## Evidenza scientifica",
        callout("abstract", f"Sintesi critica - {len(usable)}/{len(ordered)} studi utilizzabili - agg. {dt.date.today().isoformat()}",
                [syn.headline]),
        "### Gerarchia delle evidenze",
        "| Studio | Peso | Livello | Strumento | N | Stato allenamento | Sforzo | Spin | Audit | Uso |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for c in ordered:
        n = f"{c.n_participants} ({c.n_limbs} arti)" if c.n_limbs else str(c.n_participants)
        ts = c.training_status + (" (verificato)" if c.advanced_verified else " (non verificato)" if c.training_status == "advanced" else "")
        out.append(f"| {_lk(c, True)} | {c.weight:.2f} | {_LEVEL_IT[c.level]} | {_TOOL_IT.get(c.best_tool or '', '-')} | {n} | {ts} | "
                   f"{_EFFORT_IT[c.effort]} | {c.spin_severity} | {c.worst_tier or '-'} | {'si' if c.usable else 'NO'} |")
    out.append("")
    out.append("### Affermazioni")
    for i, ck in enumerate(checked, 1):
        c = ck.claim
        lines = [c.text, ""] if (c.supporting or c.contradicting or ck.notes) else [c.text]
        if c.supporting:
            lines.append("- Supporto: " + ", ".join(_lk(cards[k]) for k in c.supporting))
        if c.contradicting:
            lines.append("- Contrasto: " + ", ".join(_lk(cards[k]) for k in c.contradicting))
        lines += [f"- Nota: {n}" for n in ck.notes]
        out.append(callout(_CLAIM_CALLOUT[ck.final], f"{i}. {_STRENGTH_IT[ck.final]}", lines))
        out.append("")
    if syn.conflicts:
        out += ["### Conflitti fra studi"] + [f"- {x}" for x in syn.conflicts] + [""]
    rank = {"solid": 3, "moderate": 2, "tentative": 1, "insufficient": 0}
    rules = []
    for r in syn.practical_rules:
        ids = [i for i in r.claim_ids if 1 <= i <= len(checked)]
        if not ids:
            continue
        weakest = min((checked[i - 1].final for i in ids), key=rank.__getitem__)
        tag = "" if rank[weakest] >= 2 else "**Ipotesi, non conclusiva:** "
        rules.append(f"- {tag}{r.rule} _(affermazioni {', '.join(map(str, ids))}; forza {_STRENGTH_IT[weakest].lower()})_")
    if rules:
        out += ["### Regole operative"] + rules + [""]
    if syn.gaps:
        out += ["### Lacune"] + [f"- {x}" for x in syn.gaps] + [""]
    excl = [c for c in ordered if not c.usable]
    if excl:
        out += ["### Studi esclusi dalle conclusioni"] + [f"- {_lk(c)}: {', '.join(c.gates)}" for c in excl]
    return wrap("evidence", "\n".join(out).rstrip())
