# Profilo Disciplinare: Bodybuilding

> [!IMPORTANT]
> **Polo:** `#personale` | **Tag:** `#bodybuilding`  
> Questo profilo stabilisce l'architettura scientifica, anatomica ed evidenziale per tutte le note di Ipertrofia Muscolare, Neuromeccanica, Esercizi, Programmazione e Fisiologia dell'Esercizio con Sovraccarichi.  
> **Integrazione Tool Obbligatoria:** motore delle evidenze `evidence_search.py` (ricerca e analisi critica degli studi per ogni nota/esercizio) e `youtube_watch.py` (estrazione fotogrammi di setup e curve di resistenza).

---

## Filosofia e Regole Fondamentali

1. **Rifiuto Dogmatico del "Bro-Science" e dell'Approssimazione:**
   - Nel vault non esistono sensazioni vaghe ("brucia il muscolo", "pompa bene"). Ogni affermazione deve essere ricondotta alla neuromeccanica, alla biofisica sarcomerica o a solidi dati empirici.
2. **Distinzione Epistemologica Tra EMG Acuto e Ipertrofia Longitudinale:**
   - È severamente vietato equiparare un picco di segnale elettromiografico di superficie (sEMG) all'ipertrofia muscolare a lungo termine. L'sEMG misura solo l'attività mioelettrica acuta (spesso falsata da cross-talk o variazione della conduttanza cutanea) e ha scarsa correlazione predittiva con la crescita muscolare reale misurata con Risonanza Magnetica (MRI) o Ultrasuoni (US).
3. **Gerarchia Rigorosa dei Distretti Anatomici:**
   - I grandi distretti muscolari o articolari sono sempre **Sub-MOC** (es. [[Bicipiti e Flessori del Gomito MOC]], [[Gran Dorsale e Tirate MOC]], [[Quadricipiti e Ginocchio MOC]]).
   - I singoli ventri muscolari (es. [[Bicipite Brachiale]], [[Brachiale]], [[Brachioradiale]]) o i singoli esercizi (es. [[Bayesian Cable Curl]], [[Preacher Curl]]) sono **Note Normali**.

---

## Architettura Modulare Componibile a 6 Blocchi

Ogni nota di Bodybuilding attiva i blocchi modulari pertinenti alla fonte analizzata:

### BLOCCO 1: Neurofisiologia, Bioenergetica e Danno Muscolare
- **Reclutamento e Codifica di Frequenza:** Spiegazione del principio delle dimensioni di Henneman: le unità motorie a soglia elevata (*High-Threshold Motor Units*, HTMU) innervano le fibre di Tipo IIx/IIa e richiedono carichi elevati ($\ge 80\%\text{ 1RM}$) OPPURE la vicinanza al cedimento muscolare concentrico ($0\text{--}3\text{ RIR}$) con carichi moderati per essere completamente reclutate e massimizzare la tensione meccanica per fibra.
- **Fatica Centrale vs Periferica:**
  - *Fatica periferica:* accumulo di fosfato inorganico ($\text{P}_i$) che inibisce il rilascio di $\text{Ca}^{2+}$ dal reticolo sarcoplasmatico e riduce la sensibilità della troponina C.
  - *Fatica centrale:* inibizione presinaptica mediata dalle afferenze sensoriali muscolari di gruppo III e IV che riduce il drive neurale discendente (*voluntary activation*).
- **Via Meccanotrasduttiva mTORC1 e MyoPS:** Apertura dei canali Piezo1, rilascio di acido fosfatidico (PA) e attivazione del complesso 1 del bersaglio della rapamicina nei mammiferi (mTORC1), promuovendo la sintesi proteica muscolare (*Muscle Protein Synthesis*, MyoPS).
- **Danno Muscolare Indotto dall'Esercizio (EIMD):** Rottura delle linee Z, microlesioni della titina e *Repeated Bout Effect* (RBE) come adattamento protettivo che mitiga il danno nelle sessioni successive.

---

### BLOCCO 2: Anatomia Funzionale e Neuromeccanica
- **Origine, Inserzione e Linee di Trazione (*Line of Pull*):** Descrizione anatomica chirurgica dei punti di ancoraggio osseo e del piano tridimensionale di contrazione.
- **Tipizzazione delle Fibre e Conseguenze Pratiche:**
  - *Percentuale media Tipo I (lente/ossidative) vs Tipo IIa/IIx (rapide/glicolitiche):* (es. il soleo ha $\approx 80\%$ Tipo I, mentre il tricipite brachiale o il bicipite hanno $\approx 60\%$ Tipo II).
  - *Cosa comporta sul piano pratico:* I muscoli a prevalenza di Tipo II sono più soggetti a danno muscolare (EIMD), affaticano prima il sistema neuromuscolare e richiedono recuperi maggiori inter-serie e frequenze settimanali moderate; i muscoli a prevalenza Tipo I tollerano più volume, recuperano rapidamente e beneficiano di range di ripetizioni più estesi.
