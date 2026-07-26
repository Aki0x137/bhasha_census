# SpecKit Integration Guide for bhasha_census

How to integrate and use these SpecKit commands and command loops in your project.

## Setup

### 1. Copy Files to Project

```bash
# From project root:
cp bhasha_commands.md .specify/commands.md
cp bhasha_loops.md .specify/loops.md
```

Or manually merge into existing `.specify/` files if you have a template structure.

### 2. Create MCP Server Configuration (Optional, for Cursor Integration)

If using Cursor with MCP servers, create `.cursor/mcp_config.json`:

```json
{
  "mcpServers": {
    "speckit": {
      "command": "node",
      "args": ["path/to/speckit-mcp-server.js"],
      "env": {
        "PROJECT_ROOT": "."
      }
    }
  }
}
```

### 3. Verify Constitution

Ensure `.specify/memory/constitution.md` is present and up-to-date. Commands reference it for compliance checks.

---

## Usage Patterns

### Pattern 1: Bootstrap from Scratch

Fresh project? Run the master loop:

```bash
# In Cursor editor or terminal:
/project-init-from-scratch
```

This chains 22 commands end-to-end, scaffolding the entire MVP with:
- All 6 core services (session, challenge, video, speech, document, orchestrator)
- FastAPI routes + Temporal workflows + LangGraph aggregator
- Shared schemas (evidence, verdict, session)
- Tests, compliance checks, documentation
- Local dev environment setup

**Time**: ~15-20 minutes wall time. Outputs ready-to-test project.

### Pattern 2: Incremental Service Addition

Add a new evidence service (e.g., fingerprint liveness):

```bash
/rapid-service-scaffold
```

Prompts for:
1. Service name
2. Service type (video-based, external API, policy/scoring)
3. Auto-scaffolds with models, Temporal integration, tests

**Time**: ~5 minutes per service. Ensures all compliance checks pass.

### Pattern 3: Schema Evolution

Edited `shared/schemas/verdict.py`? Propagate changes:

```bash
/schema-change-propagate
```

Auto-updates:
- All API docs (OpenAPI schema)
- All tests (fixtures + parametrization)
- All Temporal activities consuming the schema
- Compliance report

**Time**: ~2-3 minutes. Zero manual sync.

### Pattern 4: Test & Validate Before Merge

Before pushing a PR:

```bash
/constitutional-compliance-audit --strict true
/test-coverage-full
/phase-boundary-validation  # If moving between phases
```

Each outputs structured reports:
- `.specify/compliance_report.json`
- `.specify/test_report.md`
- `.specify/phase_{N}_complete.md`

Suitable for CI/CD gates.

### Pattern 5: Rapid Iteration with Demo

Preparing for live demo or user testing?

```bash
/dev-quick-restart
/prepare-demo
```

Seeds demo fixtures, validates all services, outputs checklist. Ready in 2-3 minutes.

### Pattern 6: CI/CD Setup (GitHub Actions)

One-time setup for continuous checks:

```bash
/ci-pipeline-setup
```

Creates `.github/workflows/`:
- `test.yml` (pytest + coverage + compliance)
- `lint.yml` (black, isort, mypy, pylint)
- `schema-validation.yml` (ensures typed boundaries)
- Optional `deploy-local.yml` (e2e on docker-compose)

---

## Command-to-Cursor Integration

### Option A: Direct Slash Commands (Easiest)

In Cursor's inline chat or command palette:

```
/project-init-from-scratch
```

Cursor parses `.specify/commands.md` and executes the command definition.

### Option B: Chained Commands (Powerful)

String together multiple commands with pipes:

```bash
/project-init-from-scratch && \
/test-coverage-full && \
/constitutional-compliance-audit --strict true && \
/prepare-demo
```

Runs sequentially; one failure stops the chain.

### Option C: MCP Server Integration (Advanced)

If Cursor has MCP server support for SpecKit:

1. Define MCP endpoint in `.cursor/mcp_config.json`
2. Reference commands by name in prompts
3. Cursor executes via MCP, captures output

---

## Compliance Enforcement

### Pre-Commit Hook

Add to `.git/hooks/pre-commit` or `pre-commit` config:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: speckit-compliance
        name: SpecKit Constitution Compliance
        entry: python -m speckit.cli compliance-check-constitution --strict false
        language: system
        stages: [commit]
```

### CI Gate (GitHub Actions)

In `.github/workflows/test.yml`:

```yaml
- name: SpecKit Compliance Audit
  run: |
    /compliance-check-constitution --strict true --report-path .specify/compliance_report.json
    cat .specify/compliance_report.json
```

Fails the workflow if constitution violated.

---

## Debugging Commands

### See Generated Files

Each command outputs file paths at the end. Example:

```
✓ /scaffold-session-service
  Generated:
    - services/session/session_service.py (284 lines)
    - services/session/models.py (156 lines)
    - services/session/__init__.py
  Schemas exported:
    - shared/schemas/session.py (validated)
  Ready for import: from services.session import SessionService
