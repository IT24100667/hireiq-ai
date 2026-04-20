# routes/comparison_routes.py
# Member 04 - Comparison & Recommendation Endpoints
#
# POST /ai/comparison/compare    - returns trade-off analysis for selected candidates
# POST /ai/comparison/recommend  - returns AI recommendation based on context
#
# Spring Boot calls these - Flask never talks to MySQL here.
# Candidate score data is fetched by Spring and passed in the request body.

from flask import Blueprint, request, jsonify
from services.comparison_service import analyze_tradeoffs, generate_recommendation

comparison_bp = Blueprint("comparison", __name__, url_prefix="/ai/comparison")


@comparison_bp.route("/compare", methods=["POST"])
def compare_candidates():
    """
    Receives candidate score data from Spring and returns trade-off analysis.

    Spring sends:
    {
        "job_description": "We are looking for...",
        "candidates": [
            {
                "candidate_id": 1,
                "full_name": "John Smith",
                "total_score": 87,
                "skills_score": 35,
                "experience_score": 28,
                "education_score": 18,
                "extras_score": 6,
                "skills_weight": 40,
                "experience_weight": 30,
                "education_weight": 20,
                "extras_weight": 10,
                "matched_skills": ["Python", "AWS"],
                "missing_skills": ["Docker"],
                "ai_summary": "...",
                "company_type": "startup",
                "has_leadership": true,
                "industry": "tech",
                "notice_period": "2 weeks"
            },
            ...
        ]
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No data received"}), 400

    candidates = data.get("candidates", [])

    if len(candidates) < 2:
        return jsonify({"success": False, "error": "At least 2 candidates required"}), 400

    if len(candidates) > 3:
        return jsonify({"success": False, "error": "Maximum 3 candidates allowed"}), 400

    try:
        tradeoffs = analyze_tradeoffs(candidates)
        return jsonify({
            "success":    True,
            "tradeoffs":  tradeoffs,
            "candidates": candidates   # echo back so Spring can pass to frontend
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@comparison_bp.route("/recommend", methods=["POST"])
def recommend_candidate():
    """
    Generates a contextual AI recommendation for which candidate to hire.

    Spring sends:
    {
        "job_description": "...",
        "candidates": [ ... same shape as above ... ],
        "role_type": "Senior",
        "company_culture": "Startup",
        "top_priority": "Technical skills"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No data received"}), 400

    candidates       = data.get("candidates",       [])
    job_description  = data.get("job_description",  "")
    role_type        = data.get("role_type",        "Mid-level")
    company_culture  = data.get("company_culture",  "Corporate")
    top_priority     = data.get("top_priority",     "Technical skills")

    if len(candidates) < 2:
        return jsonify({"success": False, "error": "At least 2 candidates required"}), 400

    if not job_description:
        return jsonify({"success": False, "error": "job_description is required"}), 400

    try:
        result = generate_recommendation(
            candidates      = candidates,
            job_description = job_description,
            role_type       = role_type,
            company_culture = company_culture,
            top_priority    = top_priority
        )
        return jsonify({
            "success":        True,
            "recommendation": result["recommendation"],
            "fallback":       result["fallback"]
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500