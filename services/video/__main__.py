"""CLI entrypoint: python -m services.video.pipeline --job <path>"""
from __future__ import annotations

import argparse
import json
import sys

from services.video import plugins  # noqa: F401 — registers all plugins
from services.video.pipeline import run_verification_job
from shared.schemas.verification_job import VerificationJob


def main() -> None:
    parser = argparse.ArgumentParser(description="Run video verification pipeline")
    parser.add_argument("--job", required=True, help="Path to VerificationJob JSON file")
    args = parser.parse_args()

    with open(args.job) as f:
        raw = json.load(f)
    job = VerificationJob.model_validate(raw)
    evidence = run_verification_job(job)
    print(evidence.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
