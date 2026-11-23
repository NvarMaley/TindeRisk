"""PIN-protected named saves for the local simulation."""

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from .matching.ledger import Ledger

SCHEMA = """
CREATE TABLE IF NOT EXISTS saves (
    id TEXT PRIMARY KEY, name TEXT UNIQUE COLLATE NOCASE NOT NULL,
    token TEXT UNIQUE NOT NULL, salt BLOB NOT NULL, pin BLOB NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0, retry_at REAL NOT NULL DEFAULT 0,
    draft TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS sessions (
    digest TEXT PRIMARY KEY, save_id TEXT NOT NULL REFERENCES saves(id),
    expires REAL NOT NULL
);
"""


@contextmanager
def registry(directory):
    directory = Path(directory)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = directory / "saves.sqlite3"
    os.close(os.open(path, os.O_CREAT | os.O_WRONLY, 0o600))
    conn = sqlite3.connect(path, timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(SCHEMA)
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def _pin(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}", value):
        raise ValueError("Enter a four-digit code.")
    return value.encode()


def _hash(pin, salt):
    return hashlib.scrypt(pin, salt=salt, n=16384, r=8, p=1)


def _digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _issue(conn, save_id):
    token = "save_" + secrets.token_hex(32)
    conn.execute("DELETE FROM sessions WHERE expires <= ?", (time.time(),))
    conn.execute(
        "INSERT INTO sessions VALUES (?, ?, ?)",
        (_digest(token), save_id, time.time() + 8 * 3600),
    )
    return token


def list_saves(directory):
    with registry(directory) as conn:
        return [
            dict(r)
            for r in conn.execute(
                "SELECT id, name FROM saves ORDER BY name COLLATE NOCASE"
            )
        ]


def create_save(directory, data):
    name = data.get("name", "").strip()
    if not 1 <= len(name) <= 40:
        raise ValueError("Enter a save name of 1 to 40 characters.")
    pin = _pin(data.get("pin"))
    if pin != _pin(data.get("confirmation")):
        raise ValueError("The two codes must match.")
    salt = secrets.token_bytes(16)
    hashed = _hash(pin, salt)
    with registry(directory) as conn:
        if conn.execute("SELECT 1 FROM saves WHERE name=?", (name,)).fetchone():
            raise ValueError("That save name is already in use.")
        saved_id = secrets.token_hex(16)
        legacy = data.get("legacy_token")
        if legacy:
            if conn.execute("SELECT 1 FROM saves WHERE token=?", (legacy,)).fetchone():
                raise ValueError("That dossier already has a protected save.")
            book = Ledger(directory, legacy)
        else:
            book = Ledger.create(directory)
        conn.execute(
            "INSERT INTO saves (id,name,token,salt,pin) VALUES (?,?,?,?,?)",
            (saved_id, name, book.token, salt, hashed),
        )
        return {"access": _issue(conn, saved_id), "name": name}


def unlock_save(directory, data):
    pin = _pin(data.get("pin"))
    now = time.time()
    with registry(directory) as conn:
        row = conn.execute(
            "SELECT * FROM saves WHERE id=?", (data.get("id"),)
        ).fetchone()
        if row is None:
            raise ValueError("Unknown save.")
        if row["retry_at"] > now:
            raise ValueError("Too many attempts. Try again in five minutes.")
        if hmac.compare_digest(_hash(pin, row["salt"]), row["pin"]):
            conn.execute(
                "UPDATE saves SET attempts=0,retry_at=0 WHERE id=?", (row["id"],)
            )
            return {"access": _issue(conn, row["id"]), "name": row["name"]}
        attempts = row["attempts"] + 1
        locked = attempts >= 5
        conn.execute(
            "UPDATE saves SET attempts=?,retry_at=? WHERE id=?",
            (0 if locked else attempts, now + 300 if locked else 0, row["id"]),
        )
    raise ValueError(
        "Too many attempts. Try again in five minutes." if locked else "Incorrect code."
    )


def resolve(directory, token):
    if not isinstance(token, str):
        return token, None
    if not (Path(directory) / "saves.sqlite3").exists() and not token.startswith(
        "save_"
    ):
        return token, None
    with registry(directory) as conn:
        if token.startswith("save_"):
            row = conn.execute(
                "SELECT saves.* FROM sessions JOIN saves ON saves.id=sessions.save_id "
                "WHERE digest=? AND expires>?",
                (_digest(token), time.time()),
            ).fetchone()
            if row is None:
                raise ValueError("Unlock your save to continue.")
            return row["token"], row["id"]
        if conn.execute("SELECT 1 FROM saves WHERE token=?", (token,)).fetchone():
            raise ValueError("Unlock your save to continue.")
    return token, None


def lock_save(directory, token):
    with registry(directory) as conn:
        if isinstance(token, str) and token.startswith("save_"):
            conn.execute("DELETE FROM sessions WHERE digest=?", (_digest(token),))


def draft(directory, save_id, **changes):
    with registry(directory) as conn:
        row = conn.execute("SELECT draft FROM saves WHERE id=?", (save_id,)).fetchone()
        values = json.loads(row["draft"])
        if changes:
            values = values | changes
            conn.execute(
                "UPDATE saves SET draft=? WHERE id=?", (json.dumps(values), save_id)
            )
        return values
