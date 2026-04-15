import spacy
from langchain_core.prompts import PromptTemplate


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

