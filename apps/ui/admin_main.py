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


_STAGE_ORDER = [
    'queued',
    'running',
    'extracting',
    'embedding',
    'persisted',
    'visual_artifacts',
    'contract_validation',
    'completed',
]


def _stage_status(current_stage: str, target_stage: str, status: str) -> str:
    if status == 'failed':
        if current_stage == target_stage:
            return 'failed'
        if _STAGE_ORDER.index(target_stage) < _STAGE_ORDER.index(current_stage):
            return 'done'
        return 'pending'

    if status == 'completed':
        return 'done'

    if _STAGE_ORDER.index(target_stage) < _STAGE_ORDER.index(current_stage):
        return 'done'
    if target_stage == current_stage:
        return 'active'
    return 'pending'


def _render_stage_timeline(stage: str, status: str) -> None:
    stage_value = stage if stage in _STAGE_ORDER else 'running'
    icons = {
        'done': 'DONE',
        'active': 'RUN',
        'pending': 'WAIT',
        'failed': 'FAIL',
    }
    st.markdown('**Pipeline Timeline**')
    cols = st.columns(len(_STAGE_ORDER))
    for idx, target in enumerate(_STAGE_ORDER):
        state = _stage_status(stage_value, target, status)
        label = target.replace('_', ' ')
        cols[idx].caption(f"{icons.get(state, state.upper())} {label}")


