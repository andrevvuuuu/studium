<!--
================================================================================
SNIPPET BLUEPRINT COMPRESSO — DISCIPLINA: FISICA
Estratto dalla Nota Esempio reale: `Fisica/Teorema dell'Energia Cinetica e Lavoro.md`
================================================================================
-->

### BLOCCO 1 — REGOLA DI ACCOPPIAMENTO CON IL PROFILO DELLA MATERIA
Quando scrivi una nota o un MOC per **Fisica** (UNIVERSITÀ):
1. **Regole Logiche e Verifiche:** Segui rigorosamente il rispettivo file `.antigravity/disciplines/fisica.md` (obblighi formali, controlli incrociati e verifiche evidenziali).
2. **Modello Visivo e Tonalità:** Utilizza i 4 blocchi modello qui sotto come *calibro stilistico* per frontmatter, introduzione intuitiva, callout di decodifica, catene causali/dimostrative e tabelle.
3. **Sforzo Cognitivo Zero:** Ogni formula, termine specialistico o datazione deve possedere la sua immediata traduzione discorsiva e un'anatomia visiva chiara.

---

### BLOCCO 2 — ESEMPIO REALE DI FRONTMATTER YAML + INTRODUZIONE MODELLO
```yaml
Disciplina: Fisica
Type:
  - Teorema
tags:
  - fisica
  - università
aliases:
  - Teorema dell'Energia Cinetica
  - Teorema delle Forze Vive
  - Lavoro di una Forza
```

La trattazione di questo argomento in **Fisica** segue rigorosamente i principi del Vault Antigravity: massima precisione formale nei costrutti specialistici, ma decodifica immediata e accessibilità concettuale a sforzo cognitivo zero.

---

### BLOCCO 3 — ESEMPIO REALE DI CALLOUT DI DECODIFICA
> [!note] Decodifica Fisico-Matematica: Lavoro di una Forza lungo una Traiettoria
> - **Formulazione Matematica**: $$L_{A \to B} = \int_\gamma \vec{F} \cdot d\vec{r} = \int_A^B \vert\vec{F}\vert \, \vert d\vec{r}\vert \cos\theta$$
> - **Come si legge e Anatomia delle Grandezze**: Si legge come l'integrale curvilineo lungo il percorso $\gamma$ del prodotto scalare tra il vettore forza locale $\vec{F}$ e il vettore spostamento infinitesimo tangenziale $d\vec{r}$. L'angolo $\theta$ è l'angolo compreso tra la direzione della forza e la direzione della velocità istantanea. Il lavoro è un puro scalare. L'unità di misura nel SI è il **Joule (J)**, definito come il lavoro compiuto da una forza di $1\text{ N}$ per produrre uno spostamento di $1\text{ m}$ nella sua stessa direzione: $\text{J} = \text{N}\cdot\text{m} = \text{kg}\cdot\text{m}^2\cdot\text{s}^{-2}$.
> - **Significato Fisico (Motore, Resistente, Nullo)**:
>   - Se $0 \le \theta < \pi/2 \implies \cos\theta > 0$: La componente della forza favorisce il moto. $\delta L > 0$ e il lavoro si dice **motore**.
>   - Se $\pi/2 < \theta \le \pi \implies \cos\theta < 0$: La componente della forza si oppone al moto. $\delta L < 0$ e il lavoro si dice **resistente** (o dissipativo).
>   - Se $\theta = \pi/2 \implies \cos\theta = 0$: La forza è strettamente ortogonale alla traiettoria. $\delta L = 0$ (lavoro **nullo**). Esempi classici sono la *forza centripeta* nel moto circolare o la *forza magnetica di Lorentz*, che agiscono unicamente curvando la traiettoria senza alterare il modulo della velocità.

---

### BLOCCO 4 — ESEMPIO REALE DI DIMOSTRAZIONE / CATENA CAUSALE A SFORZO ZERO
## 5. Derivazione Analitica Passo-Passo "A Sforzo Cognitivo Zero"

