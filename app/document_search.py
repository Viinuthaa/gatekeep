
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentChunk:
    tenant_id: str
    document_id: str
    chunk_index: int
    text: str


class DocumentSearch:
    def __init__(self, chunk_size: int = 120, chunk_overlap: int = 20):
        if chunk_size < 1:
            raise ValueError("chunk_size must be positive")

        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be non-negative and smaller than chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._chunks: list[DocumentChunk] = []

    def add_document(
        self,
        tenant_id: str,
        document_id: str,
        text: str,
    ) -> list[DocumentChunk]:
        if not tenant_id.strip():
            raise ValueError("tenant_id is required")

        if not document_id.strip():
            raise ValueError("document_id is required")

        if not text.strip():
            raise ValueError("Document text cannot be empty")

        words = text.split()
        step = self.chunk_size - self.chunk_overlap
        chunks = []

        for start in range(0, len(words), step):
            chunk_words = words[start:start + self.chunk_size]

            if not chunk_words:
                break

            chunk = DocumentChunk(
                tenant_id=tenant_id,
                document_id=document_id,
                chunk_index=len(chunks),
                text=" ".join(chunk_words),
            )

            chunks.append(chunk)

            if start + self.chunk_size >= len(words):
                break

        self._chunks = [
            chunk
            for chunk in self._chunks
            if not (
                chunk.tenant_id == tenant_id
                and chunk.document_id == document_id
            )
        ]

        self._chunks.extend(chunks)

        return chunks

    def search(
        self,
        tenant_id: str,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        if not tenant_id.strip():
            raise ValueError("tenant_id is required")

        if limit < 1:
            raise ValueError("limit must be positive")

        query_terms = set(re.findall(r"\w+", query.lower()))

        if not query_terms:
            return []

        results = []

        for chunk in self._chunks:
            if chunk.tenant_id != tenant_id:
                continue

            chunk_terms = set(re.findall(r"\w+", chunk.text.lower()))
            matching_terms = query_terms.intersection(chunk_terms)

            if not matching_terms:
                continue

            score = len(matching_terms) / len(query_terms)

            results.append(
                {
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                    "score": round(score, 4),
                }
            )

        results.sort(
            key=lambda item: (
                -item["score"],
                item["document_id"],
                item["chunk_index"],
            )
        )

        return results[:limit]
