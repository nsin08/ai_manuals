from __future__ import annotations

from packages.adapters.retrieval.metadata_vector_search_adapter import MetadataVectorSearchAdapter
from packages.domain.models import Chunk
from packages.ports.embedding_port import EmbeddingPort


class FakeEmbedding(EmbeddingPort):
    def embed_text(self, text: str) -> list[float]:
        if 'torque' in text.lower():
            return [1.0, 0.0]
        return [0.0, 1.0]


def test_metadata_vector_search_uses_chunk_embeddings() -> None:
    chunks = [
        Chunk(
            chunk_id='a',
            doc_id='d1',
            content_type='text',
            page_start=1,
            page_end=1,
            content_text='torque value',
            metadata={'embedding': [1.0, 0.0]},
        ),
        Chunk(
            chunk_id='b',
            doc_id='d1',
            content_type='text',
            page_start=2,
            page_end=2,
            content_text='temperature value',
            metadata={'embedding': [0.0, 1.0]},
        ),
    ]

    results = MetadataVectorSearchAdapter(FakeEmbedding()).search('torque spec', chunks, top_k=2)
    assert results
    assert results[0].chunk.chunk_id == 'a'
