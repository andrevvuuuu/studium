<!--
================================================================================
SNIPPET BLUEPRINT COMPRESSO — DISCIPLINA: MATEMATICA
Estratto dalla Nota Esempio reale: `Matematica/Numeri Interi Relativi.md`
================================================================================
-->

### BLOCCO 1 — REGOLA DI ACCOPPIAMENTO CON IL PROFILO DELLA MATERIA
Quando scrivi una nota o un MOC per **Matematica** (UNIVERSITÀ):
1. **Regole Logiche e Verifiche:** Segui rigorosamente il rispettivo file `.antigravity/disciplines/matematica.md` (obblighi formali, controlli incrociati e verifiche evidenziali).
2. **Distinzione Vincolante Nota vs MOC:**
   - **Se scrivi una NOTA (`Concetto`, `Teorema`, `Metodo`):** Utilizza i 4 blocchi modello qui sotto come *calibro stilistico* per frontmatter, introduzione intuitiva, callout di decodifica logico-formale, dimostrazioni passo-passo a 3 atti e tabelle.
   - **Se scrivi un MOC (`Type: MOC`):** Applica tassativamente la **Legge 4 delle Core Guidelines**: ZERO formule LaTeX (`$...$`), ZERO dimostrazioni, ZERO tabelle, ZERO callout tecnici o quiz; testo 100% discorsivo causale; nomenclatura esplicita obbligatoria (`[[Teorema ...]]`, `[[Metodo ...]]`) con divieto assoluto di alias (`|`); doppia architettura Mermaid verticale `flowchart TD` (panoramico in cima + dedicato a fine di ciascun capitolo).
3. **Sforzo Cognitivo Zero:** Ogni concetto, termine specialistico o passaggio deve possedere la sua immediata traduzione discorsiva e un'anatomia visiva chiara.

---

### BLOCCO 2 — ESEMPIO REALE DI FRONTMATTER YAML + INTRODUZIONE MODELLO
```yaml
Disciplina: Matematica
Type:
  - Concetto
tags:
  - matematica
  - università
aliases:
  - Numeri Interi Relativi
  - Insieme Z
  - Z
```

L'**Insieme dei Numeri Interi Relativi**, universalmente designato con la lettera maiuscola a doppia barra $\mathbb{Z}$ (dal tedesco *Zahlen*, "numeri"), costituisce l'estensione algebrica canonica dell'insieme dei [[Numeri Naturali]] ($\mathbb{N}$). Tale struttura nasce dall'esigenza di superare l'asimmetria funzionale di $\mathbb{N}$ rispetto all'operazione di addizione, rendendo sempre risolubile l'operazione inversa della sottrazione attraverso l'introduzione formale degli **inversi additivi** (i numeri negativi) e dello zero come perno di simmetria.

---

### BLOCCO 3 — ESEMPIO REALE DI CALLOUT DI DECODIFICA
> [!note] Decodifica Logico-Formale: Mancanza di Chiusura della Sottrazione in $\mathbb{N}$
> - **Notazione Formale**: $$\exists a, b \in \mathbb{N} : \nexists x \in \mathbb{N} \text{ tale che } a + x = b$$
> - **Come si legge**: "Esistono $a$ e $b$ appartenenti a $\mathbb{N}$ tali per cui non esiste alcun $x$ appartenente a $\mathbb{N}$ tale che $a$ più $x$ sia uguale a $b$"
> - **Cosa significa (Spiegazione Rigorosa ma Intuitiva)**: Nei numeri naturali l'equazione $a + x = b$ ammette soluzione $x \in \mathbb{N}$ se e solo se $a \le b$ (nel qual caso $x = b - a$). Se $a > b$, il moto a ritroso supera lo zero verso sinistra; poiché a sinistra dello zero l'insieme $\mathbb{N}$ non possiede alcun elemento, l'operazione di sottrazione non è una funzione ovunque definita in $\mathbb{N} \times \mathbb{N}$.

---

### BLOCCO 4 — ESEMPIO REALE DI DIMOSTRAZIONE / CATENA CAUSALE A SFORZO ZERO
### 3. Dimostrazione "A Sforzo Cognitivo Zero"

