# Profilo Disciplinare: Biologia

> [!IMPORTANT]
> **Polo:** `#università` | **Tag:** `#biologia`  
> Questo profilo regola le note di Biologia Molecolare, Biochimica, Genetica, Biologia Cellulare e Fisiologia Comparata.  
> **Integrazione Tool Automatica:** `pubmed_search.py` (ricerca meccanicistica) e `science_media_fetch.py` (strutture molecolari e schemi d'organello).

---

## Filosofia e Regole Fondamentali

1. **La Biologia fondata sulla Chimica e sulla Termodinamica:**
   - La vita non viola le leggi fisiche: ogni processo biologico (dalla replicazione del DNA alla glicolisi) è guidato dall'energia libera di Gibbs ($\Delta G = \Delta H - T\Delta S$) e da accoppiamenti termodinamici con l'idrolisi di legami ad alto potenziale energetico ($\text{ATP} \to \text{ADP} + \text{P}_i$).
2. **Precisione Molecolare ed Enzimatica Assoluta:**
   - Indica sempre gli enzimi specifici con la loro classe e cofattori necessari (es. *Elicasi, DNA Polimerasi III con subunità $\beta$-clamp e magnesio $\text{Mg}^{2+}$, Topoisomerasi/Girasi, Fosfofruttochinasi-1*).
3. **Catena Enzimatica Senza Salti Logici:**
   - Ogni tappa metabolica deve chiarire:
     - *Qual è il substrato iniziale?*
     - *Quale legame chimico viene rotto o formato?*
     - *Qual è il bilancio energetico e redox ($\text{NADH}, \text{FADH}_2, \text{ATP}$)?*
     - *Perché la cellula compie questo passaggio invece di procedere direttamente?*
4. **Ponti con le Altre Discipline:**
   - Collega le vie metaboliche a `Nutrizione e Salute` (glicolisi, lipolisi, sintesi proteica) e a `Bodybuilding` (segnalazione mTORC1/AMPK, biogenesi mitocondriale).

---

## Il Callout Obbligatorio: "Decodifica Molecolare e Cellulare"

```markdown
> [!note] Decodifica Molecolare e Cellulare: Il Dogma Centrale della Biologia Molecolare
> **1. Enunciato Molecolare Fondamentale:**
> $$ \text{DNA} \xrightarrow[\text{DNA Polimerasi}]{\text{Replicazione}} \text{DNA} \xrightarrow[\text{RNA Polimerasi II}]{\text{Trascrizione}} \text{mRNA} \xrightarrow[\text{Ribosoma (28S/18S) + tRNA}]{\text{Traduzione}} \text{Proteina} $$
>
> **2. Come si legge e Flusso Informazionale:**
> "L'informazione genetica conservata stabilmente nella sequenza di desossiribonucleotidi del DNA viene duplicata fedelmente durante la fase S del ciclo cellulare; viene poi trascritta in una molecola transitoria a singolo filamento di RNA messaggero (mRNA) nel nucleo, ed infine decodificata nel citoplasma dai complessi ribosomiali in una sequenza polipeptidica primaria di amminoacidi legati tramite legami peptidici covalenti."
>
> **3. Motore Termodinamico e Direzionalità Obbligata:**
> La sintesi degli acidi nucleici avviene rigorosamente in direzione $5' \to 3'$, spinta termodinamicamente dall'idrolisi irreversibile del pirofosfato inorganico ($\text{PP}_i \to 2\text{P}_i$, con $\Delta G'^\circ \approx -33.5\text{ kJ/mol}$) liberato dai desossiribonucleosidi trifosfati precursori ($\text{dNTP}$). L'informazione proteica non può mai essere re-ingegnerizzata a ritroso in sequenza nucleotidica.
```

---

## La Catena Enzimatica Passo-Passo

Ogni via biochimica o processo molecolare deve essere documentato con passaggi numerati esaustivi:

```markdown
### Catena Enzimatica Passo-Passo: Iniziazione e Allungamento della Replicazione del DNA

1. **Riconoscimento delle Origini di Replicazione (*oriC*):**  
   Proteine iniziatrici specifiche (come DnaA nei procarioti o il complesso ORC negli eucarioti) legano sequenze ricche di paia adenina-timina ($A=T$, dotate di soli 2 legami idrogeno invece dei 3 tra $G \equiv C$), facilitando la prima denaturazione locale della doppia elica.
2. **Svolgimento Meccanico tramite Elicasi (DnaB / MCM2-7):**  
   L'elicasi si ancora a monte e consuma idrolisi di ATP per rompere i legami a idrogeno tra le basi azotate, aprendo la forcella replicativa con velocità fino a 1000 paia di basi al secondo.
3. **Rilascio della Tensione Torsionale (Topoisomerasi / Girasi):**  
   Lo svolgimento rapido accumula superavvolgimenti positivi a valle della forcella. La topoisomerasi taglia transitoriamente uno o entrambi i filamenti di fosfodiestere, fa ruotare l'elica per dissipare lo stress torsionale e risalda il legame.
4. **Stabilizzazione del Singolo Filamento (Proteine SSB / RPA):**  
   Le proteine di legame al singolo filamento impediscono che le basi idrofobiche esposte si riappaino spontaneamente o formino strutture a forcina prima del passaggio della polimerasi.
5. **Sintesi dell'Innesco tramite Primasi (RNA Primasi):**  
   Poiché nessuna DNA polimerasi nota è in grado di iniziare la sintesi *de novo* da zero senza un ossidrile libero, la primasi sintetizza un corto oligonucleotide di RNA di circa 10 nucleotidi fornendo il gruppo $3'\text{-OH}$ essenziale.
6. **Polimerizzazione Processiva ad Alta Fedeltà (DNA Polimerasi III / Pol $\delta$ e $\varepsilon$):**  
   La polimerasi attacca il gruppo fosfato in $\alpha$ del nuovo dNTP entrante all'ossidrile $3'\text{-OH}$ dell'innesco, rilasciando pirofosfato. L'attività esonucleasica intrinseca $3' \to 5'$ (*proofreading*) rimuove all'istante eventuali basi male appaiate, riducendo il tasso d'errore a meno di $1 \text{ su } 10^9$.
```

---

## Scaletta Strutturale delle Note di Biologia

1. **Frontmatter YAML** (`Disciplina: Biologia`, `Type: [Concetto | Teorema | Metodo]`).
2. **Significato Fisiologico ed Evolutivo:** Quale funzione vitale per la cellula o l'organismo garantisce questo meccanismo?
3. **Callout Decodifica Molecolare e Cellulare.**
4. **Catena Enzimatica Passo-Passo.**
5. **Bilancio Energetico e Termodinamico ($\text{ATP}, \text{NADH}, \Delta G$):**
   - Resa netta quantitativa per molecola di substrato.
6. **Regolazione Allosterica, Covalente ed Ormonale:**
   - Come viene acceso o spento il processo? (Es. insulina/glucagone, carica energetica $\text{ATP}/\text{AMP}$, feedback negativo da prodotto finale).
7. **Letteratura e Verifiche Sperimentali (Auto-Tool):**
   - Utilizzo di `pubmed_search.py` per citare studi biochimici su campioni umani o cellulari.
   - Integrazione di schemi e micrografie tramite `science_media_fetch.py`.
