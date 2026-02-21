from __future__ import annotations

from packages.adapters.vision.noop_vision_adapter import NoopVisionAdapter
from packages.adapters.vision.ollama_vision_adapter import OllamaVisionAdapter
from packages.ports.vision_port import VisionPort


def create_vision_adapter(
    *,
    provider: str,
    base_url: str,
    model: str,
) -> VisionPort:
    normalized = provider.strip().lower()
    if normalized in {'ollama', 'local'} and model.strip():
        return OllamaVisionAdapter(base_url=base_url, model=model)
    return NoopVisionAdapter()
