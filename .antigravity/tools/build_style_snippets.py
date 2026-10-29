#!/usr/bin/env python3
"""
.antigravity/tools/build_style_snippets.py

Generatore di "Snippet Stilistici Compressi + Blueprint" per le 20 Macro-Discipline del Vault.
Estrae dalle Note Esempio reali (o genera da specifica dei profili disciplinari) uno snippet
blueprint compatto di 80-120 righe per ciascuna materia, salvandolo in:
.antigravity/snippets/<disciplina>_blueprint.md

Struttura standard di ogni Blueprint:
- Blocco 1: Regola di Accoppiamento con il Profilo Disciplinare
- Blocco 2: Esempio Reale di Frontmatter YAML + Introduzione Modello
- Blocco 3: Esempio Reale di Callout di Decodifica
- Blocco 4: Esempio Reale di Dimostrazione / Catena Causale a Sforzo Zero
- Blocco 5: Esempio di Tabella Riepilogativa
"""

import os
import re
import json
import sys

VAULT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SNIPPETS_DIR = os.path.join(VAULT_ROOT, ".antigravity", "snippets")
DISCIPLINES_DIR = os.path.join(VAULT_ROOT, ".antigravity", "disciplines")
STYLE_MAP_FILE = os.path.join(VAULT_ROOT, ".antigravity", "style-examples.json")

