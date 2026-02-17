from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid

import streamlit as st


def _build_multipart_payload(
    *,
    file_field: str,
    file_name: str,
    file_bytes: bytes,
    file_content_type: str,
    fields: dict[str, str],
) -> tuple[bytes, str]:
    boundary = f'----CodexBoundary{uuid.uuid4().hex}'
    chunks: list[bytes] = []

    for key, value in fields.items():
        chunks.append(f'--{boundary}\r\n'.encode('utf-8'))
        chunks.append(
            f'Content-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode('utf-8')
        )

    chunks.append(f'--{boundary}\r\n'.encode('utf-8'))
    chunks.append(
        (
            f'Content-Disposition: form-data; name="{file_field}"; '
            f'filename="{file_name}"\r\n'
            f'Content-Type: {file_content_type}\r\n\r\n'
        ).encode('utf-8')
    )
    chunks.append(file_bytes)
    chunks.append(b'\r\n')
    chunks.append(f'--{boundary}--\r\n'.encode('utf-8'))

    payload = b''.join(chunks)
    content_type = f'multipart/form-data; boundary={boundary}'
    return payload, content_type


def _request_json(url: str, *, method: str = 'GET', data: bytes | None = None, headers: dict[str, str] | None = None, timeout: int = 60) -> dict[str, object]:
    req = urllib.request.Request(url, data=data, method=method)
    for k, v in (headers or {}).items():
        req.add_header(k, v)

    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode('utf-8'))


default_api_base_url = os.getenv('API_BASE_URL', 'http://api:8000')
API_BASE_URL = st.sidebar.text_input('API Base URL', value=default_api_base_url)

st.sidebar.caption(
    'If UI runs in Docker, use http://api:8000. '
    'If UI runs on host machine, use http://localhost:8000.'
)

st.title('Equipment Manuals Chatbot (MVP)')
st.caption('Phase 4 scaffold: upload, chat with sources, and golden-question evaluation.')

if st.button('Check API Health'):
    try:
        payload = _request_json(f'{API_BASE_URL}/health', timeout=5)
        st.success('API reachable')
        st.json(payload)
    except urllib.error.URLError as exc:
        st.error(f'API health check failed: {exc}')

if st.button('Check Contract Health'):
    try:
        payload = _request_json(f'{API_BASE_URL}/health/contracts', timeout=5)
        st.json(payload)
    except urllib.error.URLError as exc:
        st.error(f'Contract health check failed: {exc}')

st.subheader('Upload Manual (Phase 4)')
uploaded_pdf = st.file_uploader('Select PDF manual', type=['pdf'])
upload_doc_id = st.text_input('Doc ID for Upload (optional)', value='')

if st.button('Upload and Ingest PDF'):
    if uploaded_pdf is None:
        st.error('Choose a PDF file first.')
    else:
        try:
            fields: dict[str, str] = {}
            if upload_doc_id.strip():
                fields['doc_id'] = upload_doc_id.strip()

            payload_bytes, content_type = _build_multipart_payload(
                file_field='file',
                file_name=uploaded_pdf.name,
                file_bytes=uploaded_pdf.getvalue(),
                file_content_type='application/pdf',
                fields=fields,
            )

            payload = _request_json(
                f'{API_BASE_URL}/upload',
                method='POST',
                data=payload_bytes,
                headers={
                    'Content-Type': content_type,
                    'Content-Length': str(len(payload_bytes)),
                },
                timeout=240,
            )

            st.session_state['last_uploaded_doc_id'] = payload.get('doc_id')
            if payload.get('doc_id'):
                st.session_state['answer_doc_id_input'] = str(payload['doc_id'])
            st.success('Upload and ingestion completed')
            st.json(payload)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode('utf-8', errors='replace')
            st.error(f'Upload failed: HTTP {exc.code} - {body}')
        except urllib.error.URLError as exc:
            st.error(f'Upload request failed: {exc}')

st.subheader('Document Catalog')
if st.button('Load Catalog'):
    try:
        payload = _request_json(f'{API_BASE_URL}/catalog', timeout=10)
        st.json(payload)
    except urllib.error.URLError as exc:
        st.error(f'Catalog request failed: {exc}')

st.subheader('Ingestion Trigger')
ingest_doc_id = st.text_input('Catalog Doc ID', value='rockwell_powerflex_40')
if st.button('Ingest Catalog Doc'):
    try:
        encoded_doc_id = urllib.parse.quote(ingest_doc_id, safe='')
        payload = _request_json(
            f'{API_BASE_URL}/ingest/{encoded_doc_id}',
            method='POST',
            timeout=240,
        )
        st.success('Ingestion completed')
        st.json(payload)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        st.error(f'Ingestion failed: HTTP {exc.code} - {body}')
    except urllib.error.URLError as exc:
        st.error(f'Ingestion request failed: {exc}')

