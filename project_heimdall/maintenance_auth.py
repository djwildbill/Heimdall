#!/usr/bin/env python3
"""Password-protected maintenance control for Project Odin Heimdall/Josh.

Binds to localhost only. The public control-center UI can proxy to this service.
Passwords are never stored here or in Git; only a local salted hash is used.
"""
from __future__ import annotations

import json
import secrets
import subprocess
import time
from pathlib import Path

from flask import Flask, jsonify, request, session
from werkzeug.security import check_password_hash

BASE = Path(__file__).resolve().parent
AUTH_FILE = BASE / "maintenance_auth.json"
HELPER = "/usr/local/sbin/heimdall-maintenance"
SESSION_MINUTES = 15

app = Flask(__name__)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Strict",
    PERMANENT_SESSION_LIFETIME=SESSION_MINUTES * 60,
)


def load_auth() -> dict:
    if not AUTH_FILE.exists():
        return {}
    try:
        return json.loads(AUTH_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def secret_key() -> str:
    auth = load_auth()
    key = auth.get("session_secret")
    if key:
        return key
    return secrets.token_hex(32)


app.secret_key = secret_key()


def configured() -> bool:
    return bool(load_auth().get("password_hash"))


def valid_password(password: str) -> bool:
    data = load_auth()
    pwh = data.get("password_hash")
    return bool(pwh and check_password_hash(pwh, password or ""))


def authed() -> bool:
    if not session.get("maintenance_authenticated"):
        return False
    authenticated_at = float(session.get("authenticated_at", 0))
    return (time.time() - authenticated_at) <= SESSION_MINUTES * 60


def run_helper(action: str) -> tuple[str, int]:
    allowed = {
        "doctor", "restart-backend", "restart-ui", "repair-db",
        "check-update", "backup", "reboot", "shutdown",
    }
    if action not in allowed:
        return "Action not allowed", 400
    try:
        p = subprocess.run(
            ["sudo", HELPER, action],
            capture_output=True,
            text=True,
            timeout=90,
        )
        text = ((p.stdout or "") + ("\n" + p.stderr if p.stderr else "")).strip()
        return text or f"{action}: completed", (200 if p.returncode == 0 else 500)
    except subprocess.TimeoutExpired:
        return f"{action}: timed out", 504
    except Exception as exc:
        return str(exc), 500


@app.get("/api/maintenance/status")
def maintenance_status():
    return jsonify({
        "configured": configured(),
        "authenticated": authed(),
        "session_minutes": SESSION_MINUTES,
    })


@app.post("/api/maintenance/login")
def maintenance_login():
    body = request.get_json(silent=True) or {}
    password = str(body.get("password", ""))
    if not configured():
        return jsonify({"ok": False, "error": "Maintenance password has not been configured."}), 503
    if not valid_password(password):
        time.sleep(0.5)
        return jsonify({"ok": False, "error": "Invalid maintenance password."}), 401
    session.permanent = True
    session["maintenance_authenticated"] = True
    session["authenticated_at"] = time.time()
    return jsonify({"ok": True, "expires_minutes": SESSION_MINUTES})


@app.post("/api/maintenance/logout")
def maintenance_logout():
    session.clear()
    return jsonify({"ok": True})


@app.post("/api/maintenance/action/<action>")
def maintenance_action(action: str):
    if not authed():
        return jsonify({"ok": False, "error": "Maintenance authentication required."}), 401

    if action in {"reboot", "shutdown"}:
        body = request.get_json(silent=True) or {}
        password = str(body.get("password", ""))
        confirm = str(body.get("confirm", "")).strip().upper()
        required = "REBOOT" if action == "reboot" else "SHUTDOWN"
        if not valid_password(password):
            return jsonify({"ok": False, "error": "Password confirmation required for node power action."}), 401
        if confirm != required:
            return jsonify({"ok": False, "error": f"Type {required} to confirm this action."}), 400

    output, code = run_helper(action)
    return jsonify({"ok": code == 200, "action": action, "output": output}), code


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8090, debug=False, use_reloader=False)
