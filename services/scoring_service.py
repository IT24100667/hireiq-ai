import re
import json
import time                          # ADDED - needed for rate limiting delay
import spacy
from langchain_core.prompts import PromptTemplate
from core.gemini_client import gemini_model
from services.embedding_service import search_candidate_chunks

try:
    nlp = spacy.load("en_core_web_sm")
    print("[scoring_service] spaCy loaded OK")
except OSError:
    print("[scoring_service] ERROR: Run: python -m spacy download en_core_web_sm")
    nlp = None

SCORING_PROMPT = PromptTemplate(
    input_variables=[
        "job_description", "candidate_name", "resume_chunks",
        "experience_evidence", "skills_weight", "experience_weight",
        "education_weight", "extras_weight", "total_weight"
    ],
    template="""You are an expert HR analyst scoring a job candidate.

JOB DESCRIPTION:
{job_description}

CANDIDATE NAME: {candidate_name}

CANDIDATE RESUME (most relevant sections):
{resume_chunks}

EXPERIENCE EVIDENCE EXTRACTED BY NLP:
{experience_evidence}

SCORING WEIGHTS (set by HR):
- Skills Match : {skills_weight} points maximum
- Experience   : {experience_weight} points maximum
- Education    : {education_weight} points maximum
- Extras       : {extras_weight} points maximum
- TOTAL        : {total_weight} points

INSTRUCTIONS:
- Score honestly and strictly but fairly
- Base scores only on what you can see in the resume
- Use the NLP experience evidence to help score experience
- For each skill in the job description, check if the resume mentions it
- For company_type: look at past employers and classify as startup, corporate, or remote
- For has_leadership: look for words like led, managed, mentored, supervised, team lead
- For industry: identify the main industry sector from work history
- For notice_period: look for availability statements in the resume

IMPORTANT: Respond with ONLY a JSON object. No extra text. No markdown. No code fences.

{{
  "total_score": <number 0-{total_weight}>,
  "skills_score": <number 0-{skills_weight}>,
  "experience_score": <number 0-{experience_weight}>,
  "education_score": <number 0-{education_weight}>,
  "extras_score": <number 0-{extras_weight}>,
  "matched_skills": ["skill1", "skill2"],
  "missing_skills": ["skill3", "skill4"],
  "requirement_checklist": [
    {{
      "skill": "skill name",
      "status": "fully_met",
      "evidence": "exact quote or description from resume"
    }}
  ],
  "ai_summary": "2-3 sentences about this candidate fit for the role",
  "confidence_score": <number 0.0-1.0>,
  "company_type": "<startup OR corporate OR remote OR unknown>",
  "has_leadership": <true OR false>,
  "industry": "<tech OR finance OR healthcare OR education OR retail OR other>",
  "notice_period": "<immediate OR 2 weeks OR 1 month OR 3 months OR not mentioned>"
}}

Status values must be exactly: fully_met OR partially_met OR not_met
confidence_score: 1.0 = lots of evidence, 0.0 = very little resume info
company_type: classify based on past employer sizes and types seen in resume
has_leadership: true only if resume clearly shows leading/managing people
industry: pick the closest match from the options given
notice_period: use "not mentioned" if resume does not state availability"""
)

# ADDED - delay between Gemini calls to stay under 15 requests per minute.

GEMINI_CALL_DELAY_SECONDS = 2.5


def extract_experience_evidence(chunks):
    evidence = []
    if not nlp or not chunks:
        return evidence
    full_text = " ".join(chunks)

    doc = nlp(full_text[:5000])

    year_pattern = re.compile(
        r'(\d+)\+?\s*(?:years?|yrs?)(?:\s+of)?\s+(?:experience|exp)?', re.IGNORECASE)

    for sentence in doc.sents:
        text = sentence.text.strip()
        match = year_pattern.search(text)
        if match:
            years = int(match.group(1))
            if 1 <= years <= 40:
                evidence.append(text[:120])
    dates_found = []
    for entity in doc.ents:
        if entity.label_ == "DATE":
            year_match = re.search(r'\b(20\d\d|19\d\d)\b', entity.text)
            if year_match:
                dates_found.append(int(year_match.group(1)))
    if len(dates_found) >= 2:
        dates_found.sort()
        earliest = dates_found[0]
        latest = dates_found[-1]
        duration = latest - earliest
        if 1 <= duration <= 40:
            evidence.append(f"Career span detected: {earliest} to {latest} ({duration} years)")
    seen = set()
    unique = []
    for e in evidence:
        if e not in seen:
            seen.add(e)
            unique.append(e)
    return unique[:5]


