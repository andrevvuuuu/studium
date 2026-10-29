<!--
================================================================================
SNIPPET BLUEPRINT COMPRESSO — DISCIPLINA: BIOLOGIA
Estratto dalla Nota Esempio reale: `Biologia/Replicazione del DNA, Trascrizione e Traduzione.md`
================================================================================
-->

### BLOCCO 1 — REGOLA DI ACCOPPIAMENTO CON IL PROFILO DELLA MATERIA
Quando scrivi una nota o un MOC per **Biologia** (UNIVERSITÀ):
1. **Regole Logiche e Verifiche:** Segui rigorosamente il rispettivo file `.antigravity/disciplines/biologia.md` (obblighi formali, controlli incrociati e verifiche evidenziali).
2. **Modello Visivo e Tonalità:** Utilizza i 4 blocchi modello qui sotto come *calibro stilistico* per frontmatter, introduzione intuitiva, callout di decodifica, catene causali/dimostrative e tabelle.
3. **Sforzo Cognitivo Zero:** Ogni formula, termine specialistico o datazione deve possedere la sua immediata traduzione discorsiva e un'anatomia visiva chiara.

---

### BLOCCO 2 — ESEMPIO REALE DI FRONTMATTER YAML + INTRODUZIONE MODELLO
```yaml
Disciplina: Biologia
Type:
  - Concetto
tags:
  - biologia
  - genetica
  - biologia-molecolare
  - università
aliases:
  - Dogma Centrale della Biologia
  - Replicazione Trascrizione Traduzione
  - Sintesi Proteica e Codice Genetico
```

Il **Dogma Centrale della Biologia Molecolare** (enunciato da Francis Crick nel 1958 e formalizzato nel 1970) descrive il flusso monodirezionale dell'informazione biologica all'interno delle cellule viventi: la sequenza nucleotidica conservata stabilmente nel genoma nucleare viene replicata per la trasmissione generazionale, trascritta in molecole intermediarie di RNA messaggero e infine tradotta nella sequenza lineare di amminoacidi che determina la struttura e la funzione tridimensionale delle proteine.

---

### BLOCCO 3 — ESEMPIO REALE DI CALLOUT DI DECODIFICA
> [!note] Decodifica Molecolare: Il Vincolo Universale di Polimerizzazione ($5' \to 3'$)
> - **Regola Chimico-Enzimatica**: Tutte le DNA polimerasi e RNA polimerasi conosciute in natura possono sintetizzare un nuovo filamento **esclusivamente in direzione $5' \to 3'$** (leggendo il filamento stampo in direzione $3' \to 5'$).
> - **Meccanismo Chimico**: L'ossigeno nucleofilo del gruppo ossidrile libero al terminale **$3'\text{-OH}$** del filamento nascente attacca il fosfato $\alpha$ del desossiribonucleotide trifosfato in ingresso (**dNTP**), liberando pirofosfato ($\text{PP}_i$) la cui idrolisi rende la reazione termodinamicamente irreversibile ($\Delta G < 0$).
> - **Cosa significa in concreto (Sforzo Zero)**: Nessun enzima può attaccare nucleotidi "in testa" (all'estremità $5'$); si può aggiungere solo "in coda" (all'estremità $3'$). Questo singolo vincolo chimico spiega perché la replicazione dei due filamenti antiparalleli sia asimmetrica (filamento veloce vs frammenti di Okazaki) e perché esistano i telomeri.

---

### BLOCCO 4 — ESEMPIO REALE DI DIMOSTRAZIONE / CATENA CAUSALE A SFORZO ZERO
### Il Legame Fosfodiesterico e la Polarità
I nucleotidi successivi sono uniti covalentemente da **legami fosfodiesterici**: il gruppo ossidrile legato al carbonio $3'$ di un nucleotide forma un ponte fosfoestere con il gruppo fosfato legato al carbonio $5'$ del nucleotide successivo. Lo scheletro carbonioso acquisisce quindi una polarità intrinseca:
- Un'estremità **$5'\text{-fosfato}$ libera** (o fosforilata).
- Un'estremità **$3'\text{-OH}$ libera** (substrato d'innesco indispensabile per la polimerizzazione).

---

### BLOCCO 5 — ESEMPIO DI TABELLA RIEPILOGATIVA
| Enzima | Processo Biologico | Funzione Molecolare Specifica | Direzione / Requisito Energetico |
| :--- | :--- | :--- | :--- |
| **DNA Elicasi** | Replicazione | Srotola la doppia elica rompendo i legami a idrogeno tra le basi | Consumo di $\text{ATP}$ |
| **Topoisomerasi (Girasi)** | Replicazione / Trascrizione | Recide transitoriamente uno o due filamenti per allentare lo stress torsionale a monte | $\text{Topoisomerasi I}$: no ATP; $\text{Topoisomerasi II}$: richiede $\text{ATP}$ |
| **DNA Primasi** | Replicazione | Sintetizza de novo brevi inneschi di RNA ($10-12\text{ nt}$) con terminale $3'\text{-OH}$ | Sintesi in direzione $5' \to 3'$ |
| **DNA Polimerasi (III / $\delta,\epsilon$)** | Replicazione | Polimerizza la catena nascente aggiungendo dNTP al $3'\text{-OH}$ preesistente | Sintesi rigorosa $5' \to 3'$, correzione $3' \to 5'$ |
| **DNA Ligasi** | Replicazione e Riparazione | Salda i gap fosfodiesterici tra frammenti di Okazaki unendo $3'\text{-OH}$ e $5'\text{-fosfato}$ | Consumo di $\text{ATP}$ (o $\text{NAD}^+$ nei batteri) |
| **RNA Polimerasi II** | Trascrizione | Sintetizza il pre-mRNA a singolo filamento complementare al filamento stampo di DNA | Sintesi in direzione $5' \to 3'$, necessita di $\text{NTP}$ |
| **Spliceosoma (snRNP)** | Maturazione mRNA | Rimuove gli introni non codificanti e cuce insieme gli esoni via transesterificazione | Guidato da snRNA ($\text{U1-U6}$) e $\text{ATP}$ |
| **Amminoacil-tRNA Sintetasi** | Fase pre-Traduzionale | Lega covalentemente l'amminoacido corretto al braccio $3'\text{-CCA}$ del suo specifico tRNA | Attivazione a due stadi dipendente da $\text{ATP}$ |
| **Peptidil-Transferasi** | Traduzione | Ribozima (rRNA catalitico) che crea il legame peptidico tra sito P e sito A | Attività enzimatica intrinseca dell'rRNA ribosomiale |
| **Trascrittasi Inversa** | Eccezione al Dogma / Ciclo Retrovirale | DNA polimerasi RNA-dipendente: sintetizza DNA stampando da una matrice a singolo filamento di RNA | Sintesi in direzione $5' \to 3'$ |
