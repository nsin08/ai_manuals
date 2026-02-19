from __future__ import annotations

import os
import time
import urllib.error
import urllib.parse

import streamlit as st

from common import build_multipart_payload, request_json


st.set_page_config(page_title='Admin - Equipment Manuals', layout='wide')

default_api_base_url = os.getenv('API_BASE_URL', 'http://api:8000')
api_base_url = st.sidebar.text_input('API Base URL', value=default_api_base_url)
ingest_timeout_seconds = int(os.getenv('INGEST_TIMEOUT_SECONDS', '1800'))
status_poll_seconds = int(os.getenv('JOB_POLL_SECONDS', '2'))

st.sidebar.markdown('### Navigation')
st.sidebar.markdown('- [Chat](/)')
st.sidebar.markdown('- [Developer](/dev)')
st.sidebar.markdown('- **Admin** (`/admin`)')

st.title('Admin Console')
st.caption('Operate ingestion lifecycle: upload, ingest, delete, and inspect status/statistics.')

if 'active_job_id' not in st.session_state:
    st.session_state.active_job_id = ''


def _render_job_status(job_payload: dict[str, object]) -> None:
    status = str(job_payload.get('status') or 'unknown')
    stage = str(job_payload.get('stage') or '-')
    message = str(job_payload.get('message') or '')
    processed = int(job_payload.get('processed_pages') or 0)
    total = int(job_payload.get('total_pages') or 0)

    st.subheader('Active Job')
    st.caption(f"Job ID: {job_payload.get('job_id')}")

    m1, m2, m3 = st.columns(3)
    m1.metric('Status', status)
    m2.metric('Stage', stage)
    m3.metric('Progress', f'{processed}/{total}' if total > 0 else str(processed))

    if total > 0:
        st.progress(min(max(processed / total, 0.0), 1.0))

    if message:
        st.info(message)

    if status == 'failed':
        st.error(str(job_payload.get('error') or 'Unknown error'))

    if status == 'completed' and isinstance(job_payload.get('result'), dict):
        st.success('Job completed.')
        st.json(job_payload.get('result'))


job_payload: dict[str, object] | None = None
active_job_id = str(st.session_state.get('active_job_id') or '')
if active_job_id:
    try:
        job_payload = request_json(f'{api_base_url}/jobs/{active_job_id}', timeout=30)
        _render_job_status(job_payload)
        if str(job_payload.get('status') or '') in {'queued', 'running'}:
            time.sleep(max(status_poll_seconds, 1))
            st.rerun()
    except urllib.error.HTTPError as exc:
        st.error(f'Failed to fetch job status: HTTP {exc.code}')
    except urllib.error.URLError as exc:
        st.error(f'Failed to fetch job status: {exc}')

col_a, col_b = st.columns([1, 1])

