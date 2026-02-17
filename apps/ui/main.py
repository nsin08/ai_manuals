from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import streamlit as st


default_api_base_url = os.getenv('API_BASE_URL', 'http://api:8000')
API_BASE_URL = st.sidebar.text_input('API Base URL', value=default_api_base_url)

st.sidebar.caption(
    'If UI runs in Docker, use http://api:8000. '
    'If UI runs on host machine, use http://localhost:8000.'
)

st.title('Equipment Manuals Chatbot (MVP Scaffold)')
st.caption('Phase 0 UI placeholder: health checks and contract visibility.')


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


st.subheader('Next Phase')
st.write('Upload and chat workflow will be implemented in later phases.')
