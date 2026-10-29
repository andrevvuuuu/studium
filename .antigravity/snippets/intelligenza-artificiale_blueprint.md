<!--
================================================================================
SNIPPET BLUEPRINT COMPRESSO — DISCIPLINA: INTELLIGENZA ARTIFICIALE
Estratto dalla Nota Esempio reale: `Intelligenza Artificiale/Discesa del Gradiente e Varianti Stocastiche.md`
================================================================================
-->

### BLOCCO 1 — REGOLA DI ACCOPPIAMENTO CON IL PROFILO DELLA MATERIA
Quando scrivi una nota o un MOC per **Intelligenza Artificiale** (UNIVERSITÀ):
1. **Regole Logiche e Verifiche:** Segui rigorosamente il rispettivo file `.antigravity/disciplines/intelligenza-artificiale.md` (obblighi formali, controlli incrociati e verifiche evidenziali).
2. **Modello Visivo e Tonalità:** Utilizza i 4 blocchi modello qui sotto come *calibro stilistico* per frontmatter, introduzione intuitiva, callout di decodifica, catene causali/dimostrative e tabelle.
3. **Sforzo Cognitivo Zero:** Ogni formula, termine specialistico o datazione deve possedere la sua immediata traduzione discorsiva e un'anatomia visiva chiara.

---

### BLOCCO 2 — ESEMPIO REALE DI FRONTMATTER YAML + INTRODUZIONE MODELLO
```yaml
Disciplina: Intelligenza Artificiale
Type:
  - Metodo
tags:
  - intelligenza-artificiale
  - ottimizzazione
  - matematica
  - università
aliases:
  - Gradient Descent
  - Discesa del Gradiente
  - SGD
```

La **Discesa del Gradiente** (Gradient Descent) è il motore di ottimizzazione numerica alla base della quasi totalità degli algoritmi moderni di Machine Learning e Deep Learning. Costituisce un metodo iterativo del primo ordine per trovare il minimo locale (o globale, in caso di convessità) di una funzione differenziabile.

---

### BLOCCO 3 — ESEMPIO REALE DI CALLOUT DI DECODIFICA
> [!note] Decodifica Logico-Formale: Vettore Gradiente e Regola di Aggiornamento
> - **Notazione Formale**: $\boldsymbol{\theta}_{t+1} = \boldsymbol{\theta}_t - \eta \nabla \mathcal{L}(\boldsymbol{\theta}_t)$
> - **Come si legge**: Teta al passo $t+1$ è uguale a Teta al passo $t$, meno il prodotto scalare tra eta (learning rate) e il gradiente di $\mathcal{L}$ valutato nel punto Teta con indice $t$.
> - **Cosa significa**: Definiamo il prossimo vettore di parametri spostandoci dall'attuale vettore lungo la direzione opposta a quella che massimizza localmente la funzione. Il parametro $\eta$ scala l'ampiezza di questo "salto".

> [!tip]- Dimostrazione a Sforzo Zero: Perché l'antigradiente $-\nabla \mathcal{L}(\boldsymbol{\theta})$ è la direzione di massima discesa locale
> Vogliamo trovare una direzione di spostamento (un versore unitario $\mathbf{u}$ con $\Vert\mathbf{u}\Vert_2 = 1$) che minimizzi il valore della Loss. Effettuiamo un piccolo passo di lunghezza $\eta > 0$.
> 
> Usando lo sviluppo in **Serie di Taylor al primo ordine** intorno al punto $\boldsymbol{\theta}$:
> $$ \mathcal{L}(\boldsymbol{\theta} + \eta \mathbf{u}) \approx \mathcal{L}(\boldsymbol{\theta}) + \eta \nabla \mathcal{L}(\boldsymbol{\theta})^\top \mathbf{u} $$
> 
> Il nostro obiettivo è rendere $\mathcal{L}(\boldsymbol{\theta} + \eta \mathbf{u})$ il più piccolo possibile rispetto a $\mathcal{L}(\boldsymbol{\theta})$. Poiché $\eta > 0$, ciò implica minimizzare il termine di perturbazione direzionale: $\nabla \mathcal{L}(\boldsymbol{\theta})^\top \mathbf{u}$.
> 
> Ricorriamo all'identità algebrica (derivante dalla disuguaglianza di Cauchy-Schwarz) per il prodotto scalare tra due vettori:
> $$ \nabla \mathcal{L}(\boldsymbol{\theta})^\top \mathbf{u} = \Vert\nabla \mathcal{L}(\boldsymbol{\theta})\Vert_2 \Vert\mathbf{u}\Vert_2 \cos(\alpha) $$
> 
> dove $\alpha$ è l'angolo compreso tra il vettore gradiente e il nostro versore di spostamento $\mathbf{u}$.
> Poiché abbiamo imposto $\Vert\mathbf{u}\Vert_2 = 1$ e la norma del gradiente $\Vert\nabla \mathcal{L}(\boldsymbol{\theta})\Vert_2$ è fissa nel punto valutato, l'unica variabile che possiamo controllare è l'angolo $\alpha$.
> - *[... ulteriori parametri formattati con lo stesso schema analitico]*

