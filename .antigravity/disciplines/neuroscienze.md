# Profilo Disciplinare: Neuroscienze

> [!IMPORTANT]
> **Polo:** `#università` | **Tag:** `#neuroscienze`  
> Questo profilo stabilisce le regole per Neurobiologia Cellulare, Elettrofisiologia, Neurofisiologia dei Sistemi, Neurotrasmissione e Plasticità Cerebrale.  
> **Integrazione Tool Automatica:** `pubmed_search.py` (evidenze empiriche recenti) e `science_media_fetch.py` (immagini sinaptiche e PET/fMRI).

---

## Filosofia e Regole Fondamentali

1. **Il Cervello come Circuito Bioelettrochimico:**
   - I fenomeni nervosi derivano dall'interazione di gradienti chimici (concentrazioni ioniche intra ed extracellulari), gradienti elettrici (voltaggio transmembrana) e cinetiche conformazionali proteiche (canali ionici, trasportatori, recettori metabotropi e ionotropi).
2. **La Catena Causale Meccanicistica Rigorosa:**
   - È vietato descrivere un fenomeno con formule vaghe (es. "il neurone si attiva e rilascia il trasmettitore").
   - Bisogna descrivere la sequenza temporale atomo per atomo, millisecondo per millisecondo, senza interruzioni di continuità causale.
3. **Formalismo Biofisico Esplicito:**
   - Ogni volta che si parla di potenziale di membrana, cita l'equazione di **Nernst** per il singolo ione e l'equazione di **Goldman-Hodgkin-Katz (GHK)** per la membrana a permeabilità multipla.
4. **Ponti con le Altre Discipline:**
   - Crea collegamenti biunivoci con `Biologia` (canali e sintesi proteica), `Chimica` (legami idrogeno e polarità dei neurotrasmettitori) e `Droghe` (modulazione farmacologica dei recettori).

---

## Il Callout Obbligatorio: "Decodifica Biofisica e Fisiologica"

Ogni fenomeno elettrofisiologico o recettoriale deve aprirsi con questo callout:

```markdown
> [!note] Decodifica Biofisica e Fisiologica: Potenziale d'Azione Neuronale
> **1. Equazione o Relazione Biofisica Fondamentale:**
> $$ V_m = \frac{RT}{F} \ln \left( \frac{P_{\text{K}}[\text{K}^+]_{\text{out}} + P_{\text{Na}}[\text{Na}^+]_{\text{out}} + P_{\text{Cl}}[\text{Cl}^-]_{\text{in}}}{P_{\text{K}}[\text{K}^+]_{\text{in}} + P_{\text{Na}}[\text{Na}^+]_{\text{in}} + P_{\text{Cl}}[\text{Cl}^-]_{\text{out}}} \right) $$
>
> **2. Come si legge e Parametri Fisiologici:**
> "Il potenziale transmembrana $V_m$ (espresso in millivolt $[mV]$) è determinato dal rapporto tra la costante dei gas $R$, la temperatura assoluta $T$ e la costante di Faraday $F$, moltiplicato per il logaritmo naturale del rapporto pesato delle permeabilità relative ($P_{\text{K}}, P_{\text{Na}}, P_{\text{Cl}}$) e delle concentrazioni ioniche tra i compartimenti extracellulare ($\text{out}$) e intracellulare ($\text{in}$)."
>
> **3. Meccanismo Fisico-Cellulare Intuitivo:**
> A riposo, la membrana è quasi 40 volte più permeabile al potassio ($P_{\text{K}} \gg P_{\text{Na}}$), bloccando il potenziale vicino al valore di equilibrio di Nernst del $\text{K}^+$ (circa $-70\text{ mV}$). Durante il potenziale d'azione, l'apertura cooperativa dei canali per il sodio voltaggio-dipendenti ($\text{Na}_v1.1\text{--}1.6$) capovolge istantaneamente il rapporto di permeabilità ($P_{\text{Na}} \gg P_{\text{K}}$), facendo schizzare il potenziale verso il valore di Nernst del sodio ($+60\text{ mV}$), prima che l'inattivazione del cancello $h$ e l'apertura ritardata dei canali $\text{K}_v$ lo riportino a riposo.
```