DISCIPLINE_METADATA = [
    {
        "slug": "matematica",
        "name": "Matematica",
        "polo": "università",
        "primary_note": "Matematica/Numeri Interi Relativi.md",
        "alt_notes": ["Matematica/Teorema di Unicità del Limite.md", "Matematica/Elementi di Logica Matematica.md"],
        "callout_type": "Decodifica Logico-Formale",
        "causal_name": "Dimostrazione Algebrica / Costruzione a Sforzo Zero"
    },
    {
        "slug": "informatica",
        "name": "Informatica",
        "polo": "università",
        "primary_note": "Informatica/Ricerca Binaria (Binary Search).md",
        "alt_notes": [],
        "callout_type": "Decodifica Tecnica",
        "causal_name": "Traccia di Esecuzione in Memoria e Complessità"
    },
    {
        "slug": "fisica",
        "name": "Fisica",
        "polo": "università",
        "primary_note": "Fisica/Teorema dell'Energia Cinetica e Lavoro.md",
        "alt_notes": [],
        "callout_type": "Decodifica Fisico-Matematica",
        "causal_name": "Derivazione Matematica Passo-Passo con Giustificazione Fisica"
    },
    {
        "slug": "intelligenza-artificiale",
        "name": "Intelligenza Artificiale",
        "polo": "università",
        "primary_note": "Intelligenza Artificiale/Discesa del Gradiente e Varianti Stocastiche.md",
        "alt_notes": [],
        "callout_type": "Decodifica Matematico-Algoritmica",
        "causal_name": "Derivazione Vettoriale del Gradiente e Aggiornamento Pesi"
    },
    {
        "slug": "neuroscienze",
        "name": "Neuroscienze",
        "polo": "università",
        "primary_note": "Biologia e Neuroscienze/Potenziale di Membrana e Potenziale d'Azione.md",
        "alt_notes": [],
        "callout_type": "Decodifica Elettrofisiologica e Recettoriale",
        "causal_name": "Catena Biofisica Passo-Passo dell'Event Cascade"
    },
    {
        "slug": "biologia",
        "name": "Biologia",
        "polo": "università",
        "primary_note": "Biologia/Replicazione del DNA, Trascrizione e Traduzione.md",
        "alt_notes": [],
        "callout_type": "Decodifica Molecolare e Cinetica Enzimatica",
        "causal_name": "Cascata Biochimica e Flusso dell'Informazione Genetica"
    },
    {
        "slug": "bodybuilding",
        "name": "Bodybuilding",
        "polo": "personale",
        "primary_note": "Bodybuilding/Bicipite Brachiale e Flessori del Gomito.md",
        "alt_notes": [],
        "callout_type": "Decodifica Biomeccanica e Neuromuscolare",
        "causal_name": "Analisi delle Forze, Braccio del Momento e Stimolo Ipertrofico"
    },
    {
        "slug": "nutrizione-e-salute",
        "name": "Nutrizione e Salute",
        "polo": "personale",
        "primary_note": None,
        "alt_notes": [],
        "callout_type": "Decodifica Fisiologico-Metabolica",
        "causal_name": "Cinetica di Assorbimento e Cascata Ormonale a Sforzo Zero"
    },
    {
        "slug": "chimica",
        "name": "Chimica",
        "polo": "personale",
        "primary_note": "Chimica/Legame Chimico, Elettronegatività, Ibridazione degli Orbitali e Polarità Molecolare.md",
        "alt_notes": [],
        "callout_type": "Decodifica Termodinamica e Orbitale",
        "causal_name": "Meccanismo di Reazione ed Equilibrio di Gibbs"
    },
    {
        "slug": "droghe",
        "name": "Droghe",
        "polo": "personale",
        "primary_note": None,
        "alt_notes": [],
        "callout_type": "Decodifica Farmacologica e Neurochimica",
        "causal_name": "Farmacocinetica e Cascata di Segnalazione Sinaptica"
    },
    {
        "slug": "tecnologia-ed-elettronica",
        "name": "Tecnologia ed Elettronica",
        "polo": "personale",
        "primary_note": "Tecnologia ed Elettronica/Come Funziona il Wi-Fi.md",
        "alt_notes": [],
        "callout_type": "Decodifica Hardware e Principio Fisico",
        "causal_name": "Catena di Funzionamento Fisico dal Segnale all'Output"
    },
    {
        "slug": "musica-e-industria-musicale",
        "name": "Musica e Industria Musicale",
        "polo": "personale",
        "primary_note": "Musica e Industria Musicale/Come funziona l'industria musicale.md",
        "alt_notes": [],
        "callout_type": "Decodifica Discografica e Contrattuale",
        "causal_name": "Filiera di Ripartizione dei Diritti e Flussi di Cassa"
    },
    {
        "slug": "arte-e-storia-dellarte",
        "name": "Arte e Storia dell'Arte",
        "polo": "personale",
        "primary_note": "Arte/Metafisica VS Surrealismo.md",
        "alt_notes": [],
        "callout_type": "Decodifica Formale e Iconografica",
        "causal_name": "Analisi Strutturale dell'Opera e Lettura Semiotica"
    },
    {
        "slug": "filosofia",
        "name": "Filosofia",
        "polo": "personale",
        "primary_note": "Filosofia/Nietzsche/Nichilismo.md",
        "alt_notes": [],
        "callout_type": "Decodifica Concettuale e Filologica",
        "causal_name": "Deduzione Argomentativa e Confutazione a Sforzo Zero"
    },
    {
        "slug": "letteratura",
        "name": "Letteratura",
        "polo": "personale",
        "primary_note": "Letteratura/Leopardi/Il Pessimismo Cosmico e il \"Dialogo della Natura e di un Islandese.md",
        "alt_notes": [],
        "callout_type": "Decodifica Retorica e Poetica",
        "causal_name": "Commento Lineare ed Ermeneutica del Testo"
    },
    {
        "slug": "analisi-narrativa",
        "name": "Analisi Narrativa",
        "polo": "personale",
        "primary_note": "Analisi Narrativa/Bleach/Sosuke Aizen.md",
        "alt_notes": [],
        "callout_type": "Decodifica Tematica e Archetipica",
        "causal_name": "Arco di Trasformazione e Conflitto Ideologico"
    },
    {
        "slug": "storia",
        "name": "Storia",
        "polo": "personale",
        "primary_note": "Storiа/Crisi del 1929.md",
        "alt_notes": [],
        "callout_type": "Decodifica Storiografica e Documentale",
        "causal_name": "Catena Causale degli Eventi e Analisi Strutturale"
    },
    {
        "slug": "politica-e-geopolitica",
        "name": "Politica e Geopolitica",
        "polo": "personale",
        "primary_note": "Politica e Geopolitica/La Geopolitica dei Semiconduttori, TSMC e la Questione di Taiwan.md",
        "alt_notes": [],
        "callout_type": "Decodifica Strategica e Dottrinale",
        "causal_name": "Analisi di Gioco, Vettori di Potere e Chokepoints"
    },
    {
        "slug": "economia-e-finanza",
        "name": "Economia e Finanza",
        "polo": "personale",
        "primary_note": "Economia e Finanza/Inflazione, Tassi di Interesse e Meccanismo di Trasmissione della Politica Monetaria.md",
        "alt_notes": [],
        "callout_type": "Decodifica Macroeconomica e Strumentale",
        "causal_name": "Canale di Trasmissione Causale da Politica a Economia Reale"
    },
    {
        "slug": "psicologia",
        "name": "Psicologia",
        "polo": "personale",
        "primary_note": "Psicologia/Dissonanza Cognitiva (Festinger) e Meccanismi di Autogiustificazione.md",
        "alt_notes": [],
        "callout_type": "Decodifica Psicologica e Neurocognitiva",
        "causal_name": "Modello del Processo Cognitivo e Validazione Empirica"
    }
]