- **Braccio di Momento Interno ed Esterno (*Internal vs External Moment Arm*):**
  - Variazione del braccio di leva interno lungo l'escursione articolare (ROM).
  - Vettore della resistenza esterna: dove si colloca il picco di carico (in allungamento, a metà ROM a $90^\circ$, o in accorciamento).
- **Curva Lunghezza-Tensione e Ipertrofia da Allungamento (*Stretch-Mediated Hypertrophy*, SMH):**
  - Valutazione se il muscolo lavora sul braccio ascendente, sull'altopiano o sul braccio discendente della curva dei sarcomeri ($> 2.7\text{ }\mu\text{m}$).
  - Verifica della presenza di SMH (tensione passiva della titina sommata alla tensione attiva dei ponti actomiosinici) o rischio di **insufficienza attiva** nei muscoli bi-articolari.

---

### BLOCCO 3: Evidenza Empirica e Letteratura (PubMed Live Engine)
Il motore delle evidenze (`.antigravity/tools/evidence_search.py`) cerca gli studi sull'argomento, sceglie quelli pertinenti, analizza sul testo completo quelli open access (Note Studio in `Bodybuilding/Studi/`) e scrive il **dossier delle evidenze** del job. Si citano solo gli studi del dossier, con il link alla loro Nota Studio o il PMID, rispettandone peso e utilizzabilità.

