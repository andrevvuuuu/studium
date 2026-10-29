# Profilo Disciplinare: Fisica

> [!IMPORTANT]
> **Polo:** `#università` | **Tag:** `#fisica`  
> Questo profilo stabilisce gli standard analitici, concettuali e grafici per Meccanica Classica, Termodinamica, Elettromagnetismo, Onde e Meccanica Quantistica.

---

## Filosofia e Regole Fondamentali

1. **La Matematica come Linguaggio della Natura:**
   - La fisica non è mera astrazione matematica: ogni equazione modella una porzione di realtà sperimentale.
   - Ogni grandezza fisica introdotta deve specificare **sempre**:
     - *Natura vettoriale o scalare:* (es. la forza $\vec{F}$ e la velocità $\vec{v}$ sono vettori, il lavoro $L$ e la massa $m$ sono scalari).
     - *Unità di misura nel Sistema Internazionale (SI):* espresse con precisione ($[\text{J}] = [\text{N} \cdot \text{m}] = [\text{kg} \cdot \text{m}^2 / \text{s}^2]$).
     - *Ipotesi e Limiti di Validità:* (es. punto materiale, moto a velocità non relativistiche $v \ll c$, campo conservativo).
2. **Accoppiamento Fisico di Ogni Passaggio Analitico:**
   - Nelle derivazioni, differenziazioni o integrazioni, non limitarti al calcolo simbolico. Spiega **il significato fisico** di ogni operatore:
     - *Cosa rappresenta $\mathrm{d}\vec{r}$?* Lo spostamento infinitesimo lungo la traiettoria.
     - *Perché il prodotto scalare $\vec{F} \cdot \mathrm{d}\vec{r}$?* Perché solo la componente tangenziale della forza compie lavoro.
     - *Perché la derivata temporale $\frac{\mathrm{d}\vec{p}}{\mathrm{d}t}$?* È il tasso istantaneo di variazione della quantità di moto indotto dall'interazione esterna.
3. **Diagrammi di Corpo Libero e Rappresentazione Spaziale:**
   - Ove opportuno, inserisci la scomposizione vettoriale con immagini (`![[schema_forze.png]]`) o schemi dettagliati delle direzioni cartesiane.

---

## Il Callout Obbligatorio: "Decodifica Fisico-Matematica"

Ogni legge fisica o teorema deve aprirsi con questo callout rigoroso:

```markdown
> [!note] Decodifica Fisico-Matematica: Teorema dell'Energia Cinetica (delle Forze Vive)
> **1. Formulazione Matematica:**
> $$ L_{\text{tot}} = \int_{A}^{B} \vec{F}_{\text{tot}} \cdot \mathrm{d}\vec{r} = \Delta E_k = \frac{1}{2}m v_B^2 - \frac{1}{2}m v_A^2 $$
>
> **2. Come si legge, Natura delle Grandezze e Unità SI:**
> "Il lavoro totale $L_{\text{tot}}$ (grandezza scalare, misurata in Joule $[J]$) compiuto dalla risultante di tutte le forze $\vec{F}_{\text{tot}}$ (vettore, Newton $[N]$) agenti su un corpo di massa $m$ (scalare positivo, $[kg]$) lungo una traiettoria dal punto iniziale $A$ al punto finale $B$, è uguale alla variazione di energia cinetica $\Delta E_k$ (scalare, $[J]$), definita come semiprodotto della massa per il quadrato della velocità scalare finale meno il semiprodotto della massa per il quadrato della velocità scalare iniziale."
>
> **3. Significato Fisico nella Realtà e Ipotesi di Validità:**
> Il lavoro non è altro che la misura dell'energia scambiata meccanicamente: se la forza ha una componente concorde con il moto ($\vec{F} \cdot \mathrm{d}\vec{r} > 0$), il corpo accelera immagazzinando energia cinetica; se la forza si oppone (es. attrito, $\vec{F} \cdot \mathrm{d}\vec{r} < 0$), l'energia cinetica viene sottratta e dissipata. Il teorema vale in qualsiasi sistema di riferimento inerziale e si applica sia a forze conservative che non conservative.
```

---

## Derivazioni Analitico-Fisiche "Passo-Passo"

Le derivazioni devono essere racchiuse in un callout collassabile `> [!tip]- Derivazione Analitica: <Nome>`, con la motivazione fisica affiancata a ogni riga algebrica:

