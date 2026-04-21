# services/email_service.py
# Generates HR emails using Gemini AI.
# Called by: routes/email_routes.py
#
# Supports 3 stage values (sent from Spring Boot):
#   - interview  : invite a screened candidate to interview
#   - rejection  : politely reject after interview stage
#   - offer      : formal job offer for offered stage
#   Also accepts SCREENED / INTERVIEWED / OFFERED (uppercase) as aliases

import json
import re
from core.gemini_client import gemini_model


def _normalise_stage(stage):
    """Map any stage value to interview / rejection / offer."""
    s = stage.lower().strip()
    if s in ("interview", "screened"):
        return "interview"
    elif s in ("rejection", "interviewed"):
        return "rejection"
    elif s in ("offer", "offered", "hired"):
        return "offer"
    return s   # pass through — validator below will catch unknown values


def _build_prompt(stage, candidate_name, job_title, venue="", time="", extra_info=""):
    if stage == "interview":
        # Build dynamic venue/time lines only when the values were provided
        venue_line = ("- The interview will be held at: {}\n".format(venue)) if venue else ""
        time_line  = ("- The interview is scheduled for: {}\n".format(time))  if time  else ""
        extra_line = ("- Additional details: {}\n".format(extra_info))         if extra_info else ""

        instructions = (
            "- Inform the candidate their application has been reviewed and they have been shortlisted\n"
            "- Invite them for an interview\n"
            + venue_line
            + time_line
            + extra_line
            + "- Ask them to confirm their availability\n"
            "- Mention the HR team will follow up if any details are yet to be confirmed\n"
            "- Keep it warm, encouraging, and professional"
        )
    elif stage == "rejection":
        instructions = (
            "- Thank the candidate sincerely for their time and interest\n"
            "- Inform them politely that they have not been selected after the interview stage\n"
            "- Encourage them to apply for future openings at HireIQ\n"
            "- Keep it empathetic, respectful, and professional"
        )
    else:  # offer
        instructions = (
            "- Warmly congratulate the candidate on being selected for the position\n"
            "- Mention that a formal offer letter will follow shortly\n"
            "- Briefly outline the next steps (offer letter review, onboarding)\n"
            "- Keep it enthusiastic, warm, and professional"
        )

    return (
        "You are an HR representative at HireIQ. Write a professional email.\n\n"
        "Candidate Name: " + candidate_name + "\n"
        "Job Title: " + job_title + "\n\n"
        "Instructions:\n"
        + instructions + "\n"
        "- Sign off from HireIQ HR Team\n\n"
        'You MUST respond with ONLY this exact JSON format, nothing else, no markdown:\n'
        '{"subject":"your subject here","body":"your email body here"}'
    )


def generate_email(stage, candidate_name, job_title, venue="", time="", extra_info=""):
    """
    Generate an HR email using Gemini.
    Args:
        stage:      'interview' | 'rejection' | 'offer'  (or SCREENED / INTERVIEWED / OFFERED)
        venue:      interview location (optional, interview stage only)
        time:       interview date/time string (optional, interview stage only)
        extra_info: any extra notes to include in the email (optional)
    Returns: { "subject": "...", "body": "..." }
    """
    stage = _normalise_stage(stage or "")

    if stage not in ("interview", "rejection", "offer"):
        raise ValueError("Invalid stage: '{}'. Must be interview, rejection, or offer.".format(stage))
    if not candidate_name or not job_title:
        raise ValueError("candidate_name and job_title are required.")

    prompt = _build_prompt(stage, candidate_name, job_title,
                           venue=venue, time=time, extra_info=extra_info)
    print("[email_service] Generating '{}' email for {} ({})".format(stage, candidate_name, job_title))

    response = gemini_model.generate_content(prompt)
    raw = response.text.strip()

    # Strip markdown fences if Gemini adds them
    raw = re.sub(r"^```json\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"^```\s*",     "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$",     "", raw, flags=re.IGNORECASE)
    raw = raw.strip()

    json_start = raw.find("{")
    json_end   = raw.rfind("}")
    if json_start != -1 and json_end != -1:
        raw = raw[json_start:json_end + 1]

    parsed  = json.loads(raw)
    subject = parsed.get("subject", "").strip()
    body    = parsed.get("body",    "").strip()

    if not subject or not body:
        raise ValueError("Gemini returned an empty subject or body.")

    print("[email_service] Done — subject: {}".format(subject[:60]))
    return {"subject": subject, "body": body}