#### Tabella Obbligatoria degli Studi
| Studio e Anno | PMID | Disegno Sperimentale e Campione | Metodica di Misura | Risultato Chiave e Conclusioni | Limiti dello Studio |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Schoenfeld et al. (2020)** | [31855297](https://pubmed.ncbi.nlm.nih.gov/31855297/) | RCT 8 settimane su 24 soggetti allenati (*Resistance-Trained*) | Risonanza Magnetica (MRI) e Ultrasuoni (US) | Carichi pesanti (8-12 RM) e leggeri (25-30 RM) al cedimento producono simile ipertrofia sarcomerica | Piccola dimensione campionaria |

#### Gerarchia delle Evidenze (vincolante per ogni affermazione empirica)
Gli studi non si riassumono: si **pesano** e si ordinano. A parità di tema, l'evidenza di rango superiore prevale e quella inferiore non può smentirla.
1. **Metodica di misura:** MRI / CT / ecografia panoramica (fCSA, volume) > biopsia (fCSA delle fibre) e ecografia B-mode a punto singolo (spessore muscolare) > DEXA (massa magra) > BIA. Uno studio con sola BIA non sostiene alcuna conclusione sull'ipertrofia; DEXA misura la massa magra totale, non la crescita di un muscolo. Lo spessore in un punto (es. 50% del femore) non descrive l'intero ventre.
2. **Popolazione:** atleti avanzati con criteri oggettivi verificabili (standard di forza, livello agonistico, anni documentati) > allenati (≥1 anno documentato) > "recreationally trained" (auto-dichiarati) > principianti. Un risultato su ricreativi o principianti **non si generalizza** agli avanzati: va scritto per la popolazione studiata.
3. **Sforzo:** cedimento concentrico oggettivo (impossibilità di completare la ripetizione) > RIR / perdita di velocità misurata > prescrizione fissa > "fatica volizionale" (interruzione soggettiva) > non descritto. Se gli studi confrontati usano sforzi diversi, dichiaralo: la differenza di risultato può dipendere dallo sforzo e non dalla variabile studiata.
4. **Disegno e statistica:** nei disegni unilaterali (un arto per condizione) il campione è **N persone, non 2N arti**; il controllo dei fattori individuali è migliore ma c'è rischio di *cross-education* per la forza. Un p-value intra-gruppo (pre vs post) non prova la superiorità di una condizione: serve l'interazione tempo × gruppo o il confronto tra condizioni.

#### Divieti
- **Nessuna conclusione definitiva** da un solo studio, da studi con spin moderato/alto (abstract che dichiara superiorità non supportata dal test principale), da campioni con stato di allenamento ambiguo, sforzo non descritto o campione < 8 persone. Questi studi si citano solo come indizi o lacune.
- Formula la forza dell'affermazione in modo esplicito: **solida** (≥2 studi utilizzabili concordi, almeno uno con MRI/fCSA o popolazione avanzata), **moderata** (≥1 studio utilizzabile di buon livello), **provvisoria** (studio singolo, popolazione diversa, estrapolazione meccanicistica), **insufficiente**.
- Non equiparare EMG acuto, danno muscolare o "pump" all'ipertrofia misurata.

#### Collegamento alle Note Studio
Le schede critiche dei singoli paper stanno in `Bodybuilding/Studi/` (generate con «🔬 Nota Studio Scientifico»): frontmatter con `evidence_level`, `usable_for_conclusions`, `measurement_tools`, `training_status`, `effort`, `spin_severity`. Se uno studio citato ha una Nota Studio, collegala con il suo alias (es. `[[havers2025-2dbf13|Havers et al. 2025]]`) e rispetta il suo `evidence_level`: uno studio con `usable_for_conclusions: false` non può sostenere una regola pratica. Il blocco `<!-- LIT:BEGIN evidence -->…<!-- LIT:END evidence -->` è gestito da «🏋️ Integra Studi in una Nota Bodybuilding»: **non modificarlo e non duplicarlo** quando migliori la nota.

---

### BLOCCO 4: Contestualizzazione Dinamica dell'Atleta
- **Neofita vs Avanzato:**
  - *Neofita:* Alta sensibilità allo stimolo, recupero rapido, coordinazione intramuscolare incompleta, tollera volumi bassi (6-10 serie settimanali per distretto).
  - *Avanzato:* Resistente allo stimolo, necessita di modulazione del volume, richiede carichi elevati e RIR ridotto per forzare il reclutamento delle HTMU rimanenti.
- **Fase di Surplus (Bulk) vs Deficit Calorico (Cut):**
  - In cut: ridotta capacità di recupero sistemico, diminuita glicemia intracellulare e riserve di glicogeno; necessità di preservare l'intensità di carico contraendo leggermente il volume di serie spazzatura.
- **Rientro da uno Stop (Detraining / Resensibilizzazione):**
  - Perdita primaria di glicogeno e idratazione intracellulare, con preservazione dei mionuclei satellite; ripartire con volumi minimi efficaci (MEV) per sfruttare il *Repeated Bout Effect* senza DOMS paralizzanti.

---

### BLOCCO 5: Setup Chirurgico ed Esecuzione
Integrazione di screenshot estratti da YouTube tramite `youtube_watch.py` (`![[yt_...png]]`):
- **Gradi di Inclinazione e Angoli Articolari:** (es. panca inclinata a $30^\circ\text{--}45^\circ$, gomito esteso a $170^\circ$).
- **Vettore di Trazione del Cavo / Bilanciere:** Allineamento della linea di forza esterna con le fibre target.
- **Punti di Stabilizzazione Corporea:** Ancoraggio del bacino, retrazione o protrazione scapolare, *foot placement* per eliminare compensi.
- **Cadenza e Controllo Eccentrico:** 2-3 secondi in fase eccentrica controllata, sosta di 1 secondo in massimo allungamento per dissipare l'energia elastica passiva dei tendini.

---

### BLOCCO 6: Matrici Operative (Prescrizione dell'Allenamento)
Tabella Markdown prescrittiva con colonna obbligatoria del razionale fisiologico:

| Parametro | Valore Raccomandato | Razionale Meccanico e Fisiologico |
| :--- | :---: | :--- |
| **Intensità di Carico (% 1RM)** | $65\%\text{--}80\%$ | Zona ideale per massimizzare la tensione meccanica per fibra riducendo lo stress articolare e assiale |
| **Prossimità al Cedimento (RIR)** | $0\text{--}2\text{ RIR}$ | Garantisce il pieno reclutamento delle HTMU secondo la curva forza-velocità |
| **Range di Ripetizioni** | $6\text{--}10\text{ reps}$ | Ottimale per evitare che la fatica cardiovascolare o il bruciore metabolico diventino fattore limitante |
| **Tempo di Recupero** | $2\text{--}3\text{ minuti}$ | Consente il ripristino di circa il $95\%$ della fosfocreatina ($\text{PCr}$) e dissipa la fatica centrale discendente |
| **Volume Settimanale per Muscolo** | $10\text{--}16\text{ serie}$ | Intervallo di massima risposta dose-risposta prima dell'accumulo di volume spazzatura (*junk volume*) |

---

## Callout Obbligatori di Bodybuilding

```markdown
> [!info] Grado di Evidenza e Stato dell'Arte
> L'evidenza scientifica su questo principio (es. *Stretch-Mediated Hypertrophy*) è considerata di grado **FORTE (Livello A)**, corroborata da plurime metanalisi e studi longitudinali con Risonanza Magnetica (MRI).

> [!warning] Confronto Fonte vs Letteratura PubMed
> Il relatore nel video afferma che "i bicipiti vanno allenati a 30 ripetizioni per bruciare il grasso locale". La letteratura scientifica attuale smentisce categoricamente lo spot reduction (PMID 23222084) e dimostra che il dimagrimento locale è un mito fisiologico privo di riscontro sistemico.
```
