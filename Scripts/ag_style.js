/**
 * Stile condiviso dell'HUD di Antigravity e della barra del tutor: stesso vetro, stessi colori,
 * stesse animazioni. È una funzione perché Templater registra ogni file di Scripts/ come funzione utente.
 */
module.exports = function injectAgStyle() {
    if (document.getElementById("antigravity-hud-style")) return;
    const styleEl = document.createElement("style");
    styleEl.id = "antigravity-hud-style";
    styleEl.textContent = `
        .ag-hud {
            --ag-surface: color-mix(in srgb, var(--background-primary) 80%, transparent);
            --ag-track: color-mix(in srgb, var(--text-normal) 9%, transparent);
            --ag-done: var(--color-green, #34c759);
            --ag-active: var(--interactive-accent);
            --ag-danger: var(--color-red, #ff3b30);
            position: fixed;
            /* In basso a sinistra, oltre la ribbon delle icone (impostazioni, vault) */
            left: calc(var(--ribbon-width, 44px) + 12px);
            bottom: 16px;
            z-index: var(--layer-notice, 9999);
            width: 372px;
            max-width: calc(100vw - 32px);
            box-sizing: border-box;
            padding: 14px 16px 12px;
            border-radius: 14px;
            border: 1px solid var(--background-modifier-border);
            background: var(--ag-surface);
            -webkit-backdrop-filter: blur(28px) saturate(1.7);
            backdrop-filter: blur(28px) saturate(1.7);
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.12), 0 12px 32px -8px rgba(0, 0, 0, 0.38);
            color: var(--text-normal);
            font-family: var(--font-interface);
            font-size: 13px;
            line-height: 1.4;
            font-variant-numeric: tabular-nums;
            -webkit-user-select: none;
            user-select: none;
            transition: opacity 0.32s cubic-bezier(0.16, 1, 0.3, 1), transform 0.32s cubic-bezier(0.16, 1, 0.3, 1);
            animation: ag-hud-in 0.42s cubic-bezier(0.16, 1, 0.3, 1);
        }
        @keyframes ag-hud-in { from { opacity: 0; transform: translateY(12px) scale(0.98); } }
        .ag-hud-detail, .ag-hud-title { -webkit-user-select: text; user-select: text; }
        .ag-hud-overall { height: 4px; margin: 10px 0 2px; border-radius: 999px; background: var(--ag-track); overflow: hidden; }
        .ag-hud-overall > i { display: block; height: 100%; width: 0; background: var(--ag-done); border-radius: inherit; transition: width 0.5s ease; }
        .ag-hud-note { margin-top: 10px; padding-top: 8px; border-top: 1px solid var(--background-modifier-border); }
        .ag-hud-note .ag-hud-title { font-size: 13px; }
        .ag-hud-note .ag-hud-bar { margin-top: 8px; }
        .ag-hud-head { display: flex; align-items: flex-start; gap: 10px; }
        .ag-hud-heading { flex: 1; min-width: 0; }
        .ag-hud-title {
            font-size: 14px;
            font-weight: 600;
            letter-spacing: -0.01em;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .ag-hud-sub { margin-top: 2px; color: var(--text-muted); font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .ag-hud-clock { color: var(--text-muted); font-size: 12px; padding-top: 2px; }
        .ag-hud-x {
            all: unset;
            width: 22px;
            height: 22px;
            margin: -2px -4px 0 0;
            border-radius: 6px;
            display: grid;
            place-items: center;
            color: var(--text-faint);
            cursor: pointer;
        }
        .ag-hud-x svg { width: 14px; height: 14px; }
        .ag-hud-x:hover { background: var(--background-modifier-hover); color: var(--text-normal); }
        .ag-hud-x:focus-visible, .ag-hud-btn:focus-visible { outline: 2px solid var(--ag-active); outline-offset: 2px; }
        .ag-hud-chips { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
        .ag-hud-chip {
            font-size: 11px;
            padding: 1px 8px;
            border-radius: 999px;
            background: var(--ag-track);
            color: var(--text-muted);
            max-width: 100%;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .ag-hud-bar { display: flex; gap: 3px; height: 6px; margin: 12px 0 8px; }
        .ag-hud-seg { position: relative; min-width: 6px; border-radius: 999px; background: var(--ag-track); overflow: hidden; }
        .ag-hud-seg > i { position: absolute; inset: 0 auto 0 0; width: 0; border-radius: inherit; background: var(--ag-active); transition: width 0.5s ease; }
        .ag-hud-seg.is-done > i { width: 100%; background: var(--ag-done); }
        .ag-hud-seg.is-idle > i {
            width: 100%;
            background: linear-gradient(90deg, transparent, color-mix(in srgb, var(--ag-active) 55%, transparent), transparent);
            animation: ag-hud-sweep 1.6s ease-in-out infinite;
        }
        @keyframes ag-hud-sweep { from { transform: translateX(-100%); } to { transform: translateX(100%); } }
        .ag-hud-now { display: flex; justify-content: space-between; gap: 10px; align-items: baseline; }
        .ag-hud-now b { font-weight: 600; font-size: 13px; }
        .ag-hud-pct { color: var(--text-muted); font-size: 12px; }
        .ag-hud-detail { color: var(--text-muted); font-size: 12px; margin-top: 1px; min-height: 17px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .ag-hud-steps { list-style: none; margin: 10px 0 0; padding: 8px 0 0; border-top: 1px solid var(--background-modifier-border); }
        .ag-hud-steps li { display: flex; align-items: center; gap: 8px; padding: 2px 0; font-size: 12px; color: var(--text-faint); }
        .ag-hud-steps li > span:nth-child(2) { flex: 1; }
        .ag-hud-steps li > span:last-child { color: var(--text-faint); }
        .ag-hud-steps .ag-hud-mark { width: 7px; height: 7px; border-radius: 50%; border: 1.5px solid currentColor; box-sizing: border-box; flex: none; }
        .ag-hud-steps li.is-done { color: var(--text-muted); }
        .ag-hud-steps li.is-done .ag-hud-mark { background: var(--ag-done); border-color: var(--ag-done); }
        .ag-hud-steps li.is-active { color: var(--text-normal); font-weight: 500; }
        .ag-hud-steps li.is-active .ag-hud-mark { background: var(--ag-active); border-color: var(--ag-active); }
        .ag-hud-actions { display: flex; gap: 6px; margin-top: 10px; flex-wrap: wrap; }
        .ag-hud-actions .ag-hud-spacer { flex: 1; }
        .ag-hud-btn { font-size: 12px; padding: 3px 10px; height: auto; border-radius: 7px; }
        .ag-hud .ag-hud-btn.is-destructive { background: transparent; box-shadow: none; border: 0; color: var(--ag-danger); font-weight: 500; }
        .ag-hud .ag-hud-btn.is-destructive:hover { background: color-mix(in srgb, var(--ag-danger) 12%, transparent); }
        .ag-hud .ag-hud-btn:disabled { opacity: 0.55; cursor: default; }
        .ag-hud-stats { display: flex; gap: 12px; margin-top: 8px; font-size: 12px; color: var(--text-muted); }
        .ag-hud-stats strong { color: var(--text-normal); font-weight: 600; }
        .ag-hud.is-completed .ag-hud-seg > i { width: 100% !important; background: var(--ag-done); animation: none; transition: none; }
        .ag-hud.is-error .ag-hud-seg.is-active > i, .ag-hud.is-error .ag-hud-seg.is-idle > i { width: 100%; background: var(--ag-danger); animation: none; }
        .ag-hud.is-error .ag-hud-now b { color: var(--ag-danger); }
        .ag-hud.is-cancelled .ag-hud-seg > i { animation: none; opacity: 0.4; }
        .ag-hud.is-leaving { opacity: 0; transform: translateY(12px) scale(0.98); pointer-events: none; }
        @media (prefers-reduced-motion: reduce) {
            .ag-hud, .ag-hud * { animation: none !important; transition: none !important; }
            .ag-hud-seg.is-idle > i { background: color-mix(in srgb, var(--ag-active) 40%, transparent); }
        }
    
        /* Barra del tutor delle lezioni (Scripts/tutor_bar.js): stesso angolo e stesso vetro dell'HUD */
        .ag-tutor {
            --ag-surface: color-mix(in srgb, var(--background-primary) 80%, transparent);
            --ag-track: color-mix(in srgb, var(--text-normal) 9%, transparent);
            --ag-done: var(--color-green, #34c759);
            --ag-active: var(--interactive-accent);
            --ag-danger: var(--color-red, #ff3b30);
            position: fixed;
            /* In alto a destra, un po' sotto la barra delle schede */
            top: calc(var(--header-height, 40px) + 24px);
            right: 16px;
            z-index: var(--layer-notice, 9999);
            max-width: calc(100vw - 32px);
            font-family: var(--font-interface);
            font-size: 13px;
            line-height: 1.4;
            color: var(--text-normal);
            animation: ag-hud-in 0.42s cubic-bezier(0.16, 1, 0.3, 1);
        }
        body:has(.ag-hud) .ag-tutor { display: none; }
        .ag-tutor-pill, .ag-tutor-card {
            box-sizing: border-box;
            border: 1px solid var(--background-modifier-border);
            background: var(--ag-surface);
            -webkit-backdrop-filter: blur(28px) saturate(1.7);
            backdrop-filter: blur(28px) saturate(1.7);
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.12), 0 12px 32px -8px rgba(0, 0, 0, 0.38);
        }
        .ag-tutor-pill {
            display: block;
            min-height: 32px;
            padding: 6px 14px;
            border-radius: 999px;
            color: var(--text-normal);
            font: inherit;
            cursor: pointer;
        }
        .ag-tutor-lavoro .ag-tutor-pill, .ag-tutor-recupero .ag-tutor-pill { color: var(--ag-active); font-weight: 600; }
        .ag-tutor.is-open .ag-tutor-pill { display: none; }
        .ag-tutor-pill { margin-left: auto; }
        .ag-tutor.in-sidebar .ag-tutor-pill {
            width: 100%;
            height: auto;
            white-space: normal;
            text-align: center;
            line-height: 1.3;
        }
        .ag-tutor-card .ag-tutor-min { font-size: 16px; line-height: 1; }
        .ag-tutor-card {
            width: 372px;
            max-width: 100%;
            max-height: min(70vh, 640px);
            overflow-y: auto;
            padding: 14px 16px 12px;
            border-radius: 14px;
        }
        .ag-tutor-card .ag-hud-x { font-size: 16px; line-height: 1; }
        .ag-tutor-problem { margin-top: 8px; color: var(--text-muted); font-size: 12px; }
        .ag-tutor-lesson { margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--background-modifier-border); }
        .ag-tutor-lesson-title { font-weight: 600; }
        .ag-tutor-item { margin-top: 8px; }
        .ag-tutor-status { display: inline-block; margin-right: 6px; font-size: 11px; font-weight: 600; color: var(--ag-active); }
        .ag-tutor-da_completare .ag-tutor-status { color: var(--text-accent); }
        .ag-tutor-coperto .ag-tutor-status { color: var(--ag-done); }
        .ag-tutor-reason { margin-top: 2px; color: var(--text-muted); font-size: 12px; -webkit-user-select: text; user-select: text; }
        .ag-tutor-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
        .ag-tutor-actions button { min-height: 28px; }
        .ag-tutor-more { background: transparent; box-shadow: none; color: var(--text-muted); }
        .ag-tutor-foot { margin-top: 12px; padding-top: 8px; border-top: 1px solid var(--background-modifier-border); color: var(--text-muted); font-size: 12px; }
    `;
    document.head.appendChild(styleEl);
};
