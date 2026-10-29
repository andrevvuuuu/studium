#!/usr/bin/env python3
"""
notify.py — Notifiche del batch: sul Mac (Centro Notifiche) e sul telefono tramite ntfy.

Per il telefono: installa l'app gratuita "ntfy" (iOS/Android) e iscriviti al topic scritto in
.antigravity/notify.json ("ntfy_topic"). Chi conosce il nome del topic può leggere le notifiche,
per questo è un nome casuale; il contenuto è solo il titolo delle note e lo stato del batch.

Uso manuale: python3 notify.py --test
"""

import argparse
import json
import secrets
import subprocess
import sys
import urllib.request
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[1] / "notify.json"


def load_config() -> dict:
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except Exception:
        return {}


def ensure_config() -> dict:
    cfg = load_config()
    if not cfg.get("ntfy_topic"):
        cfg = {"ntfy_server": "https://ntfy.sh", "ntfy_topic": f"antigravity-{secrets.token_hex(8)}",
               "mac": True, "phone": True, **cfg}
        CONFIG.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return cfg


def notify(title: str, message: str, priority: str = "default") -> None:
    """priority: min | low | default | high | urgent (ntfy). Non solleva mai eccezioni."""
    cfg = load_config()
    if cfg.get("mac", True):
        script = f"display notification {json.dumps(message)} with title {json.dumps(title)}"
        try:
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=10, check=False)
        except Exception:
            pass
    if cfg.get("phone", True) and cfg.get("ntfy_topic"):
        payload = json.dumps({"topic": cfg["ntfy_topic"], "title": title, "message": message,
                              "priority": {"min": 1, "low": 2, "default": 3, "high": 4, "urgent": 5}.get(priority, 3),
                              "tags": ["books"]}).encode("utf-8")
        req = urllib.request.Request(cfg.get("ntfy_server", "https://ntfy.sh"), data=payload,
                                     headers={"Content-Type": "application/json"}, method="POST")
        try:
            urllib.request.urlopen(req, timeout=15).read()
        except Exception as e:
            sys.stderr.write(f"[notify] ntfy non raggiunto: {e}\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--show-topic", action="store_true")
    args = ap.parse_args()
    cfg = ensure_config()
    if args.show_topic:
        print(cfg["ntfy_topic"])
    if args.test:
        notify("Antigravity", "Notifica di prova: se la vedi, le notifiche del batch funzionano.")
        print("Inviata.")
