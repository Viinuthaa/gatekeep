
from uuid import uuid4

from sqlalchemy import select

from app.database import SessionLocal
from app.document_search import DocumentSearch
from app.models import Document


def test_document_persists_and_replacement_removes_old_chunks():
    tenant_id = f"test-tenant-{uuid4().hex}"
    document_id = f"test-doc-{uuid4().hex}"

    db = SessionLocal()

    try:
        search = DocumentSearch(db=db)

        search.add_document(
            tenant_id=tenant_id,
            document_id=document_id,
            text="Unique oldcontent biology material",
        )

        old_results = search.search(tenant_id, "oldcontent")
        assert old_results

        search.add_document(
            tenant_id=tenant_id,
            document_id=document_id,
            text="Unique newcontent chemistry material",
        )

        db.expire_all()

        old_results = search.search(tenant_id, "oldcontent")
        new_results = search.search(tenant_id, "newcontent")

        assert old_results == []
        assert new_results
        assert new_results[0]["document_id"] == document_id

        stored_document = db.scalar(
            select(Document).where(
                Document.tenant_id == tenant_id,
                Document.document_id == document_id,
            )
        )

        assert stored_document is not None
        assert len(stored_document.chunks) == 1

    finally:
        db.rollback()

        document = db.scalar(
            select(Document).where(
                Document.tenant_id == tenant_id,
                Document.document_id == document_id,
            )
        )

        if document:
            db.delete(document)
            db.commit()

        db.close()
