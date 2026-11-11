/**
 * Stile condiviso dell'HUD di Antigravity e della barra del tutor: stesso vetro, stessi colori,
 * stesse animazioni. È una funzione perché Templater registra ogni file di Scripts/ come funzione utente.
 */
module.exports = function injectAgStyle() {
    let styleEl = document.getElementById("antigravity-hud-style");
    if (!styleEl) {
        styleEl = document.createElement("style");
        styleEl.id = "antigravity-hud-style";
        document.head.appendChild(styleEl);
    }
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

        /* Selettori Interattivi Antigravity: Fonti e Materie (.ag-picker) */
        .ag-picker-backdrop {
            z-index: var(--layer-modal, 9999);
        }
        .modal.ag-picker {
            width: min(720px, 92vw);
            max-height: 88vh;
            padding: 24px;
            border-radius: var(--radius-l, 12px);
            background: var(--background-primary);
            border: 1px solid var(--background-modifier-border);
            box-shadow: 0 20px 48px rgba(0, 0, 0, 0.4);
            display: flex;
            flex-direction: column;
            gap: 16px;
            color: var(--text-normal);
            font-family: var(--font-interface);
            box-sizing: border-box;
            overflow: hidden;
        }
        .ag-picker-header {
            position: relative;
            display: flex;
            flex-direction: column;
            gap: 4px;
            padding-right: 32px;
        }
        .ag-picker-title-row {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }
        .ag-picker-title {
            font-size: 18px;
            font-weight: 600;
            color: var(--text-normal);
            margin: 0;
            line-height: 1.3;
        }
        .ag-picker-step-chip {
            font-size: 11px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 999px;
            background: color-mix(in srgb, var(--interactive-accent) 15%, transparent);
            color: var(--interactive-accent);
            border: 1px solid color-mix(in srgb, var(--interactive-accent) 30%, transparent);
        }
        .ag-picker-subtitle {
            font-size: 12px;
            color: var(--text-muted);
            margin: 0;
            line-height: 1.4;
        }
        .ag-picker-close-btn {
            position: absolute;
            top: -2px;
            right: -4px;
            width: 28px;
            height: 28px;
            display: grid;
            place-items: center;
            border-radius: var(--radius-m, 6px);
            cursor: pointer;
            color: var(--text-muted);
            transition: background 120ms ease, color 120ms ease;
        }
        .ag-picker-close-btn:hover {
            background: var(--background-modifier-hover);
            color: var(--text-normal);
        }
        .ag-picker-section {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .ag-picker-section-label {
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: var(--text-muted);
        }
        .ag-picker-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
            gap: 8px;
        }
        .ag-picker-card {
            position: relative;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            padding: 10px 12px;
            gap: 4px;
            border-radius: var(--radius-m, 8px);
            border: 1px solid var(--background-modifier-border);
            background: var(--background-secondary);
            cursor: pointer;
            transition: border-color 120ms ease, background 120ms ease, box-shadow 120ms ease;
            outline: none;
            text-align: left;
            user-select: none;
        }
        .ag-picker-card:hover {
            background: var(--background-modifier-hover);
            border-color: var(--background-modifier-border-hover);
        }
        .ag-picker-card:focus-visible {
            outline: 2px solid var(--interactive-accent);
            outline-offset: 1px;
        }
        .ag-picker-card.is-selected {
            border-color: var(--interactive-accent);
            background: color-mix(in srgb, var(--interactive-accent) 12%, var(--background-secondary));
            box-shadow: 0 0 0 1px var(--interactive-accent);
        }
        .ag-picker-card-icon {
            font-size: 20px;
            line-height: 1.2;
        }
        .ag-picker-card-name {
            font-size: 13px;
            font-weight: 600;
            color: var(--text-normal);
        }
        .ag-picker-card-desc {
            font-size: 11px;
            color: var(--text-muted);
            line-height: 1.3;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
        .ag-picker-card-featured {
            display: flex;
            flex-direction: row;
            align-items: center;
            gap: 12px;
            padding: 12px 14px;
            border-radius: var(--radius-m, 8px);
            background: color-mix(in srgb, var(--interactive-accent) 8%, var(--background-secondary));
            border: 1px solid color-mix(in srgb, var(--interactive-accent) 40%, var(--background-modifier-border));
            cursor: pointer;
            transition: all 120ms ease;
        }
        .ag-picker-card-featured:hover {
            background: color-mix(in srgb, var(--interactive-accent) 15%, var(--background-secondary));
            border-color: var(--interactive-accent);
        }
        .ag-picker-card-featured:focus-visible {
            outline: 2px solid var(--interactive-accent);
            outline-offset: 1px;
        }
        .ag-picker-card-featured .ag-picker-card-icon {
            font-size: 24px;
        }
        .ag-picker-card-featured .ag-picker-card-content {
            flex: 1;
        }
        .ag-picker-card-featured .ag-picker-card-name {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-accent, var(--interactive-accent));
        }
        .ag-picker-card-featured .ag-picker-card-desc {
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 2px;
        }
        .ag-picker-contextual {
            display: flex;
            flex-direction: column;
            gap: 12px;
            min-height: 150px;
            max-height: 38vh;
            overflow-y: auto;
            padding: 2px;
        }
        .ag-picker-search-wrap {
            position: relative;
            width: 100%;
        }
        .ag-picker-input {
            width: 100%;
            box-sizing: border-box;
            padding: 8px 12px;
            border-radius: var(--radius-m, 6px);
            border: 1px solid var(--background-modifier-border);
            background: var(--background-secondary);
            color: var(--text-normal);
            font-size: 13px;
            outline: none;
            transition: border-color 120ms ease, box-shadow 120ms ease;
        }
        .ag-picker-input:focus {
            border-color: var(--interactive-accent);
            box-shadow: 0 0 0 2px color-mix(in srgb, var(--interactive-accent) 25%, transparent);
        }
        .ag-picker-field-wrap {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .ag-picker-label {
            font-size: 12px;
            font-weight: 500;
            color: var(--text-normal);
        }
        .ag-picker-error {
            color: var(--color-red, #ff3b30);
            font-size: 11px;
            margin-top: 2px;
        }
        .ag-picker-counter {
            font-size: 11px;
            font-weight: 500;
            color: var(--text-muted);
        }
        .ag-picker-notebook-list {
            display: flex;
            flex-direction: column;
            gap: 4px;
            max-height: 180px;
            overflow-y: auto;
            border: 1px solid var(--background-modifier-border);
            border-radius: var(--radius-m, 6px);
            padding: 4px;
            background: var(--background-secondary);
        }
        .ag-picker-notebook-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 6px 10px;
            border-radius: var(--radius-s, 4px);
            cursor: pointer;
            user-select: none;
            transition: background 100ms ease;
            outline: none;
        }
        .ag-picker-notebook-item:hover {
            background: var(--background-modifier-hover);
        }
        .ag-picker-notebook-item:focus-visible {
            outline: 2px solid var(--interactive-accent);
        }
        .ag-picker-notebook-item.is-selected {
            background: color-mix(in srgb, var(--interactive-accent) 15%, transparent);
        }
        .ag-picker-checkbox {
            width: 16px;
            height: 16px;
            accent-color: var(--interactive-accent);
            cursor: pointer;
            margin: 0;
        }
        .ag-picker-notebook-info {
            flex: 1;
            min-width: 0;
        }
        .ag-picker-notebook-title {
            font-size: 13px;
            font-weight: 500;
            color: var(--text-normal);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .ag-picker-notebook-meta {
            font-size: 11px;
            color: var(--text-muted);
        }
        .ag-picker-mono {
            font-family: var(--font-monospace, monospace);
            font-size: 10px;
            opacity: 0.85;
        }
        .ag-picker-manual-row {
            display: flex;
            gap: 8px;
            align-items: center;
        }
        .ag-picker-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            padding: 6px 14px;
            font-size: 13px;
            font-weight: 500;
            border-radius: var(--radius-m, 6px);
            border: 1px solid var(--background-modifier-border);
            background: var(--background-secondary);
            color: var(--text-normal);
            cursor: pointer;
            transition: background 120ms ease, border-color 120ms ease;
            white-space: nowrap;
        }
        .ag-picker-btn:hover {
            background: var(--background-modifier-hover);
        }
        .ag-picker-btn:focus-visible {
            outline: 2px solid var(--interactive-accent);
            outline-offset: 1px;
        }
        .ag-picker-btn.mod-cta {
            background: var(--interactive-accent);
            color: var(--text-on-accent, #ffffff);
            border-color: var(--interactive-accent);
        }
        .ag-picker-btn.mod-cta:hover {
            background: var(--interactive-accent-hover, var(--interactive-accent));
        }
        .ag-picker-btn:disabled {
            opacity: 0.45;
            cursor: not-allowed;
        }
        .ag-picker-empty-state {
            padding: 16px;
            text-align: center;
            font-size: 12px;
            color: var(--text-muted);
        }
        .ag-picker-segmented {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 6px;
            background: var(--background-secondary);
            padding: 4px;
            border-radius: var(--radius-m, 8px);
            border: 1px solid var(--background-modifier-border);
        }
        .ag-picker-segment {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            padding: 8px 10px;
            border-radius: var(--radius-s, 6px);
            border: 1px solid transparent;
            background: transparent;
            cursor: pointer;
            color: var(--text-muted);
            transition: all 120ms ease;
            outline: none;
        }
        .ag-picker-segment:hover {
            color: var(--text-normal);
            background: var(--background-modifier-hover);
        }
        .ag-picker-segment:focus-visible {
            outline: 2px solid var(--interactive-accent);
        }
        .ag-picker-segment.is-selected {
            background: var(--background-primary);
            color: var(--text-normal);
            border-color: var(--background-modifier-border);
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
        }
        .ag-picker-seg-title {
            font-size: 12px;
            font-weight: 600;
        }
        .ag-picker-seg-sub {
            font-size: 10px;
            color: var(--text-muted);
            margin-top: 2px;
        }
        .ag-picker-actions-row {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .ag-picker-muted-hint {
            font-size: 12px;
            color: var(--text-muted);
        }
        .ag-picker-file-list {
            display: flex;
            flex-direction: column;
            gap: 4px;
            max-height: 120px;
            overflow-y: auto;
            margin-top: 4px;
        }
        .ag-picker-file-item {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 5px 10px;
            background: var(--background-secondary);
            border: 1px solid var(--background-modifier-border);
            border-radius: var(--radius-s, 6px);
            font-size: 12px;
        }
        .ag-picker-file-path {
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .ag-picker-file-remove {
            all: unset;
            cursor: pointer;
            color: var(--text-muted);
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 600;
        }
        .ag-picker-file-remove:hover {
            background: color-mix(in srgb, var(--color-red, #ff3b30) 15%, transparent);
            color: var(--color-red, #ff3b30);
        }
        .ag-picker-vault-results {
            margin-top: 4px;
            border: 1px solid var(--background-modifier-border);
            border-radius: var(--radius-m, 6px);
            max-height: 120px;
            overflow-y: auto;
            background: var(--background-secondary);
        }
        .ag-picker-vault-result-item {
            padding: 6px 10px;
            font-size: 12px;
            cursor: pointer;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            transition: background 100ms ease;
        }
        .ag-picker-vault-result-item:hover {
            background: var(--background-modifier-hover);
        }
        .ag-picker-info-box {
            display: flex;
            gap: 12px;
            padding: 12px 14px;
            border-radius: var(--radius-m, 8px);
            background: color-mix(in srgb, var(--interactive-accent) 8%, var(--background-secondary));
            border: 1px solid color-mix(in srgb, var(--interactive-accent) 25%, var(--background-modifier-border));
            font-size: 12px;
            color: var(--text-normal);
            line-height: 1.4;
        }
        .ag-picker-info-icon {
            font-size: 20px;
        }
        .ag-picker-info-text strong {
            display: block;
            margin-bottom: 2px;
            color: var(--text-accent, var(--interactive-accent));
        }
        .ag-picker-groups-container {
            display: flex;
            flex-direction: column;
            gap: 14px;
            max-height: 44vh;
            overflow-y: auto;
            padding: 2px;
        }
        .ag-picker-group {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .ag-picker-chips-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        .ag-picker-chip {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            border-radius: 999px;
            border: 1px solid var(--background-modifier-border);
            background: var(--background-secondary);
            color: var(--text-normal);
            font-size: 12px;
            cursor: pointer;
            transition: all 120ms ease;
            user-select: none;
            outline: none;
        }
        .ag-picker-chip:hover {
            background: var(--background-modifier-hover);
            border-color: var(--background-modifier-border-hover);
        }
        .ag-picker-chip:focus-visible {
            outline: 2px solid var(--interactive-accent);
            outline-offset: 1px;
        }
        .ag-picker-chip.is-selected {
            border-color: var(--interactive-accent);
            background: color-mix(in srgb, var(--interactive-accent) 15%, transparent);
            color: var(--interactive-accent);
            font-weight: 500;
        }
        .ag-picker-footer {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            padding-top: 12px;
            border-top: 1px solid var(--background-modifier-border);
            margin-top: auto;
        }
        .ag-picker-summary {
            font-size: 12px;
            color: var(--text-muted);
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .ag-picker-footer-buttons {
            display: flex;
            gap: 8px;
            align-items: center;
        }
        @media (prefers-reduced-motion: reduce) {
            .ag-picker, .ag-picker * {
                animation: none !important;
                transition: none !important;
            }
        }
    
    `;
    document.head.appendChild(styleEl);
};
