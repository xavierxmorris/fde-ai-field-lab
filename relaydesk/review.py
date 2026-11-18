"""A single-user review queue. Store a snapshot; never re-run a replay."""

import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def open_queue(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    try:
        db.row_factory = sqlite3.Row
        db.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id TEXT PRIMARY KEY NOT NULL,
                payload TEXT NOT NULL,
                snapshot TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('pending','accepted','rejected','handoff')),
                note TEXT NOT NULL DEFAULT ''
            )
        """)
        yield db
    finally:
        db.close()


def decode(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "input": json.loads(row["payload"]),
            "result": json.loads(row["snapshot"]), "state": row["state"], "note": row["note"]}


def show(db, request_id):
    row = db.execute("SELECT * FROM requests WHERE id=?", (request_id,)).fetchone()
    if row is None:
        raise ValueError(f"unknown request ID: {request_id}")
    return decode(row)


def submit(db, request_id, tenant, lookup_date, question, triage):
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}", request_id):
        raise ValueError("use a 1-80 character request ID made of letters, digits, dot, dash or underscore")
    # Exact canonical payload comparison detects changed whitespace as well as a changed retailer/date.
    payload = json.dumps({"tenant": tenant, "lookup_date": lookup_date, "question": question},
                         sort_keys=True, separators=(",", ":"))
    with db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM requests WHERE id=?", (request_id,)).fetchone()
        if row is not None:
            if row["payload"] != payload:
                raise ValueError(f"request ID {request_id} was already used with different input")
            return decode(row)
        snapshot = triage(tenant, lookup_date, question)
        state = "pending" if snapshot["disposition"] == "draft" else "handoff"
        db.execute("INSERT INTO requests(id,payload,snapshot,state) VALUES (?,?,?,?)",
                   (request_id, payload, json.dumps(snapshot), state))
        return show(db, request_id)


def pending(db):
    rows = db.execute("SELECT * FROM requests WHERE state='pending' ORDER BY rowid")
    return [decode(row) for row in rows]


def review(db, request_id, decision, note=""):
    if decision not in ("accept", "reject") or len(note) > 500:
        raise ValueError("use accept or reject and a synthetic note of at most 500 characters")
    state = {"accept": "accepted", "reject": "rejected"}[decision]
    with db:
        changed = db.execute("UPDATE requests SET state=?,note=? WHERE id=? AND state='pending'",
                             (state, note, request_id)).rowcount
        record = show(db, request_id)
        if changed != 1:
            raise ValueError(f"{request_id} is {record['state']}; only pending drafts can be reviewed")
        return record
