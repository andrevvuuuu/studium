# Profilo Disciplinare: Tecnologia ed Elettronica

> [!IMPORTANT]
> **Polo:** `#personale` | **Tag:** `#tecnologia_ed_elettronica`  
> Questo profilo è dedicato esclusivamente all'**hardware fisico**, all'elettronica dei semiconduttori, alle architetture dei dispositivi, alle telecomunicazioni e ai sistemi embedded.  
> **Distinzione netta da `Informatica`:** L'informatica si occupa di logica astratta, algoritmi e software; questo profilo studia la **materia fisica**, i circuiti, le tensioni, le frequenze elettromagnetiche, i consumi in Watt e la dissipazione termica.

---

## Filosofia e Regole Fondamentali

1. **La Fisica dietro il Silicio e le Onde:**
   - Nessun dispositivo o protocollo è "magia invisibile": ogni bit trasmesso o calcolato è un flusso di elettroni in un canale drogato, una carica accumulata in un condensatore o un'onda elettromagnetica che si propaga nello spazio secondo le equazioni di Maxwell.
   - Ogni termine tecnico deve collegarsi esplicitamente al principio fisico che lo genera (es. *Effetto Joule*, *Effetto Fotoelettrico*, *Legge di Friis sull'attenuazione nello spazio libero*, *Capacità parassita*, *Banda passante*).
2. **La Catena di Funzionamento Fisico Passo-Passo:**
   - Spiega il viaggio del segnale dall'input fisico (antenna, sensore, gate logico) fino all'output (tensione misurabile, dato decodificato, onda irradiata) senza mai saltare la conversione analogico-digitale o lo strato elettrico.
3. **I Compromessi Ingegneristici Invalicabili (*Trade-Offs*):**
   - In ingegneria non esistono pasti gratis: aumentare la frequenza aumenta la velocità ma riduce drasticamente la penetrazione degli ostacoli e fa esplodere i consumi energetici ($P \propto f \cdot V^2$). Ogni nota deve contenere la matrice dei compromessi.

---

## Il Callout Obbligatorio: "Decodifica Hardware e Principio Fisico"

Ogni volta che si introduce un componente hardware, un'architettura di chip o uno standard di trasmissione, deve comparire tassativamente questo callout:

```markdown
> [!note] Decodifica Hardware e Principio Fisico: Trasmissione Wi-Fi su Banda a 5 GHz
> **1. Componente Fisico o Sigla Tecnica:**
> Modulo Ricetrasmettitore RF (Radiofrequenza) IEEE 802.11ax con modulazione 1024-QAM e canali a $160\text{ MHz}$ su spettro a $5\text{ GHz}$.
>
> **2. Principio Fisico Sottostante (con collegamenti a [[Fisica MOC]]):**
> Propagazione delle [[Onde Elettromagnetiche]] nello spazio libero secondo la relazione fondamentale $c = \lambda \cdot f$. A una frequenza maggiore ($f = 5\text{ GHz}$ rispetto a $2.4\text{ GHz}$), la lunghezza d'onda si accorcia ($\lambda \approx 6\text{ cm}$ contro $\approx 12.5\text{ cm}$). In base alla formula di Friis per l'attenuazione e al principio di assorbimento dielettrico, le onde più corte subiscono una riflessione maggiore su muri, cemento e corpi d'acqua, riducendo la gittata utile ma consentendo una densità di informazione per secondo quadruplicata.
>
> **3. Cosa significa in concreto a Sforzo Cognitivo Zero:**
> Significa che la banda a $5\text{ GHz}$ è come un'autostrada a 8 corsie velocissima ma con muri di piombo ai lati: se ti trovi nella stessa stanza del router la connessione vola senza interferenze; se ti sposti dietro due pareti di cartongesso o una porta chiusa, il segnale crolla all'istante perché le micro-onde a $6\text{ cm}$ non riescono ad aggirare gli ostacoli fisici solidi.
```

---

## Scaletta Strutturale delle Note di Tecnologia ed Elettronica

### 1. Frontmatter YAML
```yaml
---
Disciplina: Tecnologia ed Elettronica
Type:
  - Concetto # oppure Metodo se si tratta di protocolli o schemi operativi
tags:
  - tecnologia_ed_elettronica
  - personale
aliases:
  - Wi-Fi
  - Reti Wireless
  - Bande di Frequenza
  - 802.11ax
---
```

### 2. Il Problema Fisico / Ingegneristico
- Quale sfida del mondo reale questo hardware o protocollo deve risolvere? (es. trasmettere flussi video 4K gigabit senza cavi fisici in un appartamento affollato di dispositivi interferenti).
- Perché le soluzioni precedenti hanno raggiunto il limite fisico (es. saturazione dello spettro ISM a $2.4\text{ GHz}$ a causa di Bluetooth, forni a microonde e vicini di casa).

### 3. Callout Decodifica Hardware e Principio Fisico

### 4. Catena di Funzionamento Fisico Passo-Passo
Descrizione cronologica e deterministica del flusso del segnale a passaggi numerati:

```markdown
### Catena di Funzionamento Fisico: Dal Bit Digitale all'Onda Radio

1. **Generazione dei Pacchetti Logici nel Processore (SoC Baseband):**  
   Il processore del router riceve i frame Ethernet e li converte in bit digitali grezzi, applicando la codifica di correzione d'errore FEC (*Forward Error Correction*) per prevenire corruzioni da rumore termico.
2. **Modulazione di Fase e Ampiezza (Costellazione QAM):**  
   Il modulatore mappa gruppi di 10 bit in coordinate di ampiezza e fase (1024-QAM). Un singolo impulso radio trasporta ora una combinazione specifica di intensità e sfasamento.
3. **Conversione Digitale-Analogica (DAC) e Up-Conversion RF:**  
   Il convertitore DAC trasforma le coordinate numeriche in una tensione analogica ad alta frequenza, che viene mixata con l'oscillatore locale a $5\text{ GHz}$ per traslare il segnale nella banda radio desiderata.
4. **Amplificazione di Potenza (PA) e Irradiazione dall'Antenna:**  
   L'amplificatore di potenza (Power Amplifier) eleva la corrente RF e la invia all'antenna dipolo. Gli elettroni che oscillano avanti e indietro nell'antenna metallica generano un campo elettrico e magnetico oscillante concatenato che si distacca nello spazio alla velocità della luce $c$.
5. **Ricezione, Filtro Passa-Banda e Low-Noise Amplifier (LNA):**  
   L'antenna dello smartphone capta una frazione microscopica di microwatt ($<-70\text{ dBm}$) dell'onda incidente. L'amplificatore a basso rumore (LNA) amplifica la tensione debole senza iniettare rumore termico prima che il demodulatore ricostruisca la stringa di bit originaria.
```

### 5. Matrice dei Compromessi Ingegneristici (*Trade-Offs*)
Tabella Markdown obbligatoria che confronta le scelte costruttive:

| Parametro Ingegneristico | Opzione A (es. 2.4 GHz) | Opzione B (es. 5 GHz) | Opzione C (es. 6 GHz / Wi-Fi 6E) | Perché la Fisica Impone il Limite |
| :--- | :---: | :---: | :---: | :--- |
| **Banda Passante Massima** | Bassa ($\approx 150\text{ Mbps}$) | Alta ($\approx 1.2\text{ Gbps}$) | Estrema ($> 2.4\text{ Gbps}$) | Canali radio più ampi ($20\text{ MHz}$ vs $160\text{ MHz}$) contengono più sottoportanti ortogonali |
| **Copertura e Penetrazione Ostacoli** | Eccellente (attraversa 3-4 muri) | Moderata (1-2 muri) | Minima (linea di vista o quasi) | Lunghezza d'onda maggiore si diffrange attorno agli spigoli; onde corte vengono assorbite |
| **Interferenze Esterne** | Saturazione totale (13 canali sovrapposti) | Basse (fino a 24 canali non sovrapposti) | Zero interferenze legacy (spettro pulito) | Condivisione delle frequenze con forni a microonde, telemetrie e baby monitor |
| **Consumo Energetico e Calore** | Basso | Medio-Alto | Alto | Frequenze elevate e campionamenti a giga-samples/s generano dissipazione capacitiva $P \propto f \cdot C \cdot V^2$ |

### 6. Architettura dei Componenti Chiave e Norme di Sicurezza
- Schema delle sezioni del circuito (RF Front-End, Transceiver, Baseband Processor, Power Management IC).
- Protocolli di crittografia hardware (WPA3-SAE, handshake Dragonfly contro attacchi a dizionario offline).
- Collegamenti alle note connesse del vault ([[Fisica MOC]], [[Informatica MOC]]).
