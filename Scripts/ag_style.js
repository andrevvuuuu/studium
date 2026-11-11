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
            z-index: 9999;
        }
        .modal.ag-picker {
            width: min(720px, calc(100vw - 32px));
            max-height: 88vh;
            padding: 24px;
            border-radius: var(--radius-l);
            background: var(--background-primary);
            border: 1px solid var(--background-modifier-border);
            box-shadow: var(--shadow-l);
            display: flex;
            flex-direction: column;
            gap: 20px;
            color: var(--text-normal);
            box-sizing: border-box;
            overflow: hidden;
        }
        .ag-picker-header {
            position: relative;
            display: flex;
            flex-direction: column;
            gap: 8px;
            padding-right: 32px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--background-modifier-border);
        }
        .ag-picker-title-row {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }
        .ag-picker-title {
            font-size: var(--font-ui-large);
            font-weight: var(--font-semibold);
            color: var(--text-normal);
            margin: 0;
            line-height: 1.3;
        }
        .ag-picker-step-chip {
            font-size: var(--font-ui-smaller);
            font-weight: var(--font-semibold);
            padding: 2px 8px;
            border-radius: 999px;
            background: var(--background-modifier-hover);
            color: var(--text-muted);
            border: 1px solid var(--background-modifier-border);
        }
        .ag-picker-subtitle {
            font-size: var(--font-ui-small);
            color: var(--text-muted);
            margin: 0;
            line-height: 1.4;
        }
        .ag-picker-close-btn {
            position: absolute;
            top: 0;
            right: 0;
            width: 28px;
            height: 28px;
            display: grid;
            place-items: center;
            border-radius: var(--radius-m);
            border: 1px solid transparent;
            background: transparent;
            cursor: pointer;
            color: var(--text-muted);
            padding: 0;
            transition: background-color 120ms ease, border-color 120ms ease, color 120ms ease;
        }
        .ag-picker-close-btn:hover {
            background: var(--background-modifier-hover);
            border-color: var(--background-modifier-border-hover);
            color: var(--text-normal);
        }
        .ag-picker-close-btn:focus-visible {
            outline: 2px solid var(--interactive-accent);
            outline-offset: 2px;
        }
        .ag-picker-section {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .ag-picker-section-label {
            font-size: var(--font-ui-smaller);
            font-weight: var(--font-semibold);
            text-transform: uppercase;
            letter-spacing: 0.04em;
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
            padding: 12px 14px;
            gap: 8px;
            border-radius: var(--radius-m);
            border: 1px solid var(--background-modifier-border);
            background: var(--background-secondary);
            cursor: pointer;
            transition: background-color 120ms ease, border-color 120ms ease, box-shadow 120ms ease;
            text-align: left;
            user-select: none;
            box-sizing: border-box;
        }
        .ag-picker-card:hover {
            background: var(--background-modifier-hover);
            border-color: var(--background-modifier-border-hover);
        }
        .ag-picker-card:focus-visible {
            outline: 2px solid var(--interactive-accent);
            outline-offset: 2px;
        }
        .ag-picker-card.is-selected,
        .ag-picker-card[aria-checked="true"] {
            border-color: var(--interactive-accent);
            background: color-mix(in srgb, var(--interactive-accent) 12%, transparent);
            box-shadow: var(--shadow-s);
        }
        .ag-picker-card:disabled,
        .ag-picker-card[aria-disabled="true"] {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .ag-picker-card-icon {
            font-size: 20px;
            line-height: 1.2;
        }
        .ag-picker-card-name {
            font-size: var(--font-ui-medium);
            font-weight: var(--font-semibold);
            color: var(--text-normal);
        }
        .ag-picker-card-desc {
            font-size: var(--font-ui-small);
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
            border-radius: var(--radius-m);
            border: 1px dashed color-mix(in srgb, var(--interactive-accent) 40%, transparent);
            background: var(--background-secondary);
            cursor: pointer;
            transition: background-color 120ms ease, border-color 120ms ease, box-shadow 120ms ease;
            text-align: left;
            user-select: none;
            box-sizing: border-box;
        }
        .ag-picker-card-featured:hover {
            background: var(--background-modifier-hover);
            border-color: var(--interactive-accent);
        }
        .ag-picker-card-featured:focus-visible {
            outline: 2px solid var(--interactive-accent);
            outline-offset: 2px;
        }
        .ag-picker-card-featured.is-selected,
        .ag-picker-card-featured[aria-checked="true"] {
            border: 1px solid var(--interactive-accent);
            background: color-mix(in srgb, var(--interactive-accent) 12%, transparent);
            box-shadow: var(--shadow-s);
        }
        .ag-picker-card-featured:disabled,
        .ag-picker-card-featured[aria-disabled="true"] {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .ag-picker-card-featured .ag-picker-card-icon {
            width: 32px;
            height: 32px;
            border-radius: var(--radius-m);
            background: color-mix(in srgb, var(--interactive-accent) 12%, transparent);
            display: grid;
            place-items: center;
            flex-shrink: 0;
            font-size: 16px;
            line-height: 1;
        }
        .ag-picker-card-featured .ag-picker-card-content {
            flex: 1;
            min-width: 0;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .ag-picker-card-featured .ag-picker-card-name {
            font-size: var(--font-ui-medium);
            font-weight: var(--font-semibold);
            color: var(--interactive-accent);
        }
        .ag-picker-card-featured .ag-picker-card-desc {
            font-size: var(--font-ui-small);
            color: var(--text-muted);
            line-height: 1.3;
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
            height: 32px;
            box-sizing: border-box;
            padding: 0 12px;
            border-radius: var(--radius-m);
            border: 1px solid var(--background-modifier-border);
            background: var(--background-modifier-form-field);
            color: var(--text-normal);
            font-size: var(--font-ui-small);
            font-family: inherit;
            transition: background-color 120ms ease, border-color 120ms ease, box-shadow 120ms ease;
        }
        .ag-picker-input:hover {
            border-color: var(--background-modifier-border-hover);
        }
        .ag-picker-input:focus-visible,
        .ag-picker-input:focus {
            border-color: var(--interactive-accent);
            outline: 2px solid var(--interactive-accent);
            outline-offset: 2px;
        }
        .ag-picker-field-wrap {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .ag-picker-label {
            font-size: var(--font-ui-small);
            font-weight: var(--font-semibold);
            color: var(--text-normal);
        }
        .ag-picker-error {
            color: var(--text-error);
            font-size: var(--font-ui-smaller);
            margin-top: 2px;
        }
        .ag-picker-counter {
            font-size: var(--font-ui-smaller);
            font-weight: var(--font-semibold);
            color: var(--text-muted);
        }
        .ag-picker-notebook-list {
            display: flex;
            flex-direction: column;
            max-height: min(40vh, 320px);
            overflow-y: auto;
            scrollbar-gutter: stable;
            border: 1px solid var(--background-modifier-border);
            border-radius: var(--radius-m);
            padding: 0;
            background: var(--background-secondary);
        }
        .ag-picker-notebook-item {
            display: flex;
            align-items: center;
            gap: 10px;
            min-height: 36px;
            padding: 6px 12px;
            border-bottom: 1px solid var(--background-modifier-border);
            cursor: pointer;
            user-select: none;
            transition: background-color 120ms ease, border-color 120ms ease, box-shadow 120ms ease;
            box-sizing: border-box;
        }
        .ag-picker-notebook-item:last-child {
            border-bottom: none;
        }
        .ag-picker-notebook-item:hover {
            background: var(--background-modifier-hover);
        }
        .ag-picker-notebook-item:focus-visible {
            outline: 2px solid var(--interactive-accent);
            outline-offset: -2px;
        }
        .ag-picker-notebook-item.is-selected,
        .ag-picker-notebook-item[aria-checked="true"] {
            background: color-mix(in srgb, var(--interactive-accent) 12%, transparent);
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
            font-size: var(--font-ui-small);
            font-weight: var(--font-semibold);
            color: var(--text-normal);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .ag-picker-notebook-meta {
            font-size: var(--font-ui-smaller);
            color: var(--text-muted);
        }
        .ag-picker-mono {
            font-family: var(--font-monospace);
            font-size: var(--font-ui-smaller);
            color: var(--text-faint);
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
            height: 32px;
            padding: 0 14px;
            font-size: var(--font-ui-small);
            font-weight: var(--font-semibold);
            border-radius: var(--radius-m);
            border: 1px solid var(--background-modifier-border);
            background: var(--background-secondary);
            color: var(--text-normal);
            cursor: pointer;
            transition: background-color 120ms ease, border-color 120ms ease, box-shadow 120ms ease;
            white-space: nowrap;
            box-sizing: border-box;
        }
        .ag-picker-btn:hover {
            background: var(--background-modifier-hover);
            border-color: var(--background-modifier-border-hover);
        }
        .ag-picker-btn:focus-visible {
            outline: 2px solid var(--interactive-accent);
            outline-offset: 2px;
        }
        .ag-picker-btn:disabled,
        .ag-picker-btn[aria-disabled="true"] {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .ag-picker-btn.mod-cta {
            background: var(--interactive-accent);
            color: var(--text-on-accent);
            border-color: var(--interactive-accent);
        }
        .ag-picker-btn.mod-cta:hover {
            background: var(--interactive-accent-hover);
            border-color: var(--interactive-accent-hover);
        }
        .ag-picker-btn.mod-cta:focus-visible {
            outline: 2px solid var(--interactive-accent);
            outline-offset: 2px;
        }
        .ag-picker-btn.mod-cta:disabled,
        .ag-picker-btn.mod-cta[aria-disabled="true"] {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .ag-picker-empty-state {
            padding: 16px;
            text-align: center;
            font-size: var(--font-ui-small);
            color: var(--text-muted);
        }
        .ag-picker-segmented {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            background: var(--background-secondary);
            padding: 4px;
            border-radius: var(--radius-m);
            border: 1px solid var(--background-modifier-border);
        }
        .ag-picker-segment {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            padding: 8px 10px;
            border-radius: var(--radius-s);
            border: 1px solid transparent;
            background: transparent;
            cursor: pointer;
            color: var(--text-muted);
            transition: background-color 120ms ease, border-color 120ms ease, box-shadow 120ms ease;
        }
        .ag-picker-segment:hover {
            color: var(--text-normal);
            background: var(--background-modifier-hover);
            border-color: var(--background-modifier-border-hover);
        }
        .ag-picker-segment:focus-visible {
            outline: 2px solid var(--interactive-accent);
            outline-offset: 2px;
        }
        .ag-picker-segment.is-selected,
        .ag-picker-segment[aria-checked="true"] {
            background: var(--background-primary);
            color: var(--text-normal);
            border-color: var(--interactive-accent);
            box-shadow: var(--shadow-s);
        }
        .ag-picker-segment:disabled,
        .ag-picker-segment[aria-disabled="true"] {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .ag-picker-seg-title {
            font-size: var(--font-ui-small);
            font-weight: var(--font-semibold);
        }
        .ag-picker-seg-sub {
            font-size: var(--font-ui-smaller);
            color: var(--text-muted);
            margin-top: 2px;
        }
        .ag-picker-actions-row {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .ag-picker-muted-hint {
            font-size: var(--font-ui-small);
            color: var(--text-muted);
        }
        .ag-picker-file-list {
            display: flex;
            flex-direction: column;
            max-height: min(40vh, 320px);
            overflow-y: auto;
            scrollbar-gutter: stable;
            border: 1px solid var(--background-modifier-border);
            border-radius: var(--radius-m);
            padding: 0;
            background: var(--background-secondary);
            margin-top: 4px;
        }
        .ag-picker-file-item {
            display: flex;
            align-items: center;
            gap: 8px;
            min-height: 36px;
            padding: 6px 12px;
            border-bottom: 1px solid var(--background-modifier-border);
            background: var(--background-secondary);
            box-sizing: border-box;
        }
        .ag-picker-file-item:last-child {
            border-bottom: none;
        }
        .ag-picker-file-icon {
            font-size: 16px;
        }
        .ag-picker-file-path {
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-family: var(--font-monospace);
            font-size: var(--font-ui-smaller);
            color: var(--text-faint);
        }
        .ag-picker-file-remove {
            all: unset;
            cursor: pointer;
            color: var(--text-muted);
            padding: 2px 6px;
            border-radius: var(--radius-s);
            font-weight: var(--font-semibold);
            transition: background-color 120ms ease, color 120ms ease;
        }
        .ag-picker-file-remove:hover {
            background: color-mix(in srgb, var(--text-error) 12%, transparent);
            color: var(--text-error);
        }
        .ag-picker-file-remove:focus-visible {
            outline: 2px solid var(--interactive-accent);
            outline-offset: 2px;
        }
        .ag-picker-vault-fallback {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .ag-picker-vault-results {
            margin-top: 4px;
            border: 1px solid var(--background-modifier-border);
            border-radius: var(--radius-m);
            max-height: min(40vh, 320px);
            overflow-y: auto;
            scrollbar-gutter: stable;
            padding: 0;
            background: var(--background-secondary);
        }
        .ag-picker-vault-result-item {
            min-height: 36px;
            display: flex;
            align-items: center;
            padding: 6px 12px;
            font-family: var(--font-monospace);
            font-size: var(--font-ui-smaller);
            color: var(--text-faint);
            cursor: pointer;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            border-bottom: 1px solid var(--background-modifier-border);
            transition: background-color 120ms ease, color 120ms ease;
            box-sizing: border-box;
        }
        .ag-picker-vault-result-item:last-child {
            border-bottom: none;
        }
        .ag-picker-vault-result-item:hover {
            background: var(--background-modifier-hover);
            color: var(--text-normal);
        }
        .ag-picker-vault-result-item:focus-visible {
            outline: 2px solid var(--interactive-accent);
            outline-offset: -2px;
        }
        .ag-picker-info-box {
            display: flex;
            gap: 12px;
            padding: 12px 14px;
            border-radius: var(--radius-m);
            background: color-mix(in srgb, var(--interactive-accent) 12%, transparent);
            border: 1px solid color-mix(in srgb, var(--interactive-accent) 40%, transparent);
            font-size: var(--font-ui-small);
            color: var(--text-normal);
            line-height: 1.4;
        }
        .ag-picker-info-icon {
            font-size: 20px;
        }
        .ag-picker-info-text strong {
            display: block;
            margin-bottom: 2px;
            color: var(--interactive-accent);
        }
        .ag-picker-groups-container {
            display: flex;
            flex-direction: column;
            gap: 16px;
            max-height: 44vh;
            overflow-y: auto;
            scrollbar-gutter: stable;
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
            font-size: var(--font-ui-small);
            cursor: pointer;
            transition: background-color 120ms ease, border-color 120ms ease, box-shadow 120ms ease;
            user-select: none;
            box-sizing: border-box;
        }
        .ag-picker-chip:hover {
            background: var(--background-modifier-hover);
            border-color: var(--background-modifier-border-hover);
        }
        .ag-picker-chip:focus-visible {
            outline: 2px solid var(--interactive-accent);
            outline-offset: 2px;
        }
        .ag-picker-chip.is-selected,
        .ag-picker-chip[aria-checked="true"] {
            border-color: var(--interactive-accent);
            background: color-mix(in srgb, var(--interactive-accent) 12%, transparent);
            color: var(--interactive-accent);
            font-weight: var(--font-semibold);
        }
        .ag-picker-chip:disabled,
        .ag-picker-chip[aria-disabled="true"] {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .ag-picker-footer {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            padding-top: 16px;
            border-top: 1px solid var(--background-modifier-border);
            margin-top: auto;
            position: sticky;
            bottom: 0;
            background: var(--background-primary);
            z-index: 2;
        }
        .ag-picker-summary {
            font-size: var(--font-ui-small);
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
        .ag-picker-skeleton {
            display: flex;
            flex-direction: column;
            justify-content: center;
            gap: 6px;
            min-height: 36px;
            padding: 8px 12px;
            border-bottom: 1px solid var(--background-modifier-border);
            box-sizing: border-box;
        }
        .ag-picker-skeleton:last-child {
            border-bottom: none;
        }
        .ag-picker-skeleton-bar,
        .ag-picker-skeleton > div {
            height: 12px;
            border-radius: var(--radius-s);
            background: var(--background-modifier-hover);
            animation: ag-picker-shimmer 1.2s ease-in-out infinite;
        }
        .ag-picker-skeleton-title,
        .ag-picker-skeleton-bar:first-child,
        .ag-picker-skeleton > div:first-child {
            width: 60%;
        }
        .ag-picker-skeleton-meta,
        .ag-picker-skeleton-bar:last-child,
        .ag-picker-skeleton > div:nth-child(2) {
            width: 35%;
        }
        .ag-picker-sr-only {
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
            border: 0;
        }
        @keyframes ag-picker-shimmer {
            0% {
                opacity: 0.45;
            }
            50% {
                opacity: 0.9;
            }
            100% {
                opacity: 0.45;
            }
        }
        /* Regole Selettore Scelte Tutor (.ag-picker-choice) */
        .ag-picker-choice-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-height: min(48vh, 380px);
            overflow-y: auto;
            scrollbar-gutter: stable;
            padding: 2px;
        }
        .ag-picker-choice-card {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 14px;
            border-radius: var(--radius-m);
            border: 1px solid var(--background-modifier-border);
            background: var(--background-secondary);
            cursor: pointer;
            text-align: left;
            user-select: none;
            box-sizing: border-box;
            transition: background-color 120ms ease, border-color 120ms ease, box-shadow 120ms ease;
        }
        .ag-picker-choice-card:hover {
            background: var(--background-modifier-hover);
            border-color: var(--background-modifier-border-hover);
        }
        .ag-picker-choice-card:focus-visible {
            outline: 2px solid var(--interactive-accent);
            outline-offset: 2px;
        }
        .ag-picker-choice-card.is-selected,
        .ag-picker-choice-card[aria-checked="true"] {
            border-color: var(--interactive-accent);
            background: color-mix(in srgb, var(--interactive-accent) 12%, transparent);
            box-shadow: var(--shadow-s);
        }
        .ag-picker-choice-card:disabled,
        .ag-picker-choice-card[aria-disabled="true"] {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .ag-picker-choice-icon {
            width: 32px;
            height: 32px;
            border-radius: var(--radius-m);
            background: color-mix(in srgb, var(--interactive-accent) 12%, transparent);
            color: var(--interactive-accent);
            display: grid;
            place-items: center;
            flex-shrink: 0;
            font-size: 16px;
            line-height: 1;
        }
        .ag-picker-choice-icon svg {
            width: 18px;
            height: 18px;
            stroke-width: 2;
        }
        .ag-picker-choice-content {
            flex: 1;
            min-width: 0;
            display: flex;
            flex-direction: column;
            gap: 3px;
        }
        .ag-picker-choice-title {
            font-size: var(--font-ui-medium);
            font-weight: var(--font-semibold);
            color: var(--text-normal);
        }
        .ag-picker-choice-desc {
            font-size: var(--font-ui-small);
            color: var(--text-muted);
            line-height: 1.3;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: normal;
        }
        .ag-picker-choice-knowledge-section {
            margin-top: 4px;
        }
        @media (max-width: 600px) {
            .modal.ag-picker {
                padding: 16px;
                width: calc(100vw - 32px);
            }
            .ag-picker-grid {
                grid-template-columns: 1fr;
            }
            .ag-picker-footer {
                flex-direction: column;
                align-items: stretch;
                gap: 12px;
            }
            .ag-picker-footer-buttons {
                flex-direction: column-reverse;
                width: 100%;
                gap: 8px;
            }
            .ag-picker-footer-buttons .ag-picker-btn {
                width: 100%;
            }
        }
        @media (prefers-reduced-motion: reduce) {
            .ag-picker,
            .ag-picker *,
            .ag-picker-skeleton-bar,
            .ag-picker-skeleton > div {
                animation: none !important;
                transition: none !important;
            }
        }
    
    `;
    document.head.appendChild(styleEl);
};
