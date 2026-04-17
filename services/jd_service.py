
import re
import json
from langchain_core.prompts import PromptTemplate
from core.gemini_client import gemini_model

JD_ANALYSIS_PROMPT = PromptTemplate(
    input_variables=["original_jd"],
    template="""You are an expert HR consultant and job description specialist.

Analyze the following job description and return a detailed quality report.

JOB DESCRIPTION:
{original_jd}

INSTRUCTIONS:
- Score the JD honestly out of 100
- Look for these common problems:
  * Vague or unclear responsibilities
  * Missing required qualifications section
  * Missing preferred qualifications section
  * Biased or exclusionary language (e.g. "rockstar", "ninja", "young")
  * No salary or benefits information
  * Unrealistic requirements (e.g. 10 years experience in a 5 year old technology)
  * Missing company culture or values description
  * Overly long or overly short description
  * Missing location or remote work policy
  * Spelling or grammar issues
- Generate a fully refined and improved version of the JD
- Keep the refined JD professional, inclusive, and clear

IMPORTANT: Respond with ONLY a JSON object. No extra text. No markdown. No code fences.

{{
  "quality_score": <number 0-100>,
  "issues_found": [
    "Issue description 1",
    "Issue description 2"
  ],
  "improvement_summary": "2-3 sentences summarizing what was improved in the refined version",
  "refined_jd": "The full improved job description text here..."
}}

quality_score guide:
- 90-100: Excellent, minor improvements only
- 70-89:  Good, a few issues to fix
- 50-69:  Average, several important sections missing
- 30-49:  Poor, major restructuring needed
- 0-29:   Very poor, almost needs to be rewritten"""
)


def analyze_jd(original_jd, job_id=None):
    """
    Sends the raw JD to Gemini for analysis.
    Returns quality score, issues, improvement summary, and refined JD.
    """
    print(f"[jd_service] Analyzing JD (job_id={job_id}, length={len(original_jd)} chars)...")

    prompt_text = JD_ANALYSIS_PROMPT.format(original_jd=original_jd[:4000])

    try:
        response = gemini_model.generate_content(prompt_text)
        raw_text = response.text.strip()


        if "```" in raw_text:
            raw_text = re.sub(r"```json?\n?", "", raw_text)
            raw_text = re.sub(r"```", "", raw_text)
            raw_text = raw_text.strip()

        result = json.loads(raw_text)

        # Safety Handlings defualt settings
        result.setdefault("quality_score",       50)
        result.setdefault("issues_found",        [])
        result.setdefault("improvement_summary", "")
        result.setdefault("refined_jd",          original_jd)

        print(f"[jd_service] Done. Quality score: {result.get('quality_score')}/100, "
              f"Issues found: {len(result.get('issues_found', []))}")

        return result

    except json.JSONDecodeError as e:
        print(f"[jd_service] JSON parse error: {e}")
        raise RuntimeError("Gemini returned invalid JSON. Please try again.")

    except Exception as e:
        print(f"[jd_service] Gemini error: {e}")
        raise RuntimeError(f"Gemini analysis failed: {str(e)}")