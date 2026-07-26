"""Temporal video activity worker."""
from __future__ import annotations

import asyncio
import os

from temporalio.client import Client
from temporalio.worker import Worker

from services.video import plugins  # noqa: F401 — registers all plugins
from services.video.activity import analyze_verification_job
from shared.utils.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

TASK_QUEUE = "video-verification"


async def run_worker() -> None:
    host = os.getenv("TEMPORAL_HOST", "localhost:7233")
    client = await Client.connect(host)
    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        activities=[analyze_verification_job],
    ):
        logger.info("video_worker_started", task_queue=TASK_QUEUE, host=host)
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(run_worker())
