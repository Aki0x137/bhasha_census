# bhasaha_census

Local-first MVP for video liveness and human-vs-AI media verification
(Linux and macOS).

- **Architecture & MVP design**: [`docs/liveliness_check_mvp.md`](docs/liveliness_check_mvp.md)
- **Project constitution** (scope, stack, contracts, decision authority):
  [`.specify/memory/constitution.md`](.specify/memory/constitution.md)

**Stack (constitution)**: Python + pip, Temporal, LangGraph, typed Pydantic
contracts, FastAPI, Sarvam (speech/docs), AWS Bedrock (orchestration),
local video workers, SQLite + filesystem evidence. 
test
