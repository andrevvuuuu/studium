/**
 * study_panel.js
 * ==============
 * Pannello Interattivo "Flashcard & Quiz" per DataviewJS in Obsidian.
 * 
 * Funzionalità Principali:
 * 1. Parsing Sicuro per il LaTeX:
 *    - Nessun crash da JSON.parse su backslash matematici (\mathbb, \forall, \frac, \{a,b\}, etc.).
 *    - Preservazione rigorosa di tutti i comandi LaTeX durante la sanitizzazione JSON.
 * 2. Rendering Nativo Obsidian Markdown & LaTeX:
 *    - Risoluzione robusta di MarkdownRenderer e Component tramite Obsidian API nativa.
 *    - Supporto MathJax/LaTeX asincrono e completo su fronte, retro, domande quiz, opzioni A-D e spiegazioni.
 * 3. Header Unificato & Moderno:
 *    - Segmented pill switcher ("Flashcard (N)" / "Quiz (M)").
 *    - Badge compatto di consolidamento "Consolidate: X/N" e pulsante "Sync Anki".
 * 4. Navigazione Ergonomica:
 *    - Select stilizzato a tutta larghezza con text-overflow: ellipsis (nessun testo tagliato).
 *    - Frecce ← e → con stato disabilitato evidente, contatore e pulsante "Mescola".
 *    - Scorciatoie da tastiera scoped al container (Spazio per girare la carta, Frecce per navigare).
 * 5. Flashcard & Quiz in Stile Linear/Raycast/Notion:
 *    - Card ad alto contrasto con badge "DOMANDA (FRONTE)" e "RISPOSTA (RETRO)".
 *    - Barra di progresso con traccia ben visibile.
 *    - Opzioni quiz a tutta larghezza con cerchietto lettera, feedback cromatico immediato e box spiegazione animato.
 */

