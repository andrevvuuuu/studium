# Profilo Disciplinare: Matematica

> [!IMPORTANT]
> **Polo:** `#università` | **Tag:** `#matematica`  
> Questo profilo definisce gli standard formali, la struttura logica e le convenzioni visive obbligatorie per tutte le note di Analisi Matematica, Algebra Lineare, Geometria, Logica e Probabilità.

---

## Filosofia e Regole Fondamentali

1. **Rigorosa Traduzione del Simbolismo Logico:**
   - La matematica non è un geroglifico. Ogni enunciato contenente quantificatori ($\forall, \exists, \exists!, \nexists$), connettivi logici ($\implies, \iff, \land, \lor, \neg$) o insiemistica ($\in, \subset, \cup, \cap, \setminus$) deve essere immediatamente **decodificato parola per parola**.
2. **Zero Passaggi Sottintesi nei Calcoli:**
   - Nessun passaggio algebrico può essere etichettato come "ovvio", "immediato" o "banale".
   - Se si raccoglie a fattor comune, si razionalizza, si applica una disuguaglianza triangolare o si scambia l'ordine di limiti, occorre dichiararlo esplicitamente a lato.
3. **LaTeX Standard e Igiene dei Dollari:**
   - Tutte le variabili e le formule matematiche devono essere racchiuse in simboli del dollaro: `$x \in \mathbb{R}$` per il testo inline, `$$ ... $$` per le formule centrate su blocco separato.
   - Mai inserire [[wikilink]] dentro un blocco LaTeX.

---

## Il Callout Obbligatorio: "Decodifica Logico-Formale"

Ogni volta che viene introdotta una definizione formale, un assioma o un enunciato di teorema, deve comparire tassativamente questo blocco strutturato:

```markdown
> [!note] Decodifica Logico-Formale: <Nome del Concetto o Teorema>
> **1. Notazione Formale:**
> $$ \forall \varepsilon > 0, \, \exists \delta > 0 : \forall x \in \text{dom}(f), \, 0 < |x - x_0| < \delta \implies |f(x) - L| < \varepsilon $$
>
> **2. Come si legge (Traduzione Letterale Parola per Parola):**
> "Per ogni epsilon maggiore di zero, esiste un delta maggiore di zero tale che, per ogni $x$ appartenente al dominio della funzione, se la distanza tra $x$ e $x_0$ è strettamente compresa tra zero e delta, allora la distanza tra $f(x)$ ed $L$ è strettamente minore di epsilon."
>
> **3. Cosa significa (Spiegazione Rigorosa ma Intuitiva a Sforzo Cognitivo Zero):**
> Significa che non importa quanto stretto sia l'intervallo di tolleranza attorno al valore limite $L$ sull'asse $y$ (rappresentato da $\varepsilon$): riusciamo sempre a trovare un intorno sull'asse $x$ (di raggio $\delta$) abbastanza piccolo da intrappolare tutti i valori della funzione dentro quella striscia. In termini pratici, avvicinarsi ad $x_0$ garantisce che $f(x)$ sia arbitrariamente vicina a $L$.
```

---

## Dimostrazioni "A Sforzo Cognitivo Zero"

Le dimostrazioni matematiche non devono mai essere blocchi monolitici di testo. Devono essere racchiuse in un callout collassabile `> [!tip]- Dimostrazione: <Nome>` strutturato rigorosamente in **3 Atti**:

