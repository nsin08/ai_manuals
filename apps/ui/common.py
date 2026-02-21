from __future__ import annotations

import json
import urllib.request
import uuid


def build_multipart_payload(
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


def request_json(
    url: str,
    *,
    method: str = 'GET',
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 60,
) -> dict[str, object]:
    req = urllib.request.Request(url, data=data, method=method)
    for key, value in (headers or {}).items():
        req.add_header(key, value)

    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode('utf-8'))