def _extract_gate_buckets(
    strict_errors: list[str],
    warnings: list[str],
) -> dict[str, list[str]]:
    schema_errors = [row for row in strict_errors if 'must be' in row or 'missing' in row]
    id_mapping_errors = [
        row
        for row in strict_errors
        if 'duplicate chunk_id' in row or 'not present in visual_chunks.jsonl' in row
    ]
    embedding_errors = [
        row
        for row in strict_errors
        if 'embedding' in row or 'dim' in row or 'dimensions' in row
    ]
    fallback_warnings = [row for row in warnings if 'low vision_confidence' in row]
    return {
        'schema': schema_errors,
        'id_mapping': id_mapping_errors,
        'embedding': embedding_errors,
        'fallback': fallback_warnings,
    }


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
    _render_stage_timeline(stage, status)

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
    total_visual_chunks = sum(int(row.get('visual_chunk_count') or 0) for row in rows)
    m1, m2, m3 = st.columns(3)
    m1.metric('Ingested Docs', total_docs)
    m2.metric('Total Chunks', total_chunks)
    m3.metric('Visual Chunks', total_visual_chunks)

    if rows:
        doc_options = [str(row.get('doc_id')) for row in rows if row.get('doc_id')]
        inspect_doc_id = st.selectbox('Inspect doc_id', options=doc_options, key='inspect_doc_id')
        inspect_doc = next((row for row in rows if str(row.get('doc_id')) == inspect_doc_id), None)
        delete_doc_id = st.selectbox('Delete doc_id', options=doc_options, key='delete_doc_id')
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

        c1, c2 = st.columns(2)
        with c1:
            if st.button('Reingest Selected Doc (same config)'):
                try:
                    encoded = urllib.parse.quote(inspect_doc_id, safe='')
                    payload = request_json(
                        f'{api_base_url}/jobs/reingest/{encoded}',
                        method='POST',
                        timeout=60,
                    )
                    st.session_state.active_job_id = str(payload.get('job_id') or '')
                    st.success(f"Started reingest job: {st.session_state.active_job_id}")
                    st.rerun()
                except urllib.error.HTTPError as exc:
                    body = exc.read().decode('utf-8', errors='replace')
                    st.error(f'Reingest failed: HTTP {exc.code} - {body}')
                except urllib.error.URLError as exc:
                    st.error(f'Reingest request failed: {exc}')

        with c2:
            if st.button('Regenerate Visual Artifacts'):
                try:
                    encoded = urllib.parse.quote(inspect_doc_id, safe='')
                    payload = request_json(
                        f'{api_base_url}/ingested/{encoded}/visual-artifacts/generate',
                        method='POST',
                        timeout=120,
                    )
                    st.success(
                        'Visual artifact regeneration completed '
                        f"for {payload.get('doc_id')}"
                    )
                    st.rerun()
                except urllib.error.HTTPError as exc:
                    body = exc.read().decode('utf-8', errors='replace')
                    st.error(f'Visual artifact generation failed: HTTP {exc.code} - {body}')
                except urllib.error.URLError as exc:
                    st.error(f'Visual artifact generation request failed: {exc}')

        latest_run = ((inspect_doc or {}).get('latest_ingestion_run') or {})
        latest_result = (latest_run.get('result') or {}) if isinstance(latest_run, dict) else {}
        latest_config = (latest_run.get('config') or {}) if isinstance(latest_run, dict) else {}
        if latest_result:
            st.markdown('**Latest Ingestion Metrics**')
            lm1, lm2, lm3, lm4, lm5 = st.columns(5)
            lm1.metric('Embedding Coverage', f"{float(latest_result.get('embedding_coverage') or 0.0):.2%}")
            lm2.metric('Embedding Success', int(latest_result.get('embedding_success_count') or 0))
            lm3.metric('Embedding Failed', int(latest_result.get('embedding_failed_count') or 0))
            lm4.metric(
                '2nd Pass Recovered',
                int(latest_result.get('embedding_second_pass_recovered') or 0),
            )
            lm5.metric('Embedding Warnings', int(latest_result.get('embedding_warning_count') or 0))
            st.caption(
                'Embedding config: '
                f"timeout={latest_config.get('embedding_timeout_seconds')}s, "
                f"retries={latest_config.get('embedding_max_retries')}, "
                f"second_pass_max_chars={latest_config.get('embedding_second_pass_max_chars')}"
            )

        try:
            encoded = urllib.parse.quote(inspect_doc_id, safe='')
            validation_payload = request_json(
                f'{api_base_url}/ingested/{encoded}/validation',
                timeout=30,
            )
            visual_contract = validation_payload.get('visual_contract') or {}
            strict_errors = list(visual_contract.get('strict_errors') or [])
            warnings = list(visual_contract.get('warnings') or [])
            gate_buckets = _extract_gate_buckets(strict_errors, warnings)

            st.markdown('**Deterministic Validation Gates**')
            g1, g2, g3, g4 = st.columns(4)
            g1.metric('Schema', 'PASS' if not gate_buckets['schema'] else 'FAIL')
            g2.metric('ID/Mapping', 'PASS' if not gate_buckets['id_mapping'] else 'FAIL')
            g3.metric('Embedding', 'PASS' if not gate_buckets['embedding'] else 'FAIL')
            g4.metric('Fallback', 'PASS' if not gate_buckets['fallback'] else 'WARN')

            if strict_errors:
                with st.expander(f'Contract Errors ({len(strict_errors)})'):
                    st.json(strict_errors)
            if warnings:
                with st.expander(f'Contract Warnings ({len(warnings)})'):
                    st.json(warnings)

            runs = validation_payload.get('ingestion_runs') or []
            if runs:
                with st.expander('Ingestion Run History'):
                    run_rows = [
                        {
                            'ts': row.get('ts'),
                            'source': row.get('source'),
                            'pdf_sha256': str(row.get('pdf_sha256') or '')[:12],
                            'vision_model': (row.get('config') or {}).get('vision_model'),
                            'embedding_model': (row.get('config') or {}).get('embedding_model'),
                            'validation_valid': (row.get('result') or {}).get('validation_valid'),
                            'total_chunks': (row.get('result') or {}).get('total_chunks'),
                            'embedding_coverage': (row.get('result') or {}).get('embedding_coverage'),
                            'embedding_failed_count': (row.get('result') or {}).get(
                                'embedding_failed_count'
                            ),
                            'embedding_second_pass_recovered': (row.get('result') or {}).get(
                                'embedding_second_pass_recovered'
                            ),
                            'embedding_failure_reason_count': (row.get('result') or {}).get(
                                'embedding_failure_reason_count'
                            ),
                        }
                        for row in runs
                        if isinstance(row, dict)
                    ]
                    st.dataframe(run_rows, use_container_width=True)
        except urllib.error.URLError as exc:
            st.warning(f'Validation panel unavailable: {exc}')

        try:
            encoded = urllib.parse.quote(inspect_doc_id, safe='')
            visual_payload = request_json(
                f'{api_base_url}/ingested/{encoded}/visual-chunks?limit=250',
                timeout=30,
            )
            visual_rows = [row for row in (visual_payload.get('rows') or []) if isinstance(row, dict)]
            st.markdown(f"**Visual Region Inspector** ({len(visual_rows)}/{visual_payload.get('total', 0)})")
            if visual_rows:
                selector = [
                    f"{row.get('chunk_id')} | p{row.get('page')} | {row.get('modality')}"
                    for row in visual_rows
                ]
                selected_idx = st.selectbox(
                    'Select region',
                    options=list(range(len(visual_rows))),
                    format_func=lambda idx: selector[idx],
                    key='visual_region_select',
                )
                selected_row = visual_rows[int(selected_idx)]
                st.json(selected_row)
                st.dataframe(
                    [
                        {
                            'chunk_id': row.get('chunk_id'),
                            'page': row.get('page'),
                            'modality': row.get('modality'),
                            'figure_id': row.get('figure_id'),
                            'table_id': row.get('table_id'),
                            'region_id': row.get('region_id'),
                        }
                        for row in visual_rows
                    ],
                    use_container_width=True,
                )
            else:
                st.info('No visual chunks available for this document.')
        except urllib.error.URLError as exc:
            st.warning(f'Visual region inspector unavailable: {exc}')

        table_rows = [
            {
                'doc_id': row.get('doc_id'),
                'total_chunks': row.get('total_chunks'),
                'visual_chunks': row.get('visual_chunk_count'),
                'visual_contract_valid': row.get('visual_contract_valid'),
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
