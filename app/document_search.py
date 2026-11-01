
import re
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Document, DocumentChunk


@dataclass(frozen=True)
class DocumentChunkData:
    tenant_id: str
    document_id: str
    chunk_index: int
    text: str


class DocumentSearch:
    def __init__(
        self,
        db: Session | None = None,
        chunk_size: int = 120,
        chunk_overlap: int = 20,
    ):
        if chunk_size < 1:
            raise ValueError("chunk_size must be positive")

        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError(
                "chunk_overlap must be non-negative and smaller than chunk_size"
            )

        self.db = db
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._chunks: list[DocumentChunkData] = []

    def add_document(
        self,
        tenant_id: str,
        document_id: str,
        text: str,
    ) -> list[DocumentChunkData]:
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

            chunks.append(
                DocumentChunkData(
                    tenant_id=tenant_id,
                    document_id=document_id,
                    chunk_index=len(chunks),
                    text=" ".join(chunk_words),
                )
            )

            if start + self.chunk_size >= len(words):
                break

        if self.db is not None:
            try:
                document = self.db.scalar(
                    select(Document).where(
                        Document.tenant_id == tenant_id,
                        Document.document_id == document_id,
                    )
                )

                if document is None:
                    document = Document(
                        tenant_id=tenant_id,
                        document_id=document_id,
                    )
                    self.db.add(document)
                    self.db.flush()
                else:
                    self.db.execute(
                        delete(DocumentChunk).where(
                            DocumentChunk.document_pk == document.id
                        )
                    )
                    self.db.flush()

                for chunk in chunks:
                    self.db.add(
                        DocumentChunk(
                            document_pk=document.id,
                            chunk_index=chunk.chunk_index,
                            text=chunk.text,
                        )
                    )

                self.db.commit()

            except Exception:
                self.db.rollback()
                raise

        else:
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

        if self.db is not None:
            statement = (
                select(Document, DocumentChunk)
                .join(
                    DocumentChunk,
                    Document.id == DocumentChunk.document_pk,
                )
                .where(Document.tenant_id == tenant_id)
            )

            rows = self.db.execute(statement).all()

            chunks = [
                DocumentChunkData(
                    tenant_id=document.tenant_id,
                    document_id=document.document_id,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                )
                for document, chunk in rows
            ]
        else:
            chunks = self._chunks

        results = []

        for chunk in chunks:
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
