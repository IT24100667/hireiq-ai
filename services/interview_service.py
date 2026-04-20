# services/interview_service.py
# Member 06 - Interview Question Generation Logic
# Uses Gemini to generate personalized interview questions
# based on candidate's weak areas from their score data.

import re
import json
from langchain_core.prompts import PromptTemplate
from core.gemini_client import gemini_model

INTERVIEW_PROMPT = PromptTemplate(
    input_variables=[
        "candidate_name", "job_description",
        "matched_skills", "missing_skills", "ai_summary"
    ],
    template="""You are an expert HR interviewer preparing personalized interview questions.

CANDIDATE NAME: {candidate_name}

JOB DESCRIPTION:
{job_description}

CANDIDATE ASSESSMENT:
- Matched Skills: {matched_skills}
- Missing Skills: {missing_skills}
- AI Summary: {ai_summary}

INSTRUCTIONS:
Generate personalized interview questions in exactly 3 categories:

1. MISSING_SKILLS - Questions that probe the skills this candidate lacks
   - Ask how they would handle situations requiring those missing skills
   - Ask if they have any indirect experience with those skills
   - Generate 3-4 questions

2. WEAK_EXPERIENCE - Questions that dig deeper into areas where experience seems thin
   - Ask for specific examples and outcomes
   - Ask about challenges they faced
   - Generate 3-4 questions

3. RED_FLAGS - Questions that address concerns or gaps in their profile
   - Career gaps, frequent job changes, vague descriptions
   - Ask for clarification on anything unclear in their background
   - Generate 2-3 questions

For each question also provide a short "reason" explaining WHY you are asking it.

IMPORTANT: Respond with ONLY a JSON object. No extra text. No markdown. No code fences.

{{
  "questions": [
    {{
      "category": "MISSING_SKILLS",
      "question_text": "The actual interview question here?",
      "reason": "Short explanation of why this question is being asked"
    }},
    {{
      "category": "WEAK_EXPERIENCE",
      "question_text": "The actual interview question here?",
      "reason": "Short explanation of why this question is being asked"
    }},
    {{
      "category": "RED_FLAGS",
      "question_text": "The actual interview question here?",
      "reason": "Short explanation of why this question is being asked"
    }}
  ]
}}

Category values must be exactly: MISSING_SKILLS or WEAK_EXPERIENCE or RED_FLAGS
Generate between 8-11 questions total across all 3 categories.
Make questions specific to THIS candidate, not generic."""
)


def generate_interview_questions(
        candidate_id, job_id, candidate_name,
        job_description, matched_skills,
        missing_skills, ai_summary):
    """
    Generates personalized interview questions for a candidate.
    Returns a list of question dicts with category, question_text, reason.
    """
    print(f"[interview_service] Generating questions for "
          f"{candidate_name} (ID: {candidate_id}, job_id: {job_id})...")

    # Clean up inputs - they may be JSON strings from MySQL
    def parse_field(field):
        if not field:
            return "None"
        if isinstance(field, str):
            try:
                parsed = json.loads(field)
                if isinstance(parsed, list):
                    return ", ".join(str(x) for x in parsed)
                return str(parsed)
            except Exception:
                return field
        return str(field)

    matched_str = parse_field(matched_skills)
    missing_str = parse_field(missing_skills)
    summary_str = ai_summary or "No summary available"

    prompt_text = INTERVIEW_PROMPT.format(
        candidate_name  = candidate_name,
        job_description = job_description[:2000],
        matched_skills  = matched_str[:500],
        missing_skills  = missing_str[:500],
        ai_summary      = summary_str[:500]
    )

    try:
        response = gemini_model.generate_content(prompt_text)
        raw_text = response.text.strip()

        # Clean markdown code fences if Gemini adds them
        if "```" in raw_text:
            raw_text = re.sub(r"```json?\n?", "", raw_text)
            raw_text = re.sub(r"```", "", raw_text)
            raw_text = raw_text.strip()

        result = json.loads(raw_text)
        questions = result.get("questions", [])

        # Validate and clean each question
        cleaned = []
        valid_categories = {"MISSING_SKILLS", "WEAK_EXPERIENCE", "RED_FLAGS"}
        for q in questions:
            category = q.get("category", "MISSING_SKILLS").strip().upper()
            if category not in valid_categories:
                category = "MISSING_SKILLS"
            cleaned.append({
                "category":     category,
                "question_text": q.get("question_text", "").strip(),
                "reason":        q.get("reason", "").strip()
            })

        print(f"[interview_service] Done. {len(cleaned)} questions generated.")
        return cleaned

    except json.JSONDecodeError as e:
        print(f"[interview_service] JSON parse error: {e}")
        raise RuntimeError("Gemini returned invalid JSON. Please try again.")

    except Exception as e:
        print(f"[interview_service] Gemini error: {e}")
        raise RuntimeError(f"Gemini question generation failed: {str(e)}")