def find_file_in_vault(vault_root, relative_candidate):
    if not relative_candidate:
        return None
    direct = os.path.join(vault_root, relative_candidate)
    if os.path.isfile(direct):
        return direct
    
    basename = os.path.basename(relative_candidate)
    for root, dirs, files in os.walk(vault_root):
        if any(skip in root for skip in [".git", ".antigravity", ".obsidian", ".trash"]):
            continue
        if basename in files:
            return os.path.join(root, basename)
    return None


def extract_yaml_and_intro(text):
    yaml_block = ""
    intro_block = ""
    
    yaml_match = re.search(r"^---\n(.*?)\n---", text, re.DOTALL)
    if yaml_match:
        yaml_block = yaml_match.group(0).strip()
        rest = text[yaml_match.end():].strip()
    else:
        rest = text.strip()
    
    intro_lines = []
    for line in rest.splitlines():
        if line.startswith("# ") or line.startswith("## "):
            break
        intro_lines.append(line)
    
    intro_block = "\n".join(intro_lines).strip()
    # Limita l'introduzione a 1-2 paragrafi compatti
    intro_paragraphs = [p.strip() for p in intro_block.split("\n\n") if p.strip()]
    if intro_paragraphs:
        intro_block = intro_paragraphs[0]
        if len(intro_paragraphs) > 1 and len(intro_block) < 300:
            intro_block += "\n\n" + intro_paragraphs[1]
    
    return yaml_block, intro_block


def extract_callout(text, target_type):
    callout_pattern = re.compile(r"^>\s*\[!(?:note|info|tip|important|abstract|warning)\].*?$", re.MULTILINE)
    matches = list(callout_pattern.finditer(text))
    
    if not matches:
        return None
    
    best_callout = None
    for m in matches:
        start_idx = m.start()
        lines = []
        cur_text = text[start_idx:]
        for line in cur_text.splitlines():
            if line.startswith(">"):
                lines.append(line)
            elif not line.strip() and lines:
                lines.append(line)
            else:
                break
        
        callout_text = "\n".join(lines).strip()
        if "Decodifica" in callout_text or (target_type and target_type in callout_text):
            best_callout = callout_text
            break
        if not best_callout and len(lines) >= 4:
            best_callout = callout_text
            
    if best_callout:
        # Se il callout è troppo lungo (oltre 25 righe), ridimensionalo preservando la struttura
        callout_lines = best_callout.splitlines()
        if len(callout_lines) > 20:
            trimmed = callout_lines[:18]
            trimmed.append("> - *[... ulteriori parametri formattati con lo stesso schema analitico]*")
            best_callout = "\n".join(trimmed)
            
    return best_callout


