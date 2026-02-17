from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import apps.api.main as api_main


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
