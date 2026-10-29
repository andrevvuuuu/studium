# Profilo Disciplinare: Droghe (Farmacologia e Sostanze Psicoattive)

> [!IMPORTANT]
> **Polo:** `#personale` | **Tag:** `#droghe`  
> Questo profilo stabilisce lo standard enciclopedico, clinico e tossicologico per tutte le sostanze psicoattive (stimolanti, empatogeni, psichedelici, dissociativi, sedativi, oppioidi e nootropi).  
> **Integrazione Tool Obbligatoria:**  
> 1. `science_media_fetch.py` (download della struttura molecolare 2D da PubChem e immagini cliniche/fotografie reali di midriasi, PET cerebrali o schemi sinaptici da Wikimedia Commons).  
> 2. `pubmed_search.py` (interrogazione sistematica di studi clinici e tossicologici sull'uomo con link PMID diretti).

---

## Filosofia e Regole Fondamentali

1. **Approccio Medico-Farmacologico Rigoroso:**
   - La materia è trattata con la neutralità e la profondità di un manuale universitario di Farmacologia e Tossicologia Medica (stile *Goodman & Gilman*). Rifiuto totale del sensazionalismo o di giudizi morali.
2. **Nessuna Omissione dei Meccanismi Letali:**
   - Spiega con precisione chirurgica *come* e *perché* una sostanza o una sua combinazione può uccidere: non formule generiche come "è pericoloso", ma spiegazioni biochimiche esatte (es. blocco della degradazione enzimatica per inibizione delle monoamino ossidasi $\to$ accumulo intrasinaptico massivo $\to$ sindrome serotoninergica maligna $\to$ collasso multiorgano per iperpiressia $> 41.5^\circ\text{C}$).
3. **Ispezione Visiva Obbligatoria dei Media:**
   - Le fotografie degli effetti fisici (es. midriasi vs miosi) e le scansioni PET cerebrali devono essere verificate per autenticità visiva prima di essere incluse.

---

## Il Callout Obbligatorio: "Decodifica Neurofarmacologica"

```markdown
> [!note] Decodifica Neurofarmacologica: Meccanismo d'Azione Sinaptico dell'MDMA
> **1. Bersagli Molecolari Principali:**
> - Inibizione e inversione di trasporto: $\text{SERT} > \text{NET} > \text{DAT}$
> - Inibitore del trasportatore vescicolare: $\text{VMAT2}$
> - Agonista parziale: Recettori serotoninergici $5\text{-HT}_{2\text{A}}, 5\text{-HT}_{2\text{B}}, 5\text{-HT}_{1\text{A}}$ e adrenergici $\alpha_2$
>
> **2. Come si legge il Meccanismo Molecolare:**
> "La molecola penetra nel terminale assonico presinaptico legandosi ai trasportatori di ricaptazione delle monoammine (con massima affinità per il SERT). Una volta nel citoplasma neuronale, inibisce il trasportatore vescicolare VMAT2, provocando il collasso del gradiente protonico intravescicolare e il riversamento massivo di serotonina nel citosol. L'accumulo citosolico inverte la direzione di funzionamento del SERT per fosforilazione mediata da protein chinasi C ($\text{PKC}$), espellendo serotonina nello spazio sinaptico indipendentemente dai potenziali d'azione (rilascio non-esocitotico)."
>
> **3. Cascata Neuroendocrina e Conseguenze Fisiologiche:**
> La saturazione dei recettori post-sinaptici $5\text{-HT}_{1\text{A}}$ nell'ipotalamo innesca un rilascio acuto massivo di **ossitocina** (responsabile dell'empatia profonda, prosocialità e senso di connessione emotiva) e di **vasopressina / ormone antidiuretico (ADH)**. L'eccesso di vasopressina inibisce l'escrezione renale di acqua libera: se l'utilizzatore assume ingenti quantità d'acqua per dissetarsi senza reintegrare sodio, si sviluppa una grave iponatriemia ipotonica acuta con edema cerebrale fatale.
```

---

## Struttura Obbligatoria in 7 Punti di una Nota di Sostanza

Ogni nota di sostanza deve articolarsi rigorosamente attraverso questi 7 capitoli:

### 1. Identikit Chimico e Relazione Struttura-Attività (SAR)
- Nome IUPAC, formula bruta, peso molecolare, classificazione chimica (es. fenetilammina sostituita, triptamina, arilcicloesilammina).
- Inclusione dell'immagine strutturale 2D da PubChem: `![[struttura_chimica_<sostanza>.png]]`.
- Relazione Struttura-Attività: quali gruppi funzionali (es. anello metilendiossido, catena $\alpha$-metilica) conferiscono la lipofilia e l'affinità recettoriale specifica.
- Collegamento a [[Chimica]].

### 2. Farmacocinetica (ADME) e Curva Temporale
- **Assorbimento e Biodisponibilità:** Vie di somministrazione (orale, sublinguale, intranasale), cinetica gastrica e percentuale assorbita.
- **Distribuzione:** Lipofilia, volume di distribuzione ($V_d$), legame alle proteine plasmatiche e cinetica di attraversamento della Barriera Emato-Encefalica (BBB).
- **Metabolismo Epatico (CYP450):** Isoenzimi coinvolti (es. $\text{CYP2D6}, \text{CYP3A4}, \text{CYP1A2}$), metaboliti attivi o tossici (es. MDA, norcocaina, 11-idrossi-THC).
- **Eliminazione ed Emivita ($t_{1/2}$):** Tempi di dimezzamento plasmatico ed escrezione renale/biliare.
- **Tabella Obbligatoria della Curva Temporale:**

| Fase | Durata Media (Via Orale) | Descrizione Fisiologica e Segnali di Inizio |
| :--- | :---: | :--- |
| **Onset (Inizio)** | $20\text{--}45\text{ min}$ | Primi brividi, variazione della temperatura periferica, lieve ansia di salita |
| **Come-up (Salita)** | $30\text{--}60\text{ min}$ | Rapida elevazione del tono adrenergico, accelerazione del battito, midriasi incipiente |
| **Peak (Picco / Plateau)** | $2\text{--}3.5\text{ ore}$ | Massima saturazione recettoriale, effetti empatogeni/psichedelici pieni |
| **Offset (Discesa)** | $1\text{--}2\text{ ore}$ | Graduale attenuazione della stimolazione, inizio del rilassamento muscolare |
| **Comedown (Postumi)** | $12\text{--}48\text{ ore}$ | Deplezione delle scorte vescicolari, stanchezza fisica, ipoforia transitoria |

### 3. Farmacodinamica e Neurofarmacologia
- Callout obbligatorio **Decodifica Neurofarmacologica: Meccanismo d'Azione Sinaptico**.
- Coinvolgimento recettoriale sistemico: recettori serotoninergici ($5\text{-HT}$), dopaminergici ($D_1\text{--}D_5$), adrenergici ($\alpha_1, \alpha_2, \beta_1$), glutammatergici (NMDA, AMPA) o GABAergici ($\text{GABA}_A, \text{GABA}_B$).
- Inclusione di schema sinaptico o PET scan (`![[scienza_synapse.jpg]]`) e collegamento a [[Neuroscienze]].

### 4. Quadro Completo degli Effetti Clinici (con Immagini Verificate)
- **Effetti Psicologici ed Emotivi:** Euforia, empatia, disinibizione verbale, alterazioni dell'elaborazione della paura nell'amigdala.
- **Effetti Percettivi e Visivi:** Modificazioni della corteccia visiva primaria V1 (es. *visual drifting*, traccianti, intensificazione cromatica, geometria frattale).
- **Segni Fisici e Clinici Obiettivi (con Foto Reale):**  
  Inclusione dell'immagine da Wikimedia Commons (es. [scienza_1513_mydriasis.jpg](allegati/scienza_1513_mydriasis.jpg)) con commento:
  - *Midriasi:* Densitá adrenergica sui muscoli dilatatori radiali dell'iride.
  - *Bruxismo e Trisma:* Contrazione spastica dei muscoli masseteri per iperattività dopaminergica/serotoninergica sui motoneuroni del trigemino.
  - *Ipertermia e Diaforesi:* Vasocostrizione periferica cutanea unita a termogenesi muscolare aumentata.
- **Meccanismo Neurochimico del Comedown e Neurotossicità:**
  - Deplezione acuta delle riserve vescicolari intracellulari di monoammine.
  - *Down-regulation* recettoriale post-sinaptica e internalizzazione dei recettori.
  - Formazione di metaboliti chinonici reattivi e specie reattive dell'ossigeno (ROS) che danneggiano i terminali assonici.

### 5. Tossicologia Acuta e Rischi di Mortalità
- **Come e perché la sostanza può uccidere in monoterapia:**
  - *Iperpiressia Maligna:* Collasso del centro termoregolatore ipotalamico con temperature $> 41^\circ\text{C}$, rabdomiolisi con mioglobinuria e insufficienza renale acuta.
  - *Tossicità Cardiovascolare:* Crisi ipertensive, tachiaritmie ventricolari e dissezione aortica o ischemia miocardica.
  - *Iponatriemia Acuta da Eccesso di Liquidi:* Blocco della diuresi indotto da vasopressina (SIADH-like).

### 6. Matrice Obbligatoria "Con cosa NON va mischiata"
Callout di pericolo massimo con tabella esaustiva delle sinergie farmacologiche:

```markdown
> [!danger] Sinergie Letali e Interazioni Farmacologiche Pericolose
> 
> | Sostanza / Classe Farmacologica | Livello di Rischio | Spiegazione Meccanicistica del Pericolo |
> | :--- | :---: | :--- |
> | **Inibitori delle MAO (IMAO: Tranilcipromina, Moclobemide, Ayahuasca)** |  **LETALE** | Il blocco catabolico delle MAO unito al rilascio massivo causa una tempesta serotoninergica fulminante con decesso rapido per arresto cardiaco o ipertermia estrema |
> | **Antidepressivi SSRI / SNRI (Sertralina, Fluoxetina, Venlafaxina)** |  **ALTISSIMO RISCHIO** | Competizione per il sito di legame SERT che annulla gli effetti desiderati e aumenta drammaticamente la neurotossicità e il rischio di sindrome serotoninergica atipica |
> | **Stimolanti Classici (Cocaina, Anfetamina, Caffeina ad alte dosi)** |  **ALTISSIMO RISCHIO** | Sovrapposizione adrenergica che produce vasocostrizione severa, aritmie cardiache ventricolari e ipertermia incontrollabile |
> | **Depressori del SNC e Alcol** |  **MOLTO PERICOLOSO** | L'alcol aumenta la biodisponibilità plasmatica della sostanza accelerando la disidratazione e mascherando la percezione di intossicazione acuta |
```

### 7. Evidenze PubMed e Note Collegate
- Tabella degli studi clinici e metanalisi recuperati tramite `pubmed_search.py` con link diretti a PubMed.
- Mappa bidirezionale dei collegamenti con le note connesse del vault ([[Neuroscienze]], [[Chimica]], [[Psicologia]]).