(async function main() {
    // -------------------------------------------------------------
    // 1. Risoluzione del Contesto Obsidian / Dataview
    // -------------------------------------------------------------
    const dvObj = (typeof dv !== "undefined") ? dv : (this?.dv || null);
    const appObj = dvObj?.app || window.app;
    const containerEl = dvObj?.container || this?.container || null;

    if (!appObj || !containerEl) {
        console.error("[StudyPanel] Impossibile risolvere il contesto di Obsidian / Dataview.");
        return;
    }

    const currentFilePath = dvObj?.currentFilePath || appObj.workspace?.getActiveFile()?.path || "";
    const currentFile = appObj.vault.getAbstractFileByPath(currentFilePath) || appObj.workspace?.getActiveFile();

    if (!currentFile) {
        containerEl.createEl("div", {
            text: "Errore StudyPanel: Nota attiva non identificata.",
            cls: "study-panel-error"
        });
        return;
    }

    // Risoluzione modulo nativo Obsidian
    const obsidianModule = window.obsidian || (typeof require === "function" ? require("obsidian") : null);
    const MarkdownRenderer = obsidianModule?.MarkdownRenderer;
    const Component = obsidianModule?.Component;

    // Componente di ciclo di vita per evitare memory leak nel rendering
    const panelComponent = dvObj?.component || (Component ? new Component() : null);
    if (panelComponent && !panelComponent._loaded && typeof panelComponent.load === "function") {
        panelComponent.load();
    }

    // -------------------------------------------------------------
    // 2. Lettura File e Parsing Sicuro di Flashcard e Quiz
    // -------------------------------------------------------------
    let rawContent = "";
    try {
        rawContent = await appObj.vault.cachedRead(currentFile);
    } catch (err) {
        rawContent = await appObj.vault.adapter.read(currentFile.path);
    }

    const studyData = parseStudyDataSafe(rawContent);
    const flashcards = studyData.flashcards || [];
    const quizzes = studyData.quizzes || [];

    // Se la nota non ha ancora il blocco di studio, mostra un invito accogliente
    if (flashcards.length === 0 && quizzes.length === 0) {
        const emptyBox = containerEl.createEl("div", { cls: "ag-study-empty" });
        emptyBox.createEl("h4", { text: "Palestra d'Esame Interattiva (Flashcard e Quiz)" });
        emptyBox.createEl("p", {
            text: "Questa nota non contiene ancora Flashcard o Quiz strutturati. Aggiungi il blocco %%STUDY_DATA per generare automaticamente le domande di verifica attiva e sincronizzarle con Anki."
        });
        return;
    }

    // -------------------------------------------------------------
    // 3. Risoluzione Metadati per Deck Anki
    // -------------------------------------------------------------
    const fileCache = appObj.metadataCache.getFileCache(currentFile);
    const fm = fileCache?.frontmatter || {};
    const rawPolo = fm.Polo || fm.polo || "Universitario";
    const poloClean = rawPolo.charAt(0).toUpperCase() + rawPolo.slice(1).toLowerCase();
    const rawDisc = fm.Disciplina || fm.disciplina || "Generale";
    const titleClean = currentFile.basename;
    const ankiDeckName = `Obsidian::${poloClean}::${rawDisc}::${titleClean}`;

    // -------------------------------------------------------------
    // 4. Stato Reattivo dell'Interfaccia
    // -------------------------------------------------------------
    const state = {
        activeTab: flashcards.length > 0 ? "flashcards" : "quizzes",
        // Flashcard state
        cardList: [...flashcards],
        cardIndex: 0,
        isFlipped: false,
        masteredCards: new Set(),
        // Quiz state
        quizList: [...quizzes],
        quizIndex: 0,
        selectedOption: null,
        quizAnswered: false,
        // Anki sync state
        isSyncing: false
    };

    // Svuota il contenitore prima del rendering
    containerEl.empty();

    // Wrapper Principale del Pannello con supporto al focus da tastiera (tabindex="0")
    const panelWrap = containerEl.createEl("div", { cls: "ag-study-panel" });
    panelWrap.setAttribute("tabindex", "0");

    // Gestione da tastiera confinata RIGOROSAMENTE al pannello
    panelWrap.onkeydown = (e) => {
        const activeTag = document.activeElement ? document.activeElement.tagName : "";
        if (activeTag === "SELECT" || activeTag === "INPUT" || activeTag === "TEXTAREA") {
            return;
        }

        if (e.code === "Space") {
            if (state.activeTab === "flashcards" && state.cardList.length > 0) {
                e.preventDefault();
                state.isFlipped = !state.isFlipped;
                renderFullPanel();
            }
        } else if (e.code === "ArrowLeft") {
            if (state.activeTab === "flashcards" && state.cardIndex > 0) {
                e.preventDefault();
                state.cardIndex--;
                state.isFlipped = false;
                renderFullPanel();
            } else if (state.activeTab === "quizzes" && state.quizIndex > 0) {
                e.preventDefault();
                state.quizIndex--;
                state.selectedOption = null;
                state.quizAnswered = false;
                renderFullPanel();
            }
        } else if (e.code === "ArrowRight") {
            if (state.activeTab === "flashcards" && state.cardIndex < state.cardList.length - 1) {
                e.preventDefault();
                state.cardIndex++;
                state.isFlipped = false;
                renderFullPanel();
            } else if (state.activeTab === "quizzes" && state.quizIndex < state.quizList.length - 1) {
                e.preventDefault();
                state.quizIndex++;
                state.selectedOption = null;
                state.quizAnswered = false;
                renderFullPanel();
            }
        }
    };

    // Render iniziale
    renderFullPanel();

    // -------------------------------------------------------------
    // Funzioni di Rendering Interfaccia
    // -------------------------------------------------------------
    function renderFullPanel() {
        panelWrap.empty();

        // 1. HEADER UNIFICATO
        const header = panelWrap.createEl("div", { cls: "ag-study-header" });
        
        // Segmented pill switcher
        const segmented = header.createEl("div", { cls: "ag-study-segmented" });
        
        if (flashcards.length > 0) {
            const fcPill = segmented.createEl("button", {
                cls: `ag-study-pill-btn ${state.activeTab === "flashcards" ? "active" : ""}`,
                text: `Flashcard (${flashcards.length})`
            });
            fcPill.onclick = () => {
                state.activeTab = "flashcards";
                renderFullPanel();
            };
        }

        if (quizzes.length > 0) {
            const qzPill = segmented.createEl("button", {
                cls: `ag-study-pill-btn ${state.activeTab === "quizzes" ? "active" : ""}`,
                text: `Quiz (${quizzes.length})`
            });
            qzPill.onclick = () => {
                state.activeTab = "quizzes";
                renderFullPanel();
            };
        }

        // Header Actions: Badge Consolidate + Sync Anki
        const headerActions = header.createEl("div", { cls: "ag-study-header-actions" });

        if (flashcards.length > 0) {
            headerActions.createEl("span", {
                cls: "ag-study-mastered-badge",
                text: `Consolidate: ${state.masteredCards.size}/${flashcards.length}`
            });
        }

        const ankiBtn = headerActions.createEl("button", {
            cls: "ag-study-anki-btn",
            text: state.isSyncing ? "Sincronizzazione..." : "Sync Anki"
        });
        ankiBtn.disabled = state.isSyncing;
        ankiBtn.onclick = handleAnkiSync;

        // 2. NAVIGAZIONE (Select + Frecce + Mescola)
        renderNavBar(panelWrap);

        // 3. CONTENUTO ATTIVO
        const contentArea = panelWrap.createEl("div", { cls: "ag-study-content" });

        if (state.activeTab === "flashcards" && flashcards.length > 0) {
            renderFlashcardsView(contentArea);
        } else if (state.activeTab === "quizzes" && quizzes.length > 0) {
            renderQuizzesView(contentArea);
        }
    }

    // -------------------------------------------------------------
    // Barra di Navigazione
    // -------------------------------------------------------------
    function renderNavBar(container) {
        const isFc = state.activeTab === "flashcards";
        const list = isFc ? state.cardList : state.quizList;
        const total = list.length;
        const currentIndex = isFc ? state.cardIndex : state.quizIndex;
        if (total === 0) return;

        const navBar = container.createEl("div", { cls: "ag-study-nav" });

        // Select a tutta larghezza con ellissi
        const selectWrap = navBar.createEl("div", { cls: "ag-study-select-wrap" });
        const selectEl = selectWrap.createEl("select", { cls: "ag-study-select" });

        list.forEach((item, idx) => {
            const rawTitle = item.title || item.question || `Elemento ${idx + 1}`;
            const cleanTitle = rawTitle.replace(/[\n\r]+/g, " ").trim();
            const prefix = isFc ? `Carta ${idx + 1}` : `Quiz ${idx + 1}`;
            const opt = selectEl.createEl("option", {
                value: String(idx),
                text: `${prefix}: ${cleanTitle}`
            });
            if (idx === currentIndex) opt.selected = true;
        });

        selectEl.onchange = (e) => {
            const newIdx = parseInt(e.target.value, 10);
            if (isFc) {
                state.cardIndex = newIdx;
                state.isFlipped = false;
            } else {
                state.quizIndex = newIdx;
                state.selectedOption = null;
                state.quizAnswered = false;
            }
            renderFullPanel();
        };

        // Controlli Destri: Frecce, Contatore e Mescola
        const controls = navBar.createEl("div", { cls: "ag-study-nav-controls" });

        // Freccia Sinistra (←)
        const prevBtn = controls.createEl("button", {
            cls: "ag-study-nav-btn",
            text: "←",
            title: "Precedente (Freccia Sinistra)"
        });
        prevBtn.disabled = currentIndex === 0;
        prevBtn.onclick = () => {
            if (currentIndex > 0) {
                if (isFc) {
                    state.cardIndex--;
                    state.isFlipped = false;
                } else {
                    state.quizIndex--;
                    state.selectedOption = null;
                    state.quizAnswered = false;
                }
                renderFullPanel();
            }
        };

        // Contatore
        controls.createEl("span", {
            cls: "ag-study-counter",
            text: `${currentIndex + 1} / ${total}`
        });

        // Freccia Destra (→)
        const nextBtn = controls.createEl("button", {
            cls: "ag-study-nav-btn",
            text: "→",
            title: "Successivo (Freccia Destra)"
        });
        nextBtn.disabled = currentIndex === total - 1;
        nextBtn.onclick = () => {
            if (currentIndex < total - 1) {
                if (isFc) {
                    state.cardIndex++;
                    state.isFlipped = false;
                } else {
                    state.quizIndex++;
                    state.selectedOption = null;
                    state.quizAnswered = false;
                }
                renderFullPanel();
            }
        };

        // Bottone Mescola
        const shuffleBtn = controls.createEl("button", {
            cls: "ag-study-shuffle-btn",
            text: "Mescola",
            title: "Mescola l'ordine delle carte"
        });
        shuffleBtn.onclick = () => {
            shuffleArray(list);
            if (isFc) {
                state.cardIndex = 0;
                state.isFlipped = false;
            } else {
                state.quizIndex = 0;
                state.selectedOption = null;
                state.quizAnswered = false;
            }
            renderFullPanel();
        };
    }

    // -------------------------------------------------------------
    // Vista 1: Flashcard
    // -------------------------------------------------------------
    function renderFlashcardsView(container) {
        const total = state.cardList.length;
        if (total === 0) return;
        const currentCard = state.cardList[state.cardIndex];

        // Card Box Interattiva con Flip
        const cardBox = container.createEl("div", {
            cls: `ag-study-card ${state.isFlipped ? "flipped" : ""}`
        });

        // Header della Carta
        const cardTop = cardBox.createEl("div", { cls: "ag-study-card-top" });
        cardTop.createEl("span", {
            cls: "ag-study-card-title",
            text: `${currentCard.title || `Carta ${state.cardIndex + 1}`}`
        });
        cardTop.createEl("span", {
            cls: `ag-study-badge ${state.isFlipped ? "back" : "front"}`,
            text: state.isFlipped ? "RISPOSTA (RETRO)" : "DOMANDA (FRONTE)"
        });

        // Corpo della Carta con Rendering Markdown & MathJax
        const cardBody = cardBox.createEl("div", { cls: "ag-study-card-body" });
        if (!state.isFlipped) {
            renderMarkdownText(currentCard.question, cardBody);
        } else {
            const qDim = cardBody.createEl("div", { cls: "ag-study-question-dimmed" });
            renderMarkdownText(`**Domanda:** ${currentCard.question}`, qDim);
            cardBody.createEl("hr", { cls: "ag-study-divider" });
            const aFull = cardBody.createEl("div", { cls: "ag-study-answer-full" });
            renderMarkdownText(currentCard.answer, aFull);
        }

        // Hint discreto in basso
        cardBox.createEl("div", {
            cls: "ag-study-card-hint",
            text: "Clicca sulla carta o premi Spazio per girare ↻"
        });

        // Flip su click (salvaguardando link o bottoni)
        cardBox.onclick = (e) => {
            if (e.target.tagName === "A" || e.target.tagName === "BUTTON") return;
            state.isFlipped = !state.isFlipped;
            renderFullPanel();
        };

        // Footer: Autovalutazione e Barra di Progresso
        const footerBar = container.createEl("div", { cls: "ag-study-footer" });

        const evalGroup = footerBar.createEl("div", { cls: "ag-study-eval-group" });
        
        const reviewBtn = evalGroup.createEl("button", {
            cls: "ag-study-btn-review",
            text: "Da rivedere"
        });
        reviewBtn.onclick = () => {
            state.masteredCards.delete(currentCard.id);
            if (state.cardIndex < total - 1) state.cardIndex++;
            state.isFlipped = false;
            renderFullPanel();
        };

        const masterBtn = evalGroup.createEl("button", {
            cls: "ag-study-btn-master",
            text: "Consolidata"
        });
        masterBtn.onclick = () => {
            state.masteredCards.add(currentCard.id);
            if (state.cardIndex < total - 1) state.cardIndex++;
            state.isFlipped = false;
            renderFullPanel();
        };

        // Barra di Progresso con percentuale
        const progressContainer = footerBar.createEl("div", { cls: "ag-study-progress-wrap" });
        const masteredCount = state.masteredCards.size;
        const masteredPct = Math.round((masteredCount / total) * 100);
        progressContainer.createEl("span", {
            cls: "ag-study-progress-label",
            text: `${masteredPct}%`
        });
        const progressBg = progressContainer.createEl("div", { cls: "ag-study-progress-bar" });
        const progressFill = progressBg.createEl("div", { cls: "ag-study-progress-fill" });
        progressFill.style.width = `${masteredPct}%`;
    }

    // -------------------------------------------------------------
    // Vista 2: Quiz a Scelta Multipla
    // -------------------------------------------------------------
    function renderQuizzesView(container) {
        const total = state.quizList.length;
        if (total === 0) return;
        const currentQuiz = state.quizList[state.quizIndex];

        // Box Domanda
        const questionBox = container.createEl("div", { cls: "ag-study-quiz-question" });
        const qHeader = questionBox.createEl("div", { cls: "ag-study-quiz-header" });
        qHeader.createEl("span", {
            cls: "ag-study-card-title",
            text: `${currentQuiz.title || `Quiz ${state.quizIndex + 1}`}`
        });
        const qBody = questionBox.createEl("div", { cls: "ag-study-quiz-body" });
        renderMarkdownText(currentQuiz.question, qBody);

        // Opzioni A, B, C, D Interattive
        const optionsList = container.createEl("div", { cls: "ag-study-options-list" });
        const correctKey = (currentQuiz.correct || "A").trim().toUpperCase();

        currentQuiz.options.forEach((opt) => {
            const optKey = opt.key.trim().toUpperCase();
            let optStatusCls = "";

            if (state.quizAnswered) {
                if (optKey === correctKey) {
                    optStatusCls = "opt-correct";
                } else if (state.selectedOption === optKey) {
                    optStatusCls = "opt-wrong";
                }
            }

            const optBtn = optionsList.createEl("div", {
                cls: `ag-study-option-item ${optStatusCls} ${state.quizAnswered ? "opt-disabled" : ""}`
            });

            // Badge Lettera (Cerchietto)
            optBtn.createEl("span", {
                cls: "ag-study-option-badge",
                text: optKey
            });

            // Testo Opzione con LaTeX / Markdown
            const optTextEl = optBtn.createEl("div", { cls: "ag-study-option-text" });
            renderMarkdownText(opt.text, optTextEl);

            if (!state.quizAnswered) {
                optBtn.onclick = () => {
                    state.selectedOption = optKey;
                    state.quizAnswered = true;
                    renderFullPanel();
                };
            }
        });

        // Box Spiegazione Rigorosa e Analisi Trappole (compare subito dopo la risposta)
        if (state.quizAnswered) {
            const isCorrect = state.selectedOption === correctKey;
            const expBox = container.createEl("div", {
                cls: `ag-study-explanation-box ${isCorrect ? "exp-success" : "exp-error"}`
            });

            const expHeader = expBox.createEl("div", { cls: "ag-study-exp-header" });
            expHeader.createEl("strong", {
                text: isCorrect ? "Risposta Esatta!" : `Risposta Errata (La risposta corretta è la ${correctKey})`
            });

            const expBody = expBox.createEl("div", { cls: "ag-study-exp-body" });
            const expText = currentQuiz.explanation || "Nessuna spiegazione dettagliata disponibile.";
            renderMarkdownText(`**Spiegazione Rigorosa e Analisi delle Trappole:**\n\n${expText}`, expBody);
        }
    }

    // -------------------------------------------------------------
    // Helper: Rendering Nativo Markdown / MathJax con Obsidian API
    // -------------------------------------------------------------
    async function renderMarkdownText(mdText, targetEl) {
        if (!mdText) return;
        if (typeof targetEl.empty === "function") {
            targetEl.empty();
        } else {
            targetEl.innerHTML = "";
        }
        try {
            if (MarkdownRenderer && typeof MarkdownRenderer.render === "function") {
                await MarkdownRenderer.render(
                    appObj,
                    mdText,
                    targetEl,
                    currentFilePath,
                    panelComponent
                );
                return;
            } else if (MarkdownRenderer && typeof MarkdownRenderer.renderMarkdown === "function") {
                await MarkdownRenderer.renderMarkdown(
                    mdText,
                    targetEl,
                    currentFilePath,
                    panelComponent
                );
                return;
            }
        } catch (err) {
            console.warn("[StudyPanel] Errore durante MarkdownRenderer:", err);
        }

        // Fallback pulito se MarkdownRenderer non è disponibile
        targetEl.innerHTML = markdownToSimpleHtml(mdText);
    }

    // -------------------------------------------------------------
    // Helper: Sincronizzazione Automatica con Anki (AnkiConnect)
    // -------------------------------------------------------------
    async function handleAnkiSync() {
        const Notice = window.Notice || ((msg) => console.log(msg));
        state.isSyncing = true;
        renderFullPanel();

        try {
            // 1. Verifica raggiungibilità AnkiConnect (porta 8765)
            const testRes = await fetch("http://127.0.0.1:8765", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: "version", version: 6 })
            }).catch(() => null);

            if (!testRes || !testRes.ok) {
                new Notice("Anki non raggiungibile. Assicurati che Anki sia aperto e che il plugin AnkiConnect sia attivo (porta 8765).", 5000);
                state.isSyncing = false;
                renderFullPanel();
                return;
            }

            // 2. Creazione Mazzo Gerarchico
            await fetch("http://127.0.0.1:8765", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    action: "createDeck",
                    version: 6,
                    params: { deck: ankiDeckName }
                })
            });

            // 3. Preparazione Note Anki con Conversione LaTeX per MathJax
            const ankiNotes = [];

            // A. Flashcard
            for (const fc of flashcards) {
                const frontMath = convertLatexForAnki(fc.question);
                const backMath = convertLatexForAnki(fc.answer);
                ankiNotes.push({
                    deckName: ankiDeckName,
                    modelName: "Basic",
                    fields: {
                        Front: `<b>[Flashcard] ${escapeHtml(fc.title || "Concetto")}</b><br><br>${markdownToSimpleHtml(frontMath)}`,
                        Back: `${markdownToSimpleHtml(backMath)}`
                    },
                    tags: ["obsidian-flashcard", rawDisc.toLowerCase().replace(/\s+/g, "-")]
                });
            }

            // B. Quiz a Scelta Multipla
            for (const qz of quizzes) {
                const qMath = convertLatexForAnki(qz.question);
                const correctKey = (qz.correct || "A").trim().toUpperCase();
                
                let optionsHtml = "<ol type='A' style='margin-top:10px;'>";
                for (const opt of qz.options) {
                    const optMath = convertLatexForAnki(opt.text);
                    optionsHtml += `<li style='margin-bottom:6px;'>${markdownToSimpleHtml(optMath)}</li>`;
                }
                optionsHtml += "</ol>";

                const expMath = convertLatexForAnki(qz.explanation || "");

                ankiNotes.push({
                    deckName: ankiDeckName,
                    modelName: "Basic",
                    fields: {
                        Front: `<b>[Quiz] ${escapeHtml(qz.title || "Domanda")}</b><br><br>${markdownToSimpleHtml(qMath)}${optionsHtml}`,
                        Back: `<b style='color:#2ecc71;'>Risposta Corretta: ${correctKey}</b><br><br><b>Spiegazione:</b><br>${markdownToSimpleHtml(expMath)}`
                    },
                    tags: ["obsidian-quiz", rawDisc.toLowerCase().replace(/\s+/g, "-")]
                });
            }

            // 4. Invio cumulativo tramite addNotes
            const addRes = await fetch("http://127.0.0.1:8765", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    action: "addNotes",
                    version: 6,
                    params: { notes: ankiNotes }
                })
            });

            const addData = await addRes.json();
            const createdCount = (addData.result || []).filter(id => id !== null).length;

            new Notice(`Sincronizzazione con Anki completata!\nMazzo: ${ankiDeckName}\n${createdCount} note sincronizzate (${flashcards.length} Flashcard, ${quizzes.length} Quiz).`, 5000);
        } catch (err) {
            new Notice(`Errore durante la sincronizzazione con Anki: ${err.message}`, 5000);
        } finally {
            state.isSyncing = false;
            renderFullPanel();
        }
    }

    // -------------------------------------------------------------
    // Helper: Parsing Dati di Studio (Delimitatori Markdown o JSON)
    // -------------------------------------------------------------
    function parseStudyDataSafe(content) {
        const flashcards = [];
        const quizzes = [];

        // Ricerca del blocco delimitato %%STUDY_DATA ... %% oppure <!-- STUDY_DATA ... -->
        const blockMatch = content.match(/(?:%%|<!--\s*)STUDY_DATA([\s\S]*?)(?:%%|\s*-->)/i);
        if (!blockMatch) {
            return { flashcards, quizzes };
        }

        let rawBlock = blockMatch[1].trim();

        // Rimuove eventuali prefissi di callout '>' per riga se il blocco è nidificato dentro un callout Obsidian
        const cleanLines = rawBlock.split("\n").map(line => line.replace(/^\s*>\s?/, ""));
        rawBlock = cleanLines.join("\n").trim();

        // Modalità 1: Se inizia con '{', prova il parsing JSON sicuro per LaTeX
        if (rawBlock.startsWith("{")) {
            try {
                // Sanitizzazione backslash: raddoppia TUTTI i backslash isolati non seguiti da " o \
                // e non preceduti da un altro backslash. In questo modo LaTeX come \times, \notin, \beta, \frac, \{a,b\}
                // vengono preservati intatti sia se scritti con backslash singolo che doppio.
                const sanitizedJson = rawBlock.replace(/(?<!\\)\\(?!["\\])/g, "\\\\");
                const parsed = JSON.parse(sanitizedJson);
                if (Array.isArray(parsed.flashcards)) {
                    parsed.flashcards.forEach((f, idx) => {
                        flashcards.push({
                            id: idx + 1,
                            title: f.title || `Carta ${idx + 1}`,
                            question: f.question || "",
                            answer: f.answer || ""
                        });
                    });
                }
                if (Array.isArray(parsed.quizzes)) {
                    parsed.quizzes.forEach((q, idx) => {
                        let opts = [];
                        if (Array.isArray(q.options)) {
                            opts = q.options.map((o, oIdx) => {
                                if (typeof o === "string") {
                                    const m = o.match(/^([A-D])\)\s*(.*)$/);
                                    return m ? { key: m[1], text: m[2] } : { key: String.fromCharCode(65 + oIdx), text: o };
                                }
                                return o;
                            });
                        }
                        quizzes.push({
                            id: idx + 1,
                            title: q.title || `Quiz ${idx + 1}`,
                            question: q.question || "",
                            options: opts,
                            correct: q.correct || "A",
                            explanation: q.explanation || ""
                        });
                    });
                }
                return { flashcards, quizzes };
            } catch (jsonErr) {
                console.warn("[StudyPanel] Fallback al parser Markdown per errore JSON:", jsonErr.message);
            }
        }

        // Modalità 2: Parser a Delimitatori Markdown Nativo (100% immune ai backslash)
        const items = rawBlock.split(/(?=###\s+(?:FLASHCARD|QUIZ))/i);

        for (const item of items) {
            const it = item.trim();
            if (!it) continue;

            if (/^###\s+FLASHCARD/i.test(it)) {
                const headerM = it.match(/^###\s+FLASHCARD\s*(?:\d*):?\s*(.*)$/im);
                const title = headerM ? headerM[1].trim() : "";
                const qM = it.match(/\*\*Q:\*\*\s*([\s\S]*?)(?=\*\*A:\*\*|$)/i);
                const aM = it.match(/\*\*A:\*\*\s*([\s\S]*)$/i);
                const question = qM ? qM[1].trim() : "";
                const answer = aM ? aM[1].trim() : "";

                if (question && answer) {
                    flashcards.push({
                        id: flashcards.length + 1,
                        title: title || `Carta ${flashcards.length + 1}`,
                        question,
                        answer
                    });
                }
            } else if (/^###\s+QUIZ/i.test(it)) {
                const headerM = it.match(/^###\s+QUIZ\s*(?:\d*):?\s*(.*)$/im);
                const title = headerM ? headerM[1].trim() : "";
                const qM = it.match(/\*\*Q:\*\*\s*([\s\S]*?)(?=(?:^\s*(?:-\s*\[\s*\]\s*|[-*]\s*|\*\*)?[A-D][\).:\-]|\*\*CORRECT:))/im);
                const question = qM ? qM[1].trim() : "";

                const options = [];
                const lines = it.split("\n");
                for (const line of lines) {
                    const l = line.trim();
                    if (l.startsWith("**CORRECT:") || l.startsWith("**EXPLANATION:") || l.startsWith("**Q:")) {
                        continue;
                    }
                    const optM = l.match(/^(?:-\s*\[\s*\]\s*|\*\*)?([A-D])[\).:\-]\s*\**\s*(.+)$/i);
                    if (optM) {
                        options.push({
                            key: optM[1].toUpperCase(),
                            text: optM[2].trim()
                        });
                    }
                }

                const cM = it.match(/\*\*CORRECT:\*\*\s*([A-D])/i);
                const correct = cM ? cM[1].toUpperCase().trim() : "A";

                const expM = it.match(/\*\*EXPLANATION:\*\*\s*([\s\S]*)$/i);
                const explanation = expM ? expM[1].trim() : "";

                if (question && options.length > 0) {
                    quizzes.push({
                        id: quizzes.length + 1,
                        title: title || `Quiz ${quizzes.length + 1}`,
                        question,
                        options,
                        correct,
                        explanation
                    });
                }
            }
        }

        return { flashcards, quizzes };
    }

    // -------------------------------------------------------------
    // Utility Matematiche e Conversione LaTeX per Anki
    // -------------------------------------------------------------
    function convertLatexForAnki(text) {
        if (!text) return "";
        let res = text.replace(/\$\$([\s\S]*?)\$\$/g, "\\[$1\\]");
        res = res.replace(/\$([^\$\n]+?)\$/g, "\\($1\\)");
        return res;
    }

    function markdownToSimpleHtml(t) {
        if (!t) return "";
        t = t.replace(/\[\[([^\]|]+)\|([^\]]+)\]\]/g, "$2");
        t = t.replace(/\[\[([^\]]+)\]\]/g, "$1");
        t = t.replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
        t = t.replace(/\*([^*]+)\*/g, "<i>$1</i>");
        t = t.replace(/\n\n/g, "<br><br>");
        t = t.replace(/\n/g, "<br>");
        return t;
    }

    function escapeHtml(str) {
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function shuffleArray(array) {
        for (let i = array.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [array[i], array[j]] = [array[j], array[i]];
        }
    }
})();
