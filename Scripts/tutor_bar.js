/**
 * tutor_bar.js — Barra del tutor delle lezioni, nello stile dell'HUD di Antigravity.
 *
 * Legge .antigravity/tutor/state.json (scritto da .antigravity/tools/tutor.py) e propone le note dei concetti
 * introdotti nelle ultime lezioni. `view` è la logica pura (testata in Scripts/tests/), `render` il DOM.
 * La barra propone e basta: crea solo quando si preme un pulsante.
 */
const fs = require("fs");
const path = require("path");
const child_process = require("child_process");

const WEEKDAYS = ["domenica", "lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato"];
const MONTHS = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"];
const EXAM_DAYS = 30;
const ROOT_ID = "ag-tutor";

const dayDiff = (from, to) => Math.round((Date.parse(to + "T00:00:00Z") - Date.parse(from + "T00:00:00Z")) / 86400000);
const longDate = (iso) => { const d = new Date(iso + "T00:00:00Z"); return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`; };
const weekday = (iso) => WEEKDAYS[new Date(iso + "T00:00:00Z").getUTCDay()];
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;

/** Cosa mostrare, dallo stato del tutor: nessun DOM, nessun file. */
function view(state, today) {
    if (!state || !Array.isArray(state.courses)) return { mode: "loading", pill: "Tutor · aggiorno i diari…", lessons: [], problems: [], foot: "" };
    const lessons = [];
    let toCreate = 0, toComplete = 0;
    for (const c of state.courses) {
        for (const l of c.lessons || []) {
            const open = (l.items || []).filter(it => it.status !== "coperto");
            if (!open.length) continue;
            toCreate += open.filter(it => it.status === "da_creare").length;
            toComplete += open.filter(it => it.status === "da_completare").length;
            lessons.push({ course: c.id, nome: c.nome, date: l.date, title: `${c.nome} · lezione del ${longDate(l.date)}`,
                items: open, hidden: l.items.length - open.length, all: l.items });
        }
    }
    lessons.sort((a, b) => a.date.localeCompare(b.date));
    const problems = state.courses.filter(c => c.errore).map(c => `${c.nome}: ${c.errore}`);

    const foot = [];
    for (const c of state.courses) for (const e of c.esami || []) {
        const days = dayDiff(today, e.data);
        if (days >= 0 && days <= EXAM_DAYS) foot.push(`${e.nome} (${c.nome}) tra ${plural(days, "giorno", "giorni")}`);
    }
    for (const c of state.courses) if ((c.previsione || []).length)
        foot.push(`Prossime lezioni di ${c.nome} (programma dell'anno scorso): ${c.previsione.slice(0, 3).map(t => t.split(/[.:;]/)[0].trim()).join(" · ")}`);

    let mode, pill;
    if (!lessons.length) {
        mode = "al_passo";
        const next = state.courses.filter(c => c.prossima_lezione).sort((a, b) => (a.prossima_lezione.data + a.prossima_lezione.ora).localeCompare(b.prossima_lezione.data + b.prossima_lezione.ora))[0];
        pill = "Vault al passo con le lezioni" + (next ? `. Prossima: ${next.nome}, ${weekday(next.prossima_lezione.data)} ${next.prossima_lezione.ora}` : "");
    } else if (state.recupero) {
        mode = "recupero";
        pill = `Recupero: ${toCreate} da creare, ${toComplete} da completare`;
    } else {
        mode = "lavoro";
        pill = `Tutor · ${plural(toCreate, "nota", "note")} da creare` + (toComplete ? ` · ${toComplete} da completare` : "");
    }
    return { mode, pill, lessons, problems, foot: foot.join(" · ") };
}

// -----------------------------------------------------------------------------
// DOM
// -----------------------------------------------------------------------------

function notice(msg) {
    try { const { Notice } = require("obsidian"); new Notice(msg, 6000); } catch (_) { console.log("[tutor]", msg); }
}

function macPathEnv() {
    const extra = [path.join(process.env.HOME || "", ".local/bin"), "/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin"];
    return Object.assign({}, process.env, { PATH: extra.join(":") + ":" + (process.env.PATH || "") });
}

/** tutor.py --batch-config / --edit-config: stampa il percorso della config pronta per il menu di Antigravity. */
function prepare(vaultBasePath, args) {
    return new Promise((resolve, reject) => {
        child_process.execFile("python3", [path.join(vaultBasePath, ".antigravity", "tools", "tutor.py"), ...args],
            { cwd: vaultBasePath, env: macPathEnv(), timeout: 60000 }, (err, stdout, stderr) => {
                if (err) reject(new Error((stderr || err.message).trim().split("\n").pop()));
                else resolve(JSON.parse(fs.readFileSync(stdout.trim().split("\n").pop(), "utf8")));
            });
    });
}

async function act(app, vaultBasePath, kind, lesson, button) {
    const buttons = () => document.querySelectorAll(".ag-tutor-actions button");
    const tp = window._agTutorTp;
    if (!tp) {
        notice("Tutor: premi Cmd+Alt+T e riprova");
        return;
    }
    // Un clic solo: il secondo partirebbe mentre il primo prepara la config e lancerebbe un doppione
    buttons().forEach(b => { b.disabled = true; });
    const label = button ? button.textContent : "";
    if (button) button.textContent = "Preparo…";
    try {
        const menu = require(path.join(vaultBasePath, "Scripts", "antigravity_menu.js"));
        // Il menu di Antigravity, già compilato con la lezione: fonti, conoscenza e istruzioni le scegli tu
        if (kind === "create") {
            const cfg = await prepare(vaultBasePath, ["--batch-config", lesson.course, lesson.date]);
            await menu.runTutorFlow(tp, app, vaultBasePath, { kind: "create", date: lesson.date, cfg });
        } else {
            const todo = lesson.items.filter(i => i.status === "da_completare");
            const it = todo.length > 1
                ? await tp.system.suggester(todo.map(i => `🛠️ ${i.note}: ${i.missing || i.concept}`), todo, false, "Quale nota completare?")
                : todo[0];
            if (it) {
                const job = await prepare(vaultBasePath, ["--edit-config", lesson.course, lesson.date, it.note]);
                await menu.runTutorFlow(tp, app, vaultBasePath, { kind: "edit", date: lesson.date, job });
            }
        }
    } catch (e) {
        notice(`Tutor: ${e.message}`);
    } finally {
        // Se il menu è stato annullato i pulsanti tornano usabili; se un job è partito la barra si ridisegna da sola
        buttons().forEach(b => { b.disabled = false; });
        if (button) button.textContent = label;
    }
}

/**
 * Posizione: nella barra laterale destra, nel riquadro in basso (Collegamenti) subito sotto la sua intestazione,
 * allineata al bordo destro. La scheda aperta si allarga verso sinistra sopra la nota e, se sotto non c'è spazio,
 * sale fino a stare nella finestra. Con la barra laterale chiusa resta in alto a destra della finestra (CSS).
 */
function place(root) {
    const side = document.querySelector(".workspace-split.mod-right-split");
    const rect = side && side.getBoundingClientRect();
    if (!rect || rect.width < 120) {
        for (const k of ["top", "left", "right", "max-width"]) root.style.removeProperty(k);
        root.classList.remove("in-sidebar");
        return;
    }
    const panes = [...side.querySelectorAll(":scope .workspace-tabs")].filter(p => p.offsetHeight > 0)
        .sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
    const lower = panes.length > 1 ? panes[panes.length - 1].getBoundingClientRect() : null;
    let top = lower ? lower.top + 56 : rect.bottom - 120;
    const height = root.offsetHeight || 34;
    top = Math.max(rect.top + 12, Math.min(top, window.innerHeight - 12 - height));
    const open = root.classList.contains("is-open");
    root.style.top = `${Math.round(top)}px`;
    root.style.right = `${Math.round(Math.max(8, window.innerWidth - rect.right + 12))}px`;
    // Chiusa, la pillola occupa la larghezza della barra laterale con la scritta centrata (va a capo se serve);
    // aperta, la scheda resta attaccata al bordo destro e si allarga verso sinistra sopra la nota
    root.style.left = open ? "auto" : `${Math.round(rect.left + 12)}px`;
    root.style.maxWidth = "";
    root.classList.toggle("in-sidebar", !open);
}

function watchPlacement(root) {
    const again = () => { if (document.body.contains(root)) place(root); };
    // La barra si ridisegna a ogni cambio di stato: un solo osservatore alla volta
    window._agTutorPlacement?.disconnect();
    window.removeEventListener("resize", window._agTutorResize || (() => {}));
    window._agTutorResize = again;
    window.addEventListener("resize", again);
    const side = document.querySelector(".workspace-split.mod-right-split");
    if (side && typeof ResizeObserver !== "undefined") {
        window._agTutorPlacement = new ResizeObserver(again);
        window._agTutorPlacement.observe(side);
        side.querySelectorAll(".workspace-tabs").forEach(p => window._agTutorPlacement.observe(p));
    }
}

const hiddenToday = (today) => { try { return localStorage.getItem("ag-tutor-hidden") === today; } catch (_) { return false; } };

function el(tag, cls, text) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
}