---

### BLOCCO 4 — ESEMPIO REALE DI DIMOSTRAZIONE / CATENA CAUSALE A SFORZO ZERO
## 3. Algoritmo Operativo Passo-Passo e Codice Python/NumPy

L'implementazione algoritmica richiede una precisa sequenza di stati:
1. **Inizializzazione**: Scegliere un vettore di pesi di partenza $\boldsymbol{\theta}_0$ (spesso campionato casualmente da distribuzioni normali) e un learning rate $\eta$.
2. **Ciclo Iterativo (fino a convergenza)**:
   - **Forward Pass**: Valutare $\mathcal{L}(\boldsymbol{\theta}_t)$.
   - **Backward Pass**: Calcolare analiticamente o tramite Autodiff il vettore gradiente $\mathbf{g}_t = \nabla \mathcal{L}(\boldsymbol{\theta}_t)$.
   - **Step di Aggiornamento**: $\boldsymbol{\theta}_{t+1} \leftarrow \boldsymbol{\theta}_t - \eta \mathbf{g}_t$.
3. **Criterio di Arresto**: Il ciclo si interrompe quando la pendenza è quasi nulla (norma del gradiente $\Vert\mathbf{g}_t\Vert_2 < \varepsilon$, con $\varepsilon$ molto piccolo, es. $10^{-5}$), o dopo un limite prefissato di iterazioni (epochs).

```python
import numpy as np

def gradient_descent(gradient_func, theta_init, learning_rate=0.01, max_iter=1000, tol=1e-5):
    """
    Implementazione vettorizzata della Discesa del Gradiente.
    
    :param gradient_func: Funzione callable che restituisce il gradiente (vettore numpy).
    :param theta_init: Vettore dei pesi iniziale (numpy array).
    :param learning_rate: Dimensione del passo (eta).
    :param max_iter: Numero massimo di iterazioni consentite.
    :param tol: Tolleranza epsilon per il criterio di arresto.
    """
    theta = np.copy(theta_init)

*[I passaggi analitici continuano esplicitando ogni deduzione logica e causale senza alcun salto]*

---

### BLOCCO 5 — ESEMPIO DI TABELLA RIEPILOGATIVA
| Variante | Formula del Gradiente | Costo per Step | Varianza della Stima | Pro e Contro |
| :--- | :--- | :--- | :--- | :--- |
| **Batch GD** (Vanilla) | $\frac{1}{N} \sum_{i=1}^N \nabla \ell_i(\boldsymbol{\theta})$ | Elevatissimo ($\mathcal{O}(N)$) | Zero (Gradiente Deterministico) | **Pro:** Discesa molto fluida, convergenza stabile.<br>**Contro:** Impossibile da calcolare con dataset enormi; blocco in minimi locali (no rumore). |
| **Stochastic GD (SGD)** | $\nabla \ell_i(\boldsymbol{\theta})$ *(per un singolo elemento $i$ a caso)* | Minimo ($\mathcal{O}(1)$) | Estrema | **Pro:** Aggiornamenti iper-veloci; sfugge bene dai punti di sella grazie al rumore stocastico.<br>**Contro:** Non vettorializzabile su hardware moderno; convergenza "nervosa" attorno al minimo locale. |
| **Mini-Batch SGD** | $\frac{1}{\|B\|} \sum_{i \in B} \nabla \ell_i(\boldsymbol{\theta})$ *(con $\|B\|$ tra $16$ e $512$)* | Moderato ($\mathcal{O}(\|B\|)$) | Bassa/Moderata (bilanciabile) | **Pro:** Sfrutta a pieno l'architettura SIMD delle moderne GPU/TPU (vettorizzazione); ottimo bilanciamento stabilità/velocità.<br>**Contro:** Richiede la selezione empirica di un iperparametro addizionale (dimensione del batch $B$). |
