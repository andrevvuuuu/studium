# Profilo Disciplinare: Informatica

> [!IMPORTANT]
> **Polo:** `#università` | **Tag:** `#informatica`  
> Questo profilo definisce le linee guida per Algoritmi, Strutture Dati, Programmazione (C, Python, Rust), Architettura dei Calcolatori e Sistemi Operativi.

---

## Filosofia e Regole Fondamentali

1. **Dal Problema Concreto all'Astrazione:**
   - Non partire mai direttamente dal listato di codice o dalla pura complessità asintotica.
   - Parti sempre dal **problema computazionale concreto**: cosa vogliamo calcolare, perché una soluzione naive (a forza bruta) è inaccettabile e qual è l'intuizione chiave per ottimizzare.
2. **Cosa succede sotto il cofano (In Memoria):**
   - Un informatico deve sempre sapere cosa accade a livello fisico o a basso livello: allocazione nello Stack vs Heap, puntatori, riferimenti, cache lines e access pattern.
3. **Nessun Codice "Magico" o Non Commentato:**
   - Ogni riga di codice deve essere comprensibile. I costrutti algoritmici complessi (scambi di puntatori, indici mediani, allocazioni) devono avere commenti inline esplicativi.
4. **Verifica Empirica tramite Dry Run:**
   - Ogni algoritmo deve essere verificato tracciando a mano un piccolo input di esempio passo dopo passo.

---

## Il Callout Obbligatorio: "Decodifica Tecnica e Meccanismo in Memoria"

Ogni volta che si introduce una struttura dati, un algoritmo o una firma di funzione, inserisci questo callout:

```markdown
> [!note] Decodifica Tecnica e Meccanismo in Memoria: <Nome Algoritmo o Struttura>
> **1. Firma Formale o Prototipo:**
> ```c
> int binary_search(const int arr[], int size, int target);
> ```
>
> **2. Come si legge (Spiegazione Tecnica della Firma):**
> "Funzione `binary_search` che riceve come parametri un array costante di interi `arr` (passato per puntatore al primo elemento per evitare costose copie), la sua dimensione intera `size`, e l'elemento cercato `target`. Restituisce un intero rappresentante l'indice dell'elemento se trovato, oppure `-1` in caso di esito negativo."
>
> **3. Cosa succede sotto il cofano in Memoria (Stack / Heap / Cache):**
> L'array risiede in memoria contigua (nello Stack del chiamante o nell'Heap se allocato con `malloc`). La funzione alloca nel proprio Stack Frame solo 3 variabili locali di tipo intero (`low`, `high`, `mid`), occupando spazio ausiliario costante $\mathcal{O}(1)$. A livello di memoria cache L1/L2, l'accesso dicotomico a salti dimezzati non sfrutta al massimo la località spaziale dei salti sequenziali, ma riduce il numero totale di letture a sole $\log_2(n)$ iterazioni.
```

---

## Scaletta Strutturale delle Note di Informatica

### 1. Frontmatter YAML
```yaml
---
Disciplina: Informatica
Type:
  - Metodo # oppure Concetto se si tratta di una struttura dati
tags:
  - informatica
  - università
aliases:
  - Binary Search
  - Ricerca Dicotomica
---
```

### 2. Inquadramento del Problema e Intuizione Visiva
- **Input:** Specifiche rigorose dell'input (es. array ordinato di $n$ elementi).
- **Output:** Risultato atteso (es. indice dell'elemento cercato o segnale di assenza).
- **L'idea chiave:** Spiegazione in 2-3 frasi dell'intuizione (es. dividere a metà l'intervallo di ricerca ad ogni passo, scartando la metà inutile).

### 3. Callout Decodifica Tecnica e Meccanismo in Memoria

### 4. Implementazione Pulita e Commentata Riga per Riga
- Fornisci l'implementazione in C (o Python quando l'argomento è ad alto livello / data science).
- Evita scorciatoie o librerie predefinite (`bsearch` di stdlib): implementa la logica esplicita.
- Esempio di codice commentato:
  ```c
  int binary_search(const int arr[], int size, int target) {
      int low = 0;
      int high = size - 1;

      while (low <= high) {
          // Calcolo sicuro del punto medio per evitare overflow aritmetico di (low + high)
          int mid = low + (high - low) / 2;

          if (arr[mid] == target) {
              return mid; // Bersaglio trovato all'indice mid
          }
          if (arr[mid] < target) {
              low = mid + 1; // Il bersaglio si trova necessariamente nella metà destra
          } else {
              high = mid - 1; // Il bersaglio si trova necessariamente nella metà sinistra
          }
      }
      return -1; // Elemento non presente nell'array
  }
  ```

### 5. Callout Collassabile: Dry Run (Esecuzione Tracciata Passo-Passo)
Traccia obbligatoria su un array di test con tabella delle iterazioni:

```markdown
> [!tip]- Dry Run: Tracciamento su Input Esempio
> **Input di Test:** `arr = [2, 5, 8, 12, 16, 23, 38, 56, 72, 91]`, `size = 10`, `target = 23`.
>
> | Iterazione | `low` | `high` | `mid` | `arr[mid]` | Confronto (`arr[mid]` vs `target`) | Azione successiva |
> | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
> | **Inizio** | 0 | 9 | - | - | - | Inizializzazione puntatori |
> | **Passo 1** | 0 | 9 | 4 | 16 | $16 < 23$ $\to$ Bersaglio a destra | `low = mid + 1` = 5 |
> | **Passo 2** | 5 | 9 | 7 | 56 | $56 > 23$ $\to$ Bersaglio a sinistra | `high = mid - 1` = 6 |
> | **Passo 3** | 5 | 6 | 5 | 23 | $23 == 23$ $\to$ Trovato! | `return mid` (5) |
>
> **Esito:** L'elemento `23` è stato individuato all'indice `5` in soli 3 confronti.
```

### 6. Analisi di Complessità Computazionale e Casi Limite
- **Complessità Temporale:**
  - *Best Case:* $\mathcal{O}(1)$ (quando l'elemento cercato è esattamente al centro al primo passo).
  - *Worst Case:* $\mathcal{O}(\log_2 n)$ (quando l'elemento si trova alle estremità o è assente).
  - *Dimostrazione Formale:* Spiegare la relazione di ricorrenza $T(n) = T(n/2) + \mathcal{O}(1)$ risolta tramite Master Theorem.
- **Complessità Spaziale:**
  - Versione iterativa: $\mathcal{O}(1)$ (spazio ausiliario costante).
  - Versione ricorsiva: $\mathcal{O}(\log n)$ (dovuta ai frame di chiamata nello Stack).
- **Corner Cases e Trabocchetti da Evitare:**
  - Array vuoto (`size == 0`).
  - Overflow di `low + high` in linguaggi con interi a dimensione fissa (spiegare la correzione `low + (high - low) / 2`).
  - Gestione di elementi duplicati (se occorre la prima o l'ultima occorrenza).
