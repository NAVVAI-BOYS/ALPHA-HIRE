"""
AlphaHire Decision Exposure Pre Read
Serves the app, captures leads, optionally emails the report.
Built for AlphaHire by Navvai.

Environment variables (all optional except ADMIN_KEY if you want the exports):
  ADMIN_KEY        password for /api/leads and /api/leads.csv
  RESEND_API_KEY   turns on real email sending
  FROM_EMAIL       verified sender, e.g. reports@alpha-hire.com
  TEAM_EMAIL       internal copy, e.g. leads@alpha-hire.com
"""
import os, json, csv, io, datetime, threading

from flask import Flask, request, jsonify, send_from_directory, Response

APP_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(APP_DIR, "static")
DATA_DIR = os.path.join(APP_DIR, "data")
LEADS_FILE = os.path.join(DATA_DIR, "leads.json")
EVENTS_FILE = os.path.join(DATA_DIR, "events.json")

ADMIN_KEY = os.environ.get("ADMIN_KEY", "")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "")
TEAM_EMAIL = os.environ.get("TEAM_EMAIL", "")

app = Flask(__name__, static_folder=None)
_lock = threading.Lock()

os.makedirs(DATA_DIR, exist_ok=True)


def _read(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _append(path, row):
    with _lock:
        rows = _read(path)
        rows.append(row)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
    return len(rows)


def _authed():
    return ADMIN_KEY and request.args.get("key") == ADMIN_KEY


# ---------- pages ----------
@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(STATIC_DIR, path)


@app.route("/api/health")
def health():
    return jsonify(
        ok=True,
        leads=len(_read(LEADS_FILE)),
        email_configured=bool(RESEND_API_KEY and FROM_EMAIL),
    )


# ---------- lead capture ----------
@app.route("/api/lead", methods=["POST"])
def lead():
    data = request.get_json(silent=True) or {}
    row = {
        "captured_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "first_name": data.get("first_name", ""),
        "last_name": data.get("last_name", ""),
        "email": data.get("email", ""),
        "company": data.get("company", ""),
        "title": data.get("title", ""),
        "lane": data.get("lane", ""),
        "verdict": data.get("verdict", ""),
        "weakest_pillar": data.get("weakest_pillar", ""),
        "weakest_score": data.get("weakest_score", ""),
        "confidence_pct": data.get("confidence_pct", ""),
        "gaps": data.get("gaps", ""),
        "monthly_cost": data.get("monthly_cost", ""),
        "exposure_low": data.get("exposure_low", ""),
        "exposure_high": data.get("exposure_high", ""),
        "stage": data.get("stage", ""),
        "goal": data.get("goal", ""),
        "answers": data.get("answers", []),
    }
    _append(LEADS_FILE, row)
    app.logger.info("LEAD %s %s %s | %s | %s",
                    row["first_name"], row["last_name"], row["company"],
                    row["verdict"], row["email"])

    emailed = False
    if RESEND_API_KEY and FROM_EMAIL:
        emailed = _send_email(row)
    return jsonify(ok=True, emailed=emailed)


def _send_email(row):
    """Sends a short summary. The full report lives in the browser; this is the hook."""
    try:
        import requests
        name = (row["first_name"] + " " + row["last_name"]).strip()
        subject = "Your AlphaHire pre read: %s" % row["verdict"]
        body = """
        <div style="font-family:Helvetica,Arial,sans-serif;color:#0B0B12;max-width:560px">
          <p style="font-size:12px;letter-spacing:.12em;color:#7C3AED;font-weight:700">
            DECISION EXPOSURE PRE READ</p>
          <h2 style="letter-spacing:-.03em">%s, here is your read.</h2>
          <p><b>Verdict:</b> %s, set by your weakest pillar (%s at %s of 10).</p>
          <p><b>Decision confidence:</b> %s%%. <b>Gaps found:</b> %s.</p>
          <p><b>Cost if the read is wrong:</b> $%s to $%s, from the figures you gave us.</p>
          <p><b>Your stated goal:</b> %s</p>
          <p style="margin-top:24px">
            <a href="https://alpha-hire.com/start/"
               style="background:#7C3AED;color:#fff;padding:13px 24px;border-radius:999px;
                      text-decoration:none;font-weight:700">Book the market read</a></p>
          <p style="font-size:12px;color:#6B6B7B;margin-top:24px">
            Every figure above is computed from numbers you supplied. AlphaHire, Workforce
            Intelligence Platform.</p>
        </div>""" % (name, row["verdict"], row["weakest_pillar"], row["weakest_score"],
                     row["confidence_pct"], row["gaps"],
                     "{:,}".format(int(row["exposure_low"] or 0)),
                     "{:,}".format(int(row["exposure_high"] or 0)),
                     row["goal"])

        to = [row["email"]]
        if TEAM_EMAIL:
            to.append(TEAM_EMAIL)
        r = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": "Bearer " + RESEND_API_KEY,
                     "Content-Type": "application/json"},
            json={"from": FROM_EMAIL, "to": to, "subject": subject, "html": body},
            timeout=12)
        if r.status_code >= 300:
            app.logger.warning("RESEND FAILED %s %s", r.status_code, r.text[:300])
            return False
        return True
    except Exception as e:  # never break the report on an email failure
        app.logger.warning("RESEND ERROR %s", e)
        return False


# ---------- funnel events ----------
@app.route("/api/event", methods=["POST"])
def event():
    d = request.get_json(silent=True) or {}
    _append(EVENTS_FILE, {
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "event": d.get("event", ""), "lane": d.get("lane", ""), "step": d.get("step", ""),
    })
    return jsonify(ok=True)


# ---------- exports ----------
@app.route("/api/leads")
def leads_json():
    if not _authed():
        return jsonify(error="Add ?key=YOUR_ADMIN_KEY"), 401
    return jsonify(_read(LEADS_FILE))


@app.route("/api/events")
def events_json():
    if not _authed():
        return jsonify(error="Add ?key=YOUR_ADMIN_KEY"), 401
    return jsonify(_read(EVENTS_FILE))


@app.route("/api/leads.csv")
def leads_csv():
    if not _authed():
        return Response("Add ?key=YOUR_ADMIN_KEY", status=401, mimetype="text/plain")
    cols = ["captured_at", "first_name", "last_name", "email", "company", "title", "lane",
            "stage", "verdict", "weakest_pillar", "weakest_score", "confidence_pct", "gaps",
            "monthly_cost", "exposure_low", "exposure_high", "goal"]
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in _read(LEADS_FILE):
        w.writerow(r)
    return Response(out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=alphahire-leads.csv"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