def extract_causal_block(text):
    headers = list(re.finditer(r"^(?:##|###)\s+(.*?)$", text, re.MULTILINE))
    priorities = ["dimostrazione", "derivazione", "catena", "passo-passo", "algoritmo", "funzionamento", "meccanismo", "analisi"]
    
    for kw in priorities:
        for i, h in enumerate(headers):
            h_title = h.group(1).lower()
            if kw in h_title:
                start_pos = h.start()
                end_pos = len(text)
                for next_h in headers[i+1:]:
                    if h.group(0).startswith("### ") and (next_h.group(0).startswith("### ") or next_h.group(0).startswith("## ")):
                        end_pos = next_h.start()
                        break
                    elif h.group(0).startswith("## ") and next_h.group(0).startswith("## "):
                        end_pos = next_h.start()
                        break
                candidate = text[start_pos:end_pos].strip()
                lines = candidate.splitlines()
                if len(lines) > 28:
                    trimmed = lines[:24]
                    trimmed.append("\n*[I passaggi analitici continuano esplicitando ogni deduzione logica e causale senza alcun salto]*")
                    candidate = "\n".join(trimmed)
                if len(candidate.strip()) > 80:
                    return candidate
            
    if headers:
        idx = 1 if len(headers) > 1 else 0
        start_pos = headers[idx].start()
        end_pos = headers[idx+1].start() if idx+1 < len(headers) else len(text)
        chosen_section = text[start_pos:end_pos].strip()
        lines = chosen_section.splitlines()
        if len(lines) > 28:
            trimmed = lines[:24]
            trimmed.append("\n*[I passaggi analitici continuano esplicitando ogni deduzione logica e causale senza alcun salto]*")
            chosen_section = "\n".join(trimmed)
        return chosen_section
            
    return None


def extract_table(text):
    table_pattern = re.compile(r"(\|[^\n]+\|\n\|[-:| ]+\|\n(?:\|[^\n]+\|\n?)+)")
    tables = table_pattern.findall(text)
    if not tables:
        return None
    # Prendi la tabella con il miglior bilanciamento di righe
    for t in tables:
        lines = t.strip().splitlines()
        if 3 <= len(lines) <= 12:
            return t.strip()
    return tables[0].strip()


