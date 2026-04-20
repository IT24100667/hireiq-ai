# configuration for application

import os
from dotenv import load_dotenv

load_dotenv(override=True)

FLASK_PORT = 5000
DEBUG_MODE = True

# File Upload Settings 
UPLOAD_FOLDER      = "uploads"          # folder where resume files are saved
ALLOWED_EXTENSIONS = {"pdf", "docx"}    # only these file types are accepted
MAX_FILE_SIZE_MB   = 50                 # max upload size in megabytes

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")

CHROMA_PATH       = "chroma_store"  # folder where ChromaDB saves its data locally
CHROMA_COLLECTION = "resumes"       # name of the collection (like a table) inside ChromaDB

CHUNK_SIZE    = 500  # how many characters per chunk
CHUNK_OVERLAP = 50   # overlap between chunks so we don't lose context at the edges