function render(app, vaultBasePath) {
    require(path.join(vaultBasePath, "Scripts", "ag_style.js"))();
    const today = new Date().toLocaleDateString("sv-SE");
    document.getElementById(ROOT_ID)?.remove();
    if (hiddenToday(today)) return;
    let state = null;
    try { state = JSON.parse(fs.readFileSync(path.join(vaultBasePath, ".antigravity", "tutor", "state.json"), "utf8")); } catch (_) {}
    const v = view(state, today);

    const root = el("div", "ag-tutor ag-tutor-" + v.mode);
    root.id = ROOT_ID;
    const pill = el("button", "ag-tutor-pill", v.pill);
    pill.type = "button";
    root.appendChild(pill);
    const card = el("div", "ag-tutor-card");
    // Aperta o ridotta a pillola: la scelta resta anche quando la barra si ridisegna
    const setOpen = (open) => {
        card.hidden = !open;
        root.classList.toggle("is-open", open);
        try { localStorage.setItem("ag-tutor-open", open ? "1" : "0"); } catch (_) {}
        place(root);
    };
    let startOpen = false;
    try { startOpen = localStorage.getItem("ag-tutor-open") === "1"; } catch (_) {}
    pill.addEventListener("click", () => setOpen(true));

    const head = el("div", "ag-hud-head");
    head.appendChild(el("div", "ag-hud-title ag-hud-heading", v.mode === "recupero" ? "Recupero delle lezioni" : "Tutor delle lezioni"));
    const close = el("button", "ag-hud-x");
    close.type = "button";
    close.setAttribute("aria-label", "Nascondi fino a domani");
    close.textContent = "×";
    close.addEventListener("click", () => { try { localStorage.setItem("ag-tutor-hidden", today); } catch (_) {} root.remove(); });
    const minimize = el("button", "ag-hud-x ag-tutor-min");
    minimize.type = "button";
    minimize.setAttribute("aria-label", "Riduci a pillola");
    minimize.title = "Riduci";
    minimize.textContent = "–";
    minimize.addEventListener("click", () => setOpen(false));
    head.appendChild(minimize);
    head.appendChild(close);
    card.appendChild(head);

    for (const p of v.problems) card.appendChild(el("div", "ag-tutor-problem", p));
    for (const l of v.lessons) {
        const box = el("div", "ag-tutor-lesson");
        box.appendChild(el("div", "ag-tutor-lesson-title", l.title));
        const list = el("div", "ag-tutor-items");
        const fill = (items) => {
            list.replaceChildren();
            for (const it of items) {
                const row = el("div", "ag-tutor-item ag-tutor-" + it.status);
                const label = it.status === "da_creare" ? "Da creare" : it.status === "da_completare" ? "Da completare" : "Coperto";
                row.appendChild(el("span", "ag-tutor-status", label));
                row.appendChild(el("span", "ag-tutor-name", it.title || it.note || it.concept));
                row.appendChild(el("div", "ag-tutor-reason", it.status === "da_completare" && it.missing ? `${it.reason} Manca: ${it.missing}` : it.reason));
                list.appendChild(row);
            }
        };
        fill(l.items);
        box.appendChild(list);
        const actions = el("div", "ag-tutor-actions");
        const nCreate = l.items.filter(i => i.status === "da_creare").length;
        const nComplete = l.items.filter(i => i.status === "da_completare").length;
        if (nCreate) {
            const b = el("button", "mod-cta", `Crea ${nCreate === 1 ? "1 nota" : nCreate + " note"}`);
            b.addEventListener("click", () => act(app, vaultBasePath, "create", l, b));
            actions.appendChild(b);
        }
        if (nComplete) {
            const b = el("button", "", `Completa ${nComplete === 1 ? "1 nota" : nComplete + " note"}`);
            b.addEventListener("click", () => act(app, vaultBasePath, "complete", l, b));
            actions.appendChild(b);
        }
        if (l.hidden) {
            const b = el("button", "ag-tutor-more", "mostra tutto");
            b.addEventListener("click", () => { fill(l.all); b.remove(); });
            actions.appendChild(b);
        }
        box.appendChild(actions);
        card.appendChild(box);
    }
    if (v.foot) card.appendChild(el("div", "ag-tutor-foot", v.foot));
    root.appendChild(card);
    document.body.appendChild(root);
    setOpen(startOpen);
    watchPlacement(root);
}

module.exports = render;
module.exports.view = view;
