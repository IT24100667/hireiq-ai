from flask import Blueprint, request, jsonify
from services.chat_service import process_chat_message

chat_bp = Blueprint("chat", __name__, url_prefix="/ai/chat")


@chat_bp.route("/message", methods=["POST"])
def chat_message():
    """
    Receives a chat message from Spring Boot and returns an AI response.

    Spring sends:
    {
        "message":          "Who has the best Python skills?",
        "session_id":       "session_abc123",
        "job_id":           1,              <- optional, null = search all jobs
        "candidate_scores": [               <- Spring fetches these from MySQL
            {
                "full_name":        "John Smith",
                "total_score":      87,
                "skills_score":     35,
                "experience_score": 28,
                "education_score":  18,
                "ai_summary":       "...",
                "matched_skills":   "Python, AWS"
            },
            ...
        ]
    }

    Flask returns:
    {
        "success":    true,
        "response":   "John Smith has the strongest Python skills...",
        "session_id": "session_abc123"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No data received"}), 400

    user_message     = data.get("message", "").strip()
    session_id       = data.get("session_id", "")
    job_id           = data.get("job_id", None)         # optional
    candidate_scores = data.get("candidate_scores", []) # sent by Spring from MySQL

    if not user_message:
        return jsonify({"success": False, "error": "Message cannot be empty"}), 400

    try:
        response_text = process_chat_message(
            user_message     = user_message,
            job_id           = job_id,
            candidate_scores = candidate_scores
        )

        return jsonify({
            "success":    True,
            "response":   response_text,
            "session_id": session_id
        }), 200

    except Exception as e:
        print(f"[chat_routes] Error: {e}")
        return jsonify({
            "success":    False,
            "error":      str(e),
            "session_id": session_id
        }), 500


@chat_bp.route("/health", methods=["GET"])
def health():
    """Simple check to confirm this blueprint is running."""
    return jsonify({"status": "ok", "blueprint": "chat"}), 200