st.subheader('Ask Grounded Question')
default_doc_id = st.session_state.get('last_uploaded_doc_id', 'rockwell_powerflex_40')
answer_query = st.text_input(
    'Question',
    value='What does fault F005 mean and what action is recommended?',
)
answer_doc_id = st.text_input('Doc ID Filter (optional)', value=default_doc_id, key='answer_doc_id_input')
answer_top_n = st.slider('Answer Evidence Top N', min_value=1, max_value=20, value=6)

if st.button('Ask Question'):
    try:
        params = {'q': answer_query, 'top_n': str(answer_top_n)}
        if answer_doc_id.strip():
            params['doc_id'] = answer_doc_id.strip()

        payload = _request_json(f"{API_BASE_URL}/answer?{urllib.parse.urlencode(params)}", timeout=60)
        st.success(f"Answer status: {payload.get('status', 'unknown')}")

        st.markdown('#### Answer')
        st.write(payload.get('answer', ''))

        follow_up = payload.get('follow_up_question')
        if follow_up:
            st.info(f'Follow-up: {follow_up}')

        warnings = payload.get('warnings') or []
        if warnings:
            for warning in warnings:
                st.warning(str(warning))

        st.markdown('#### Sources')
        citations = payload.get('citations') or []
        if not citations:
            st.write('No citations available.')
        else:
            for citation in citations:
                st.code(str(citation.get('label', '')))

        with st.expander('Raw Answer Payload'):
            st.json(payload)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        st.error(f'Answer failed: HTTP {exc.code} - {body}')
    except urllib.error.URLError as exc:
        st.error(f'Answer request failed: {exc}')

st.subheader('Search Evidence (Debug)')
search_query = st.text_input('Search Query', value='fault code corrective action')
search_doc_id = st.text_input('Search Doc ID Filter (optional)', value='rockwell_powerflex_40')
search_top_n = st.slider('Search Top N', min_value=1, max_value=20, value=8)

if st.button('Search Evidence'):
    try:
        params = {'q': search_query, 'top_n': str(search_top_n)}
        if search_doc_id.strip():
            params['doc_id'] = search_doc_id.strip()

        payload = _request_json(f"{API_BASE_URL}/search?{urllib.parse.urlencode(params)}", timeout=60)
        st.success('Search completed')
        st.json(payload)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        st.error(f'Search failed: HTTP {exc.code} - {body}')
    except urllib.error.URLError as exc:
        st.error(f'Search request failed: {exc}')

st.subheader('Golden Evaluation (Phase 4)')
eval_doc_id = st.text_input('Golden Eval Doc Filter (optional)', value='')
eval_top_n = st.slider('Golden Eval Top N', min_value=1, max_value=20, value=6)
eval_limit = st.slider('Golden Eval Question Limit (0 = all)', min_value=0, max_value=50, value=10)

if st.button('Run Golden Evaluation'):
    try:
        params = {'top_n': str(eval_top_n), 'limit': str(eval_limit)}
        if eval_doc_id.strip():
            params['doc_id'] = eval_doc_id.strip()

        payload = _request_json(
            f"{API_BASE_URL}/evaluate/golden?{urllib.parse.urlencode(params)}",
            timeout=240,
        )

        cols = st.columns(4)
        cols[0].metric('Total', int(payload.get('total_questions', 0)))
        cols[1].metric('Passed', int(payload.get('passed_questions', 0)))
        cols[2].metric('Failed', int(payload.get('failed_questions', 0)))
        cols[3].metric('Pass Rate %', float(payload.get('pass_rate', 0.0)))

        missing_docs = payload.get('missing_docs') or []
        if missing_docs:
            st.warning(f"Missing docs: {', '.join(str(x) for x in missing_docs)}")

        rows = payload.get('results') or []
        if rows:
            compact_rows = [
                {
                    'question_id': row.get('question_id'),
                    'doc': row.get('doc'),
                    'intent': row.get('intent'),
                    'answer_status': row.get('answer_status'),
                    'pass_result': row.get('pass_result'),
                    'citation_count': row.get('citation_count'),
                    'reasons': '; '.join(row.get('reasons') or []),
                }
                for row in rows
            ]
            st.dataframe(compact_rows, use_container_width=True)

        with st.expander('Raw Evaluation Payload'):
            st.json(payload)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        st.error(f'Evaluation failed: HTTP {exc.code} - {body}')
    except urllib.error.URLError as exc:
        st.error(f'Evaluation request failed: {exc}')
