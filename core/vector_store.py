from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
import config

# Embedding model 
embedding_model = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

# ChromaDB vector store 
# persist_directory = folder where ChromaDB saves data locally
# collection_name   = like a table name inside ChromaDB
vector_store = Chroma(
    collection_name   = config.CHROMA_COLLECTION,
    embedding_function= embedding_model,
    persist_directory = config.CHROMA_PATH
)

print("[vector_store] ChromaDB ready")