with col_a:
    st.subheader('Upload and Ingest')
    upload_file = st.file_uploader('PDF manual', type=['pdf'])
    upload_doc_id = st.text_input('Optional doc_id', value='')
    if st.button('Upload PDF'):
        if upload_file is None:
            st.error('Select a PDF file first.')
        else:
            try:
                fields: dict[str, str] = {}
                if upload_doc_id.strip():
                    fields['doc_id'] = upload_doc_id.strip()
                payload_bytes, content_type = build_multipart_payload(
                    file_field='file',
                    file_name=upload_file.name,
                    file_bytes=upload_file.getvalue(),
                    file_content_type='application/pdf',
                    fields=fields,
                )
                payload = request_json(
                    f'{api_base_url}/jobs/upload',
                    method='POST',
                    data=payload_bytes,
                    headers={
                        'Content-Type': content_type,
                        'Content-Length': str(len(payload_bytes)),
                    },
                    timeout=ingest_timeout_seconds,
                )
                st.session_state.active_job_id = str(payload.get('job_id') or '')
                st.success(f"Started upload job: {st.session_state.active_job_id}")
                st.rerun()
            except urllib.error.HTTPError as exc:
                body = exc.read().decode('utf-8', errors='replace')
                st.error(f'Upload failed: HTTP {exc.code} - {body}')
            except TimeoutError:
                st.error(
                    'Upload timed out while sending file to API. '
                    f'Increase INGEST_TIMEOUT_SECONDS (current: {ingest_timeout_seconds}).'
                )
            except urllib.error.URLError as exc:
                st.error(f'Upload request failed: {exc}')

    st.subheader('Ingest Catalog Doc')
    try:
        catalog = request_json(f'{api_base_url}/catalog', timeout=30)
        catalog_docs = catalog.get('documents') or []
        catalog_ingestable = [
            str(row.get('doc_id'))
            for row in catalog_docs
            if isinstance(row, dict)
            and row.get('doc_id')
            and str(row.get('status') or '').lower() == 'present'
        ]
    except urllib.error.URLError:
        catalog_ingestable = []

    catalog_doc_id = st.selectbox('Catalog doc_id', options=catalog_ingestable or [''])
    if st.button('Ingest Selected Catalog Doc'):
        if not catalog_doc_id:
            st.error('No ingestable catalog document available.')
        else:
            try:
                encoded = urllib.parse.quote(catalog_doc_id, safe='')
                payload = request_json(
                    f'{api_base_url}/jobs/ingest/{encoded}',
                    method='POST',
                    timeout=60,
                )
                st.session_state.active_job_id = str(payload.get('job_id') or '')
                st.success(f"Started catalog ingestion job: {st.session_state.active_job_id}")
                st.rerun()
            except urllib.error.HTTPError as exc:
                body = exc.read().decode('utf-8', errors='replace')
                st.error(f'Ingestion failed: HTTP {exc.code} - {body}')
            except urllib.error.URLError as exc:
                st.error(f'Ingestion request failed: {exc}')

    if st.button('Clear Active Job'):
        st.session_state.active_job_id = ''
        st.rerun()

with col_b:
    st.subheader('Ingested Documents')
    try:
        ingested = request_json(f'{api_base_url}/ingested/docs', timeout=30)
        rows = ingested.get('documents') or []
        rows = [row for row in rows if isinstance(row, dict)]
    except urllib.error.URLError as exc:
        rows = []
        st.error(f'Failed to load ingested docs: {exc}')

    total_docs = len(rows)
    total_chunks = sum(int(row.get('total_chunks') or 0) for row in rows)
    m1, m2 = st.columns(2)
    m1.metric('Ingested Docs', total_docs)
    m2.metric('Total Chunks', total_chunks)

    if rows:
        doc_options = [str(row.get('doc_id')) for row in rows if row.get('doc_id')]
        delete_doc_id = st.selectbox('Delete doc_id', options=doc_options)
        if st.button('Delete Selected Doc'):
            try:
                encoded = urllib.parse.quote(delete_doc_id, safe='')
                payload = request_json(f'{api_base_url}/ingested/{encoded}', method='DELETE', timeout=60)
                st.success(f"Deleted {payload.get('doc_id')}")
                st.rerun()
            except urllib.error.HTTPError as exc:
                body = exc.read().decode('utf-8', errors='replace')
                st.error(f'Delete failed: HTTP {exc.code} - {body}')
            except urllib.error.URLError as exc:
                st.error(f'Delete request failed: {exc}')

        table_rows = [
            {
                'doc_id': row.get('doc_id'),
                'total_chunks': row.get('total_chunks'),
                'updated_at': row.get('updated_at'),
                'catalog_status': row.get('catalog_status'),
                'in_catalog': row.get('in_catalog'),
            }
            for row in rows
        ]
        st.dataframe(table_rows, use_container_width=True)

        with st.expander('Type Breakdown'):
            st.json(
                {
                    str(row.get('doc_id')): row.get('by_type')
                    for row in rows
                    if row.get('doc_id')
                }
            )

st.subheader('Recent Jobs')
try:
    jobs_payload = request_json(f'{api_base_url}/jobs?limit=20', timeout=30)
    jobs = jobs_payload.get('jobs') or []
    if jobs:
        table_rows = [
            {
                'job_id': row.get('job_id'),
                'kind': row.get('kind'),
                'doc_id': row.get('doc_id'),
                'status': row.get('status'),
                'stage': row.get('stage'),
                'processed_pages': row.get('processed_pages'),
                'total_pages': row.get('total_pages'),
                'updated_at': row.get('updated_at'),
            }
            for row in jobs
            if isinstance(row, dict)
        ]
        st.dataframe(table_rows, use_container_width=True)
except urllib.error.URLError as exc:
    st.info(f'Jobs API unavailable: {exc}')
