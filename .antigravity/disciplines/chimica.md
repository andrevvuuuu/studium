# Profilo Disciplinare: Chimica

> [!IMPORTANT]
> **Polo:** `#personale` | **Tag:** `#chimica`  
> Questo profilo definisce gli standard per Chimica Generale, Inorganica, Chimica Organica, Termodinamica Chimica e Meccanismi di Reazione.  
> **Integrazione Tool Automatica:** `science_media_fetch.py` (download delle strutture molecolari 2D ad alta risoluzione da PubChem e schemi da Wikimedia Commons).

---

## Filosofia e Regole Fondamentali

1. **Il Comportamento Elettronico Governa la Materia:**
   - Tutte le proprietà macroscopiche osservabili (stato fisico, punto di ebollizione, tensione di vapore, solubilità, conducibilità, acidità $\text{p}K_a$) sono la diretta conseguenza della configurazione elettronica microscopica: densità di carica, elettronegatività di Pauling, ibridazione degli orbitali ($sp, sp^2, sp^3$) e geometria tridimensionale (teoria VSEPR).
2. **Meccanismi di Reazione Senza Salti di Frecce:**
   - Nei meccanismi di reazione organici o inorganici, descrivi sempre esplicitamente il movimento dei doppietti elettronici (frecce curve):
     - *Chi è il nucleofilo (specie ricca di elettroni, base di Lewis)?*
     - *Chi è l'elettrofilo (specie povera di elettroni, acido di Lewis)?*
     - *Qual è l'ingombro sterico del centro di reazione?*
     - *Qual è il gruppo uscente migliore e perché la sua base coniugata è stabile?*
3. **Termodinamica vs Cinetica:**
   - Distingui sempre tra controllo termodinamico (stabilità relativa dei prodotti governata da $\Delta G^\circ = \Delta H^\circ - T\Delta S^\circ$) e controllo cinetico (barriera dell'energia di attivazione $E_a$ e stabilità dello stato di transizione secondo l'equazione di Arrhenius).
4. **Ponti con le Altre Discipline:**
   - Collega le strutture chimiche direttamente a `Biologia` (macromolecole), `Neuroscienze` (neurotrasmettitori) e `Droghe` (farmacofori e relazioni struttura-attività SAR).

---

## Il Callout Obbligatorio: "Decodifica Chimico-Fisica e Molecolare"

```markdown
> [!note] Decodifica Chimico-Fisica e Molecolare: Legame Covalente Polare e Ibridazione $sp^3$
> **1. Formula, Geometria e Angoli di Legame:**
> $$ \text{H}_2\text{O} \quad \implies \quad \text{Geometria:} \text{ Piegata (Bent)}, \quad \angle_{\text{H-O-H}} \approx 104.5^\circ $$
>
> **2. Come si legge e Parametri Elettronici:**
> "La molecola d'acqua è costituita da un atomo centrale di ossigeno con ibridazione $sp^3$ legato covalentemente a due atomi di idrogeno tramite orbitali molecolari di tipo $\sigma(sp^3\text{-}1s)$, con due doppietti elettronici solitari (*lone pairs*) non condivisi."
>
> **3. Meccanismo Elettronico, Sterico e Conseguenze Macroscopiche:**
> A causa della notevole differenza di elettronegatività ($\Delta\chi = 3.44 - 2.20 = 1.24$), i legami $\text{O-H}$ sono fortemente polarizzati ($\delta^-$ sull'ossigeno, $\delta^+$ sugli idrogeni). I due doppietti solitari esercitano una repulsione elettrostatica maggiore rispetto alle coppie di legame, comprimendo l'angolo tetraedrico ideale di $109.5^\circ$ fino a $104.5^\circ$. La mancata cancellazione dei vettori di momento dipolare genera un dipolo molecolare permanente netto ($\mu \approx 1.85\text{ Debye}$), conferendo all'acqua un'elevata costante dielettrica ($\varepsilon_r \approx 80$) e la capacità di formare reti tridimensionali di legami a idrogeno responsabili del suo alto punto di ebollizione anomalo ($100^\circ\text{C}$).
```

---

## Meccanismo di Reazione Passo-Passo

I meccanismi chimici devono essere dettagliati a passaggi numerati con esplicitazione degli intermedi:

```markdown
### Meccanismo di Reazione Passo-Passo: Sostituzione Nucleofila Bimolecolare ($S_N2$)

1. **Avvicinamento del Nucleofilo con Attacco da Tergo (*Backside Attack*):**  
   Il nucleofilo forte (es. lo ione idrossido $\text{OH}^-$) si avvicina al carbonio elettrofilo con un angolo rigoroso di $180^\circ$ rispetto al legame con il gruppo uscente (alogeno), per massimizzare la sovrapposizione con il lobo posteriore dell'orbitale antilegante vuoto $\sigma^*$.
2. **Formazione dello Stato di Transizione Pentacoordinato a Più Alta Energia:**  
   Si forma uno stato di transizione instabile in cui il carbonio centrale assume una geometria trigonale bipiramidale transitoria: il legame con il nucleofilo si sta parzialmente formando ($\delta^-$) mentre il legame con il gruppo uscente si sta parzialmente rompendo ($\delta^-$).
3. **Espulsione del Gruppo Uscente ed Inversione di Configurazione (Inversione di Walden):**  
   L'alogenuro (es. $\text{Br}^-$) viene espulso come base debole stabile portando con sé il doppietto elettronico. Il carbonio centrale recupera l'ibridazione tetraedrica $sp^3$, ma con i suoi tre sostituenti ribaltati come un ombrello al vento (inversione stereochimica totale $R \leftrightarrow S$).
```

---

## Scaletta Strutturale delle Note di Chimica

1. **Frontmatter YAML** (`Disciplina: Chimica`, `Type: [Concetto | Metodo]`).
2. **Identikit del Composto o della Reazione:** Formula bruta, formula di struttura, peso molecolare, nome IUPAC e CAS registry number.
3. **Integrazione Immagine Strutturale 2D (PubChem):**
   - Inserimento dell'immagine scaricata con `science_media_fetch.py`: `![[struttura_chimica_<molecola>.png]]`.
4. **Callout Decodifica Chimico-Fisica e Molecolare.**
5. **Meccanismo Elettronico o Fasi di Reazione Passo-Passo.**
6. **Proprietà Fisico-Chimiche Spiegate a Livello Microscopico:**
   - Tabella delle costanti fisiche (punto di fusione, ebollizione, costante dielettrica, $\text{p}K_a$).
   - Spiegazione del *perché* di ciascun valore in base a legami a idrogeno, polarità e forze di dispersione di London.
7. **Reattività, Sintesi e Applicazioni Pratiche:**
   - Reagenti compatibili e incompatibilità pericolose (es. reazioni fortemente esotermiche o formazione di gas tossici).
