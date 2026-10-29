# Profilo Disciplinare: Economia e Finanza

> [!IMPORTANT]
> **Polo:** `#personale` | **Tag:** `#economia_e_finanza`  
> Questo profilo stabilisce gli standard analitici per Macroeconomia, Politica Monetaria, Mercati Finanziari, Finanza Aziendale, Teoria degli Investimenti e Dinamiche Bancarie.

---

## Filosofia e Regole Fondamentali

1. **La Catena Causale delle Variabili Economiche:**
   - In economia non esistono variabili isolate: quando una banca centrale muove i tassi o quando il prezzo del petrolio sale, si attiva un effetto domino determinabile che tocca mutui, occupazione, investimenti aziendali, tassi di cambio e consumi al dettaglio.
   - Ogni trattazione deve rappresentare visivamente questa catena con **frecce logiche direzionali ($\uparrow, \downarrow, \implies$)**, spiegando riga per riga il meccanismo di causa-effetto.
2. **L'Obbligo dell'Esempio Numerico Concreto:**
   - Le formule matematiche (es. rendimento effettivo a scadenza YTM, equazione quantitativa della moneta $M \cdot V = P \cdot Y$, costo medio ponderato del capitale WACC) devono essere obbligatoriamente accompagnate da un **esempio numerico semplice e realistico** con Euro/Dollari e percentuali, calcolato passo dopo passo.
3. **I Limiti del Modello e i Ritardi di Trasmissione (*Time Lags*):**
   - La teoria economica pura assume spesso mercati privi di attrito e agenti razionali. Le note devono chiarire sempre la realtà empirica: i ritardi lunghi e variabili (*long and variable lags*, tipicamente 12-18 mesi prima che un rialzo dei tassi raffreddi i prezzi) e gli effetti collaterali distorsivi.

---

## Il Callout Obbligatorio: "Decodifica Economica"

```markdown
> [!note] Decodifica Economica: Tassi d'Interesse Ufficiali e Politica Monetaria Restrittiva
> **1. Definizione Tecnica e Strumento di Mercato:**
> Il tasso di riferimento sui depositi o sui rifinanziamenti principali fissato dalla Banca Centrale (BCE o Federal Reserve) per le operazioni di mercato aperto con le banche commerciali.
>
> **2. Come si legge e Meccanismo sul Sistema Bancario:**
> "Quando la Banca Centrale alza il tasso ufficiale (es. dal $0\%$ al $4.5\%$), il costo a cui le banche commerciali prendono in prestito denaro a breve termine aumenta all'istante. Le banche commerciali trasferiscono questo rincaro sui tassi applicati a mutui, prestiti personali e linee di credito alle aziende, rendendo l'indebitamento più oneroso e remunerando maggiormente i conti deposito vincolati."
>
> **3. Cosa significa in concreto a Sforzo Cognitivo Zero:**
> I tassi di interesse sono come il pedale del freno dell'economia: alzare i tassi significa rendere il denaro "scarso e caro". Se il mutuo per la casa passa da 500 a 900 euro al mese e il prestito per macchinari industriali costa il doppio, famiglie e imprese rimandano gli acquisti non essenziali. Minori acquisti significano che i commercianti smettono di alzare i prezzi, raffreddando l'inflazione al prezzo però di rallentare la crescita e rischiare la disoccupazione.
```

---

## Scaletta Strutturale delle Note di Economia e Finanza

### 1. Frontmatter YAML
```yaml
---
Disciplina: Economia e Finanza
Type:
  - Concetto # oppure Metodo se si tratta di una formula di pricing/valutazione
tags:
  - economia_e_finanza
  - personale
aliases:
  - Politica Monetaria
  - Tassi di Interesse
  - Meccanismo di Trasmissione
  - Inflazione
---
```

