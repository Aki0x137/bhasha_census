# SIR Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** A local, read-only FastAPI web dashboard to view SIR submissions: a counts summary (total + today) and a table of decrypted fields, with a per-row link that serves the decrypted EPIC image inline.

**Architecture:** Reuses the existing storage layer. Adds a `list_all()` read method to `SubmissionStore`. A new `kyc_bot/dashboard.py` FastAPI app renders an HTML table server-side and an image endpoint that decrypts a submission's vaulted image on the fly. Bound to 127.0.0.1 only. Requires `KYC_MASTER_KEY` to decrypt.

**Tech Stack:** FastAPI + Uvicorn, existing `SubmissionStore`/`Vault`/`crypto`, `pytest` (FastAPI `TestClient`).

**Privacy:** The dashboard displays decrypted PII and ID images. It binds to localhost only, has no auth (MVP), and must never be exposed publicly. Noted in the run docs.

---

### Task 1: Add FastAPI + uvicorn dependency

**Files:** Modify `pyproject.toml`, `requirements.txt`

- [ ] **Step 1:** In `pyproject.toml` `[project].dependencies`, add after `cryptography==43.0.1`:
```toml
    "fastapi==0.115.2",
    "uvicorn==0.31.1",
```
- [ ] **Step 2:** Add to `requirements.txt`:
```
fastapi==0.115.2
uvicorn==0.31.1
httpx==0.27.2
```
(`httpx` is needed by FastAPI's `TestClient` in tests.)
- [ ] **Step 3:** Also add `httpx==0.27.2` to the `[project.optional-dependencies].dev` list in `pyproject.toml`:
```toml
    "httpx==0.27.2",
```
- [ ] **Step 4:** Install: `cd /Users/psabata/bhasaha_census && .venv/bin/pip install -e ".[dev]"` — expect clean.
- [ ] **Step 5:** Verify: `.venv/bin/python -c "import fastapi, uvicorn, httpx; print('ok')"` → `ok`.
- [ ] **Step 6:** Commit:
```bash
git add pyproject.toml requirements.txt
git commit -m "chore: add fastapi, uvicorn, httpx for the dashboard"
```

---

### Task 2: Add `list_all()` to SubmissionStore

**Files:** Modify `kyc_bot/storage/db.py`, Test `tests/storage/test_db.py`

- [ ] **Step 1: Add the failing test** — append to `tests/storage/test_db.py`:

```python
def test_list_all_returns_all_decrypted(tmp_path):
    key = Fernet.generate_key()
    store = SubmissionStore(tmp_path / "s.db", key=key)
    store.save(_sub("ref1"))
    store.save(_sub("ref2"))
    got = store.list_all()
    assert {s.id for s in got} == {"ref1", "ref2"}
    assert all(s.name == "Ravi Kumar" for s in got)


def test_list_all_empty(tmp_path):
    key = Fernet.generate_key()
    store = SubmissionStore(tmp_path / "s.db", key=key)
    assert store.list_all() == []
```

- [ ] **Step 2: Run** `.venv/bin/pytest tests/storage/test_db.py -v` → the two new tests FAIL (`list_all` missing).

- [ ] **Step 3: Implement** — add this method to `SubmissionStore` (after `get`):

```python
    def list_all(self) -> list[Submission]:
        """Return all submissions, newest first, with PII decrypted."""
        with sqlite3.connect(self._path) as conn:
            rows = conn.execute(
                "SELECT id, user_id, name_enc, epic_enc, dob_enc, address_enc, "
                "image_path, created_at FROM submissions ORDER BY created_at DESC"
            ).fetchall()
        return [
            Submission(
                id=row[0],
                user_id=row[1],
                name=crypto.decrypt_str(row[2], self._key),
                epic=crypto.decrypt_str(row[3], self._key),
                dob=crypto.decrypt_str(row[4], self._key),
                address=crypto.decrypt_str(row[5], self._key),
                image_path=row[6],
                created_at=row[7],
            )
            for row in rows
        ]
```

- [ ] **Step 4: Run** `.venv/bin/pytest tests/storage/test_db.py -v` → all pass.
- [ ] **Step 5: Commit:**
```bash
git add kyc_bot/storage/db.py tests/storage/test_db.py
git commit -m "feat: add SubmissionStore.list_all for the dashboard"
```

---

### Task 3: Dashboard app (build_dashboard factory)

**Files:** Create `kyc_bot/dashboard.py`, Test `tests/test_dashboard.py`

The app is built by a `build_dashboard(store, vault)` factory so tests inject fakes and no env/key is needed at import.

- [ ] **Step 1: Write the failing test** `tests/test_dashboard.py`:

```python
from fastapi.testclient import TestClient

from kyc_bot.dashboard import build_dashboard
from kyc_bot.storage.db import Submission


class FakeStore:
    def __init__(self, subs):
        self._subs = subs

    def list_all(self):
        return list(self._subs)

    def get(self, sid):
        return next((s for s in self._subs if s.id == sid), None)


class FakeVault:
    def __init__(self, images):
        self._images = images

    def load(self, path):
        return self._images[path]


def _sub(id="ref1", created="2026-07-26T08:00:00+00:00"):
    return Submission(
        id=id, user_id="42", name="Ravi Kumar", epic="ABC1234567",
        dob="1990-01-01", address="12 MG Road", image_path=f"/vault/epic_{id}.enc",
        created_at=created,
    )


def _client(subs, images=None):
    store = FakeStore(subs)
    vault = FakeVault(images or {})
    return TestClient(build_dashboard(store, vault))


def test_index_shows_table_with_submissions():
    client = _client([_sub("ref1"), _sub("ref2")])
    r = client.get("/")
    assert r.status_code == 200
    assert "Ravi Kumar" in r.text
    assert "ABC1234567" in r.text
    assert "ref1" in r.text and "ref2" in r.text


def test_index_shows_counts_summary():
    client = _client([_sub("ref1"), _sub("ref2")])
    r = client.get("/")
    # total count appears
    assert "2" in r.text
    assert "Total" in r.text


def test_image_endpoint_serves_decrypted_bytes():
    subs = [_sub("ref1")]
    images = {"/vault/epic_ref1.enc": b"\xff\xd8\xff-jpeg-bytes"}
    client = _client(subs, images)
    r = client.get("/image/ref1")
    assert r.status_code == 200
    assert r.content == b"\xff\xd8\xff-jpeg-bytes"


def test_image_endpoint_404_for_unknown():
    client = _client([_sub("ref1")])
    r = client.get("/image/nope")
    assert r.status_code == 404
```

- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_dashboard.py -v` → FAIL (module missing).

- [ ] **Step 3: Implement** `kyc_bot/dashboard.py`:

```python
"""Read-only local dashboard for SIR submissions (FastAPI).

Displays DECRYPTED PII and serves decrypted EPIC images. Localhost only, no
auth — never expose publicly. Build with build_dashboard(store, vault); the
module-level `app` (via create_app) is used by `python -m kyc_bot.dashboard`.
"""
from __future__ import annotations

import html
from datetime import date

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response


def _render(submissions) -> str:
    total = len(submissions)
    today = date.today().isoformat()
    today_count = sum(1 for s in submissions if s.created_at.startswith(today))
    rows = []
    for s in submissions:
        rows.append(
            "<tr>"
            f"<td>{html.escape(s.id)}</td>"
            f"<td>{html.escape(s.name)}</td>"
            f"<td>{html.escape(s.epic)}</td>"
            f"<td>{html.escape(s.dob)}</td>"
            f"<td>{html.escape(s.address)}</td>"
            f"<td>{html.escape(s.created_at)}</td>"
            f'<td><a href="/image/{html.escape(s.id)}" target="_blank">view</a></td>'
            "</tr>"
        )
    body = "".join(rows) or '<tr><td colspan="7">No submissions yet.</td></tr>'
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>SIR Submissions</title>
<style>
 body {{ font-family: -apple-system, system-ui, sans-serif; margin: 32px; color:#111; }}
 h1 {{ font-size: 20px; }}
 .cards {{ display:flex; gap:16px; margin:16px 0; }}
 .card {{ background:#f4f5f7; border-radius:10px; padding:14px 18px; }}
 .card .n {{ font-size:24px; font-weight:700; }}
 .card .l {{ font-size:12px; color:#666; }}
 table {{ border-collapse: collapse; width:100%; font-size:14px; }}
 th,td {{ text-align:left; padding:8px 10px; border-bottom:1px solid #e3e3e3; }}
 th {{ color:#666; font-size:12px; text-transform:uppercase; }}
</style></head><body>
<h1>SIR Submissions</h1>
<div class="cards">
  <div class="card"><div class="n">{total}</div><div class="l">Total</div></div>
  <div class="card"><div class="n">{today_count}</div><div class="l">Today</div></div>
</div>
<table>
<tr><th>Ref</th><th>Name</th><th>EPIC</th><th>DOB</th><th>Address</th><th>Submitted</th><th>ID image</th></tr>
{body}
</table>
</body></html>"""


def build_dashboard(store, vault) -> FastAPI:
    app = FastAPI(title="SIR Dashboard")

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return _render(store.list_all())

    @app.get("/image/{submission_id}")
    def image(submission_id: str) -> Response:
        sub = store.get(submission_id)
        if sub is None:
            return Response(status_code=404)
        data = vault.load(sub.image_path)
        return Response(content=data, media_type="image/jpeg")

    return app


def create_app() -> FastAPI:
    """Build the dashboard from real config + env key (used by __main__)."""
    from kyc_bot import config
    from kyc_bot.storage import crypto
    from kyc_bot.storage.db import SubmissionStore
    from kyc_bot.storage.vault import Vault

    key = crypto.load_key()
    return build_dashboard(
        SubmissionStore(config.db_path(), key=key),
        Vault(root=config.vault_dir(), key=key),
    )


def main() -> None:
    import uvicorn

    uvicorn.run(create_app(), host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run** `.venv/bin/pytest tests/test_dashboard.py -v` → 4 passed.
- [ ] **Step 5: Full suite + lint:** `.venv/bin/pytest -q && .venv/bin/ruff check kyc_bot tests` → all pass, ruff clean.
- [ ] **Step 6: Verify import without key** (create_app not called at import): `.venv/bin/python -c "import kyc_bot.dashboard"` → exit 0.
- [ ] **Step 7: Commit:**
```bash
git add kyc_bot/dashboard.py tests/test_dashboard.py
git commit -m "feat: add read-only SIR submissions dashboard"
```

---

### Task 4: Dashboard run docs

**Files:** Modify `README.md`

- [ ] **Step 1:** Append to `README.md`:

```markdown
## View submissions (local dashboard)

Read-only dashboard showing all SIR submissions (decrypted) with a counts
summary and inline EPIC image viewing. **Localhost only, no auth — never
expose this publicly; it displays decrypted PII and ID photos.**

```bash
KYC_MASTER_KEY=<same key used by the bot> .venv/bin/python -m kyc_bot.dashboard
```

Then open http://127.0.0.1:8000. Use the same `KYC_MASTER_KEY` (and
`KYC_DATA_DIR` if you set one) as the running bot, or the data won't decrypt.
```

- [ ] **Step 2:** Commit:
```bash
git add README.md
git commit -m "docs: add dashboard run instructions"
```

---

## Definition of Done
- `SubmissionStore.list_all()` returns all decrypted submissions, newest first.
- `python -m kyc_bot.dashboard` serves a localhost table + counts (Total/Today)
  and an `/image/<ref>` endpoint that decrypts and serves the EPIC image.
- Dashboard unit tests pass (TestClient, fakes — no key/network); full suite green; ruff clean.
