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



def search_candidate_chunks(candidate_id, query_text, job_id=None, n_results=6):
 
    try:
        if job_id is not None:
            search_filter = {
                "$and": [
                    {"candidate_id": {"$eq": str(candidate_id)}},
                    {"job_id":       {"$eq": str(job_id)}}
                ]
            }
        else:
            search_filter = {"candidate_id": {"$eq": str(candidate_id)}}

        results = vector_store.similarity_search_with_score(
            query  = query_text,
            k      = n_results,
            filter = search_filter
        )
        # Return just the text - scorer doesn't need the scores
        # we get something like: [(Document(page_content="chunk text", metadata={...}), 0.85), ...]
        return [doc.page_content for doc, score in results]

    except Exception as e:
        print(f"[embedding_service] Search error for candidate {candidate_id}: {e}")
        return []


def search_all_candidates(query_text, job_id=None, top_k=10):
 
    try:
        search_filter = {"job_id": str(job_id)} if job_id else None

        results = vector_store.similarity_search_with_score(
            query  = query_text,
            k      = top_k,
            filter = search_filter
        )

        output = []
        for doc, score in results:
            output.append({
                "text":         doc.page_content,
                "candidate_id": doc.metadata.get("candidate_id"),
                "full_name":    doc.metadata.get("full_name"),
                "email":        doc.metadata.get("email"),
                "score":        round(float(score), 4)
            })

        return output

    except Exception as e:
        print(f"[embedding_service] Search all error: {e}")
        return []