### 2. Definizione Rigorosa e Inquadramento del Fenomeno
- Tipologie della variabile (es. inflazione da domanda vs inflazione da costi da shock energetico; tassi nominali vs tassi reali corretti per l'inflazione tramite l'equazione di Fisher $r = i - \pi$).
- Mandato statutario delle Banche Centrali (stabilità dei prezzi all'$2\%$ per la BCE; doppio mandato inflazione/piena occupazione per la Fed).

### 3. Callout Decodifica Economica

### 4. La Catena Causale delle Variabili
Mappa logico-deduttiva esplicita del meccanismo di trasmissione monetaria:

```markdown
### La Catena Causale del Meccanismo di Trasmissione (Dai Tassi all'Inflazione)

$$\text{Rialzo Tassi Centrali} (\uparrow i) \implies \text{Costo del Credito Bancario} (\uparrow) \implies \text{Erogazione Mutui e Finanziamenti} (\downarrow)$$
$$\implies \text{Investimenti Industriali e Consumi a Debito} (\downarrow) \implies \text{Domanda Aggregata} (\downarrow AD)$$
$$\implies \text{Pressione sui Prezzi dei Beni al Dettaglio} (\downarrow P) \implies \text{Raffreddamento dell'Inflazione} (\downarrow \pi)$$

#### Dettaglio delle Fasi di Causa-Effetto
1. **Canale dei Tassi e del Costo del Capitale:**  
   L'aumento dei tassi d'interesse disincentiva le aziende dall'avviare nuovi investimenti a lungo termine (poiché il valore attuale netto dei flussi di cassa futuri attualizzati decresce).
2. **Canale del Prezzo delle Attività Finanziarie (Effetto Ricchezza):**  
   Tassi più alti aumentano i rendimenti obbligazionari $\implies$ calo dei corsi azionari e dei prezzi immobiliari $\implies$ i cittadini si percepiscono meno ricchi riducendo la propensione marginale al consumo.
3. **Canale del Tasso di Cambio:**  
   Tassi domestici più elevati attraggono capitali esteri a caccia di rendimento $\implies$ apprezzamento della valuta locale $\implies$ le importazioni (inclusi petrolio e materie prime) costano meno, importando deflazione.
```

### 5. Callout Obbligatorio "Esempio Numerico Concreto"
Simulazione matematica con valori tangibili:

```markdown
> [!example] Esempio Numerico Concreto: L'Impatto di un Rialzo del 3% su un Mutuo Casa
> Ipotizziamo un cittadino che accende un mutuo a tasso variabile di **200.000€ su 25 anni** (300 rate mensili):
>
> - **Scenario 1 (Tassi a zero, Euribor 0% + Spread 1% = Tasso 1.0%):**  
>   Rata mensile = **753.60€**  
>   Quota interessi totale restituita alla banca in 25 anni = **26.080€**.
>
> - **Scenario 2 (Stretta monetaria, Euribor 3% + Spread 1% = Tasso 4.0%):**  
>   Rata mensile = **1.055.70€** ($+302.10\text{€ al mese}$, pari a $+40\%$)  
>   Quota interessi totale restituita alla banca = **116.710€** ($+90.630\text{€}$ solo di interessi).
>
> **L'Effetto Macroeconomico:** Quel consumatore ha all'istante **300€ in meno al mese** da spendere in ristoranti, abbigliamento o viaggi. Moltiplicato per milioni di famiglie, i consumi crollano provocando la contrazione della domanda e la stabilizzazione dei listini prezzi.
```

### 6. Limiti del Modello, Ritardi Temporali ed Effetti Collaterali
- **Stagflazione e Shock da Offerta:** Se l'inflazione è causata dal blocco delle forniture di gas o petrolio (e non da un'economia surriscaldata da eccesso di credito), alzare i tassi abbatte la produzione senza risolvere la penuria fisica della risorsa, generando disoccupazione con prezzi che restano alti (*stagflazione*).
- **Rischio di Instabilità Finanziaria:** L'improvvisa svalutazione dei titoli di stato a tasso fisso in pancia agli istituti di credito (come nel collasso di Silicon Valley Bank nel 2023).
- **Ponti Interdisciplinari:** [[Storia]] (il ciclo Volcker del 1979-1982), [[Politica e Geopolitica]] (guerre valutarie, ruolo del dollaro).
