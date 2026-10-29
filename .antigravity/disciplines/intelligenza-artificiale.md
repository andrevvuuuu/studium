# Profilo Disciplinare: Intelligenza Artificiale

> [!IMPORTANT]
> **Polo:** `#università` | **Tag:** `#intelligenza_artificiale`  
> Questo profilo definisce gli standard per Machine Learning, Deep Learning, Reti Neurali, NLP, Computer Vision e Teoria dell'Ottimizzazione.

---

## Filosofia e Regole Fondamentali

1. **La Triade dell'Intelligenza Artificiale:**
   Ogni nota di Machine Learning o Deep Learning deve fondarsi su tre pilastri inscindibili:
   - **L'Intuizione Geometrica:** Cosa accade nello spazio dei dati $\mathbb{R}^d$ o nello spazio dei parametri/pesi $\mathbb{R}^p$? (Iperpiani di separazione, manifold non lineari, valli della loss function).
   - **La Formalizzazione Matematica Rigorosa:** Derivata parziale, gradiente $\nabla$, hessiana, matrice jacobiana, divergenza KL, aspettazione $\mathbb{E}$.
   - **La Realizzazione Algoritmica Vettorizzata:** Codice efficiente in Python/PyTorch che sfrutta il calcolo tensoriale e il parallelismo GPU/SIMD senza cicli `for` lenti.
2. **Zero "Scatole Nere":**
   - Non trattare mai una rete neurale o un ottimizzatore come una scatola nera magica. Mostra sempre la formula esatta dell'update dei pesi e la catena di derivate (Chain Rule).
3. **Analisi dei Casi di Fallimento:**
   - Spiega sempre dove l'algoritmo si rompe: esplosione o scomparsa del gradiente (*Vanishing/Exploding Gradients*), punti di sella ad alta dimensione (*Saddle Points*), cattivo condizionamento della matrice hessiana, *overfitting* e collasso del manifold.

---

## Il Callout Obbligatorio: "Decodifica Logico-Formale e Geometrica"

```markdown
> [!note] Decodifica Logico-Formale: Discesa del Gradiente (Gradient Descent)
> **1. Regola di Aggiornamento dei Parametri:**
> $$ \theta_{t+1} = \theta_t - \eta \nabla_{\theta} \mathcal{L}(\theta_t) = \theta_t - \eta \cdot \frac{1}{N} \sum_{i=1}^N \nabla_{\theta} \ell(f(x_i; \theta_t), y_i) $$
>
> **2. Come si legge (Spiegazione Notazionale):**
> "Il vettore dei parametri $\theta$ al passo temporale successivo $t+1$ è ottenuto sottraendo al vettore dei parametri corrente $\theta_t$ il prodotto tra il tasso di apprendimento $\eta > 0$ (learning rate, scalare positivo) e il vettore gradiente della funzione di costo empirica $\nabla_\theta \mathcal{L}(\theta_t)$, calcolato mediando i gradienti delle perdite individuali $\ell$ su tutti gli $N$ campioni del dataset."
>
> **3. Significato Geometrico nello Spazio dei Pesi:**
> Il gradiente $\nabla_\theta \mathcal{L}$ indica per definizione la direzione di massima crescita istantanea della superficie della loss. Muoversi nella direzione opposta ($-\nabla$) equivale a scendere lungo la linea di massima pendenza della vallata d'errore. Il learning rate $\eta$ controlla la lunghezza del passo: un passo troppo lungo rischia di superare il minimo e divergere; un passo troppo corto richiede tempi computazionali proibitivi o rimane intrappolato in plateaux piatti.
```

---

## Scaletta Strutturale delle Note di Intelligenza Artificiale

### 1. Frontmatter YAML
```yaml
---
Disciplina: Intelligenza Artificiale
Type:
  - Metodo # oppure Concetto se si tratta di un'architettura/funzione di perdita
tags:
  - intelligenza_artificiale
  - università
aliases:
  - Gradient Descent
  - Discesa del Gradiente
  - Discesa di Gradiente Stocastica (SGD)
---
```

### 2. Intuizione Geometrica e Fondamenti Teorici
- Definizione della superficie d'errore (Loss Landscape).
- Rappresentazione visiva di curve di livello, paraboliidi o conformazioni non convesse.
- Inclusione di grafici o diagrammi (`![[loss_landscape.png]]`).

### 3. Callout Decodifica Logico-Formale e Geometrica