def score_candidate(candidate_id, full_name, jd_text,
                    job_id=None,
                    skills_weight=40, experience_weight=30,
                    education_weight=20, extras_weight=10):

    print(f"  [scoring_service] Scoring {full_name} (ID: {candidate_id})...")

    # get relevant chunks from chromaDB 
    chunks = search_candidate_chunks(candidate_id=candidate_id, query_text=jd_text, job_id=job_id, n_results=6)
    if not chunks:
        print(f"  [scoring_service] No chunks found for {full_name}")
        return None
    # extract NLP evidence
    experience_evidence = extract_experience_evidence(chunks)
    evidence_text = ("\n".join(f"- {e}" for e in experience_evidence)
                     if experience_evidence else "No specific years of experience found")
    
    # build and send prompt
    prompt_text = SCORING_PROMPT.format(
        job_description=jd_text[:2000],
        candidate_name=full_name,
        resume_chunks="\n\n---\n\n".join(chunks)[:5000],
        experience_evidence=evidence_text,
        skills_weight=skills_weight,
        experience_weight=experience_weight,
        education_weight=education_weight,
        extras_weight=extras_weight,
        total_weight=skills_weight + experience_weight + education_weight + extras_weight
    )
    try:
        # call Gemini
        response = gemini_model.generate_content(prompt_text)

        raw_text = response.text.strip()
        
        if "```" in raw_text:
            raw_text = re.sub(r"```json?\n?", "", raw_text)
            raw_text = re.sub(r"```", "", raw_text)
            raw_text = raw_text.strip()
        # parse JSON
        score_data = json.loads(raw_text)
        score_data["candidate_id"] = candidate_id
        score_data["full_name"] = full_name
        score_data["experience_evidence"] = experience_evidence
        score_data.setdefault("company_type", "unknown")
        score_data.setdefault("has_leadership", False)
        score_data.setdefault("industry", "other")
        score_data.setdefault("notice_period", "not mentioned")
        print(f"  [scoring_service] {full_name} scored {score_data.get('total_score', 0)}/100")
        return score_data
    
    except json.JSONDecodeError as e:
        print(f"  [scoring_service] JSON parse error for {full_name}: {e}")
        return None
    except Exception as e:
        print(f"  [scoring_service] Gemini error for {full_name}: {e}")
        return None


def score_all_candidates(candidates, jd_text,
                         job_id=None,
                         skills_weight=40, experience_weight=30,
                         education_weight=20, extras_weight=10):
    print(f"\n[scoring_service] Scoring {len(candidates)} candidates...")
    scores = []
    for i, candidate in enumerate(candidates):
        candidate_id = candidate["candidate_id"]
        full_name = candidate.get("full_name", "Unknown")
        email = candidate.get("email", "")
        phone = candidate.get("phone", "")
        score = score_candidate(
            candidate_id=candidate_id, full_name=full_name, jd_text=jd_text,
            job_id=job_id,
            skills_weight=skills_weight, experience_weight=experience_weight,
            education_weight=education_weight, extras_weight=extras_weight
        )
        if score:
            score["email"] = email
            score["phone"] = phone
            scores.append(score)
        else:
            scores.append({
                "candidate_id": candidate_id, "full_name": full_name,
                "email": email, "phone": phone,
                "total_score": 0, "skills_score": 0, "experience_score": 0,
                "education_score": 0, "extras_score": 0,
                "matched_skills": [], "missing_skills": [],
                "requirement_checklist": [],
                "ai_summary": "Scoring failed. Please re-score.",
                "confidence_score": 0.0, "experience_evidence": [],
                "company_type": "unknown", "has_leadership": False,
                "industry": "other", "notice_period": "not mentioned",
                "status": "failed"
            })

        # ADDED - wait between Gemini calls to respect the 15 RPM rate limit.
        # Skip the delay after the last candidate to avoid unnecessary waiting.
        if i < len(candidates) - 1:
            print(f"  [scoring_service] Rate limit delay ({GEMINI_CALL_DELAY_SECONDS}s)...")
            time.sleep(GEMINI_CALL_DELAY_SECONDS)

    scores.sort(key=lambda x: x.get("total_score", 0), reverse=True)
    for i, score in enumerate(scores):
        score["rank"] = i + 1
    print(f"[scoring_service] Done. {len(scores)} candidates ranked.\n")
    return scores