```markdown
> [!tip]- Derivazione Analitica: Dal Secondo Principio della Dinamica al Teorema delle Forze Vive
> **1.  Obiettivo Fisico della Derivazione:**
> Dimostrare come integrando la seconda legge di Newton $\vec{F} = m \vec{a}$ lungo lo spazio percorso si ottenga la conservazione e la trasformazione dell'energia cinetica.
>
> **2.  Catena di Calcolo con Motivazione Fisica a Ogni Passo:**
> - **Passo 1 (Definizione di Lavoro Infinitesimo):**  
>   Consideriamo una particella di massa $m$ costante soggetta a una forza totale $\vec{F}$. Il lavoro infinitesimo $\mathrm{d}L$ per uno spostamento $\mathrm{d}\vec{r}$ è:
>   $$ \mathrm{d}L = \vec{F} \cdot \mathrm{d}\vec{r} $$
>
> - **Passo 2 (Introduzione della Seconda Legge di Newton):**  
>   Sostituiamo $\vec{F} = m \vec{a} = m \frac{\mathrm{d}\vec{v}}{\mathrm{d}t}$:
>   $$ \mathrm{d}L = \left(m \frac{\mathrm{d}\vec{v}}{\mathrm{d}t}\right) \cdot \mathrm{d}\vec{r} $$
>
> - **Passo 3 (Riorganizzazione cinematica del differenziale):**  
>   Poiché la velocità vettoriale è definita come $\vec{v} = \frac{\mathrm{d}\vec{r}}{\mathrm{d}t}$, possiamo riscrivere lo spostamento infinitesimo come $\mathrm{d}\vec{r} = \vec{v} \, \mathrm{d}t$. Sostituendo:
>   $$ \mathrm{d}L = m \frac{\mathrm{d}\vec{v}}{\mathrm{d}t} \cdot (\vec{v} \, \mathrm{d}t) = m \, \vec{v} \cdot \mathrm{d}\vec{v} $$
>   *Significato fisico:* Il tempo $\mathrm{d}t$ scompare dalla relazione: il lavoro dipende esclusivamente dalla velocità e dallo spazio, non dalla rapidità con cui il percorso viene coperto.
>
> - **Passo 4 (Differenziale del prodotto scalare della velocità):**  
>   Ricordiamo che il modulo quadro della velocità è $v^2 = \vec{v} \cdot \vec{v}$. Differenziando entrambi i membri otteniamo:
>   $$ \mathrm{d}(v^2) = \mathrm{d}(\vec{v} \cdot \vec{v}) = \mathrm{d}\vec{v} \cdot \vec{v} + \vec{v} \cdot \mathrm{d}\vec{v} = 2 (\vec{v} \cdot \mathrm{d}\vec{v}) \implies \vec{v} \cdot \mathrm{d}\vec{v} = \frac{1}{2} \mathrm{d}(v^2) $$
>
> - **Passo 5 (Integrazione definita tra stato iniziale e finale):**  
>   Sostituiamo quanto appena ricavato nel lavoro infinitesimo ed integriamo tra la configurazione $A$ ($v = v_A$) e $B$ ($v = v_B$):
>   $$ L_{\text{tot}} = \int_A^B \mathrm{d}L = \int_{v_A}^{v_B} m \left( \frac{1}{2} \mathrm{d}(v^2) \right) = \frac{1}{2} m \int_{v_A^2}^{v_B^2} \mathrm{d}(v^2) = \frac{1}{2} m (v_B^2 - v_A^2) $$
>
> - **Passo 6 (Definizione di Energia Cinetica):**  
>   Definendo l'energia cinetica come $E_k = \frac{1}{2} m v^2$, otteniamo:
>   $$ L_{\text{tot}} = E_k(B) - E_k(A) = \Delta E_k $$
>
> **3. Conclusione e Q.E.D.:**  
> Il lavoro di tutte le forze applicate equivale esattamente alla variazione di energia cinetica del sistema. $\blacksquare$
```

---

## Scaletta Tipica di una Nota di Fisica

1. **Frontmatter YAML** (`Disciplina: Fisica`, `Type: [Teorema | Concetto | Metodo]`).
2. **Inquadramento Fenomenologico:** Quale osservazione sperimentale o problema fisico ha condotto a questa teoria?
3. **Callout Decodifica Fisico-Matematica.**
4. **Callout Derivazione Analitica Passo-Passo.**
5. **Casi Limite ed Interpretazione Energetica/Fisica:**
   - *Cosa accade se la forza è ortogonale allo spostamento?* (es. forza centripeta, lavoro nullo).
   - *Cosa accade per forze conservative vs dissipative?*
6. **Esercizio Fisico Tipico Svolto:**
   - Schema delle forze e scelta del sistema di riferimento cartesiano.
   - Equazioni proiettate sugli assi.
   - Risoluzione analitica simbolica prima di sostituire i valori numerici con relative unità di misura.