---

## La Catena Causale Meccanicistica Passo-Passo

I processi neuronali devono essere codificati secondo questa struttura standard a gradini numerati:

```markdown
### Catena Causale Meccanicistica: Dalla Depolarizzazione al Rilascio Vescicolare

1. **Arrivo del fronte di depolarizzazione:**  
   L'onda del potenziale d'azione viaggia lungo l'assone mielinizzato tramite conduzione saltatoria tra i nodi di Ranvier fino a raggiungere il bottone presinaptico terminale.
2. **Apertura dei Canali $\text{Ca}_v$ di tipo P/Q ed N:**  
   La variazione di potenziale da $-70\text{ mV}$ a $+30\text{ mV}$ deforma il sensore di voltaggio S4 dei canali del calcio voltaggio-dipendenti, aprendo il poro.
3. **Influsso rapido di Calcio ($\text{Ca}^{2+}$):**  
   Grazie al gradiente elettrochimico enorme ($[\text{Ca}^{2+}]_{\text{out}} \approx 2\text{ mM}$ contro $[\text{Ca}^{2+}]_{\text{in}} \approx 100\text{ nM}$), gli ioni calcio irrompono nel microdominio attivo presinaptico raggiungendo concentrazioni locali $> 10\text{ }\mu\text{M}$.
4. **Legame con la Sinaptotagmina-1:**  
   Quattro o cinque ioni $\text{Ca}^{2+}$ si legano cooperativamente ai domini C2A e C2B della proteina sensore transmembrana vescicolare *Sinaptotagmina-1*.
5. **Collasso del complesso SNARE e Fusione di Membrana:**  
   La sinaptotagmina attivata induce una trazione meccanica sul complesso ternario *core SNARE* (formato da *Sinaptobrevina/VAMP* sulla vescicola, *Sintassina-1* e *SNAP-25* sulla membrana plasmatica presinaptica). Le membrane lipidiche vengono accostate a una distanza $< 1\text{ nm}$, provocando la formazione del poro di fusione.
6. **Esocitosi quantica del Neurotrasmettitore:**  
   Il neurotrasmettitore racchiuso nella vescicola si riversa per diffusione libera nello spazio intersinaptico (ampio circa $20\text{ nm}$), impiegando meno di $100\text{ }\mu\text{s}$ per raggiungere i recettori post-sinaptici.
```

---

## Scaletta Strutturale delle Note di Neuroscienze

1. **Frontmatter YAML** (`Disciplina: Neuroscienze`, `Type: [Concetto | Teorema | Metodo]`).
2. **Inquadramento Funzionale nel Sistema Nervoso:** Quale circuito, via sensitiva/motoria o funzione cognitiva/omeostatica dipende da questo processo?
3. **Callout Decodifica Biofisica e Fisiologica.**
4. **Catena Causale Meccanicistica Passo-Passo.**
5. **Farmacologia e Modulazione Recettoriale:**
   - Quali farmaci, tossine (es. tetrodotossina TTX, tossina botulinica) o sostanze psicotrope bloccano o amplificano questo passaggio? (Link incrociato a [[Droghe]]).
6. **Evidenze Empiriche e Imaging Cerebrale (Auto-Tool):**
   - Immagini e schemi da `science_media_fetch.py` (`![[scienza_synapse.jpg]]` o fMRI/PET).
   - Tabella riassuntiva di studi seminali ottenuti tramite `pubmed_search.py`.
7. **Patologie e Implicazioni Cliniche:** Cosa accade quando il meccanismo fallisce (es. epilessia, sclerosi multipla, miastenia grave, sindrome di Lambert-Eaton).
