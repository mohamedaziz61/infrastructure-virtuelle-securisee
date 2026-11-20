"""Demo application "Lab Inventory": small inventory web app backed by PostgreSQL.
Exposes /health (liveness+DB check) and /metrics (Prometheus format)."""
import os, time, html
from flask import Flask, request, redirect, Response
import psycopg2

app = Flask(__name__)
START = time.time()
REQS = {"count": 0}


def db_password():
    path = os.environ.get("DB_PASSWORD_FILE", "/run/secrets/db_password")
    with open(path) as f:
        return f.read().strip()


def conn():
    return psycopg2.connect(host=os.environ.get("DB_HOST", "db"), dbname="inventory", user="inventory",
                            password=db_password(), connect_timeout=3)


def init_db():
    for _ in range(30):
        try:
            with conn() as c, c.cursor() as cur:
                cur.execute("CREATE TABLE IF NOT EXISTS assets (id SERIAL PRIMARY KEY, name TEXT NOT NULL,"
                            " vlan TEXT NOT NULL, created TIMESTAMP DEFAULT now())")
            return
        except psycopg2.OperationalError:
            time.sleep(2)
    raise SystemExit("database unavailable")


@app.before_request
def count():
    REQS["count"] += 1


@app.get("/")
def index():
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT id, name, vlan, created FROM assets ORDER BY id")
        rows = cur.fetchall()
    trs = "".join(f"<tr><td>{r[0]}</td><td>{html.escape(r[1])}</td><td>{html.escape(r[2])}</td><td>{r[3]:%Y-%m-%d %H:%M}</td></tr>" for r in rows)
    return f"""<!doctype html><meta charset=utf-8><title>Lab Inventory</title>
<style>body{{font-family:sans-serif;max-width:760px;margin:2em auto}}td,th{{border:1px solid #ccc;padding:4px 8px}}table{{border-collapse:collapse}}</style>
<h1>Lab Inventory — srv01</h1><p>Application conteneurisée (Flask + PostgreSQL) — hôte : {html.escape(os.uname().nodename)}</p>
<form method=post action=/assets><input name=name placeholder="Nom de l'équipement" required maxlength=80>
<select name=vlan><option>VLAN10</option><option>VLAN20</option><option>VLAN30</option><option>VLAN99</option></select>
<button>Ajouter</button></form><table><tr><th>#</th><th>Nom</th><th>VLAN</th><th>Créé</th></tr>{trs}</table>"""


@app.post("/assets")
def add():
    name = request.form.get("name", "").strip()[:80]
    vlan = request.form.get("vlan", "VLAN20")
    if name and vlan in {"VLAN10", "VLAN20", "VLAN30", "VLAN99"}:
        with conn() as c, c.cursor() as cur:
            cur.execute("INSERT INTO assets (name, vlan) VALUES (%s, %s)", (name, vlan))
    return redirect("/", code=303)


@app.get("/health")
def health():
    try:
        with conn() as c, c.cursor() as cur:
            cur.execute("SELECT 1")
        return {"status": "ok", "db": "ok"}
    except Exception as e:  # noqa: BLE001
        return {"status": "degraded", "db": type(e).__name__}, 503


@app.get("/metrics")
def metrics():
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT count(*) FROM assets")
        n = cur.fetchone()[0]
    body = (f"# TYPE labapp_assets_total gauge\nlabapp_assets_total {n}\n"
            f"# TYPE labapp_requests_total counter\nlabapp_requests_total {REQS['count']}\n"
            f"# TYPE labapp_uptime_seconds gauge\nlabapp_uptime_seconds {time.time() - START:.0f}\n")
    return Response(body, mimetype="text/plain; version=0.0.4")


init_db()
