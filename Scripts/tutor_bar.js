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
    // Un clic solo: il secondo partirebbe mentre il primo prepara la config e lancerebbe un doppione
    document.querySelectorAll(".ag-tutor-actions button").forEach(b => { b.disabled = true; });
    if (button) button.textContent = "Avvio…";
    try {
        const menu = require(path.join(vaultBasePath, "Scripts", "antigravity_menu.js"));
        if (kind === "create") {
            menu.launchBatch(app, vaultBasePath, await prepare(vaultBasePath, ["--batch-config", lesson.course, lesson.date]));
        } else {
            for (const it of lesson.items.filter(i => i.status === "da_completare")) {
                const job = await prepare(vaultBasePath, ["--edit-config", lesson.course, lesson.date, it.note]);
                menu.launchJob(app, vaultBasePath, job);
                break; // una modifica alla volta: la pipeline di Antigravity lavora su un job per volta
            }
        }
    } catch (e) {
        notice(`Tutor: ${e.message}`);
        document.querySelectorAll(".ag-tutor-actions button").forEach(b => { b.disabled = false; });
    }
}

/**
 * Posizione: nella barra laterale sinistra, in alto a destra subito sotto le sue schede (la pillola finisce al
 * bordo destro della barra laterale, la scheda aperta parte dallo stesso punto e si allarga sopra la nota).
 * Con la barra laterale chiusa resta in alto a destra della finestra (CSS).
 */
function place(root) {
    const side = document.querySelector(".workspace-split.mod-left-split");
    const rect = side && side.getBoundingClientRect();
    if (!rect || rect.width < 120) {
        root.style.removeProperty("top");
        root.style.removeProperty("left");
        root.style.removeProperty("right");
        return;
    }
    const header = side.querySelector(".workspace-tab-header-container");
    const top = (header ? header.getBoundingClientRect().bottom : rect.top + 40) + 20;
    // Con la scheda aperta la pillola è nascosta: si usa la larghezza misurata quando era visibile
    const pill = root.querySelector(".ag-tutor-pill");
    if (pill && pill.offsetWidth) window._agTutorPillWidth = pill.offsetWidth;
    const pillWidth = window._agTutorPillWidth || 160;
    const left = Math.max(8, rect.right - 12 - pillWidth);
    root.style.top = `${Math.round(top)}px`;
    root.style.left = `${Math.round(left)}px`;
    root.style.right = "auto";
}

function watchPlacement(root) {
    const again = () => { if (document.body.contains(root)) place(root); };
    // La barra si ridisegna a ogni cambio di stato: un solo osservatore alla volta
    window._agTutorPlacement?.disconnect();
    window.removeEventListener("resize", window._agTutorResize || (() => {}));
    window._agTutorResize = again;
    window.addEventListener("resize", again);
    const side = document.querySelector(".workspace-split.mod-left-split");
    if (side && typeof ResizeObserver !== "undefined") {
        window._agTutorPlacement = new ResizeObserver(again);
        window._agTutorPlacement.observe(side);
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
