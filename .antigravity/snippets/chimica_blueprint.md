<!--
================================================================================
SNIPPET BLUEPRINT COMPRESSO — DISCIPLINA: CHIMICA
Estratto dalla Nota Esempio reale: `Chimica/Legame Chimico, Elettronegatività, Ibridazione degli Orbitali e Polarità Molecolare.md`
================================================================================
-->

### BLOCCO 1 — REGOLA DI ACCOPPIAMENTO CON IL PROFILO DELLA MATERIA
Quando scrivi una nota o un MOC per **Chimica** (PERSONALE):
1. **Regole Logiche e Verifiche:** Segui rigorosamente il rispettivo file `.antigravity/disciplines/chimica.md` (obblighi formali, controlli incrociati e verifiche evidenziali).
2. **Modello Visivo e Tonalità:** Utilizza i 4 blocchi modello qui sotto come *calibro stilistico* per frontmatter, introduzione intuitiva, callout di decodifica, catene causali/dimostrative e tabelle.
3. **Sforzo Cognitivo Zero:** Ogni formula, termine specialistico o datazione deve possedere la sua immediata traduzione discorsiva e un'anatomia visiva chiara.

---

### BLOCCO 2 — ESEMPIO REALE DI FRONTMATTER YAML + INTRODUZIONE MODELLO
```yaml
Disciplina: Chimica
Type:
  - Concetto
tags:
  - chimica
  - personale
aliases:
  - Legame Chimico
  - Ibridazione sp3 sp2 sp
  - Polarità e Forze Intermolecolari
```

La trattazione di questo argomento in **Chimica** segue rigorosamente i principi del Vault Antigravity: massima precisione formale nei costrutti specialistici, ma decodifica immediata e accessibilità concettuale a sforzo cognitivo zero.

---

### BLOCCO 3 — ESEMPIO REALE DI CALLOUT DI DECODIFICA
> [!note] Decodifica Chimico-Fisica: Elettronegatività ($\Delta\chi$) e Momento di Dipolo Elettrico ($\vec{\mu}$)
> - **Formulazione Formale**: 
>   $$\vec{\mu} := q \cdot \vec{d} \qquad (\text{Unità: Debye, } 1\text{ D} \approx 3,336 \times 10^{-30}\text{ C}\cdot\text{m})$$
> - **Come si legge e Anatomia delle Grandezze**: 
>   - $q$: Entità della carica parziale localizzata sui baricentri ($\delta^+$ e $\delta^-$), espressa in Coulomb ($\text{C}$).
>   - $\vec{d}$: Vettore spostamento internucleare orientato convenzionalmente in chimica dal polo positivo ($\delta^+$) al polo negativo ($\delta^-$), espresso in metri ($\text{m}$).
>   - $\Delta\chi$: Differenza assoluta di elettronegatività tra i due partner di legame: $\Delta\chi = \vert{}\chi_A - \chi_B\vert{}$.
> - **Cosa significa a livello elettronico (Sforzo Zero)**: 
>   Quando due atomi con diversa elettronegatività condividono elettroni, l'atomo più "avido" deforma la nuvola elettronica tirandola verso di sé. Questo crea un'asimmetria di carica permanente: una frazione di carica negativa reale ($\delta^-$) su di sé e una complementare frazione positiva ($\delta^+$) sul partner. Tuttavia, **avere legami singoli polari non implica che l'intera molecola sia polare**: se la geometria molecolare distribuisce i singoli vettori dipolo in modo perfettamente simmetrico, la loro risultante vettoriale si annulla:
>   $$\vec{\mu}_{\text{tot}} = \sum_{i=1}^{n} \vec{\mu}_i = \vec{0}$$

---

### BLOCCO 4 — ESEMPIO REALE DI DIMOSTRAZIONE / CATENA CAUSALE A SFORZO ZERO
### L'Anatomia della Curva:
* **Per $r > r_0$ (Fase attrattiva)**: l'attrazione elettrostatica nucleo-elettrone prevale sulle repulsioni. L'energia potenziale del sistema diminuisce ($V(r) < 0$): avvicinandosi, il sistema libera energia sotto forma di calore verso l'ambiente ($\Delta H < 0$).
* **Al punto $r = r_0$ (Distanza di legame)**: si raggiunge la buca di potenziale (minimo assoluto dell'energia potenziale). In questo punto esatto la risultante delle forze è nulla:
  $$F = -\frac{\partial V(r)}{\partial r} = 0$$
  La distanza $r_0$ corrisponde alla **lunghezza di legame sperimentale** (es. $74\text{ pm}$ per $\text{H}_2$), e la profondità della buca corrisponde all'**energia di dissociazione di legame** ($D_e \approx 436\text{ kJ/mol}$). La molecola è stabile.
* **Per $r < r_0$ (Fase repulsiva catastrofica)**: se forziamo i nuclei ad avvicinarsi oltre $r_0$, le repulsioni internucleari e la compressione degli orbitali interni generano una barriera repulsiva asintotica verticale ($V(r) \to +\infty$).

> **Regola aurea**: Un legame chimico non è una sbarretta rigida materiale, ma una **posizione di equilibrio dinamico** in cui le forze attrattive e repulsive si annullano perfettamente al minimo energetico consentito dalla meccanica quantistica.

---

---

### BLOCCO 5 — ESEMPIO DI TABELLA RIEPILOGATIVA
| Ibridazione | Orbitali Coinvolti | Geometria Molecolare (VSEPR) | Angolo di Legame | Tipologia Legami | Carattere $s$ / $p$ | Esempio Rappresentativo |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **$sp^3$** | $1s + 3p$ | Tetraedrica | $109,5^\circ$ | Soltanto legami $\sigma$ (rotazione libera) | $25\% \; s$ <br> $75\% \; p$ | Metano ($\text{CH}_4$), Etano ($\text{C}_2\text{H}_6$), Ione Ammonio ($\text{NH}_4^+$) |
| **$sp^2$** | $1s + 2p$ (+ $1p$ puro libero) | Trigonale Planare | $120^\circ$ | 1 legame $\sigma$ + 1 legame $\pi$ (rotazione bloccata) | $33,3\% \; s$ <br> $66,7\% \; p$ | Etene ($\text{CH}_2=\text{CH}_2$), Benzene ($\text{C}_6\text{H}_6$), Formaldeide ($\text{H}_2\text{C}=\text{O}$) |
| **$sp$** | $1s + 1p$ (+ $2p$ puri liberi) | Lineare | $180^\circ$ | 1 legame $\sigma$ + 2 legami $\pi$ (struttura rigida cilindrica) | $50\% \; s$ <br> $50\% \; p$ | Etino/Acetilene ($\text{C}_2\text{H}_2$), $\text{CO}_2$, Cianuro ($\text{HCN}$) |
| **$sp^3d$** | $1s + 3p + 1d$ | Bipiramidale Trigonale | $90^\circ$ (assiali) <br> $120^\circ$ (equatoriali) | 5 legami $\sigma$ (ottetto espanso) | $20\% \; s$ <br> $60\% \; p$ <br> $20\% \; d$ | Pentacloruro di fosforo ($\text{PCl}_5$) |
| **$sp^3d^2$** | $1s + 3p + 2d$ | Ottaedrica | $90^\circ$ | 6 legami $\sigma$ (ottetto espanso) | $16,7\% \; s$ <br> $50\% \; p$ <br> $33,3\% \; d$ | Esafluoruro di zolfo ($\text{SF}_6$) |