> [!tip]- Derivazione Completa del Teorema dell'Energia Cinetica
> **1. Strategia della derivazione**
> L'obiettivo è calcolare l'integrale del lavoro sostituendo al suo interno la Seconda Legge di Newton ($\vec{F} = m\frac{d\vec{v}}{dt}$). Dopodiché, trasformeremo l'integrale di linea (nello spazio) in un integrale rispetto alla sola variabile velocità scalare, sfruttando le regole di differenziazione del prodotto scalare per il quadrato della norma di un vettore.
> 
> **2. Passaggi matematici e fisici espliciti**
> Partiamo dalla definizione di lavoro totale tra $A$ e $B$:
> $$ L_{A \to B}^{\text{tot}} = \int_A^B \vec{F}_{\text{tot}} \cdot d\vec{r} $$
> Sostituiamo l'equazione del moto $\vec{F}_{\text{tot}} = m\frac{d\vec{v}}{dt}$:
> $$ L_{A \to B}^{\text{tot}} = \int_A^B \left( m \frac{d\vec{v}}{dt} \right) \cdot d\vec{r} $$
> Poiché $d\vec{r} = \vec{v} dt$, possiamo riorganizzare i differenziali scambiando di posto $dt$ e $d\vec{v}$ (lecito poiché sono espressioni differenziali ordinarie):
> $$ L_{A \to B}^{\text{tot}} = \int_A^B m \left( \frac{d\vec{v}}{dt} \cdot \vec{v} dt \right) = \int_{v_A}^{v_B} m (\vec{v} \cdot d\vec{v}) $$
> 
> Ora dobbiamo risolvere il termine $\vec{v} \cdot d\vec{v}$. Ricordiamo che il modulo quadro della velocità è $v^2 = \vec{v} \cdot \vec{v}$. Differenziamo questa quantità usando la regola del prodotto di Leibniz per il prodotto scalare:
> $$ d(v^2) = d(\vec{v} \cdot \vec{v}) = d\vec{v} \cdot \vec{v} + \vec{v} \cdot d\vec{v} = 2 (\vec{v} \cdot d\vec{v}) $$
> Dividendo per 2, otteniamo l'identità cruciale:
> $$ \vec{v} \cdot d\vec{v} = \frac{1}{2} d(v^2) = v \, dv $$
> *(Dimostrazione alternativa per componenti cartesiane a scanso di equivoci: $\vec{v} \cdot d\vec{v} = v_x dv_x + v_y dv_y + v_z dv_z = \frac{1}{2}d(v_x^2) + \frac{1}{2}d(v_y^2) + \frac{1}{2}d(v_z^2) = \frac{1}{2}d(v_x^2+v_y^2+v_z^2) = \frac{1}{2}d(v^2)$).*
> 
> Sostituiamo questa identità nell'integrale. L'estremo di integrazione passa dagli stati $A, B$ ai valori del modulo della velocità $v_A, v_B$:
> $$ L_{A \to B}^{\text{tot}} = m \int_{v_A}^{v_B} v \, dv $$
> Estraiamo la massa $m$ (costante) e calcoliamo l'integrale primitivo di $v$:
> $$ L_{A \to B}^{\text{tot}} = m \left[ \frac{1}{2} v^2 \right]_{v_A}^{v_B} $$

*[I passaggi analitici continuano esplicitando ogni deduzione logica e causale senza alcun salto]*

---

### BLOCCO 5 — ESEMPIO DI TABELLA RIEPILOGATIVA
| Simbolo | Descrizione Fisica e Matematica | Unità (SI) |
| :--- | :--- | :--- |
| $\vec{F}$ | Vettore forza locale (risultante) | Newton ($\text{N}$) |
| $d\vec{r}$ | Spostamento vettoriale infinitesimo lungo $\gamma$ | Metri ($\text{m}$) |
| $\delta L$ | Lavoro elementare infinitesimo (differenziale inesatto) | Joule ($\text{J}$) |
| $L_{A \to B}$ | Lavoro finito calcolato tramite integrale curvilineo | Joule ($\text{J}$) |
| $P(t)$ | Potenza istantanea erogata o assorbita | Watt ($\text{W}$) |
| $K$ (o $T$) | Energia cinetica traslazionale del punto materiale | Joule ($\text{J}$) |
