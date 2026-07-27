# AlphaHire Decision Exposure Pre Read

Lead magnet web app. Built for AlphaHire by Navvai.

The whole app is one file, `static/index.html`. It runs with no backend at all, so you can
double click it locally and everything works except lead capture and email. `app.py` is a thin
Flask wrapper that serves it, stores every lead and optionally emails the summary.

---

## Option A: deploy in five minutes as a static site (no lead capture)

Use this only for a demo link to send someone before the call.

1. Push this folder to GitHub.
2. Render, **New** then **Static Site**.
3. Repository: your repo.
4. **Build Command:** leave empty.
5. **Publish Directory:** `static`
6. Create Static Site.

You get a live URL. Leads are not captured and nothing is emailed.

---

## Option B: deploy as a web service (recommended, captures leads)

1. Push this folder to GitHub, for example `NAVVAI-BOYS/alphahire-pre-read`.

2. Render, **New** then **Web Service**, connect the repo.

3. Settings, exactly these:

   | Field | Value |
   |---|---|
   | Language / Runtime | Python 3 |
   | Root Directory | leave blank if `app.py` sits at the repo root. If you nest this folder inside a bigger repo, put the folder name here |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60` |
   | Health Check Path | `/api/health` |
   | Instance Type | Starter or above. **Not Free**: free instances sleep and wipe the disk |

4. **Environment** tab, add these variables:

   | Key | Value | Needed? |
   |---|---|---|
   | `ADMIN_KEY` | any long random string you invent | Yes, it is the password for the lead export |
   | `RESEND_API_KEY` | your Resend key | Only if you want emails sent |
   | `FROM_EMAIL` | `reports@alpha-hire.com` | Only if you want emails sent |
   | `TEAM_EMAIL` | `leads@alpha-hire.com` | Optional, sends the team a copy |

5. **Disks** tab, add a disk so leads survive a redeploy:

   | Field | Value |
   |---|---|
   | Name | `leads` |
   | Mount Path | `/opt/render/project/src/data` |
   | Size | 1 GB |

   Without a disk, Render wipes `data/` on every deploy and you lose the leads.

6. Create Web Service. First build takes about two minutes.

If you would rather not click through all of that, `render.yaml` is already in the repo.
Render, **New** then **Blueprint**, point it at the repo, and it reads every setting above
from that file. You still add `RESEND_API_KEY` and `FROM_EMAIL` by hand, because secrets are
never committed.

---

## Getting the leads out

- Spreadsheet: `https://YOUR-APP.onrender.com/api/leads.csv?key=YOUR_ADMIN_KEY`
- Full JSON including every answer: `https://YOUR-APP.onrender.com/api/leads?key=YOUR_ADMIN_KEY`
- Funnel events, who started and who reached the email gate:
  `https://YOUR-APP.onrender.com/api/events?key=YOUR_ADMIN_KEY`
- Every lead is also written to the Render logs, so you can find one without the export.

---

## Turning email on

1. Resend, add and verify `alpha-hire.com` (Resend gives you the DKIM and SPF records to
   paste into your DNS).
2. Copy the API key into `RESEND_API_KEY` on Render.
3. Set `FROM_EMAIL` to a verified address on that domain.
4. Redeploy.

The app checks at runtime. Until the key is set, the report says the read has been saved.
Once it is set, the same line says it has been sent. It never claims to have emailed
something it did not.

---

## Putting it on your own domain

Render, your service, **Settings**, **Custom Domains**. Add for example
`readiness.alpha-hire.com` and add the CNAME Render shows you to your DNS. HTTPS is automatic.

---

## Editing the app

Everything is in `static/index.html`.

| What you want to change | Where |
|---|---|
| Colours | the `:root` block at the top of the CSS |
| The four decision lanes, headlines, built for lines | the `LANES` object |
| Product names and descriptions | the `SOL` object |
| Questions, options and scores | `buildQuestions()` |
| Pillar names, definitions and 1 and 10 anchors | the `PILLARS` object |
| Verdict bands | search for `>=7?"Go"` in `scores()` and the ladder copy in `renderReport()` |
| Home screen demo scenarios | the `SCEN` object |
| Booking link | the `Book the market read` button, and the link in `app.py` |

No build step, no framework, no npm. Edit, commit, push, Render redeploys.

---

## Known gaps before this goes fully live

1. **No rate limiting.** Fine for a link sent to prospects. Add one before it goes on the
   public nav.
2. **The published research strip is deliberately missing.** Everything in the report is
   either the prospect's own answers or AlphaHire's own published site figures. If you want a
   third party research strip, supply the real sources and they get added with citations.
3. **A tap is required on scoring questions.** The typed box is quoted in the report but does
   not score. Typed only scoring can be added if you want it.
4. **Booking button is a placeholder alert in the static version** and should point at the
   real AlphaHire calendar link.
