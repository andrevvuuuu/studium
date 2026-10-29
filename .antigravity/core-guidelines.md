# Costituzione Universale del Vault Obsidian (Antigravity Core Guidelines)

> [!IMPORTANT]
> Questo documento definisce le **Leggi Fondamentali** che l'agente Antigravity deve leggere e rispettare **SEMPRE** prima di creare, modificare o aggiornare qualsiasi nota o MOC nel vault. Non sono ammesse deroghe, omissioni o scorciatoie stilistiche.

---

## REGOLA FONDAMENTALE — Criterio di Confine Concettuale ed Esaustività

Questa regola definisce i confini invalicabili di ogni nota e sostituisce qualsiasi formulazione precedente di atomicità o scorporo:

### 1. Nessun Limite di Parole (Né Minimo né Massimo)
- Una nota è lunga esattamente **quanto serve per spiegare in modo totale, rigoroso e senza saltare passaggi** l'argomento richiesto.
- Il conteggio parole non è mai un vincolo o un obiettivo quantitativo: è un mero dato descrittivo a posteriori.
- Il problema cruciale da evitare è mescolare dentro la stessa nota concetti diversi, teoremi derivati e procedure operative che devono invece costituire note autonome collegate con [[wikilink]].

### 2. Un Solo `Type` per Nota (Formato YAML Rigido)
- Nel frontmatter YAML è obbligatorio il formato lista su riga singola con **un solo valore univoco**:
  ```yaml
  Type:
    - Concetto
  ```
- **Vietati tassativamente valori multipli**, sintassi con pipe (`[Concetto | Teorema]`), array inline (`[Concetto]`) o stringhe inline (`Type: Concetto`).
- I valori canonici ammessi (uno solo per nota) sono:
  * `Concetto`: Definizioni teoriche, costrutti, entità anatomiche/fisiologiche, strutture dati o molecole.
  * `Teorema`: Enunciati formali matematici o leggi fisiche con ipotesi, tesi e dimostrazione formale a sé stante.
  * `Metodo`: Algoritmi, procedure operative passo-passo, protocolli applicativi, batterie di esercizi d'esame.
  * `Analisi`: Trattazioni critico-ermeneutiche su singole opere narrative, eventi storici, casi studio empirici o trattati.
  * `MOC`: Mappe di orientamento discorsive e architetture gerarchiche di contenuto.

### 3. Contenuto di una Nota `Type: Concetto` su $X$
Dentro una nota Concetto $X$ deve essere spiegato **tutto ciò che c'è da sapere su $X$ stesso**, senza tralasciare nulla:
1. **Motivazione e Genesi:** Perché i matematici, scienziati o pensatori hanno introdotto $X$? Quale vuoto teorico o pratico colma?
2. **Definizione Formale Rigorosa con Callout Decodifica:** Enunciato matematico/scientifico esatto con notazione formale, traduzione parola per parola e spiegazione concettuale a sforzo zero.
3. **Interpretazione Geometrica, Grafica o Intuitiva:** Spiegazione visiva o schematica della definizione.
4. **Tassonomia e Casi Particolari:** Classificazione interna di $X$ (es. per gli Intervalli: limitati/illimitati, aperti/chiusi, degeneri/vuoto).
5. **Proprietà Costitutive di $X$ con Dimostrazioni Complete Passo-Passo:** Tutte le proprietà che **definiscono l'identità di $X$** o il comportamento delle sue operazioni basilari (es. negli Intervalli: il Teorema di Caratterizzazione come insiemi connessi rispetto all'ordine, la stabilità per intersezione arbitraria, le condizioni di stabilità per unione con dimostrazioni complete ed esplicite).
6. **Esempi e Controesempi Rapidi:** Casi tipici in cui la definizione si applica e casi limite/trabocchetti per comprendere a fondo le definizioni.

### 4. Il Test Operativo DENTRO / FUORI per ogni Risultato $R$
Prima di scrivere ogni sezione o risultato matematico/scientifico $R$, applica tassativamente questo test:
- **DENTRO:** Il risultato $R$ resta nella nota se **serve a definire o a far funzionare $X$** e si dimostra usando **esclusivamente la definizione di $X$ e note/proprietà già esistenti** (es. stabilità per intersezione di intervalli).
- **FUORI:** Il risultato $R$ deve essere **scorporato in una nota autonoma** se:
  * $R$ usa $X$ meramente come ipotesi o ambiente per dimostrare qualcosa su **altri enti o funzioni** (es. una funzione continua su un intervallo).
  * $R$ ha un **nome proprio con vita autonoma** (es. *Teorema di Cantor degli Intervalli Inscatolati*, *Teorema di Heine-Borel*, *Teorema di Weierstrass*).
  * $R$ sarà citato altrove nel vault come risultato a sé stante.
- **Caso di Dubbio:** In caso di incertezza su un risultato borderline, **non decidere in silenzio**: segnala esplicitamente il caso nella risposta finale spiegando il motivo della scelta di collocazione.

### 5. Cosa va FUORI dalla Nota $X$ (Note Separate collegate con [[wikilink]])
1. **Teoremi Derivati o Autonomi che poggiano su $X$:**
   - Nella nota di $X$ inserisci **unicamente il ponte logico** (spiegando discorsivamente perché le proprietà di $X$ rendono possibile quel teorema e a cosa serve) e il [[wikilink]].
   - **Divieto Assoluto:** Non inserire nella nota di $X$ l'enunciato formale completo, la dimostrazione a 3 atti e l'analisi delle ipotesi del teorema derivato (questi risiedono esclusivamente nella nota autonoma `Type: Teorema`).
2. **Concetti Adiacenti o Successivi con Definizione Autonoma:**
   - Concetti come *Intorni*, *Punti di Accumulazione*, *Insiemi Aperti e Chiusi* possiedono una definizione autonoma: nella nota di $X$ compaiono solo come collegamento logico naturale e [[wikilink]].
3. **Procedure Operative e Batterie di Esercizi d'Esame:**
   - I metodi di risoluzione standard, gli algoritmi di calcolo e le batterie di esercizi d'esame non appesantiscono la nota teorica: vanno in una nota collegata `Type: Metodo` (es. [[Risoluzione di Disequazioni Fratte con Intervalli]]).

### 6. Nessuna Sezione Artificiale
- I callout di **"Conflitto Epistemico"** e i paragrafi di **"Confronto Interdisciplinare"** compaiono **solo se esistono davvero nelle fonti o aggiungono comprensione fondamentale**. Non forzare mai la presenza di queste sezioni se non giustificate dai contenuti.

### 7. Sezione Finale Unificata per gli Scorpori
- Nella sezione finale `Note e Paragrafi Collegati`, inserisci **obbligatoriamente** la voce:
  `### Teoremi e Concetti Derivati (Note Separate)`
  contenente l'elenco dei teoremi, concetti derivati e metodi operativi scorporati dalla nota, ciascuno corredato da un breve raccordo logico e dal relativo [[wikilink]].