```markdown
> [!tip]- Dimostrazione: Teorema di Unicità del Limite
> **1. Strategia della Dimostrazione:**
> Procediamo per **dimostrazione per assurdo** (vedi [[Elementi di Logica Matematica]]). Supponiamo che esistano due limiti distinti $L_1 \neq L_2$. Sceglieremo una tolleranza $\varepsilon$ pari alla metà della loro distanza per mostrare che la funzione dovrebbe trovarsi contemporaneamente in due intorni disgiunti, violando la definizione di funzione.
>
> **2. Passaggi Logico-Deduttivi:**
> - **Passo 1 (Ipotesi d'Assurdo):**  
>   Supponiamo per assurdo che esistano $L_1, L_2 \in \mathbb{R}$ con $L_1 \neq L_2$ tali che:
>   $$ \lim_{x \to x_0} f(x) = L_1 \quad \text{e} \quad \lim_{x \to x_0} f(x) = L_2 $$
>
> - **Passo 2 (Scelta strategica di $\varepsilon$):**  
>   Poniamo $\varepsilon = \frac{|L_1 - L_2|}{2}$.  
>   *Perché proprio questa quantità?* Poiché $L_1 \neq L_2$, la distanza $|L_1 - L_2| > 0$, quindi $\varepsilon > 0$ è una scelta lecita. Questa metà esatta serve a fare in modo che gli intorni centrati in $L_1$ ed $L_2$ non si tocchino (siano disgiunti).
>
> - **Passo 3 (Applicazione della definizione di limite a $L_1$ e $L_2$):**  
>   Dalla definizione di limite per $L_1$, esiste $\delta_1 > 0$ tale che per ogni $0 < |x - x_0| < \delta_1$:
>   $$ |f(x) - L_1| < \varepsilon $$
>   Dalla definizione di limite per $L_2$, esiste $\delta_2 > 0$ tale che per ogni $0 < |x - x_0| < \delta_2$:
>   $$ |f(x) - L_2| < \varepsilon $$
>
> - **Passo 4 (Intersezione degli intorni):**  
>   Prendiamo $\delta = \min(\delta_1, \delta_2)$. Per ogni $x$ tale che $0 < |x - x_0| < \delta$, entrambe le disuguaglianze valgono contemporaneamente.
>
> - **Passo 5 (Disuguaglianza Triangolare e Contraddizione):**  
>   Valutiamo la distanza tra i due presunti limiti aggiungendo e togliendo $f(x)$:
>   $$ |L_1 - L_2| = |L_1 - f(x) + f(x) - L_2| $$
>   Applichiamo la disuguaglianza triangolare ($|a + b| \le |a| + |b|$):
>   $$ |L_1 - L_2| \le |L_1 - f(x)| + |f(x) - L_2| = |f(x) - L_1| + |f(x) - L_2| $$
>   Sostituiamo le maggiorazioni trovate al Passo 3:
>   $$ |L_1 - L_2| < \varepsilon + \varepsilon = 2\varepsilon $$
>   Ma al Passo 2 avevamo scelto $2\varepsilon = |L_1 - L_2|$. Sostituendo otteniamo:
>   $$ |L_1 - L_2| < |L_1 - L_2| $$
>   Una quantità strettamente minore di se stessa è una contraddizione logica insanabile ($k < k$).
>
> **3. Conclusione e Q.E.D.:**
> L'ipotesi che esistano due limiti distinti è falsa. Pertanto, se il limite esiste, esso è unico. $\blacksquare$
```

---

## Scalette per Tipo di Nota

> [!IMPORTANT]
> **Criterio di Confine Concettuale (Regola Fondamentale delle Core Guidelines):**
> Per ogni nota si applica tassativamente il test operativo DENTRO/FUORI e il vincolo di un solo `Type:` in formato lista YAML. Dentro una nota Concetto risiedono esclusivamente l'inquadramento, la definizione formale e le proprietà costitutive con dimostrazioni delle operazioni base. Tutti i teoremi derivati con nome proprio, i concetti con definizione autonoma e le procedure d'esame devono essere note autonome collegate tramite [[wikilink]] ed essere riassunte nella sottosezione finale `### Teoremi e Concetti Derivati (Note Separate)`.

### A. Scaletta per `Type: Teorema`
1. **Frontmatter YAML** (`Disciplina: Matematica`, `Type:\n  - Teorema`).
2. **Inquadramento Intuitivo:** A cosa serve questo teorema nel quadro della teoria? Qual è l'idea di base prima della formalizzazione?
3. **Enunciato Formale:**
   - **Ipotesi:** Elenco puntato di tutte le condizioni necessarie (es. continuità in $[a,b]$, derivabilità in $(a,b)$).
   - **Tesi:** Risultato garantito espresso sia in simboli che a parole.
4. **Callout Decodifica Logico-Formale** (se la tesi/ipotesi presenta simbolismo logico denso).
5. **Callout Dimostrazione a 3 Atti** (Strategia $\to$ Passaggi Logico-Deduttivi $\to$ Conclusione e Q.E.D.).
6. **Analisi Critica delle Ipotesi e Controesempi:**
   - *Cosa succede se cade una delle ipotesi?* (es. "Se la funzione non è continua in un solo punto, il teorema di Weierstrass fallisce: vedi controesempio $f(x) = ...$").
7. **Applicazioni e Corollari Chiave:** Collegamenti ad altri teoremi del vault tramite [[wikilink]].

---

