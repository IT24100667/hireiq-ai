# routes/email_routes.py
# Email generation endpoint — called by Spring Boot (EmailController.java).
#
# POST /ai/email/generate
#   Spring sends: { "candidate_id", "candidate_name", "job_title", "stage" }
#   Returns:      { "success": true, "subject": "...", "body": "..." }

from flask import Blueprint, request, jsonify
from services.email_service import generate_email

email_bp = Blueprint("email", __name__, url_prefix="/ai/email")


@email_bp.route("/generate", methods=["POST"])
def generate_email_route():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No data received"}), 400

    # Spring Boot sends camelCase keys
    candidate_name = (data.get("candidateName") or data.get("candidate_name") or "").strip()
    job_title      = (data.get("jobTitle")      or data.get("job_title")      or "").strip()
    stage          = (data.get("stage")         or data.get("email_type")     or "").strip()

    # Optional interview details (collected from the UI form)
    venue      = (data.get("venue")     or "").strip()
    time       = (data.get("time")      or "").strip()
    extra_info = (data.get("extraInfo") or data.get("extra_info") or "").strip()

    if not stage:
        return jsonify({"success": False, "error": "stage is required"}), 400
    if not candidate_name:
        return jsonify({"success": False, "error": "candidateName is required"}), 400
    if not job_title:
        return jsonify({"success": False, "error": "jobTitle is required"}), 400

    try:
        result = generate_email(stage, candidate_name, job_title,
                                venue=venue, time=time, extra_info=extra_info)
        return jsonify({
            "success": True,
            "subject": result["subject"],
            "body":    result["body"]
        }), 200

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

    except Exception as e:
        print("[email_routes] Error: {}".format(e))
        return jsonify({"success": False, "error": "Failed to generate email: " + str(e)}), 500