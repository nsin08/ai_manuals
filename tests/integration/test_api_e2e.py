from __future__ import annotations

from pathlib import Path
import time

from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.ingestion_jobs import IngestionJobManager


def test_upload_query_answer_flow(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(api_main, 'ASSETS_DIR', tmp_path / 'assets')
    monkeypatch.setattr(api_main, 'UPLOADS_DIR', tmp_path / 'uploads')

    client = TestClient(api_main.app)
    sample_pdf = Path('.context/project/data/22b-um001_-en-e.pdf')
    assert sample_pdf.exists()

    with sample_pdf.open('rb') as fh:
        upload_response = client.post(
            '/upload',
            data={'doc_id': 'rockwell_e2e'},
            files={'file': ('22b-um001_-en-e.pdf', fh, 'application/pdf')},
        )

    assert upload_response.status_code == 200
    upload_payload = upload_response.json()
    uploaded_doc_id = upload_payload['doc_id']
    assert uploaded_doc_id.startswith('rockwell_e2e_')
    assert upload_payload['total_chunks'] > 0

    answer_response = client.get(
        '/answer',
        params={
            'q': 'fault code corrective action',
            'doc_id': uploaded_doc_id,
            'top_n': 5,
        },
    )
    assert answer_response.status_code == 200
    answer_payload = answer_response.json()
    assert answer_payload['status'] in {'ok', 'not_found', 'needs_follow_up'}
    assert 'citations' in answer_payload


def test_background_upload_job_flow(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(api_main, 'ASSETS_DIR', tmp_path / 'assets')
    monkeypatch.setattr(api_main, 'UPLOADS_DIR', tmp_path / 'uploads')
    monkeypatch.setattr(api_main, 'JOB_MANAGER', IngestionJobManager(max_workers=1))

    client = TestClient(api_main.app)
    sample_pdf = Path('.context/project/data/22b-um001_-en-e.pdf')
    assert sample_pdf.exists()

    with sample_pdf.open('rb') as fh:
        job_response = client.post(
            '/jobs/upload',
            data={'doc_id': 'rockwell_job'},
            files={'file': ('22b-um001_-en-e.pdf', fh, 'application/pdf')},
        )

    assert job_response.status_code == 200
    job_payload = job_response.json()
    job_id = str(job_payload['job_id'])
    assert job_payload['status'] in {'queued', 'running', 'completed'}

    terminal: dict[str, object] | None = None
    for _ in range(120):
        status_response = client.get(f'/jobs/{job_id}')
        assert status_response.status_code == 200
        status_payload = status_response.json()
        if status_payload['status'] in {'completed', 'failed'}:
            terminal = status_payload
            break
        time.sleep(0.1)

    assert terminal is not None
    assert terminal['status'] == 'completed'
    result = terminal.get('result') or {}
    assert int(result.get('total_chunks') or 0) > 0


def test_ingested_validation_and_reingest_flow(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(api_main, 'ASSETS_DIR', tmp_path / 'assets')
    monkeypatch.setattr(api_main, 'UPLOADS_DIR', tmp_path / 'uploads')
    monkeypatch.setattr(api_main, 'JOB_MANAGER', IngestionJobManager(max_workers=1))

    client = TestClient(api_main.app)
    sample_pdf = Path('.context/project/data/22b-um001_-en-e.pdf')
    assert sample_pdf.exists()

    with sample_pdf.open('rb') as fh:
        upload_response = client.post(
            '/upload',
            data={'doc_id': 'visual_ops'},
            files={'file': ('22b-um001_-en-e.pdf', fh, 'application/pdf')},
        )

    assert upload_response.status_code == 200
    uploaded_doc_id = str(upload_response.json()['doc_id'])

    validation_response = client.get(f'/ingested/{uploaded_doc_id}/validation')
    assert validation_response.status_code == 200
    validation_payload = validation_response.json()
    assert bool((validation_payload.get('visual_contract') or {}).get('strict_valid'))
    assert isinstance(validation_payload.get('ingestion_runs'), list)
    assert validation_payload['ingestion_runs']

    chunks_response = client.get(f'/ingested/{uploaded_doc_id}/visual-chunks', params={'limit': 5})
    assert chunks_response.status_code == 200
    chunks_payload = chunks_response.json()
    assert int(chunks_payload.get('total') or 0) >= len(chunks_payload.get('rows') or [])

    regen_response = client.post(f'/ingested/{uploaded_doc_id}/visual-artifacts/generate')
    assert regen_response.status_code == 200
    regen_payload = regen_response.json()
    assert regen_payload.get('result', {}).get('generated') is True

    reingest_response = client.post(f'/jobs/reingest/{uploaded_doc_id}')
    assert reingest_response.status_code == 200
    job_id = str(reingest_response.json()['job_id'])
    terminal: dict[str, object] | None = None

    for _ in range(300):
        status_response = client.get(f'/jobs/{job_id}')
        assert status_response.status_code == 200
        status_payload = status_response.json()
        if status_payload['status'] in {'completed', 'failed'}:
            terminal = status_payload
            break
        time.sleep(0.1)

    assert terminal is not None
    assert terminal['status'] == 'completed'
    terminal_result = terminal.get('result') or {}
    assert int(terminal_result.get('total_chunks') or 0) > 0
    assert isinstance(terminal_result.get('ingestion_run'), dict)
