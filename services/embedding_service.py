from langchain_core.documents import Document
from core.vector_store import vector_store


def store_embeddings(candidate_id, job_id, full_name, email, phone, chunks):

    if not chunks:
        print(f"[embedding_service] No chunks to store for candidate {candidate_id}")
        return 0

    # Delete old chunks first in case this candidate was re-uploaded
    # This prevents duplicate chunks building up in ChromaDB
    delete_candidate_chunks(candidate_id)

    documents = []
    ids       = []

    for i, chunk in enumerate(chunks):
        if not chunk or not chunk.strip():
            continue

        doc = Document(
            page_content=chunk,
            metadata={
                # Store candidate info with every chunk so search results
                # know which candidate they came from
                "candidate_id": str(candidate_id),
                "job_id":       str(job_id) if job_id else "none",
                "full_name":    full_name or "Unknown",
                "email":        email     or "",
                "phone":        phone     or "",
                "chunk_index":  str(i)
            }
        )
        documents.append(doc)

        # Unique ID per chunk: cand_5_chunk_0, cand_5_chunk_1, etc.
        ids.append(f"cand_{candidate_id}_chunk_{i}")

    if not documents:
        return 0

    # LangChain handles embedding generation and storage automatically
    vector_store.add_documents(documents=documents, ids=ids)

    print(f"[embedding_service] Stored {len(documents)} chunks for candidate {candidate_id} ({full_name})")
    return len(documents)

def delete_candidate_chunks(candidate_id):

    try:
        vector_store.delete(where={"candidate_id": str(candidate_id)})
    except Exception as e:
        # Safe to ignore - chunks may not exist yet on first upload
        print(f"[embedding_service] Delete notice for candidate {candidate_id}: {e}")
