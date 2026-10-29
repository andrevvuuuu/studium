# Profilo Disciplinare: Nutrizione e Salute

> [!IMPORTANT]
> **Polo:** `#personale` | **Tag:** `#nutrizione_e_salute`  
> Questo profilo regola le note di Biochimica Nutrizionale, Composizione Corporea, Fabbisogno Energetico, Marcatori Ematici e Integrazione Funzionale.  
> **Integrazione Tool Obbligatoria:** `pubmed_search.py` (interrogazione sistematica delle evidenze cliniche sull'uomo).

---

## Filosofia e Regole Fondamentali

1. **Il Primato della Termodinamica e del Bilancio Energetico:**
   - La prima legge della termodinamica ($\Delta E = E_{\text{in}} - E_{\text{out}}$) è invalicabile: nessuna dieta o manipolazione ormonale può aggirare il bilancio calorico netto nel determinare la variazione di massa corporea.
2. **Distinzione Tra Traccianti Isotopici Acuti e Outcome Longitudinali:**
   - Negli studi su proteine e ipertrofia, distingui rigorosamente tra misurazioni acute del tasso di sintesi proteica frazionaria (*Fractional Synthetic Rate*, FSR con traccianti isotopici nelle prime 4 ore) e l'ipertrofia o ritenzione azotata reale misurata dopo settimane/mesi di intervento controllato.
3. **Rigore negli Studi Clinici (Isocalorici ed Isoproteici):**
   - Per valutare l'effetto di una specifica variabile (es. digiuno intermittente, dieta chetogenica, timing dei nutrienti), cita studi che mantengano rigidamente costanti **le calorie totali** e **l'apporto proteico totale**. Qualsiasi beneficio rilevato in condizioni non isocaloriche è quasi sempre un artefatto del deficit calorico o del differente introito proteico.
4. **Ponti con le Altre Discipline:**
   - Collega le vie metaboliche a `Biologia` (respirazione e insulina), `Chimica` (struttura di trigliceridi e carboidrati) e `Bodybuilding` (gestione delle fasi di Bulk, Cut e Body Recomposition).

---

## Il Callout Obbligatorio: "Decodifica Biochimica e Molecolare"

```markdown
> [!note] Decodifica Biochimica e Molecolare: Sintesi Proteica Muscolare (MPS) e Soglia Leucinica
> **1. Equazione o Relazione del Bilancio Proteico Netto (NPB):**
> $$ \text{NPB} = \text{MPS} - \text{MPB} $$
>
> **2. Come si legge e Parametri Fisiologici:**
> "Il Bilancio Proteico Netto ($\text{NPB}$, Net Protein Balance) è determinato dalla differenza algebrica tra il Tasso di Sintesi Proteica Muscolare ($\text{MPS}$) e il Tasso di Degradazione Proteica Muscolare ($\text{MPB}$). Un accumulo netto di massa muscolare magra ($\text{NPB} > 0$) si verifica esclusivamente quando la sintesi supera la degradazione."
>
> **3. Meccanismo Molecolare e Sensore Sestrin2:**
> La leucina agisce come interruttore molecolare legandosi al sensore citosolico *Sestrin2*, rilasciando l'inibizione su GATOR2 e promuovendo l'ancoraggio delle GTPasi Rag alla membrana lisosomiale. Qui mTORC1 viene reclutato e attivato tramite fosforilazione di p70S6K e 4E-BP1. Per saturare la risposta di MPS in un singolo pasto è necessaria una dose soglia di circa $2.5\text{--}3.0\text{ g}$ di leucina pura (corrispondente a circa $25\text{--}40\text{ g}$ di proteine ad alto valore biologico).
```

---

## Scaletta Strutturale delle Note di Nutrizione e Salute

### 1. Frontmatter YAML
```yaml
---
Disciplina: Nutrizione e Salute
Type:
  - Concetto # oppure Metodo se si tratta di un protocollo nutrizionale
tags:
  - nutrizione_e_salute
  - personale
aliases:
  - Muscle Protein Synthesis
  - MPS
  - Soglia Leucinica
  - Timing Proteico
---
```

### 2. Fisiologia Digestiva, Cinetica di Assorbimento e Destino Metabolico
- Digestione gastrica e duodenale (pepsina, tripsina, chimotripsina, lipasi pancreatica).
- Meccanismi di trasporto enterocitario (trasportatori PepT1, SGLT1, GLUT5, micelle lipidiche).
- Transito epatico e biodisponibilità sistemica.

### 3. Callout Decodifica Biochimica e Molecolare

### 4. Impatto su Parametri Ematici, Salute Sistemica e Sazietà
- **Quadro Lipidico ed Ematochimico:** Effetti su colesterolo totale, LDL, HDL, trigliceridi, glicemia a digiuno, $\text{HbA}_{1c}$, proteina C-reattiva ad alta sensibilità ($\text{hs-CRP}$) e transaminasi.
- **Regolazione Neuroendocrina della Sazietà:** Secrezione di grelina (gastrica, oressizzante) vs peptide YY (PYY), GLP-1 e colecistochinina (CCK, anoressizzanti).
- **Longevità e Autofagia:** Bilanciamento tra attivazione anabolica di mTORC1 e stimolo catabolico/autofagico di AMPK.

### 5. Evidenza Empirica e Letteratura (PubMed Live Engine)
Esecuzione di `pubmed_search.py` per citare studi clinici controllati con link PMID diretti:

| Studio | PMID | Disegno e Campione | Metodica di Misura | Risultato Chiave | Limiti |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Morton et al. (2018)** | [28698222](https://pubmed.ncbi.nlm.nih.gov/28698222/) | Metanalisi su 49 studi e 1863 partecipanti | DEXA e biopsia muscolare con traccianti | L'introito proteico ottimale per l'ipertrofia satura a $\approx 1.62\text{ g/kg/die}$ (intervallo di confidenza fino a $2.2\text{ g/kg/die}$) | Eterogeneità tra partecipanti giovani e anziani |

### 6. Callout Obbligatori di Grado e Confronto Miti
```markdown
> [!info] Grado di Evidenza e Consenso Scientifico
> L'evidenza sul fabbisogno proteico ottimale per soggetti che svolgono allenamento con sovraccarichi è considerata **FORTE (Grado A)**: apporti superiori a $2.2\text{ g/kg/die}$ in atleti euglicemici ed eucalorici non offrono vantaggi statisticamente significativi sull'accrescimento muscolare sarcomerico.

> [!warning] Confronto Falsi Miti vs Letteratura PubMed
> Il mito comune secondo cui *"il corpo non può assimilare più di 30 grammi di proteine a pasto"* è biologicamente errato: l'intero carico proteico ingerito viene digerito e assorbito nel lume intestinale; ciò che satura transitoriamente è solo la velocità acuta di sintesi proteica muscolare (*muscle-full effect*), mentre gli amminoacidi rimanenti vengono impiegati per la riparazione viscerale, la sintesi di peptidi immunitari o l'ossidazione energetica.
```

### 7. Tabelle Quantitative di Applicazione Pratica
- Fabbisogno per fase:
  - *Bulk (Surplus):* $1.6\text{--}2.0\text{ g/kg/die}$ di proteine, carboidrati alti ($4\text{--}7\text{ g/kg}$), grassi moderati ($0.8\text{--}1.2\text{ g/kg}$).
  - *Cut (Deficit):* $2.0\text{--}2.4\text{ g/kg/die}$ di proteine per contrastare il catabolismo muscolare in bilancio energetico negativo.
  - *Ripartizione nei Pasti:* 3-5 pasti giornalieri distanziati di 3-4 ore, ciascuno con almeno $0.4\text{ g/kg}$ di proteine ad elevata quota di amminoacidi ramificati (BCAA).