### B. Scaletta per `Type: Concetto`
1. **Frontmatter YAML** (`Disciplina: Matematica`, `Type:\n  - Concetto`).
2. **Intuizione e Motivazione:** Perché i matematici hanno introdotto questo oggetto? Quale problema teorico o geometrico risolve?
3. **Definizione Formale e Callout Decodifica Logico-Formale.**
4. **Tassonomia e Casi Particolari:** Classificazione interna completa ed esaustiva dell'ente.
5. **Proprietà Costitutive e Dimostrazioni Interne:** Tutte le proprietà che definiscono l'identità dell'oggetto o delle sue operazioni basilari (dimostrate passo-passo a sforzo zero se derivano unicamente dalla definizione).
6. **Interpretazione Geometrica o Grafica:** Inclusione di grafici o rappresentazioni cartesiane (`![[grafico.png]]`).
7. **Esempi Notevoli e Controesempi:** Casi tipici in cui la definizione si applica e casi limite/trabocchetti per comprenderla a fondo.
8. **Ponte Logico verso i Teoremi Derivati (Note Separate):** I teoremi autonomi con nome proprio che poggiano su questo concetto (es. Cantor, Heine-Borel) NON vengono dimostrati né enunciati qui: compaiono solo con un breve ponte logico e [[wikilink]]. Vengono riepilogati a fondo pagina in `### Teoremi e Concetti Derivati (Note Separate)`.

---

### C. Scaletta per `Type: Metodo`
1. **Frontmatter YAML** (`Disciplina: Matematica`, `Type:\n  - Metodo`).
2. **Callout `> **Quando si usa?**`:** Elenco dei trigger operativi (es. "Quando hai una matrice a coefficienti reali e vuoi calcolare il rango, invertire la matrice o risolvere un sistema lineare parametrico").
3. **Scaletta Operativa Passo-Passo (Algoritmo):**
   - **Passo 1:** *Cosa fare* + *Perché funziona matematicamente*.
   - **Passo 2:** *Cosa fare* + *Attenzione a questo trabocchetto*.
   - **Passo N:** *Verifica del risultato*.
4. **Esercizio Modello Svolto Passo-Passo:**
   - Testo dell'esercizio.
   - Svolgimento integrale senza saltare nessun passaggio di calcolo.
   - Verifica finale e commento sull'eventuale errore comune da evitare.

---

### D. Scaletta per `Type: MOC`
1. **Frontmatter YAML:** `Disciplina: Matematica`, `Type:\n  - MOC`, tag e alias della roadmap.
2. **ZERO Formule LaTeX, ZERO Dimostrazioni, ZERO Tabelle:**
   - Divieto assoluto di formule con dollari (`$...$`, `$$...$$`). I concetti sono espressi esclusivamente con la loro denominazione accademica discorsiva in prosa italiana.
   - Zero dimostrazioni, zero callout tecnici (`[!definition]`, `[!theorem]`), zero box flashcard/quiz, zero emoji, zero riferimenti meta a lezioni o capitoli.
   - Nessuna tabella riassuntiva: la trattazione vive unicamente nella narrazione discorsiva e nei diagrammi Mermaid.
3. **Testo 100% Discorsivo Causale:**
   - Prosa fluida e rigorosa che esplora il filo logico causale: perché nasce ogni concetto, quali limiti del concetto precedente impongono di progredire verso il successivo e come da ciascuno scaturiscano rigorosamente i relativi teoremi e metodi operativi.
4. **Nomenclatura Esplicita e Divieto Assoluto di Alias nei Wikilink:**
   - Tutte le note teorema devono iniziare con `Teorema ...` (o `Lemma ...`, `Corollario ...`, `Principio ...`, `Criterio ...`): es. `[[Teorema di Weierstrass]]`.
   - Tutte le note metodo devono iniziare con `Metodo ...` (o `Studio ...`, `Calcolo ...`, `Risoluzione ...`, `Algoritmo ...`): es. `[[Metodo di Eliminazione di Gauss]]`.
   - Divieto totale del pipe `|`: ogni wikilink deve comparire unicamente nella sua forma pura canonica `[[Nome Esatto della Nota]]`, senza apici né backtick.
5. **Doppia Architettura Mermaid Verticale (`flowchart TD`):**
   - Un diagramma generale `flowchart TD` in cima al MOC con la sequenza macro-modulare del corso.
   - Un diagramma dedicato `flowchart TD` in fondo a **ciascun singolo capitolo/modulo** che collega i nodi di Concetto ai rispettivi `[[Teorema ...]]` e `[[Metodo ...]]` trattati nel capitolo (nodi centrati verticali, etichette tra doppi apici `"..."`, zero formule matematiche LaTeX, zero emoji).
6. **Sezione Finale di Raccordo:**
   - `## Note e Paragrafi Collegati` con risalita a `[[Matematica MOC]]` e alle macro-aree correlate.
