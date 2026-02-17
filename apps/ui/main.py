from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

import streamlit as st


default_api_base_url = os.getenv('API_BASE_URL', 'http://api:8000')
API_BASE_URL = st.sidebar.text_input('API Base URL', value=default_api_base_url)

st.sidebar.caption(
    'If UI runs in Docker, use http://api:8000. '
    'If UI runs on host machine, use http://localhost:8000.'
)

st.title('Equipment Manuals Chatbot (MVP Scaffold)')
st.caption('Phase 1 scaffold: health, catalog, and single-document ingestion trigger.')


if st.button('Check API Health'):
    try:
        with urllib.request.urlopen(f'{API_BASE_URL}/health', timeout=5) as response:
            payload = json.loads(response.read().decode('utf-8'))
        st.success('API reachable')
        st.json(payload)
    except urllib.error.URLError as exc:
        st.error(f'API health check failed: {exc}')


if st.button('Check Contract Health'):
    try:
        with urllib.request.urlopen(f'{API_BASE_URL}/health/contracts', timeout=5) as response:
            payload = json.loads(response.read().decode('utf-8'))
        st.json(payload)
    except urllib.error.URLError as exc:
        st.error(f'Contract health check failed: {exc}')

st.subheader('Document Catalog')
if st.button('Load Catalog'):
    try:
        with urllib.request.urlopen(f'{API_BASE_URL}/catalog', timeout=10) as response:
            payload = json.loads(response.read().decode('utf-8'))
        st.json(payload)
    except urllib.error.URLError as exc:
        st.error(f'Catalog request failed: {exc}')

st.subheader('Ingestion Trigger')
ingest_doc_id = st.text_input('Doc ID', value='rockwell_powerflex_40')

if st.button('Ingest Doc'):
    try:
        encoded_doc_id = urllib.parse.quote(ingest_doc_id, safe='')
        req = urllib.request.Request(f'{API_BASE_URL}/ingest/{encoded_doc_id}', method='POST')
        with urllib.request.urlopen(req, timeout=120) as response:
            payload = json.loads(response.read().decode('utf-8'))
        st.success('Ingestion completed')
        st.json(payload)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        st.error(f'Ingestion failed: HTTP {exc.code} - {body}')
    except urllib.error.URLError as exc:
        st.error(f'Ingestion request failed: {exc}')

st.subheader('Next Phase')
st.write('Phase 2 will add hybrid retrieval and evidence ranking.')
