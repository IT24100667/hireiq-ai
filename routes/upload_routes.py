import os
from flask import Blueprint, request, jsonify
from services.document_service import process_resume
import config

# Blueprint groups all Member 03 routes under /ai/upload/
upload_bp = Blueprint("upload", __name__, url_prefix="/ai/upload")


def _allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in config.ALLOWED_EXTENSIONS


@upload_bp.route("/process", methods=["POST"])
def process_resume_file():
    """
    Receives a single resume file from Spring Boot.
    Processes it and returns extracted data.

    Spring Boot sends:
    - file:         the resume file (PDF or DOCX)
    - candidate_id: the ID Spring already saved in MySQL
    - job_id:       which job this resume is for

    Flask returns:
    {
        "success": true,
        "candidate_id": 5,
        "metadata": { "full_name": "...", "email": "...", "phone": "..." },
        "chunk_count": 12,
        "documents": [ { "text": "...", "metadata": {...} }, ... ]
    }

    NOTE: Spring passes candidate_id here because Spring saved
    the candidate row first. Flask just needs to tag the chunks
    with that ID so Member 01 can link them back to the candidate.
    """

    # ── Validate incoming request
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file included in request"}), 400

    file         = request.files["file"]
    candidate_id = request.form.get("candidate_id")
    job_id       = request.form.get("job_id")

    if not candidate_id or not job_id:
        return jsonify({"success": False, "error": "candidate_id and job_id are required"}), 400

    if file.filename == "" or not _allowed_file(file.filename):
        return jsonify({"success": False, "error": "Invalid file. Only PDF and DOCX are accepted."}), 400

    # ── Validate candidate_id and job_id are integers
    try:
        candidate_id_int = int(candidate_id)
        job_id_int       = int(job_id)
    except ValueError:
        return jsonify({"success": False, "error": "candidate_id and job_id must be integers"}), 400

    # ── Save file to disk
    # We use candidate_id in the filename to avoid name collisions
    # (two candidates could both upload "resume.pdf")
    file_type   = file.filename.rsplit(".", 1)[1].lower()
    safe_name   = f"candidate_{candidate_id_int}.{file_type}"
    save_path   = os.path.join(config.UPLOAD_FOLDER, safe_name)

    try:
        file.save(save_path)
    except Exception as e:
        return jsonify({"success": False, "error": f"Could not save file: {str(e)}"}), 500

    # ── Run the processing pipeline
    result = process_resume(save_path, file_type, candidate_id_int, job_id_int)

    if not result["success"]:
        return jsonify({"success": False, "error": result["error"]}), 422

    # ── Return processed data to Spring Boot
    return jsonify({
        "success":      True,
        "candidate_id": candidate_id_int,
        "metadata":     result["metadata"],
        "chunk_count":  len(result["chunks"]),
        "documents":    result["documents"]   # Member 01 will use this for embeddings
    }), 200


@upload_bp.route("/health", methods=["GET"])
def health():
    """Simple check to confirm this blueprint is running."""
    return jsonify({"status": "ok", "blueprint": "upload"}), 200