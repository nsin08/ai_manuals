from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from typing import Any, Callable
import traceback
import uuid


@dataclass
class IngestionJob:
    job_id: str
    kind: str
    doc_id: str | None
    filename: str | None
    status: str
    created_at: str
    updated_at: str
    stage: str
    message: str | None
    processed_pages: int
    total_pages: int
    error: str | None
    result: dict[str, Any] | None


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class IngestionJobManager:
    def __init__(self, max_workers: int = 2, max_jobs: int = 200) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max(1, max_workers))
        self._max_jobs = max(20, max_jobs)
        self._lock = Lock()
        self._jobs: dict[str, IngestionJob] = {}

    def submit(
        self,
        *,
        kind: str,
        doc_id: str | None,
        filename: str | None,
        task: Callable[[Callable[[dict[str, Any]], None]], dict[str, Any]],
    ) -> IngestionJob:
        job_id = str(uuid.uuid4())
        now = _now_iso()
        job = IngestionJob(
            job_id=job_id,
            kind=kind,
            doc_id=doc_id,
            filename=filename,
            status='queued',
            created_at=now,
            updated_at=now,
            stage='queued',
            message='Queued for processing',
            processed_pages=0,
            total_pages=0,
            error=None,
            result=None,
        )

        with self._lock:
            self._jobs[job_id] = job
            self._trim_jobs_locked()

        self._executor.submit(self._run_job, job_id, task)
        return self.get(job_id)

    def get(self, job_id: str) -> IngestionJob:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(job_id)
            return IngestionJob(**job.__dict__)

    def list(self, limit: int = 50) -> list[IngestionJob]:
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda row: row.created_at, reverse=True)
            return [IngestionJob(**row.__dict__) for row in jobs[: max(1, limit)]]

    def _update_job(self, job_id: str, **updates: Any) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            for key, value in updates.items():
                setattr(job, key, value)
            job.updated_at = _now_iso()

    def _run_job(
        self,
        job_id: str,
        task: Callable[[Callable[[dict[str, Any]], None]], dict[str, Any]],
    ) -> None:
        self._update_job(job_id, status='running', stage='running', message='Started')

        def progress(payload: dict[str, Any]) -> None:
            self._update_job(
                job_id,
                stage=str(payload.get('stage') or 'running'),
                message=str(payload.get('message') or ''),
                processed_pages=int(payload.get('processed_pages') or 0),
                total_pages=int(payload.get('total_pages') or 0),
            )

        try:
            result = task(progress)
            self._update_job(
                job_id,
                status='completed',
                stage='completed',
                message='Completed',
                result=result,
                error=None,
            )
        except Exception as exc:
            self._update_job(
                job_id,
                status='failed',
                stage='failed',
                message='Failed',
                error=f'{exc}\n{traceback.format_exc()}',
                result=None,
            )

    def _trim_jobs_locked(self) -> None:
        if len(self._jobs) <= self._max_jobs:
            return
        ordered = sorted(self._jobs.values(), key=lambda row: row.created_at, reverse=True)
        keep = {row.job_id for row in ordered[: self._max_jobs]}
        for job_id in list(self._jobs.keys()):
            if job_id not in keep:
                del self._jobs[job_id]
