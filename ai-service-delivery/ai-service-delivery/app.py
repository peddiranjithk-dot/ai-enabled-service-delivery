import sqlite3
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template, request, g
from ai_engine import analyze

DB = "service.db"
app = Flask(__name__)


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d:
        d.close()


def init_db():
    with sqlite3.connect(DB) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS tickets(
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, message TEXT,
            category TEXT, priority TEXT, sentiment TEXT, team TEXT, reply TEXT,
            ai_source TEXT, status TEXT DEFAULT 'open', created TEXT, due TEXT)""")


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/tickets")
def create_ticket():
    data = request.get_json(force=True)
    name, message = data.get("name", "").strip(), data.get("message", "").strip()
    if not name or not message:
        return jsonify(error="name and message are required"), 400
    a = analyze(message)
    now = datetime.now()
    due = now + timedelta(hours=a["sla_hours"])
    cur = db().execute(
        "INSERT INTO tickets(name,message,category,priority,sentiment,team,reply,ai_source,created,due) "
        "VALUES(?,?,?,?,?,?,?,?,?,?)",
        (name, message, a["category"], a["priority"], a.get("sentiment", "neutral"), a["team"],
         a["reply"], a["source"], now.isoformat(timespec="seconds"), due.isoformat(timespec="seconds")))
    db().commit()
    return jsonify(id=cur.lastrowid, **a), 201


@app.get("/api/tickets")
def list_tickets():
    order = "CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, created DESC"
    rows = db().execute(f"SELECT * FROM tickets ORDER BY {order}").fetchall()
    return jsonify([dict(r) for r in rows])


@app.patch("/api/tickets/<int:tid>")
def update_ticket(tid):
    status = request.get_json(force=True).get("status")
    if status not in ("open", "in_progress", "resolved"):
        return jsonify(error="invalid status"), 400
    db().execute("UPDATE tickets SET status=? WHERE id=?", (status, tid))
    db().commit()
    return jsonify(ok=True)


@app.get("/api/stats")
def stats():
    d = db()
    q = lambda sql: [dict(r) for r in d.execute(sql).fetchall()]
    return jsonify(
        total=d.execute("SELECT COUNT(*) FROM tickets").fetchone()[0],
        by_category=q("SELECT category k, COUNT(*) n FROM tickets GROUP BY category"),
        by_priority=q("SELECT priority k, COUNT(*) n FROM tickets GROUP BY priority"),
        by_status=q("SELECT status k, COUNT(*) n FROM tickets GROUP BY status"),
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
