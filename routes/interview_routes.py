from flask import Blueprint, request, jsonify
from services.interview_service import generate_interview_questions

interview_bp = Blueprint("interview", __name__, url_prefix="/ai/interview")


@interview_bp.route("/generate", methods=["POST"])
def generate():
    """
    Receives candidate score data from Spring Boot,
    generates personalized interview questions using Gemini,
    and returns them grouped by category.

    Spring sends:
    {
        "candidate_id":    1,
        "job_id":          1,
        "candidate_name":  "John Smith",
        "job_description": "We are looking for...",
        "matched_skills":  "[\"Python\", \"Django\"]",
        "missing_skills":  "[\"AWS\", \"Docker\"]",
        "ai_summary":      "Strong backend developer but lacks cloud experience..."
    }

    Flask returns:
    {
        "success": true,
        "candidate_id": 1,
        "job_id": 1,
        "questions": [
            {
                "category":      "MISSING_SKILLS",
                "question_text": "Have you worked with any cloud platforms?",
                "reason":        "AWS is listed as required but not found in resume"
            },
            ...
        ]
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No data received"}), 400

    candidate_id    = data.get("candidate_id")
    job_id          = data.get("job_id")
    candidate_name  = data.get("candidate_name",  "Unknown")
    job_description = data.get("job_description", "")
    matched_skills  = data.get("matched_skills",  "[]")
    missing_skills  = data.get("missing_skills",  "[]")
    ai_summary      = data.get("ai_summary",      "")

    # Validate required fields
    if not candidate_id:
        return jsonify({"success": False, "error": "candidate_id is required"}), 400

    if not job_id:
        return jsonify({"success": False, "error": "job_id is required"}), 400

    if not job_description:
        return jsonify({"success": False, "error": "job_description is required"}), 400

    try:
        questions = generate_interview_questions(
            candidate_id    = candidate_id,
            job_id          = job_id,
            candidate_name  = candidate_name,
            job_description = job_description,
            matched_skills  = matched_skills,
            missing_skills  = missing_skills,
            ai_summary      = ai_summary
        )

        return jsonify({
            "success":      True,
            "candidate_id": candidate_id,
            "job_id":       job_id,
            "questions":    questions,
            "count":        len(questions)
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500