**Strategia della Dimostrazione:**
Procederemo tramite una [[Elementi di Logica Matematica#Dimostrazione per Assurdo|dimostrazione per assurdo]]. Ipotizzeremo che il limite non sia unico (cioè $l_1 \neq l_2$) e mostreremo che questo ci porta a una palese impossibilità algebrica e geometrica (costringeremo la distanza tra $l_1$ e $l_2$ ad essere strettamente minore di se stessa).

**Sviluppo Passo-Passo Argomentato:**

**Passo 1: L'ipotesi per assurdo e la scelta del "raggio" $\varepsilon$**
Supponiamo per assurdo che $l_1 \neq l_2$. 
Se sono due numeri diversi, la loro distanza (valore assoluto della differenza) è strettamente positiva:
$$|l_1 - l_2| > 0$$
Poiché nella definizione di limite possiamo scegliere un $\varepsilon > 0$ piccolo a piacere, scegliamo astutamente un $\varepsilon$ pari esattamente a *metà* della distanza tra i due presunti limiti:
$$\varepsilon = \frac{|l_1 - l_2|}{2}$$
*(Geometricamente, stiamo creando due "bolle" di raggio $\varepsilon$ attorno a $l_1$ e $l_2$ che si sfiorano ma non si sovrappongono).*

**Passo 2: Applichiamo la definizione di limite per $l_1$**
Poiché $\lim_{x \to x_0} f(x) = l_1$, sappiamo che in corrispondenza del nostro $\varepsilon$ scelto, esiste un raggio $\delta_1 > 0$ tale che per tutti gli $x \in A$ che soddisfano $0 < |x - x_0| < \delta_1$, vale:
$$|f(x) - l_1| < \varepsilon$$

**Passo 3: Applichiamo la definizione di limite per $l_2$**
Poiché anche $\lim_{x \to x_0} f(x) = l_2$, in corrispondenza dello *stesso* $\varepsilon$, esiste un raggio $\delta_2 > 0$ tale che per tutti gli $x \in A$ che soddisfano $0 < |x - x_0| < \delta_2$, vale:
$$|f(x) - l_2| < \varepsilon$$

**Passo 4: Troviamo una zona dove valgono entrambe**

*[I passaggi analitici continuano esplicitando ogni deduzione logica e causale senza alcun salto]*

---

### BLOCCO 5 — ESEMPIO DI TABELLA RIEPILOGATIVA
| Simbolo / Notazione | Come si legge | Significato Concettuale |
| :--- | :--- | :--- |
| $\mathbb{Z}$ | "insieme dei numeri interi relativi" | Insieme $\{\dots, -2, -1, 0, 1, 2, \dots\}$ |
| $\mathbb{Z}^*$ oppure $\mathbb{Z} \setminus \{0\}$ | "Z star" / "Z senza zero" | Insieme dei numeri interi non nulli |
| $\mathbb{Z}^+$ | "Z più" / "interi positivi" | Sottoinsieme $\{1, 2, 3, \dots\}$ coincidente con $\mathbb{N} \setminus \{0\}$ |
| $\mathbb{Z}^-$ | "Z meno" / "interi negativi" | Sottoinsieme degli interi strettamente minori di zero |
| $[(a, b)]_\sim$ | "classe di equivalenza della coppia $(a, b)$" | Definizione formale di intero come differenza formale $a - b$ |
| $-a$ | "opposto di $a$" / "meno $a$" | Inverso additivo unico di $a$ rispetto all'addizione ($a + (-a) = 0$) |
| $\le$ | "minore o uguale a" | Relazione d'ordine totale basata sulla chiusura additiva in $\mathbb{N}$ |
| $\veebar$ | "aut" / "o esclusivamente" | Connettivo logico di disgiunzione esclusiva (tricotomia) |
| $\|a\|$ | "valore assoluto di $a$" / "modulo di $a$" | Distanza di $a$ dallo zero sulla retta numerica |
| $\mathcal{U}(\mathbb{Z})$ | "gruppo delle unità di $\mathbb{Z}$" | Insieme degli elementi invertibili rispetto al prodotto, pari a $\{-1, 1\}$ |
| $\aleph_0$ | "aleph zero" | Cardinalità del discreto numerabile ($\#\mathbb{Z} = \aleph_0$) |

---

### BLOCCO 6 — ESEMPIO DI SEZIONE FINALE NOTE E PARAGRAFI COLLEGATI
## Note e Paragrafi Collegati

### Teoremi e Concetti Derivati (Note Separate)
- [[Teorema di Caratterizzazione degli Intervalli]]: formulazione e dimostrazione formale della connessione topologica/ordinale avanzata.
- [[Teorema di Cantor degli Intervalli Inscatolati]]: principio di compattezza e intersezione non vuota che poggia sugli intervalli chiusi e limitati.
- [[Teorema di Heine-Borel]]: teorema sui ricoprimenti aperti di intervalli compatti $[a, b]$.
- [[Metodo del Segno per Disequazioni con Intervalli]]: procedura algoritmica d'esame e batteria di esercizi svolti passo-passo.

### Riferimenti Puntuali a Paragrafi
- [[Numeri Reali#Assioma di Completezza]]: assioma d'ordine e completezza impiegato per garantire l'esistenza del sup.
- [[Elementi di Logica Matematica#Dimostrazione per Assurdo]]: tecnica dimostrativa impiegata nella disuguaglianza triangolare.

### Note Generali e MOC
- [[Analisi 1 MOC]]: quadro organico e di raccordo didattico.
- [[Numeri Reali]]: ambiente metrico continuo di riferimento.