```

### Validate Without Committing

Use `--dry-run` flag on any command:

```bash
/scaffold-session-service --dry-run true
```

Outputs proposed changes without writing files. Preview before committing.

### Regenerate Specific Module

Many commands support `--regenerate true` to overwrite existing files:

```bash
/scaffold-fastapi-session-routes --regenerate true
```

Useful for re-applying defaults after manual tweaks.

---

## Troubleshooting

### Command Not Found

Check `.specify/commands.md` exists and is readable:

```bash
ls -la .specify/commands.md
```

### Schema Validation Errors

If `/compliance-check-constitution` reports untyped boundaries:

1. Identify violating service in report
2. Run: `/scaffold-{service}-service --regenerate true`
3. Re-run compliance check

### Test Coverage Below 80%

Run detailed report:

```bash
/generate-schema-tests --include-fixtures true --schemas-path shared/schemas
/generate-policy-tests --pass-threshold 0.80 --review-threshold 0.55
```

Then:

```bash
make test --cov=services --cov=shared --cov-report=html
open htmlcov/index.html  # Review gaps
```

### State Machine Complexity

If `/generate-state-machine-docs` shows too many transitions:

1. Review `.specify/memory/constitution.md` §VI (Layered Evidence Architecture)
2. Ensure retries only within challenge states
3. No non-monotonic transitions
4. Run: `/compliance-check-constitution --strict true`

---

## Quick Commands Reference

| Intent | Command | Time |
|--------|---------|------|
| Start from scratch | `/project-init-from-scratch` | 15-20m |
| Add service | `/rapid-service-scaffold` | 5m |
| Update schema | `/schema-change-propagate` | 2-3m |
| Full test + audit | `/constitutional-compliance-audit --strict true && /test-coverage-full` | 5-8m |
| Gen docs | `/docs-regenerate-full` | 3m |
| Setup CI | `/ci-pipeline-setup` | 5m |
| Demo ready | `/dev-quick-restart && /prepare-demo` | 2-3m |
| Validate phase | `/phase-boundary-validation` | 10m + manual |

---

## Best Practices

### 1. Commit Generated Files

SpecKit output is deterministic and should be version controlled:

```bash
/project-init-from-scratch
git add -A
git commit -m "feat: bootstrap MVP with SpecKit"
```

Regeneration (e.g., after schema change) is tracked as a normal commit.

### 2. Update Constitution When Changing Stack

If you deviate from the constitution (e.g., swap FastAPI for Quart), amend it:

```bash
# Edit .specify/memory/constitution.md
# Bump CONSTITUTION_VERSION in the file
git add .specify/memory/constitution.md
git commit -m "chore: update constitution - switch to Quart (v1.1.0)"
```

Compliance checks will pass with the new version.

### 3. Use `--strict true` Before PR

Before pushing:

```bash
/compliance-check-constitution --strict true
```

Exit code 0 = safe to merge. Non-zero = fix violations first.

### 4. Schedule Compliance Audits

Run periodically in CI to catch drift:

```yaml
# .github/workflows/nightly-audit.yml
name: Nightly Compliance Audit
on:
  schedule:
    - cron: '0 2 * * *'
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: SpecKit Audit
        run: /compliance-check-constitution --strict true
```

---

## Integration with Existing `.specify/` Structure

If you already have `.specify/` files, merge:

### Merge Commands

```bash
# Append to existing .specify/commands.md
cat bhasha_commands.md >> .specify/commands.md
```

Or manually copy-paste sections.

### Merge Loops

```bash
# Append to existing .specify/loops.md
cat bhasha_loops.md >> .specify/loops.md
```

### Update Constitution

If `.specify/memory/constitution.md` exists, review differences:

```bash
# Compare
diff .specify/memory/constitution.md bhasha_constitution.md
```

Merge if compatible, or create `.specify/memory/bhasha_constitution.md` alongside.

---

## Next Steps

1. **Copy files**: `cp bhasha_commands.md .specify/commands.md`, etc.
2. **Verify constitution**: Check `.specify/memory/constitution.md` is present
3. **Try a command**: `/project-init-from-scratch --dry-run true`
4. **Set up CI**: `/ci-pipeline-setup`
5. **Add to pre-commit**: Ensure `/.git/hooks/pre-commit` or `.pre-commit-config.yaml` runs compliance checks
6. **Document in README**: Add "SpecKit Commands" section to project README

---

## Support

For issues or feature requests:
1. Check `.specify/commands.md` parameters and contracts
2. Run `/compliance-check-constitution --strict false` for detailed report
3. Review `.specify/memory/constitution.md` for governance
4. Consult `docs/liveliness_check_mvp.md` for architecture context

All commands are designed to be self-documenting; use `--help` (if implemented) or review the command definition in `.specify/commands.md`.