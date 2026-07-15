import os
import sqlite3

from flask import Blueprint, jsonify, request


reactions_bp = Blueprint("reactions", __name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reactions.db")

REACTION_TYPES = ["love", "like", "fire", "laugh", "wow", "sad"]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS reaction_counts (
                type TEXT PRIMARY KEY,
                count INTEGER NOT NULL DEFAULT 0
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS device_reactions (
                device_id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        for reaction_type in REACTION_TYPES:
            conn.execute(
                "INSERT OR IGNORE INTO reaction_counts (type, count) VALUES (?, 0)",
                (reaction_type,),
            )
        conn.commit()
    finally:
        conn.close()


def _read_counts(conn):
    rows = conn.execute("SELECT type, count FROM reaction_counts").fetchall()
    return {row["type"]: row["count"] for row in rows}


@reactions_bp.route("/api/reactions", methods=["GET"])
def get_reactions():
    device_id = (request.args.get("device_id") or "").strip()

    conn = get_db()
    try:
        counts = _read_counts(conn)
        selected = None

        if device_id:
            row = conn.execute(
                "SELECT type FROM device_reactions WHERE device_id = ?",
                (device_id,),
            ).fetchone()
            if row:
                selected = row["type"]

        return jsonify({"counts": counts, "selected": selected})
    finally:
        conn.close()


@reactions_bp.route("/api/react", methods=["POST"])
def react():
    data = request.get_json(silent=True) or {}
    device_id = (data.get("device_id") or "").strip()
    new_type = data.get("type")

    if not device_id or len(device_id) > 100:
        return jsonify({"error": "invalid device_id"}), 400
    if new_type is not None and new_type not in REACTION_TYPES:
        return jsonify({"error": "invalid type"}), 400

    conn = get_db()
    try:
        conn.execute("BEGIN IMMEDIATE")

        row = conn.execute(
            "SELECT type FROM device_reactions WHERE device_id = ?",
            (device_id,),
        ).fetchone()
        old_type = row["type"] if row else None

        if old_type != new_type:
            if old_type:
                conn.execute(
                    "UPDATE reaction_counts SET count = MAX(count - 1, 0) WHERE type = ?",
                    (old_type,),
                )

            if new_type:
                conn.execute(
                    "UPDATE reaction_counts SET count = count + 1 WHERE type = ?",
                    (new_type,),
                )
                conn.execute(
                    """INSERT INTO device_reactions (device_id, type, updated_at)
                       VALUES (?, ?, CURRENT_TIMESTAMP)
                       ON CONFLICT(device_id) DO UPDATE SET
                           type = excluded.type,
                           updated_at = CURRENT_TIMESTAMP""",
                    (device_id, new_type),
                )
            else:
                conn.execute(
                    "DELETE FROM device_reactions WHERE device_id = ?",
                    (device_id,),
                )

            conn.commit()

        counts = _read_counts(conn)
        return jsonify({"counts": counts, "selected": new_type})
    finally:
        conn.close()