- Usa quest'unica voce standard senza duplicarla con dizioni alternative.

### 8. Auto-Controllo Vincolante Prima di Concludere la Nota
Prima di considerare conclusa la stesura della nota, esegui mentalmente questa checklist:
- [ ] Nessuna sezione ha come titolo un teorema con nome proprio che usa $X$ come ambiente o ipotesi su altri oggetti.
- [ ] Nessuna dimostrazione o enunciato formale di un risultato derivato è presente nella nota.
- [ ] Il campo `Type:` nel frontmatter contiene un solo valore ed è in formato lista `- Valore`.
- [ ] È presente nella sezione finale la sottosezione esplicita `### Teoremi e Concetti Derivati (Note Separate)`.


### 9. Le Cinque Regole Tassative di Forma e Formattazione
1. **Zero Riferimenti Meta a Lezioni, Capitoli o Notebook nel Testo o nei Titoli:** L'indice del libro e il diario delle lezioni servono esclusivamente dietro le quinte per consentire la mappatura della totalità del programma d'esame. Nelle note e nei MOC generati è severamente vietato scrivere diciture metadidattiche come `(Lezioni 1–28 | Indice Libro [Alg] Capp. 1, 2)`, `(Dal Diario delle Lezioni)`, `(Cap. 3 del Libro)` o codici dei notebook come `(SMIA: Analisi 1)` nei titoli dei paragrafi, nelle tabelle o nel corpo del testo. I titoli delle sezioni e il testo devono essere puramente accademici e disciplinari, come in un vero trattato universitario.
2. **Wikilink Puri senza Apici né Backtick:** I collegamenti ipertestuali devono essere scritti SEMPRE in formato puro Obsidian: [[Nome Nota]] o [[Nome Nota#Paragrafo|Alias]]. È severamente vietato racchiudere i wikilink tra apici singoli, doppi o dentro backtick in qualunque parte del documento (testo normale, elenchi puntati, tabelle markdown, callout). In Obsidian i backtick trasformano il link in blocco di codice inerte e gli apici impediscono il riconoscimento dell'ipertesto, rendendo il link non cliccabile.
3. **Purga Totale delle Emoji:** Nelle note e nei MOC generati è severamente vietato l'uso di qualsiasi emoji Unicode. I titoli delle sezioni, le tabelle e i callout devono mantenere uno stile sobrio, accademico ed elegante. I titoli delle fasi di dimostrazione devono essere: `**1. Strategia della Dimostrazione:**`, `**2. Passaggi Logico-Deduttivi:**`, `**3. Conclusione e Q.E.D.:**`. Il callout della palestra d'esame deve essere: `> [!abstract]- Palestra d'Esame Interattiva: Flashcard e Quiz` (senza emoji).
4. **Delimitazione Rigorosa delle Formule LaTeX nelle Note Normali:** Nella prosa Markdown delle Note Normali, ogni espressione matematica LaTeX deve essere racchiusa nei delimitatori appropriati: $...$ inline e $$...$$ per formule isolate. Non lasciare comandi come \forall, \exists, \frac, \mathbb, \lim, \sum o \in fuori dalla modalità matematica. Controlla anche callout e contenuti di studio.
5. **Divieto di `\vline` in LaTeX:** Obsidian MathJax non riconosce il comando `\vline` e genera un errore di parsing rosso nel rendering matematico. È tassativamente vietato usare `\vline`. Per rappresentare linee verticali in formule matematiche, matrici o insiemi usare sempre `\vert`, `|` o `\mid` (es. `\{x \in A \mid P(x)\}`).


---

## LEGGE 1: Linguaggio Semplice ma Rigoroso (Lettura a Sforzo Cognitivo Zero)

La mente umana apprende con facilità quando la **complessità sintattica è ridotta a zero**, ma la **precisione lessicale e scientifica è massima**. L'obiettivo è consentire una comprensione istantanea al primo colpo d'occhio, senza costringere a rileggere la stessa frase due volte.

1. **Sintassi Immediata e Diretta:**
   - Usa frasi brevi, lineari e coordinate (Soggetto $\to$ Verbo $\to$ Complemento).
   - Elimina subordinate a incastro, incisi infiniti, forme passive pesanti o perifrasi burocratiche.
   - Struttura il testo con **elenchi puntati**, **grassetto selettivo** sulle parole chiave e **tabelle comparative** per guidare lo sguardo (*skimming visuale*).
2. **Lessico Accademico e Scientifico Non Diluito:**
   - È severamente vietato "banalizzare" la materia sostituendo i termini tecnici con metafore infantili o approssimazioni imprecise.
   - Usa sempre i termini propri della disciplina: es. *potenziale d'azione*, *forza viva*, *iniettività*, *ipertrofia sarcomerica*, *saturazione recettoriale*, *complessità asintotica*, *eterogeneità di varianza*.
   - **Regola della Definizione Istantanea:** Ogni volta che introduci un termine tecnico denso o un'astrazione formale, spiega subito tra parentesi o nella frase successiva il suo significato pratico e tangibile in parole semplici.
3. **Gerarchia Visiva Pulita:**
   - Usa intestazioni coerenti (`#`, `##`, `###`, `####`).
   - Sfrutta i callout nativi di Obsidian (`> [!note]`, `> [!tip]`, `> [!warning]`, `> [!danger]`, `> [!example]`) per isolare definizioni, decodifiche, dimostrazioni e controesempi.

---

## LEGGE 2: Zero Passaggi Sottintesi (Evoluzione Continua della Catena Logica)

Nessun passaggio concettuale, matematico, biologico, algoritmico o storico può essere dato per "scontato", "banale", "ovvio" o "lasciato per esercizio al lettore".

1. **Ricostruzione dei Passaggi Intermedi:**
   - Se una fonte, un professore o un articolo salta un passaggio logico o un'equazione intermedia compiendo un "salto acrobatico", l'agente ha il dovere tassativo di **ricostruire ed esplicitare il passaggio mancante**.
2. **Catene di Uguaglianze e Dimostrazioni Matematiche:**
   - Nelle derivazioni e nelle dimostrazioni, ogni singola riga di calcolo deve avere a fianco o sotto la motivazione chiara della proprietà applicata:
     - *Perché si aggiunge e toglie quella quantità?*
     - *Quale ipotesi del teorema stiamo sfruttando per passare al limite?*
     - *Perché quel denominatore è diverso da zero?*
3. **Catene Causali nelle Scienze Sperimentali e Naturali:**
   - Nelle note di Neuroscienze, Biologia, Medicina, Farmacologia e Bodybuilding, i processi biologici devono essere espressi come **catene causali causa-effetto sequenziali numerate**, senza buchi temporali o salti molecolari (es. *Stimolo meccanico $\to$ apertura canali meccanosensibili Piezo1 $\to$ influsso di $\text{Ca}^{2+}$ $\to$ attivazione FAK/mTORC1 $\to$ fosforilazione p70S6K $\to$ traduzione ribosomiale*).

---

## LEGGE 3: Standard Frontmatter YAML e Tipizzazione Automatica

Ogni nota creata nel vault deve iniziare rigorosamente con il blocco Frontmatter YAML standard.

### Schema Obbligatorio
```yaml
---
Disciplina: <Nome Esatto di una delle 20 Macro-Discipline>
Type:
  - <MOC | Teorema | Concetto | Metodo | Analisi>
tags:
  - <tag_disciplina_minuscolo_senza_spazi>
  - <polo: università | personale>
aliases:
  - <Sinonimi, sigle, acronimi, termini in inglese utili per i wikilink>
---
```

### Regole Tassative di Compilazione
1. **Un solo `Type` per nota (Formato Lista Rigoroso):**
   - Nel frontmatter YAML il `Type` deve contenere **esattamente un solo valore univoco**, espresso nel formato lista standard:
     ```yaml
     Type:
       - Concetto
     ```
   - **Vietati tassativamente valori multipli**, sintassi con pipe o parentesi quadre (`Type: [Concetto | Teorema]`), stringhe inline (`Type: Concetto`) o array inline (`Type: [Concetto]`).
2. **Nessun cancelletto nei tag:** Nei campi YAML i tag non devono contenere `#` (Obsidian li trasforma automaticamente in tag interni).
3. **Attributo `Disciplina`:** Deve coincidere esattamente con uno dei 20 nomi ufficiali (es. `Matematica`, `Intelligenza Artificiale`, `Bodybuilding`, `Nutrizione e Salute`, `Droghe`).
4. **I 5 Valori Canonici del `Type`:**
   - `Concetto`: Definizioni teoriche, costrutti, fenomeni anatomici/fisiologici o entità molecolari.
   - `Teorema`: Enunciati formali matematici o leggi fisiche con ipotesi, tesi e dimostrazione formale a sé stante.
   - `Metodo`: Algoritmi, procedure operative, protocolli d'allenamento, tecniche di calcolo o batterie di esercizi d'esame.
   - `Analisi`: Trattazioni critico-ermeneutiche su opere letterarie, narrative, correnti filosofiche, eventi storici o casi studio empirici.
   - `MOC`: Mappe di orientamento discorsive e architetture gerarchiche di contenuto.
5. **Campo `aliases`:** Deve contenere tutte le varianti linguistiche (singolare/plurale, inglese, abbreviazioni, es. `[Intervalli Reali, Intervallo Reale, Intervalli della Retta Reale]`), consentendo il collegamento naturale nel testo da qualsiasi altra nota.

---

## LEGGE 4: Filosofia dei MOC (Mappe Discorsive e le 3 Modalità di Studio)

Un MOC (**Map of Content**) non è MAI un mero indice analitico, né una sterile lista puntata della spesa di collegamenti ipertestuali, né un formulario o un riassunto tecnico. Un MOC è una **lezione panoramica discorsiva e progressiva** dell'intero percorso accademico: prende per mano chi studia, racconta l'evoluzione causale e gerarchica dei concetti e spiega chiaramente *perché* una determinata nozione viene introdotta prima di un'altra.

---

### 1. I 4 Vincoli Strutturali Tassativi dei MOC (Regole Definitive)

Tutti i MOC generati nel vault devono rispettare tassativamente queste 4 regole strutturali:

1. **ZERO FORMULE, ZERO DIMOSTRAZIONI, ZERO TABELLE NEI MOC:**
   - **Divieto Assoluto di LaTeX:** Nei MOC è severamente vietato inserire formule matematiche o simboliche racchiuse tra dollari (`$...$` o `$$...$$`). I concetti vanno descritti esclusivamente mediante la loro denominazione concettuale in prosa italiana accademica (es. scrivere *"aritmetica modulare nell'anello delle classi di resto"* e MAI *"aritmetica in $\mathbb{Z}_n$"* o *$ax \equiv b \pmod n$*).
   - **Zero Dimostrazioni ed Enunciati Formali:** Il MOC non dimostra teoremi e non ne riporta gli enunciati simbolici con ipotesi e tesi formali. Spiega invece lo scopo teorico del teorema e la ragione logica per cui esso scaturisce dal concetto precedente.
   - **Zero Tabelle Riassuntive:** È severamente vietato inserire tabelle riassuntive, elenchi colonnari o matrici di confronto nei MOC. Tutta la materia deve vivere unicamente nella prosa narrativa continua e nei diagrammi Mermaid.
   - **Zero Callout Tecnici e Zero Pannelli Studio:** Nei MOC non devono comparire callout di definizione (`> [!definition]`), teoremi (`> [!theorem]`), decodifiche logico-formali o il blocco Flashcard/Quiz (`%%STUDY_DATA`, `study_panel.js`).
   - **Zero Riferimenti Meta e Zero Emoji:** È tassativamente vietato menzionare numeri di lezione, capitoli del libro o nomi di notebook (es. mai scrivere `(Lezioni 1-10)` o `(Cap. 3 del libro)`). Purga totale di qualsiasi emoji Unicode.

2. **TESTO 100% DISCORSIVO CAUSALE (Il "Perché" del Passaggio da una Nota all'Altra):**
   - Il MOC deve essere scritto interamente in prosa discorsiva fluida e coerente, articolata in paragrafi narrativi approfonditi.
   - La trattazione deve sviscerare sistematicamente il *filo logico causale*:
     * Perché nasce un determinato concetto e quale problema pratico o teorico risolve.
     * Quale limite strutturale del concetto precedente impone di introdurre il successivo.
     * Come e perché da quel concetto scaturiscono rigorosamente i relativi teoremi e metodi applicativi.
   - È severamente vietato presentare sezioni costituite da soli elenchi puntati privi di raccordo causale.

3. **NOMENCLATURA ESPLICITA OBBLIGATORIA E DIVIETO ASSOLUTO DI ALIAS NEI WIKILINK DEL MOC:**
   - Per consentire a chi studia di distinguere immediatamente a colpo d'occhio nel testo discorsivo, nel grafo e nella barra laterale la tipologia di ciascuna nota:
     * **Note Teorema:** Devono SEMPRE iniziare con il prefisso canonico `Teorema ...` (oppure `Lemma ...`, `Corollario ...`, `Principio ...`, `Criterio ...`) all'interno delle doppie quadre (es. `[[Teorema di Weierstrass]]`, `[[Teorema di Rouché-Capelli]]`, `[[Criterio di Diagonalizzabilità]]`). È severamente vietato scrivere `il teorema di [[Weierstrass]]`.
     * **Note Metodo:** Devono SEMPRE iniziare con il prefisso canonico `Metodo ...` (oppure `Studio ...`, `Calcolo ...`, `Risoluzione ...`, `Algoritmo ...`) all'interno delle doppie quadre (es. `[[Metodo di Eliminazione di Gauss]]`, `[[Calcolo dell'Inversa di una Matrice]]`, `[[Risoluzione delle Equazioni Diofantee Lineari]]`).
     * **DIVIETO ASSOLUTO DI ALIAS NEI MOC:** Nei MOC è vietato usare pipe/alias nei wikilink (es. MAI `[[Teorema di Weierstrass|teorema]]` né `[[Metodo di Eliminazione di Gauss|algoritmo]]`). Solo ed esclusivamente il wikilink puro col titolo completo della nota: `[[Nome Esatto della Nota]]`. Questo rende palese a colpo d'occhio nel testo se una parola linkata è un Concetto, un Teorema o un Metodo.
     * **Wikilink Puri:** Mai racchiudere i wikilink tra apici singoli `'[[...]]'`, doppi `"[[...]]"` o backtick `` `[[...]]` ``.

4. **DOPPIA ARCHITETTURA MERMAID VERTICALE (`flowchart TD`):**
   - **1. Diagramma Generale d'Insieme (Top-Level):** Posizionato in cima al MOC, subito dopo l'introduzione, con orientamento verticale `flowchart TD` per visualizzare la propedeuticità e la successione logica dei macro-moduli del corso.
   - **2. Diagrammi Modulari Dedicati (End-of-Chapter):** In fondo a **ciascun singolo capitolo/modulo**, è obbligatorio inserire un diagramma `flowchart TD` che mappi l'architettura interna del capitolo: nodi di `[[Concetto]]`, collegati ai rispettivi `[[Teorema ...]]` e `[[Metodo ...]]`.
   - **Regole Sintattiche Anti-Crash Mermaid:**
     * Nodi centrati verticali (`flowchart TD`).
     * Testo di ciascun nodo racchiuso rigorosamente tra doppi apici `"..."` (es. `A["[[Spazi Vettoriali]]"] --> B["[[Teorema del Completamento della Base]]"]`).
     * Zero formule LaTeX e zero delimitatori `$...$` all'interno dei nodi.
     * Zero emoji Unicode nei diagrammi.

---

### 2. Le 3 Modalità Operative di Creazione dei MOC
Il vault supporta tre distinte modalità di generazione dei MOC, ciascuna concepita per una specifica fase del percorso di apprendimento:

1. **Modalità 1: `start_notebooklm` (Inizio Studio — Da NotebookLM):**
   - **Obiettivo:** Creare una roadmap didattica e concettuale esaustiva a partire dai materiali di studio, sbobinature, dispense o libri caricati su uno o più NotebookLM, integrando l'Indice del Libro e il Diario delle Lezioni del docente.
   - **Logica Operativa:** L'agente estrae l'intera architettura dei moduli, i capitoli, i teoremi e i metodi chiave presenti nelle fonti di NotebookLM mediante scansione multi-query profonda (8–15 blocchi logici + audit di completezza) e li incrocia con `.antigravity/vault-index.json`.
   - **Fusione Paritaria ($A \cup B$) e Copertura Totale d'Esame:** Il MOC deve integrare il 100% degli argomenti dell'Indice del Libro, del Diario delle Lezioni del docente e delle risposte multi-query di `nlm`, dando a libro e lezioni lo stesso identico peso. Deve organizzare i contenuti in un percorso discorsivo organico che colleghi TUTTE le singole note atomiche (`Concetto`, `Teorema`, `Metodo`) necessarie per preparare l'esame, assegnando a ogni singolo concetto, teorema e metodo il proprio [[wikilink]] individuale.
   - **Regola dei Wikilink:**
     * Per i concetti che hanno già una nota dedicata nel vault, usa **esattamente il titolo del file esistente** (con eventuale alias grammaticale).
     * Per i concetti presenti nelle fonti ma non ancora redatti, inserisce i **[[wikilink futuri]]** pianificati con titoli canonici puliti, trasformando il MOC nel piano di lavoro operativo per le sessioni di studio successive.

2. **Modalità 2: `start_base_knowledge` (Inizio Studio — Da Conoscenza Base di Antigravity):**
   - **Obiettivo:** Progettare da zero una roadmap accademica e concettuale rigorosa su un argomento o una disciplina, senza disporre di fonti esterne immediate.
   - **Logica Operativa:** L'agente sfrutta la propria conoscenza enciclopedica e specialistica per strutturare un percorso di studio ideale secondo i migliori standard universitari.
   - **Regola dei Wikilink:** Consulta `.antigravity/vault-index.json` per riutilizzare tutti i titoli delle note affini già scritte nel vault e progetta l'albero dei collegamenti futuri con wikilink canonici ordinati logicamente.

3. **Modalità 3: `end_vault_consolidation` (Fine Studio / Consolidamento — Dalle Note Presenti nel Vault):**
   - **Obiettivo:** Sintetizzare e consolidare l'intero corpus di appunti studiati e redatti nel vault in vista di un esame universitario, di un progetto o di una revisione finale.
   - **Logica Operativa:** L'agente legge il dossier strutturato `.antigravity/job-context/vault_notes_summary.md` (che raccoglie tutte le note della disciplina, gli estratti iniziali, le intestazioni e la mappa dei collegamenti) e costruisce una grande sintesi organica che leghi tra loro tutte le note effettivamente create.
   - **Callout Obbligatorio di Diagnosi Pre-Esame:** Ogni MOC in modalità `end_vault_consolidation` DEVE concludersi tassativamente con il seguente blocco diagnostico:
     ```markdown
     > [!todo] Diagnosi di Completezza (Fine Studio / Pre-Esame)
     > ### Link Rossi (Concetti Citati ma Privi di Nota Dedicata nel Vault)
     > - [[Titolo Link Rosso 1]]: citato in [[Nota A]] (sezione X) — *priorità alta per la preparazione*.
     > - [[Titolo Link Rosso 2]]: citato in [[Nota B]] — *definizione da approfondire*.
     > 
     > ### Argomenti Cardine Mancanti per la Piena Padronanza
     > - **[Argomento Cardine A]**: argomento essenziale nel programma canonico della materia, attualmente non coperto da alcuna nota nel vault.
     > - **[Argomento Cardine B]**: snodo teorico consigliato per completare la visione d'insieme.
     ```

### 3. Architettura a 3 Livelli Gerarchici del Vault
- **Livello 1: Macro-MOC di Disciplina:** (es. [[Matematica MOC]], [[Analisi 1 MOC]], [[Bodybuilding MOC]], [[Droghe MOC]]).
- **Livello 2: Sub-MOC Tematici:** Autori filosofici/letterari, singole opere narrative, periodi storici o distretti muscolari (es. [[Friedrich Nietzsche MOC]], [[Bleach MOC]], [[Bicipiti e Flessori del Gomito MOC]], [[Guerra Fredda MOC]]).
- **Livello 3: Note Atomiche:** Singoli concetti, teoremi, esercizi modello, personaggi, eventi o composti (es. [[Teorema di Rolle]], [[Bayesian Cable Curl]], [[MDMA (3,4-Metilendiossimetanfetamina)]]).

---

## LEGGE 5: Igiene dei [[Wikilink]], Collegamenti Chirurgici a Paragrafi e Aggiornamento Bidirezionale

Il grafo della conoscenza di Obsidian acquista valore solo se i collegamenti sono densi, corretti, chirurgicamente precisi e privi di link orfani o generici.

1. **Consultazione Obbligatoria dell'Indice e del Dossier Raccomandazioni:**
   - Prima di scrivere o modificare una nota, l'agente consulta `.antigravity/vault-index.json` e il dossier generato da `paragraph_linker.py` (`.antigravity/job-context/recommended-links.md`) per individuare esattamente quali note, paragrafi specifici e blocchi semantici collegare.
2. **Sintassi con Alias Grammaticale nelle Note Normali vs Divieto Assoluto nei MOC:**
   - **Nelle Note Normali (`Concetto`, `Teorema`, `Metodo`, `Esercizio`, `Analisi`):** Per non spezzare la naturalezza della prosa in italiano, usa la sintassi con alias:
     `[[Titolo Reale Nota|parola declinata nel testo]]` (es. `per studiare la [[Ricerca Binaria (Binary Search)|ricerca dicotomica]] applichiamo...`).
   - **Nei MOC (`Type: MOC`): DIVIETO ASSOLUTO DI ALIAS:** Nei MOC è vietato l'uso del carattere pipe `|`. I collegamenti devono comparire unicamente nella loro forma canonica pura `[[Nome Esatto della Nota]]` (es. `[[Teorema di Weierstrass]]`, `[[Metodo di Eliminazione di Gauss]]`, `[[Spazi Vettoriali]]`). Questo consente a chi legge la mappa di identificare all'istante la categoria ontologica di ciascuna nota (Concetto, Teorema, Metodo) e di ritrovarla senza ambiguità nel file explorer e nel grafo.
3. **Regole di Posizionamento dei Wikilink:**
   - **Prima occorrenza significativa:** Linka un concetto solo la prima volta che compare all'interno di una sezione logica. Non riempire la stessa pagina di decine di link ripetuti allo stesso termine.
   - **MAI nei Titoli:** È tassativamente vietato inserire wikilink dentro le intestazioni Markdown (`# [[Titolo]]`, `## [[Titolo]]`).
   - **MAI nel Codice o nelle Formule:** Non inserire wikilink dentro blocchi LaTeX (`$$...$$` o `$...$`) né dentro blocchi di codice (`` `inline` `` o ````fenced````).
4. **Quando usare [[Nota Intera|testo]] vs [[Nota#Paragrafo|testo]] (Precisione Chirurgica):**
   - **Link a Nota Intera:** Usa [[Nome Nota|testo]] (es. [[Numeri Interi Relativi|numeri interi]]) esclusivamente quando nel discorso ti riferisci all'oggetto o alla materia generale nel suo complesso.
   - **Link a Paragrafo Specifico (OBBLIGATORIO):** Usa **obbligatoriamente** la sintassi di sezione [[Nome Nota#Numero e Titolo Esatto Paragrafo|testo nel discorso]] ogni volta che citi una proprietà specifica, una tecnica dimostrativa, un sottoconcetto o un passaggio matematico/ingegneristico che non ha una nota autonoma ma è trattato in un paragrafo preciso di un'altra nota (es. [[Elementi di Logica Matematica#4.2 Dimostrazione per Assurdo|dimostrazione per assurdo]] o [[Numeri Interi Relativi#4.2 Proprietà di Integrità e Legge di Cancellazione Moltiplicativa|legge di cancellazione moltiplicativa]]). Prendi i link pronti dalla **Tabella A** di `recommended-links.md`.
5. **Uso e Creazione di ID di Blocco Semantici (`^id-blocco`):**
   - **Quando citi un teorema o un box formalizzato:** Se il concetto citato è un singolo callout o teorema specifico presente in un'altra nota, linka direttamente il blocco con [[Nome Nota#^id-blocco|testo]] (prendendo la sintassi dalla **Tabella B** di `recommended-links.md`).
   - **Quando scrivi una nuova nota:** In fondo ai callout più importanti (`> [!theorem]`, `> [!definition]`, `> [!tip] Dimostrazione...` e `> [!note] Decodifica...` fondamentali) **aggiungi obbligatoriamente un ID di blocco semantico pulito in kebab-case** (es. `^teo-unicita-limite`, `^def-relazione-equivalenza`, `^decodifica-significato-fisico`), così le note future potranno agganciarsi direttamente a quel singolo blocco concettuale.
6. **Sezione Finale `Note e Paragrafi Collegati`:**
   - In fondo a ogni nota, all'interno della sezione dedicata ai collegamenti, struttura le voci in questo modo tassativo:
     * **Teoremi e Concetti Derivati (Note Separate):** Sottosezione esplicita `### Teoremi e Concetti Derivati (Note Separate)` contenente l'elenco dei teoremi autonomi, concetti adiacenti o metodi d'esame scorporati dalla nota, ciascuno collegato tramite [[wikilink]] con un breve ponte logico discorsivo. Usa esclusivamente questa voce senza duplicarla con dizioni alternative.
     * **Riferimenti Puntuali a Paragrafi:** Sottosezione esplicita `### Riferimenti Puntuali a Paragrafi` che elenca e sintetizza i collegamenti diretti [[Nota#Paragrafo]] e [[Nota#^id-blocco]] impiegati nel testo.
     * **Note Generali e MOC:** Collegamenti alle note macro e di risalita al MOC di disciplina.
7. **Aggiornamento Bidirezionale Obbligatorio:**
   - Ogni volta che l'agente genera o aggiorna una Nota Normale, ha il dovere tassativo di **aprire il relativo MOC o Sub-MOC di riferimento** e inserire la nuova nota all'interno della sezione pertinente, corredata da una frase esplicativa. Una nota non deve mai nascere orfana.

---

## LEGGE 6: Regola Multimodale e Ispezione Visiva Obbligatoria

Un concetto tecnico o scientifico non è completamente spiegato se manca la sua rappresentazione visiva quando quest'ultima riduce drasticamente il carico cognitivo.

1. **Casi d'Uso Obbligatori per le Immagini:**
   - **Matematica e Fisica:** Grafici cartesiani di funzioni critiche, interpretazione geometrica di derivate, integrali o vettori, schemi di corpo libero.
   - **Informatica e IA:** Strutture dati in memoria (array, alberi, grafi), loss landscapes, matrici di confusione.
   - **Bodybuilding e Anatomia:** Setup angolari dell'attrezzatura, bracci di momento (*moment arm*), curve lunghezza-tensione, tabelle delle fibre muscolari, fotogrammi chiave del movimento da YouTube.
   - **Scienze Sperimentali, Chimica e Droghe:** Strutture molecolari 2D (PubChem), schemi sinaptici, scansioni fMRI/PET cerebrali, manifestazioni cliniche ed effetti somatici (Wikimedia Commons).
2. **Ispezione Visiva Obbligatoria dell'Agente:**
   - L'agente non può mai limitarsi a scaricare un'immagine e "sperare" che sia corretta.
   - **Prima** di includere il tag `![[nome_immagine.png]]` nella nota finale, l'agente deve **ispezionare fisicamente l'immagine** usando i propri tool di visione/lettura file.
   - Verifica che il file non sia una transizione nera o sfocata, che non sia un'icona vuota e che contenga effettivamente il diagramma didattico o la dimostrazione spiegata nel testo.
3. **Didascalia Narrativa:**
   - Ogni immagine inserita nella nota deve essere sempre accompagnata da una didascalia in corsivo o da un callout esplicativo che illustri chiaramente cosa osservare nella figura.

---

## LEGGE 7: Principio di Conservazione in Modalità Modifica (`operation: "edit"`)

Quando modifichi, ampli, riformatti o fondi una nuova fonte in una nota già esistente nel vault:
1. **Divieto Assoluto di Regressione Informativa (Regola Aurea):**
   - **Non devi mai impoverire, riassumere, accorciare o cancellare** dimostrazioni, definizioni rigorose, formule, passaggi algebrici intermedi, esempi concreti, tabelle riepilogative o dettagli tecnici già presenti nella nota, a meno che io non ti abbia chiesto esplicitamente di correggerli, sostituirli o rimuoverli.
2. **Merge Organico e Armonico:**
   - Quando integri una nuova fonte (`edit_mode: "merge_source"`), i nuovi concetti, i dati sperimentali e gli screenshot verificati devono essere fusi in modo naturale dentro la struttura preesistente. Arricchisci le sezioni già presenti o crea nuove sottosezioni coerenti, preservando la continuità logica e la voce accademica della nota originale.
3. **Chirurgicità Assoluta:**
   - Nelle richieste di correzione puntuale (`edit_mode: "surgical_prompt"`), intervieni esclusivamente sui punti menzionati nella richiesta dell'utente, lasciando il 100% del restante documento perfettamente intatto.
4. **Preservazione dei Metadati e del Grafo:**
   - Conserva sempre i tag, gli alias, la proprietà `Disciplina` e i [[wikilink]] consolidati, arricchendoli se la modifica introduce nuove correlazioni.

---

## LEGGE 8: Palestra d'Esame Interattiva (Flashcard & Quiz) e Sincronizzazione Anki

Ogni Nota Normale generata o riformattata nel vault deve terminare **obbligatoriamente** con un callout chiuso di default contenente il pannello interattivo DataviewJS e i dati strutturati per l'auto-valutazione e la sincronizzazione con Anki:

```markdown
> [!abstract]- Palestra d'Esame Interattiva: Flashcard e Quiz (Clicca per aprire)
> ```dataviewjs
> const panelPath = ".antigravity/scripts/study_panel.js";
> if (await app.vault.adapter.exists(panelPath)) {
>     const code = await app.vault.adapter.read(panelPath);
>     new Function("dv", code)(dv);
> } else {
>     await dv.view("Scripts/study_panel");
> }
> ```
> 
> %%STUDY_DATA
> ### FLASHCARD 1: [Titolo Concetto]
> **Q:** [Domanda di verifica attiva / Retrieval Practice]
> **A:** [Risposta rigorosa, completa e motivata a sforzo zero]
> 
> ### FLASHCARD 2: [Titolo Concetto]
> ... (minimo 6–10 Flashcard per ogni nota normale) ...
> 
> ### QUIZ 1: [Titolo Argomento]
> **Q:** [Domanda a scelta multipla con scenario, formula o proprietà]
> - [ ] A) [Opzione A]
> - [ ] B) [Opzione B]
> - [ ] C) [Opzione C]
> - [ ] D) [Opzione D]
> **CORRECT:** B
> **EXPLANATION:** [Spiegazione rigorosa: perché B è vera e perché i distrattori A, C, D sono falsi / analisi delle trappole d'esame]
> 
> ### QUIZ 2: [Titolo Argomento]
> ... (minimo 4–6 Quiz per ogni nota normale) ...
> %%
```

### 1. Fondamenti Scientifici del Design delle Domande
Le Flashcard e i Quiz non sono un riassunto mnemonico passivo, ma uno strumento di consolidamento neurobiologico basato su tre pilastri della ricerca cognitiva:
1. **Retrieval Practice (Roediger & Karpicke, 2006):** Il richiamo attivo forzato della memoria consolida le connessioni sinaptiche molto più della rilettura passiva ed elimina l'illusione di competenza (*fluency illusion*).
2. **Elaborative Interrogation (Dunlosky et al., 2013):** Stimolare la domanda sul "Perché" di una proprietà, di un'ipotesi o di un meccanismo costringe la mente a integrare le nuove nozioni con la rete di conoscenze pregresse.
3. **Desirable Difficulties (Bjork & Bjork, 2011):** Domande stimolanti, che richiedono discriminazione critica tra casi limite e analisi di trabocchetti, producono un apprendimento profondo, duraturo e trasferibile.

### 2. Standard Quantitativi e Qualitativi Obbligatori
- **Quantità Minima:** Ogni nota normale deve contenere **almeno 6–10 Flashcard** e **almeno 4–6 Quiz a Scelta Multipla**.
- **Divieto Assoluto di Quesiti Banali o Puri Esercizi di Memoria:** È severamente vietato formulare domande come *"Qual è la definizione di X?"* o *"In che anno è stato scoperto Y?"*.
- **I 4 Ambiti di Indagine Obbligatori:**
  1. **Il "Perché" dei Vincoli e delle Ipotesi:** Cosa crolla se cade una specifica ipotesi? (Es. *"Perché nel teorema di Rolle è richiesta la continuità sull'intervallo chiuso e non solo sull'aperto? Quale controesempio invalida la tesi se la funzione è discontinua agli estremi?"*).
  2. **Decodifica di Formule, Simboli e Meccanismi:** Cosa rappresenta un termine specifico in una formula o un passaggio in una reazione/circuito? (Es. *"Nell'equazione di Schrödinger, cosa quantifica il termine $-\frac{\hbar^2}{2m}\nabla^2$ e perché include il segno meno?"*).
  3. **Individuazione di Trappole d'Esame e Falsi Ragionamenti (Distrattori Plausibili):** Nei Quiz a 4 opzioni, i distrattori (opzioni errate) devono rappresentare i tipici errori commessi dagli studenti (scambio di ipotesi e tesi, errori di segno, generalizzazioni indebite). Nel campo `**EXPLANATION:**` devi analizzare esplicitamente **sia la risposta corretta sia i trabocchetti dei distrattori**.
  4. **Applicazione Pratica, Discriminazione e Calcolo Rapido:** Porre scenari operativi in cui bisogna scegliere il metodo o il setup corretto (es. *"Tra questi 4 integrali, quale non può essere risolto per parti standard e richiede la sostituzione euleriana?"*).

### 3. Sincronizzazione Automatica e Continua con Anki
- Il blocco `%%STUDY_DATA` è strutturato per essere sincronizzato sia tramite il pulsante **`Sincronizza con Anki`** nel pannello di Obsidian, sia tramite lo script `.antigravity/tools/anki_sync.py`.
- Il mazzo Anki segue la tassonomia gerarchica: `Obsidian::<Polo>::<Disciplina>::<Titolo Nota>`.
- Tutte le formule LaTeX sono convertite automaticamente nei delimitatori nativi MathJax di Anki (`\[...\]` e `\(...\)`), garantendo una resa impeccabile su desktop e mobile.

---

## LEGGE 9: Rilevatore Critico di Contraddizioni ed Evoluzioni Epistemiche (CONDIZIONALE)

La conoscenza scientifica e accademica non è statica ma dinamica e in continua evoluzione. Tuttavia, **la presenza di sezioni o callout sui conflitti epistemici non deve mai essere forzata o artificiosa**: compare **esclusivamente se esiste una reale contraddizione concettuale, una discrepanza nei dati/parametri o un'evoluzione accertata** tra le nuove fonti e quanto già presente nel vault.

1. **Consultazione del Dossier `existing-vault-claims.md`:**
   - Prima di iniziare la stesura o il merge, leggi attentamente `.antigravity/job-context/existing-vault-claims.md`.
   - Se le affermazioni della fonte concordano con il vault o ne rappresentano una naturale estensione coerente, **non inserire alcun callout di conflitto epistemico**.
2. **Callout di Conflitto Epistemico / Evoluzione (Solo se Reale ed Evidente):**
   - Esclusivamente quando rilevi una vera contraddizione concettuale, un cambiamento di consenso scientifico o un dato divergente, inserisci il callout di allerta critica:
     ```markdown
     > [!warning] Conflitto Epistemico / Evoluzione rispetto a [[Nome Nota Esistente#Paragrafo]]
     > - **Cosa riporta la nota precedente nel vault**: <Sintesi fedele e puntuale dell'affermazione precedente>
     > - **Cosa afferma la nuova fonte / letteratura**: <Sintesi della nuova evidenza o della prospettiva divergente>
     > - **Risoluzione Critica**: <Spiegazione rigorosa del motivo della differenza: es. popolazione di studio differente, evoluzione temporale del consenso, metodologia di misurazione diversa, assunzione di ipotesi non dichiarate o divergenza tra scuole di pensiero>
     ```
3. **Mantenimento della Coerenza Bidirezionale:**
   - Se la nota precedente nel vault riportava un dato ormai superato o falsificato, aggiorna coerentemente anche la nota precedente con un rimando critico.

---

## LEGGE 10: Visualizzazione Strutturale con Diagrammi `Mermaid.js` Anti-Crash

La comprensione a sforzo cognitivo zero richiede che la struttura logica, temporale o causale dei concetti complessi sia visualizzabile a colpo d'occhio.

1. **Quando Generare Obbligatoriamente un Diagramma ` ```mermaid `:**
   - **Assenza di Immagini Didattiche:** Ogni volta che la fonte sorgente non include già un'immagine esplicativa per un processo a più stadi, una catena causale o un'architettura.
   - **Mappa Mentale / Catena Causale:** Per sintetizzare flussi di causa-effetto (es. cascate biochimiche in Medicina/Bodybuilding, catene di eventi storici, modelli macroeconomici, passaggi di compilazione o transizioni di stato).
   - **Tipologie di Diagramma Consentite:**
     * `flowchart TD` (standard universale per flussi causali, pipeline, algoritmi e alberi decisionali) o `flowchart LR` (rigorosamente circoscritto a sequenze brevi di max 3-4 nodi).
     * `sequenceDiagram` per protocolli di comunicazione, flussi contrattuali nell'industria musicale o interazioni tra attori.
     * `stateDiagram-v2` per macchine a stati finiti, cicli metabolici o fasi di un sistema.
2. **REGOLA SINTATTICA FERREA OBSIDIAN MERMAID (Anti-Crash):**
   - Il parser Mermaid nativo di Obsidian va in crash se le etichette dei nodi contengono parentesi tonde `( )`, quadre `[ ]`, due punti `:`, virgole o operatori matematici non protetti.
   - **VINCOLO TASSATIVO:** Racchiudi **SEMPRE** il testo di ciascun nodo e di ciascuna freccia tra **doppi apici (`"..."`)**:
     ```mermaid
     flowchart LR
       A["Stimolo Meccanico (Tensione)"] -->|"Attiva sensori integrine"| B["Complesso mTORC1"]
       B -->|"Fosforilazione p70S6K"| C["Sintesi Proteica Muscolare (MPS)"]
     ```
   - **Divieto Assoluto di Formule $\LaTeX$ dentro Mermaid:** Il motore Mermaid di Obsidian non compila i delimitatori `$...$` o `$$...$$` all'interno dei nodi e va in errore. Utilizza esclusivamente caratteri e simboli Unicode standard puliti tra virgolette (es. `∀`, `∃`, `→`, `←`, `↑`, `↓`, `Δ`, `α`, `β`, `γ`, `λ`, `≠`, `≤`, `≥`, `≈`, `∈`).
3. **Standard di Orientamento e Layout dei Nodi (Fit-to-Width & Leggibilità):**
   - **Orientamento Standard (`flowchart TD`):** Per tutte le catene causali, gli algoritmi, le derivazioni matematiche e i flussi logici complessi utilizza **obbligatoriamente `flowchart TD`** (sviluppo verticale dall'alto verso il basso), in modo da sfruttare l'altezza della pagina senza comprimere la scala dei caratteri.
   - **Uso Ristretto di `flowchart LR`:** Usa l'orientamento orizzontale (`flowchart LR`) **esclusivamente** per sequenze lineari brevi di al massimo **3-4 nodi**.
   - **Concavità e Sintesi del Testo dei Nodi:** Il testo all'interno di ciascun nodo deve essere conciso ed ergonomico: massimo **5-7 parole per riga**, spezzando le frasi più articolate tramite il tag `<br/>` per andare a capo (es. `A["Costruzione di Dedekind<br/>su sezioni contigue"]`).

---

## LEGGE 11: Sintesi Multi-Fonte (Cross-Notebook) e Fusione Interdisciplinare (CONDIZIONALE)

Quando crei una nuova nota o una roadmap MOC partendo da più NotebookLM contemporaneamente (o combinando notebook di diverse discipline), devi applicare il principio di **fusione sinergica dei contesti**:

1. **Divieto di Giustapposizione Asfittica (Fusione Organica):**
   > Se ti vengono fornite informazioni estratte da più NotebookLM contemporaneamente, non limitarti a incollarle in blocchi separati. Devi **fondere organicamente i concetti**, evidenziando i collegamenti logici, i punti in comune o le eventuali contraddizioni tra i diversi notebook all'interno della struttura rigorosa della nota.
2. **Architettura per Macro-Temi Logici:**
   - La struttura della nota non deve mai ricalcare i singoli notebook d'origine (es. è severamente vietato intitolare i paragrafi *"Cosa dice il Notebook 1"* e *"Cosa dice il Notebook 2"*).
   - I paragrafi (`##`, `###`) devono essere organizzati secondo l'evoluzione concettuale dell'argomento, tessendo insieme definizioni, parametri sperimentali e modelli teorici provenienti da ciascun notebook.
3. **Ponti Interdisciplinari (Nessuna Sezione Artificiale):**
   - I confronti interdisciplinari o i ponti tra materie diverse compaiono **solo se esistono davvero nelle fonti o aggiungono comprensione fondamentale**.
   - È vietato inserire paragoni forzati o sezioni interdisciplinari artificiose se la materia non lo richiede naturalmente. Se presenti, evidenzia esplicitamente come un concetto studiato in una disciplina (es. la tensione meccanica o la biochimica dell'ATP) si raccordi con i modelli di un'altra materia (es. la biomeccanica articolare o la programmazione dell'allenamento).

---

*La Costituzione Universale è vincolante per qualsiasi interazione con il vault Obsidian.*

---

## LEGGE 12: Vincolo della Fonte NotebookLM (Anti-Fallback Totale e Modalità Conoscenza)

Quando una nota, un MOC o una modifica viene generata a partire da **NotebookLM** (singolo o multi-notebook), l'agente Antigravity opera secondo una disciplina rigorosa che garantisce la fedeltà assoluta alle fonti universitarie dell'utente, eliminando ogni rischio di allucinazione o deviazione arbitraria.

---

### 1. Hard-Gate Universale Anti-Fallback (Fail-Fast Obbligatorio in Entrambe le Modalità)
Indipendentemente dalla modalità di conoscenza selezionata dall'utente (`allow_base_knowledge: false` oppure `allow_base_knowledge: true`):
1. **Estrazione Reale Obbligatoria:** L'orchestratore deve sempre interrogare tutti i notebook selezionati tramite `nlm`, salvare il testo in `extracted_source.md` e mostrare il conteggio esatto dei caratteri sulla loading bar HUD.
2. **Soglia Minima di 400 Caratteri Reali:** Se l'estrazione da `nlm` fallisce, va in errore, restituisce credenziali scadute o produce meno di **400 caratteri reali**, l'esecuzione **DEVE INTERROMPERSI IMMEDIATAMENTE** con errore. È severamente vietato procedere e generare la nota a partire dalla memoria pre-addestrata dell'AI se l'estrazione non ha avuto successo.

---

### 2. Modalità `allow_base_knowledge: false` ( Solo NotebookLM — Esclusivo / Zero Conoscenza Esterna)
Quando l'utente seleziona la modalità esclusiva:
1. **Confinamento Rigoroso a `extracted_source.md`:** Tutto ciò che viene inserito nella nota — definizioni, impostazione didattica, notazioni del docente, enunciati di teoremi, dimostrazioni ed esempi — deve provenire **esclusivamente** da quanto registrato nel dossier estratto.
2. **Nessun Teorema o Concetto Non Presente:** Se il professore o il libro nel notebook non trattano un argomento o una dimostrazione accessoria, l'agente non deve aggiungerlo. Se una dimostrazione manca nelle fonti, l'agente dichiara esplicitamente: `*(Dimostrazione non presente nelle fonti del professore)*` invece di inventarla.
3. **Fedeltà Notazionale Assoluta:** Adotta al 100% i simboli e le convenzioni del docente/testo presenti nell'estrazione.
4. **Unico Uso Consentito della Capacità Deduttiva:** L'intelligenza matematica/logica dell'agente può essere usata **esclusivamente per**:
   - Esplicitare i passaggi matematici intermedi saltati negli appunti (*Zero Passi Saltati*).
   - Decodifica Logico-Formale a Sforzo Zero (Legge 3).
   - Formulazione di flashcard e quiz per la Palestra d'Esame (Legge 8).

---

### 3. Modalità `allow_base_knowledge: true` (+ NotebookLM Primario + Conoscenza Base AI Integrativa)
Quando l'utente autorizza l'integrazione accademica:
1. **Gerarchia Ferrea (Primato Assoluto del NotebookLM):**
   - Il materiale estratto in `extracted_source.md` è la **spina dorsale inviolabile**: comanda su struttura, taglio didattico, notazioni del professore, definizioni principali e impostazione metodologica.
   - In caso di discrepanza o diverso formalismo tra la tua conoscenza base e il NotebookLM, **vince sempre e indiscutibilmente il NotebookLM**.
2. **Ruolo della Conoscenza di Base (Tutor Accademico di Supporto):**
   L'agente è autorizzato a usare la propria conoscenza accademica pre-addestrata per:
   - **Completare ed espandere:** Approfondire definizioni, casi particolari, osservazioni o proprietà che negli appunti del NotebookLM sono solo accennati, sintetici o incompleti.
   - **Dimostrazioni complete:** Fornire dimostrazioni rigorose complete se nelle fonti del NotebookLM è riportato solo l'enunciato o una traccia parziale (adottando rigorosamente i simboli e l'approccio del docente).
   - **Controesempi e Intuizioni Geometriche:** Aggiungere controesempi canonici, interpretazioni geometriche/intuitive ed esempi chiarificatori che arricchiscono la comprensione concettuale.
   - **Completamento MOC Pre-Esame:** Nei MOC, colmare eventuali buchi logici tra una lezione e l'altra del professore o omissioni dell'indice, garantendo che il percorso propedeutico d'esame sia coperto al 100%.
   - **Confine Concettuale Atomico:** Rispettare sempre il confine concettuale della singola nota (un solo concetto/teorema cardine per nota, senza inglobare teoremi derivati o metodi che appartengono a note separate collegate tramite [[wikilink]]).
