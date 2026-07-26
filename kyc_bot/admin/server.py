"""Census admin approval page.

A lightweight FastAPI app that lists persisted census records in a table and
lets an admin Approve / Reject each one. Reads the same SQLite DB the census bot
writes to.

Run:  uvicorn kyc_bot.admin.server:app --host 127.0.0.1 --port 8100
"""
from __future__ import annotations

import html

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse

from kyc_bot.storage import census_db

app = FastAPI(title="Census Admin")


@app.on_event("startup")
def _startup() -> None:
    census_db.init_db()


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return _page(census_db.list_records(), census_db.counts())


@app.post("/records/{record_id}/approve")
def approve(record_id: int) -> RedirectResponse:
    census_db.set_status(record_id, "approved")
    return RedirectResponse("/", status_code=303)


@app.post("/records/{record_id}/reject")
def reject(record_id: int) -> RedirectResponse:
    census_db.set_status(record_id, "rejected")
    return RedirectResponse("/", status_code=303)


def _badge(status: str) -> str:
    color = {"pending": "#b58900", "approved": "#2ea043", "rejected": "#d1242f"}.get(
        status, "#888"
    )
    return f'<span class="badge" style="background:{color}">{status}</span>'


def _row(r: dict) -> str:
    e = lambda v: html.escape(str(v if v not in (None, "") else "—"))  # noqa: E731
    assets = ", ".join(r["assets"]) if r["assets"] else "—"
    review = "⚠️ review" if r["needs_review"] else "✓"
    match = f'{r["id_name_match"]:.0%}' if r["id_name_match"] is not None else "—"
    # Liveness is "submitted" until an admin decides; "accepted" only on approval.
    liveness_disp = {"approved": "accepted ✓", "rejected": "rejected ✗"}.get(
        r["status"], e(r["liveness"])
    )
    # Lock actions once a decision is made — no further updates allowed.
    if r["status"] == "pending":
        actions = (
            f'<form method="post" action="/records/{r["id"]}/approve" style="display:inline">'
            f'<button class="ok">Approve</button></form> '
            f'<form method="post" action="/records/{r["id"]}/reject" style="display:inline">'
            f'<button class="no">Reject</button></form>'
        )
    else:
        actions = '<span class="dim">🔒 locked</span>'
    return (
        "<tr>"
        f"<td>{r['id']}</td>"
        f"<td class='dim'>{e(r['created_at'])}</td>"
        f"<td>{e(r['head_name'])}</td>"
        f"<td>{e(r['head_age'])}</td>"
        f"<td>{e(r['head_sex'])}</td>"
        f"<td>{e(r['head_marital'])}</td>"
        f"<td>{e(r['household_size'])}</td>"
        f"<td>{e(r['ownership'])}</td>"
        f"<td>{e(assets)}</td>"
        f"<td class='dim'>{e(r['id_masked'])}</td>"
        f"<td>{e(r['id_name'])} <span class='dim'>({match})</span></td>"
        f"<td>{liveness_disp}</td>"
        f"<td>{review}</td>"
        f"<td>{_badge(r['status'])}</td>"
        f"<td>{actions}</td>"
        "</tr>"
    )


def _page(records: list[dict], c: dict[str, int]) -> str:
    rows = "".join(_row(r) for r in records) or (
        "<tr><td colspan='15' class='dim' style='text-align:center;padding:32px'>"
        "No records yet — complete a survey in the census bot.</td></tr>"
    )
    return f"""<!doctype html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Census Admin — Approvals</title>
<style>
body{{font-family:system-ui,sans-serif;margin:0;background:#0d1117;color:#e6edf3}}
header{{padding:18px 24px;border-bottom:1px solid #21262d}}
h1{{margin:0;font-size:20px}}
.sub{{color:#8b949e;font-size:13px;margin-top:4px}}
.stats{{display:flex;gap:10px;margin:16px 24px}}
.stat{{background:#161b22;border:1px solid #21262d;border-radius:8px;padding:8px 14px;font-size:13px}}
.stat b{{font-size:18px;display:block}}
.wrap{{overflow-x:auto;padding:0 24px 32px}}
table{{border-collapse:collapse;width:100%;font-size:13px;min-width:1100px}}
th,td{{padding:8px 10px;border-bottom:1px solid #21262d;text-align:left;white-space:nowrap}}
th{{color:#8b949e;font-weight:600;position:sticky;top:0;background:#0d1117}}
.dim{{color:#8b949e}}
.badge{{color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;text-transform:uppercase}}
button{{border:0;border-radius:6px;padding:5px 11px;font-size:12px;cursor:pointer;color:#fff}}
button.ok{{background:#238636}} button.no{{background:#da3633}}
</style></head><body>
<header><h1>🗂️ Census Admin — Approval Queue</h1>
<div class=sub>Records submitted by the Bhasha Census bot. Approve or reject each household.</div></header>
<div class=stats>
  <div class=stat><b>{c['pending']}</b>pending</div>
  <div class=stat><b>{c['approved']}</b>approved</div>
  <div class=stat><b>{c['rejected']}</b>rejected</div>
</div>
<div class=wrap><table>
<thead><tr>
<th>ID</th><th>Submitted</th><th>Head</th><th>Age</th><th>Sex</th><th>Marital</th>
<th>House size</th><th>Ownership</th><th>Assets</th><th>ID (masked)</th>
<th>Card name (match)</th><th>Liveness</th><th>Flag</th><th>Status</th><th>Action</th>
</tr></thead>
<tbody>{rows}</tbody>
</table></div>
</body></html>"""
