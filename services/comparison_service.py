# services/comparison_service.py
# Member 04 - Comparison & Recommendation Logic
# Pure AI logic - no database calls.
#
# Called by: routes/comparison_routes.py
# Receives candidate score data from Spring (already fetched from MySQL).
# Returns trade-off analysis and AI recommendation.

import json
from core.gemini_client import gemini_model


def analyze_tradeoffs(candidates):
    """
    Identifies trade-offs between 2-3 candidates based on their scores.
    No AI call needed here - pure logic comparing score breakdowns.

    Returns a list of trade-off dicts:
    { "type": "...", "description": "...", "implication": "..." }
    """
    tradeoffs = []

    if len(candidates) < 2:
        return tradeoffs

    # ── Trade-off 1: Skills vs Experience ─────────────────
    # Find if one candidate has better skills but less experience
    # and another has the reverse
    skills_leader     = max(candidates, key=lambda c: c.get("skills_score", 0))
    experience_leader = max(candidates, key=lambda c: c.get("experience_score", 0))

    if skills_leader["candidate_id"] != experience_leader["candidate_id"]:
        tradeoffs.append({
            "type": "Skills vs Experience",
            "description": (
                f"{skills_leader['full_name']} leads on technical skills "
                f"({skills_leader['skills_score']} pts) while "
                f"{experience_leader['full_name']} has stronger experience "
                f"({experience_leader['experience_score']} pts)."
            ),
            "implication": (
                "Consider whether the role demands immediate technical ability "
                "or benefits more from seasoned judgment and track record."
            )
        })

    # ── Trade-off 2: Education vs Practical Experience ────
    education_leader  = max(candidates, key=lambda c: c.get("education_score", 0))
    experience_leader2 = max(candidates, key=lambda c: c.get("experience_score", 0))

    if education_leader["candidate_id"] != experience_leader2["candidate_id"]:
        tradeoffs.append({
            "type": "Education vs Practical Experience",
            "description": (
                f"{education_leader['full_name']} has stronger academic credentials "
                f"({education_leader['education_score']} pts) while "
                f"{experience_leader2['full_name']} brings more hands-on experience "
                f"({experience_leader2['experience_score']} pts)."
            ),
            "implication": (
                "For research or graduate roles, education may matter more. "
                "For delivery-focused roles, practical experience often predicts success better."
            )
        })

    # ── Trade-off 3: Leadership vs Specialization ─────────
    leaders      = [c for c in candidates if c.get("has_leadership")]
    non_leaders  = [c for c in candidates if not c.get("has_leadership")]

    if leaders and non_leaders:
        # Pick the non-leader with the highest skills score (the specialist)
        specialist = max(non_leaders, key=lambda c: c.get("skills_score", 0))
        leader     = leaders[0]
        tradeoffs.append({
            "type": "Leadership vs Specialization",
            "description": (
                f"{leader['full_name']} has demonstrated leadership experience "
                f"while {specialist['full_name']} appears to be a deep technical specialist."
            ),
            "implication": (
                "If the role involves managing a team or mentoring others, "
                "the leader profile is safer. For individual contributor roles, "
                "the specialist may deliver more immediate value."
            )
        })

    return tradeoffs


def generate_recommendation(candidates, job_description,
                             role_type, company_culture, top_priority):
    """
    Uses Gemini to generate a contextual hiring recommendation.
    Falls back to rule-based logic if Gemini fails.

    candidates      : list of candidate score dicts
    job_description : full job description text
    role_type       : Junior / Mid-level / Senior / Lead
    company_culture : Startup / Scale-up / Corporate / Remote-first / Hybrid
    top_priority    : Technical skills / Experience level / Culture fit /
                      Growth potential / Leadership ability
    """

    # Build a summary of each candidate for the prompt
    candidate_summaries = []
    for c in candidates:
        summary = (
            f"Name: {c['full_name']}\n"
            f"Total Score: {c.get('total_score', 0)}/100\n"
            f"Skills: {c.get('skills_score', 0)}, "
            f"Experience: {c.get('experience_score', 0)}, "
            f"Education: {c.get('education_score', 0)}, "
            f"Extras: {c.get('extras_score', 0)}\n"
            f"Background: {c.get('company_type', 'unknown')} company\n"
            f"Leadership experience: {c.get('has_leadership', False)}\n"
            f"Industry: {c.get('industry', 'other')}\n"
            f"Notice period: {c.get('notice_period', 'not mentioned')}\n"
            f"AI Summary: {c.get('ai_summary', '')}"
        )
        candidate_summaries.append(summary)

    divider   = '=' * 40
    separator = '\n' + divider + '\n'

    prompt = f"""You are an expert HR consultant helping make a final hiring decision.

JOB DESCRIPTION:
{job_description[:1500]}

CANDIDATES BEING COMPARED:
{divider}
{separator.join(candidate_summaries)}
{divider}

HIRING CONTEXT:
- Role Type: {role_type}
- Company Culture: {company_culture}
- Top Priority: {top_priority}

Based on the candidates, job description, and hiring context above:
1. Recommend which candidate is the best fit and clearly explain why
2. Mention any risks or considerations for your recommended candidate
3. Briefly explain why the other candidate(s) were not selected

Write in clear, professional language suitable for an HR report.
Keep your response to 3-4 paragraphs maximum."""

    try:
        response    = gemini_model.generate_content(prompt)
        return {
            "recommendation": response.text.strip(),
            "fallback":       False
        }
    except Exception as e:
        print(f"[comparison_service] Gemini recommendation failed: {e}")
        # Rule-based fallback - picks highest scorer with context notes
        return _rule_based_recommendation(candidates, role_type, company_culture, top_priority)


def _rule_based_recommendation(candidates, role_type, company_culture, top_priority):
    """
    Simple rule-based fallback when Gemini is unavailable.
    Picks the best candidate based on the top_priority setting.
    """
    priority_map = {
        "Technical skills":   "skills_score",
        "Experience level":   "experience_score",
        "Growth potential":   "extras_score",
        "Leadership ability": "has_leadership",
        "Culture fit":        "total_score"
    }

    sort_key = priority_map.get(top_priority, "total_score")

    if sort_key == "has_leadership":
        # For leadership, prefer candidates with leadership experience
        sorted_candidates = sorted(
            candidates,
            key=lambda c: (c.get("has_leadership", False), c.get("total_score", 0)),
            reverse=True
        )
    else:
        sorted_candidates = sorted(
            candidates,
            key=lambda c: c.get(sort_key, 0),
            reverse=True
        )

    best = sorted_candidates[0]
    others = [c["full_name"] for c in sorted_candidates[1:]]

    recommendation = (
        f"Based on the hiring context ({role_type} role at a {company_culture} environment, "
        f"prioritising {top_priority}), **{best['full_name']}** is the recommended candidate.\n\n"
        f"They achieved a total score of {best.get('total_score', 0)}/100 with strong performance "
        f"in the priority area. "
    )

    if best.get("has_leadership"):
        recommendation += "Their demonstrated leadership experience is a notable strength. "

    if best.get("notice_period") == "immediate":
        recommendation += "They are also immediately available. "

    if others:
        recommendation += (
            f"\n\nWhile {', '.join(others)} showed merit, they ranked lower "
            f"when evaluated against the stated priority of {top_priority}."
        )

    return {
        "recommendation": recommendation,
        "fallback":       True
    }