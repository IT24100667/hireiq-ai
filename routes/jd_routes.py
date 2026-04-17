# routes/jd_routes.py
# Member 06 - JD Analysis Endpoints
# Called by Spring Boot only - never by frontend directly.
#
# POST /ai/jd/analyze  - analyze and refine a job description

from flask import Blueprint, request, jsonify
from services.jd_service import analyze_jd

jd_bp = Blueprint("jd", __name__, url_prefix="/ai/jd")


@jd_bp.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No data received"}), 400

    original_jd = data.get("original_jd", "").strip()
    job_id      = data.get("job_id", None)

    if not original_jd:
        return jsonify({"success": False, "error": "original_jd is required"}), 400

    if len(original_jd) < 50:
        return jsonify({
            "success": False,
            "error": "Job description is too short. Please provide a more detailed JD."
        }), 400

    try:
        result = analyze_jd(original_jd=original_jd, job_id=job_id)
        return jsonify({
            "success":             True,
            "job_id":              job_id,
            "quality_score":       result.get("quality_score",       50),
            "issues_found":        result.get("issues_found",        []),
            "improvement_summary": result.get("improvement_summary", ""),
            "refined_jd":          result.get("refined_jd",          original_jd)
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500