def build_fallback_blueprint(meta):
    """Costruisce un blueprint formale coerente con il profilo per le discipline senza nota esempio fisica."""
    slug = meta["slug"]
    name = meta["name"]
    polo = meta["polo"]
    callout_type = meta["callout_type"]
    causal_name = meta["causal_name"]
    
    if slug == "nutrizione-e-salute":
        yaml_block = f"""---
Disciplina: {name}
Type:
  - Concetto
tags:
  - nutrizione_e_salute
  - {polo}
aliases:
  - Sintesi Proteica Muscolare
  - MPS
  - Soglia Leucinica
---"""
        intro = """La **Sintesi Proteica Muscolare (MPS)** rappresenta il processo biochimico cellulare mediante il quale gli aminoacidi plasmatici vengono incorporati all'interno delle proteine contrattili del miocita (actina e miosina). Insieme al Degradamento Proteico Muscolare (MPB), determina il bilancio proteico netto del tessuto muscolare scheletrico."""
        callout = f"""> [!note] {callout_type}: La Soglia Leucinica e l'Attivazione di mTORC1
> - **Parametro Fisiologico**: Concentrazione plasmatica di leucina $\\ge 3.0\\text{{ g}}$ per bolo proteico.
> - **Meccanismo Molecolare**: La leucina si lega al sensore intracellulare Sestrin2, sbloccando le GTPasi Rag e reclutando il complesso mTORC1 sulla membrana lisosomiale, dove viene attivato da Rheb.
> - **Cosa significa in concreto (Sforzo Zero)**: Non basta consumare proteine; per innescare l'avvio della costruzione muscolare serve un "picco di concentrazione" di leucina. Dosi sub-ottimali non superano la soglia del sensore cellulare e lasciano inattiva la cascata."""
        causal = f"""### {causal_name}

1. **Assunzione e Digestione:** Il bolo proteico viene scisso nello stomaco e assorbito nel duodeno sotto forma di di-peptidi, tri-peptidi e aminoacidi liberi.
2. **Iperaminoacidemia e Picco di Leucina:** Entro 45–90 minuti si raggiunge il picco ematico di EAA (Aminoacidi Essenziali).
3. **Fosforilazione delle Chinasi a Valle:** mTORC1 fosforila p70S6K e 4E-BP1, rimuovendo l'inibizione su eIF4E e avviando la traduzione dei ribosomi.
4. **Periodo Refrattario ("Muscle Full Effect"):** Dopo circa 120–180 minuti, la sintesi proteica torna ai livelli basali anche in presenza di aminoacidi circolanti elevati."""
        table = """| Parametro Nutrizionale | Valore Target / Range | Meccanismo Fisiologico |
| :--- | :--- | :--- |
| **Quota Proteica Giornaliera** | 1.6 – 2.2 g/kg/die | Saturazione del turn-over proteico dell'intero organismo |
| **Leucina per Pasto** | 2.5 – 3.5 g | Superamento della soglia del sensore Sestrin2/mTORC1 |
| **Frequenza dei Pasti** | Ogni 3 – 5 ore | Rispetto del periodo refrattario cellulare (Muscle Full) |"""

    elif slug == "droghe":
        yaml_block = f"""---
Disciplina: {name}
Type:
  - Analisi
tags:
  - droghe
  - {polo}
aliases:
  - MDMA
  - 3,4-Metilendiossimetanfetamina
  - Entactogeni
---"""
        intro = """L'**MDMA (3,4-metilendiossimetanfetamina)** è una molecola psicoattiva sintetica appartenente alla classe chimica delle fenetilammine e delle anfetamine sostituite. Si distingue per un profilo farmacodinamico peculiare classificato come *entattogeno/empatogeno*, mediato da un massiccio rilascio presinaptico di monoammine, con netta preponderanza serotoninergica."""
        callout = f"""> [!note] {callout_type}: Trasportatore VMAT-2 e Inversione di SERT
> - **Bersaglio Molecolare**: VMAT-2 (Vesicular Monoamine Transporter 2) e SERT (Serotonin Transporter).
> - **Meccanismo Sinaptico**: L'MDMA penetra nel terminale presinaptico e inibisce VMAT-2, impedendo il re-immagazzinamento della serotonina nelle vescicole. La serotonina libera citosolica costringe il SERT a funzionare al contrario (retro-trasporto verso la fessura sinaptica).
> - **Cosa significa in concreto (Sforzo Zero)**: La molecola non si limita a stimolare i recettori; svuota letteralmente le scorte interne del neurone direttamente nello spazio di comunicazione, innescando un'ondata neurochimica transitoria ad altissima intensità."""
        causal = f"""### {causal_name}

1. **Assorbimento Gastrointestinale e Passaggio BEE:** Rapida biodisponibilità orale e attraversamento della Barriera Emato-Encefalica grazie alla lipofilia della catena metilendiossi.
2. **Cascata Neuroendocrina (Ossitocina e Prolattina):** L'iper-attivazione dei recettori $5\\text{{-HT}}_{{1A}}$ e $5\\text{{-HT}}_{{2A}}$ stimola l'ipotalamo a rilasciare elevate concentrazioni di ossitocina, spiegando il marcato effetto prosociale e di apertura emozionale.
3. **Deplezione e Periodo di Recupero ("Comedown"):** Esaurite le scorte vescicolari di monoammine e inattivati temporaneamente gli enzimi di sintesi (Triptofano Idrossilasi), si verifica una temporanea deplezione serotoninergica della durata di 48–72 ore."""
        table = """| Recettore / Target | Affinità / Effetto | Esito Neurobiologico Clinico |
| :--- | :--- | :--- |
| **SERT (Inversione)** | Massiccio efflusso di $5\\text{-HT}$ | Amplificazione empatica, distorsione temporale, benessere |
| **DAT e NET** | Rilascio di Dopamina e Noradrenalina | Tachicardia, ipertensione arteriosa, iperarousal psicomotorio |
| **Recettore $5\\text{-HT}_{2A}$** | Agonismo parziale diretto | Lievi alterazioni percettive visive, euforia emotiva |"""

    else:
        tag_name = meta['slug'].replace('-', '_')
        yaml_block = f"""---
Disciplina: {name}
Type:
  - Concetto
tags:
  - {tag_name}
  - {polo}
aliases:
  - Esempio Concettuale {name}
---"""
        intro = f"""La trattazione di questo argomento in **{name}** segue rigorosamente i principi del Vault Antigravity: massima precisione formale nei costrutti specialistici, ma decodifica immediata e accessibilità concettuale a sforzo cognitivo zero."""
        callout = f"""> [!note] {callout_type}: Concetto Fondamentale e Struttura Chiave
> - **Termine / Costrutto Tecnico**: Definizione del parametro fondante della disciplina.
> - **Come si legge / Articolazione**: Descrizione analitica del comportamento del sistema.
> - **Cosa significa in concreto (Sforzo Zero)**: Traduzione pragmatica dell'astrazione teorica in una dinamica tangibile e visivamente evidente."""
        causal = f"""### {causal_name}

1. **Fase Iniziale / Condizioni al Contorno:** Definizione dello stato di partenza e dei vincoli strutturali del sistema.
2. **Evoluzione / Trasmissione Causale:** Analisi del meccanismo trasmissivo passaggio per passaggio senza salti logici né deduzioni implicite.
3. **Stato Finale / Risultato Stabile:** Dimostrazione della conclusione e verifica delle implicazioni empiriche o formali."""
        table = """| Componente / Variabile | Ruolo nel Sistema | Implicazione Pratica |
| :--- | :--- | :--- |
| **Elemento Fondamentale** | Innesco della dinamica | Stabilisce le condizioni al contorno |
| **Meccanismo Trasmissivo** | Mediazione dell'effetto | Determina la velocità e la stabilità del processo |
| **Risultato Finale** | Output verificabile | Convalida sperimentale o formale del modello |"""

    return yaml_block, intro, callout, causal, table


