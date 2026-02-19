from __future__ import annotations

import os
import urllib.error
import urllib.parse

import streamlit as st

from common import request_json


st.set_page_config(page_title='Equipment Manuals Assistant', layout='wide')


def _browser_api_base(url: str) -> str:
    # Streamlit can call service DNS name inside Docker, but browser links cannot.
    if url.startswith('http://api:'):
        return url.replace('http://api:', 'http://localhost:')
    if url.startswith('https://api:'):
        return url.replace('https://api:', 'https://localhost:')
    return url


def _to_superscript(n: int) -> str:
    digits = str(n)
    sup_map = str.maketrans('0123456789', '⁰¹²³⁴⁵⁶⁷⁸⁹')
    return digits.translate(sup_map)


def _citation_link(citation: dict[str, object], api_base: str) -> str | None:
    c_doc_id = str(citation.get('doc_id') or '')
    if not c_doc_id:
        return None
    page = citation.get('page')
    pdf_url = f"{api_base}/pdf/{urllib.parse.quote(c_doc_id, safe='')}"
    if page:
        pdf_url = f'{pdf_url}#page={page}'
    return pdf_url

default_api_base_url = os.getenv('API_BASE_URL', 'http://api:8000')
api_base_url = st.sidebar.text_input('API Base URL', value=default_api_base_url)
browser_api_base_url = _browser_api_base(api_base_url)

st.sidebar.markdown('### Navigation')
st.sidebar.markdown('- **Chat** (`/`)')
st.sidebar.markdown('- [Developer](/dev)')
st.sidebar.markdown('- [Admin](/admin)')

st.sidebar.markdown('### Ingested Manuals')

if 'selected_doc_ids' not in st.session_state:
    st.session_state['selected_doc_ids'] = []
if 'chat_messages' not in st.session_state:
    st.session_state['chat_messages'] = []

doc_rows: list[dict[str, object]] = []
doc_error: str | None = None
try:
    doc_payload = request_json(f'{api_base_url}/ingested/docs', timeout=15)
    raw_docs = doc_payload.get('documents') or []
    if isinstance(raw_docs, list):
        doc_rows = [row for row in raw_docs if isinstance(row, dict)]
except urllib.error.URLError as exc:
    doc_error = str(exc)

doc_ids = [str(row.get('doc_id')) for row in doc_rows if row.get('doc_id')]

btn_col1, btn_col2 = st.sidebar.columns(2)
if btn_col1.button('Select All', use_container_width=True):
    st.session_state['selected_doc_ids'] = list(doc_ids)
if btn_col2.button('Clear All', use_container_width=True):
    st.session_state['selected_doc_ids'] = []

selected_doc_ids: list[str] = list(st.session_state.get('selected_doc_ids', []))

if doc_error:
    st.sidebar.error(f'Unable to load ingested docs: {doc_error}')

for row in doc_rows:
    doc_id = str(row.get('doc_id') or '')
    if not doc_id:
        continue
    checked = st.sidebar.checkbox(doc_id, value=doc_id in selected_doc_ids, key=f'doc_sel_{doc_id}')
    if checked and doc_id not in selected_doc_ids:
        selected_doc_ids.append(doc_id)
    if not checked and doc_id in selected_doc_ids:
        selected_doc_ids.remove(doc_id)

st.session_state['selected_doc_ids'] = selected_doc_ids

evidence_depth = st.sidebar.slider('Evidence Depth', min_value=1, max_value=20, value=8)
st.sidebar.caption(
    'Higher evidence depth retrieves more chunks before answer generation. '
    'Use 6-10 for most manuals.'
)

with st.sidebar.expander('Info'):
    st.write('Checked manuals define scope for answers.')
    st.write('No manuals selected means global search across all ingested manuals.')
    st.write('Use `/admin` to upload, delete, and inspect ingestion stats.')

st.title('Equipment Manuals Assistant')
st.caption('Grounded answers with citations from selected manuals.')

if not st.session_state['chat_messages']:
    st.info('Ask a question to start. Follow-up questions are kept in this chat thread.')

for message in st.session_state['chat_messages']:
    with st.chat_message(message['role']):
        content = str(message['content'])
        citations = message.get('citations') or []
        inline_links: list[str] = []
        if citations:
            details: list[tuple[str, str]] = []
            seen_labels: set[str] = set()
            for citation in citations:
                if not isinstance(citation, dict):
                    continue
                label = str(citation.get('label') or '').strip()
                if label and label in seen_labels:
                    continue
                if label:
                    seen_labels.add(label)
                url = _citation_link(citation, browser_api_base_url)
                if not url:
                    continue
                idx = len(inline_links) + 1
                sup = _to_superscript(idx)
                inline_links.append(
                    f'<sup><a href="{url}" target="_blank" rel="noopener">[{sup}]</a></sup>'
                )
                details.append((f'[{sup}] {label or url}', url))

            if inline_links:
                st.markdown(f'{content} {" ".join(inline_links)}', unsafe_allow_html=True)
            else:
                st.markdown(content)
            if details:
                with st.expander('Sources details'):
                    for text, url in details:
                        st.markdown(f'- [{text}]({url})')
        else:
            st.markdown(content)

prompt = st.chat_input('Ask about operation, troubleshooting, wiring, or maintenance...')
if prompt:
    st.session_state['chat_messages'].append({'role': 'user', 'content': prompt})
    with st.chat_message('user'):
        st.markdown(prompt)

    params = {
        'q': prompt,
        'top_n': str(evidence_depth),
    }
    if selected_doc_ids:
        params['doc_ids'] = ','.join(selected_doc_ids)

    try:
        payload = request_json(
            f"{api_base_url}/answer?{urllib.parse.urlencode(params)}",
            timeout=120,
        )
        answer_text = str(payload.get('answer') or '')
        status = str(payload.get('status') or 'unknown')
        warnings = payload.get('warnings') or []
        follow_up = payload.get('follow_up_question')
        citations = payload.get('citations') or []

        assistant_lines = [answer_text]
        if follow_up:
            assistant_lines.append(f'\nFollow-up: {follow_up}')
        if warnings:
            assistant_lines.append('\nWarnings:')
            assistant_lines.extend([f'- {w}' for w in warnings])
        if status != 'ok':
            assistant_lines.append(f'\nStatus: `{status}`')
        assistant_text = '\n'.join(assistant_lines)

        st.session_state['chat_messages'].append(
            {
                'role': 'assistant',
                'content': assistant_text,
                'citations': citations,
            }
        )
        st.rerun()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        error_text = f'Answer failed: HTTP {exc.code} - {body}'
        st.session_state['chat_messages'].append({'role': 'assistant', 'content': error_text})
        st.rerun()
    except urllib.error.URLError as exc:
        error_text = f'Answer request failed: {exc}'
        st.session_state['chat_messages'].append({'role': 'assistant', 'content': error_text})
        st.rerun()