### 4. Derivazione Matematica della Regola di Apprendimento
- Applicazione del differenziale o dello sviluppo in serie di Taylor al primo/secondo ordine per mostrare perché la direzione $-\nabla$ minimizza la funzione.
- Calcolo esplicito del gradiente per un modello lineare o con funzione di attivazione non lineare ($\sigma, \text{ReLU}$).

### 5. Algoritmo Passo-Passo e Codice Python Vettorizzato (PyTorch/NumPy)
- Niente cicli riga per riga: usa moltiplicazioni matriciali `@` e broadcasting NumPy/PyTorch.
```python
import torch

def train_step(X: torch.Tensor, y: torch.Tensor, weights: torch.Tensor, lr: float) -> tuple[torch.Tensor, float]:
    """
    Esegue un singolo passo di discesa del gradiente vettorizzato per regressione lineare.
    X: matrice di design (N x D)
    y: target reali (N x 1)
    weights: parametri del modello (D x 1)
    lr: learning rate scalare
    """
    N = X.shape[0]
    
    # 1. Forward Pass (Predizione)
    predictions = X @ weights
    
    # 2. Calcolo della Loss (Mean Squared Error)
    loss = (1.0 / (2.0 * N)) * torch.sum((predictions - y) ** 2).item()
    
    # 3. Calcolo analitico del gradiente (Vettorizzato: (X^T @ (y_pred - y)) / N)
    grad = (1.0 / N) * (X.T @ (predictions - y))
    
    # 4. Aggiornamento parametri (Gradient Descent Update)
    weights = weights - lr * grad
    
    return weights, loss
```

### 6. Callout Collassabile: Dry Run Numerico
Esempio numerico su matrici di dimensione ridotta ($N=2, D=2$):
```markdown
> [!tip]- Dry Run Numerico su Dati Giocattolo
> Dati iniziali: $X = \begin{pmatrix} 1 & 2 \\ 1 & 3 \end{pmatrix}$, $y = \begin{pmatrix} 5 \\ 7 \end{pmatrix}$, $w_0 = \begin{pmatrix} 0 \\ 0 \end{pmatrix}$, $\eta = 0.1$.
> - Predizioni: $\hat{y} = X w_0 = \begin{pmatrix} 0 \\ 0 \end{pmatrix}$.
> - Errore residuo: $\hat{y} - y = \begin{pmatrix} -5 \\ -7 \end{pmatrix}$.
> - Gradiente calcolato: $\nabla = \frac{1}{2} X^T (\hat{y} - y) = \frac{1}{2} \begin{pmatrix} -12 \\ -31 \end{pmatrix} = \begin{pmatrix} -6 \\ -15.5 \end{pmatrix}$.
> - Nuovi pesi: $w_1 = w_0 - 0.1 \begin{pmatrix} -6 \\ -15.5 \end{pmatrix} = \begin{pmatrix} 0.6 \\ 1.55 \end{pmatrix}$.
> La loss decresce immediatamente già dal primo passo.
```

### 7. Matrice Comparativa delle Varianti
Tabella riassuntiva dei principali algoritmi derivati:

| Algoritmo | Formula di Aggiornamento | Vantaggi Principali | Svantaggi / Iperparametri Critici |
| :--- | :--- | :--- | :--- |
| **Batch GD** | $\theta_{t+1} = \theta_t - \eta \nabla \mathcal{L}_{\text{full}}$ | Gradiente esatto, traiettoria stabile | Lento su dataset enormi, memoria saturata |
| **SGD** | $\theta_{t+1} = \theta_t - \eta \nabla \ell(x_i)$ | Aggiornamenti istantanei, sfugge a minimi locali | Alta varianza, traiettoria a zig-zag |
| **Momentum** | $v_{t+1} = \beta v_t + \eta \nabla$; $\theta \leftarrow \theta - v_{t+1}$ | Smorza le oscillazioni, accelera lungo i canyon | Introduce l'iperparametro di inerzia $\beta$ |
| **Adam** | Combina primo e secondo momento con correzione del bias | Adattivo per feature sparse, standard de facto | Può non convergere in setting particolari |

### 8. Analisi dei Fallimenti e Linee Guida Operative
- Come scegliere il learning rate (*Learning Rate Schedules*, *Warmup*, *Cosine Annealing*).
- Segnali diagnostici di *Underfitting* vs *Overfitting* sulle curve di apprendimento.