def generate_blueprint_for_discipline(meta):
    slug = meta["slug"]
    name = meta["name"]
    polo = meta["polo"]
    
    real_note_path = find_file_in_vault(VAULT_ROOT, meta["primary_note"])
    if not real_note_path:
        for alt in meta.get("alt_notes", []):
            real_note_path = find_file_in_vault(VAULT_ROOT, alt)
            if real_note_path:
                break
                
    if real_note_path and os.path.isfile(real_note_path):
        with open(real_note_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
            
        yaml_block, intro_block = extract_yaml_and_intro(raw_text)
        callout_block = extract_callout(raw_text, meta["callout_type"])
        causal_block = extract_causal_block(raw_text)
        table_block = extract_table(raw_text)
        
        # Se ci sono alt_notes, controlla se una di esse offre un blocco dimostrativo superiore
        if meta.get("alt_notes"):
            for alt in meta["alt_notes"]:
                alt_path = find_file_in_vault(VAULT_ROOT, alt)
                if alt_path and os.path.isfile(alt_path):
                    with open(alt_path, "r", encoding="utf-8") as af:
                        alt_text = af.read()
                        alt_causal = extract_causal_block(alt_text)
                        if alt_causal and ("dimostrazione" in alt_causal.lower() or "derivazione" in alt_causal.lower()):
                            causal_block = alt_causal
                            break
        
        # Fallback parziale per eventuali blocchi non rintracciabili
        fb_yaml, fb_intro, fb_callout, fb_causal, fb_table = build_fallback_blueprint(meta)
        if not yaml_block:
            yaml_block = fb_yaml
        if not intro_block:
            intro_block = fb_intro
        if not callout_block:
            callout_block = fb_callout
        if not causal_block:
            causal_block = fb_causal
        if not table_block:
            table_block = fb_table
            
        source_desc = f"Estratto dalla Nota Esempio reale: `{os.path.relpath(real_note_path, VAULT_ROOT)}`"
    else:
        yaml_block, intro_block, callout_block, causal_block, table_block = build_fallback_blueprint(meta)
        source_desc = f"Costruito dalle specifiche e dal contratto di disciplina: `.antigravity/disciplines/{slug}.md`"

    # Composizione del Blueprint standard 80-120 righe
    coupling_rule = f"""<!--
================================================================================
SNIPPET BLUEPRINT COMPRESSO — DISCIPLINA: {name.upper()}
{source_desc}
================================================================================
-->

### BLOCCO 1 — REGOLA DI ACCOPPIAMENTO CON IL PROFILO DELLA MATERIA
Quando scrivi una nota o un MOC per **{name}** ({polo.upper()}):
1. **Regole Logiche e Verifiche:** Segui rigorosamente il rispettivo file `.antigravity/disciplines/{slug}.md` (obblighi formali, controlli incrociati e verifiche evidenziali).
2. **Modello Visivo e Tonalità:** Utilizza i 4 blocchi modello qui sotto come *calibro stilistico* per frontmatter, introduzione intuitiva, callout di decodifica, catene causali/dimostrative e tabelle.
3. **Sforzo Cognitivo Zero:** Ogni formula, termine specialistico o datazione deve possedere la sua immediata traduzione discorsiva e un'anatomia visiva chiara."""

    block2 = f"""### BLOCCO 2 — ESEMPIO REALE DI FRONTMATTER YAML + INTRODUZIONE MODELLO
```yaml
{yaml_block.replace('---', '').strip()}
```

{intro_block}"""

    block3 = f"""### BLOCCO 3 — ESEMPIO REALE DI CALLOUT DI DECODIFICA
{callout_block}"""

    block4 = f"""### BLOCCO 4 — ESEMPIO REALE DI DIMOSTRAZIONE / CATENA CAUSALE A SFORZO ZERO
{causal_block}"""

    block5 = f"""### BLOCCO 5 — ESEMPIO DI TABELLA RIEPILOGATIVA
{table_block}"""

    full_blueprint = f"""{coupling_rule}

---

{block2}

---

{block3}

---

{block4}

---

{block5}
"""
    return full_blueprint


def main():
    os.makedirs(SNIPPETS_DIR, exist_ok=True)
    print(f"[*] Cartella Snippets: {SNIPPETS_DIR}")
    
    generated_count = 0
    for meta in DISCIPLINE_METADATA:
        slug = meta["slug"]
        out_file = os.path.join(SNIPPETS_DIR, f"{slug}_blueprint.md")
        content = generate_blueprint_for_discipline(meta)
        
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(content)
            
        line_count = len(content.splitlines())
        print(f"[+] Generato: {slug}_blueprint.md ({line_count} righe)")
        generated_count += 1
        
    # Gestione Symlinks per Alias comuni
    aliases = [
        ("arte_blueprint.md", "arte-e-storia-dellarte_blueprint.md"),
        ("musica-e-industria_blueprint.md", "musica-e-industria-musicale_blueprint.md")
    ]
    for alias_name, target_name in aliases:
        alias_path = os.path.join(SNIPPETS_DIR, alias_name)
        if os.path.exists(alias_path) or os.path.islink(alias_path):
            os.remove(alias_path)
        os.symlink(target_name, alias_path)
        print(f"[+] Symlink creato: {alias_name} -> {target_name}")

    print(f"\n[OK] Generazione completata con successo: {generated_count} blueprint generati in .antigravity/snippets/")


if __name__ == "__main__":
    main()
