import config
from core.gemini_client import gemini_model
from services.embedding_service import search_all_candidates


def build_context(search_results, candidate_scores):
    """
    Combines ChromaDB search results and MySQL scores into one
    readable context string that we pass to Gemini.

    search_results  : list of matching resume chunks from ChromaDB
    candidate_scores: list of score dicts passed in from Spring (from MySQL)
    """
    context_parts = []

    # Resume chunks from ChromaDB
    if search_results:
        context_parts.append("=== RELEVANT RESUME INFORMATION ===")
        seen_candidates = set()  # avoid repeating the same candidate name

        for result in search_results:
            name  = result.get("full_name", "Unknown")
            chunk = result.get("text", "")

            if name not in seen_candidates:
                seen_candidates.add(name)
                context_parts.append(f"\nCandidate: {name}")

            if chunk:
                # Only show first 300 chars of each chunk to keep context short
                context_parts.append(f"  Resume excerpt: {chunk[:300]}")

    # Score data passed in from Spring
    if candidate_scores:
        context_parts.append("\n=== CANDIDATE SCORES & RANKINGS ===")

        for i, score in enumerate(candidate_scores[:10], 1):
            name       = score.get("fullName",        score.get("full_name", "Unknown"))
            total      = score.get("totalScore",      score.get("total_score", 0))
            skills     = score.get("skillsScore",     score.get("skills_score", 0))
            experience = score.get("experienceScore", score.get("experience_score", 0))
            education  = score.get("educationScore",  score.get("education_score", 0))
            summary    = score.get("aiSummary",       score.get("ai_summary", ""))
            matched    = score.get("matchedSkills",   score.get("matched_skills", ""))

            context_parts.append(
                f"\n#{i} {name} — Total: {total}/100 "
                f"(Skills: {skills}, Experience: {experience}, Education: {education})"
            )
            if summary:
                context_parts.append(f"   Summary: {summary[:200]}")
            if matched:
                context_parts.append(f"   Matched skills: {matched}")

    # If nothing was found at all, tell Gemini so it doesn't make things up
    if not context_parts:
        return "No candidate data is available yet. Candidates need to be uploaded and scored first."

    return "\n".join(context_parts)


def ask_gemini(user_message, context):
    """
    Sends the HR question + candidate context to Gemini.
    Returns Gemini's response as a plain string.
    """
    prompt = f"""You are HireIQ Assistant, an AI helper for HR professionals.
You help recruiters understand and compare job candidates based on their resumes and scores.

You have access to the following candidate data:

{context}

HR Question: {user_message}

Instructions:
- Answer the question directly and clearly based on the candidate data provided
- If ranking candidates, mention their scores
- If comparing skills, be specific about who has what
- Keep your answer professional and concise
- If no relevant data is found, say so honestly
- Format your answer in a readable way using line breaks where helpful
- Do not make up information that is not in the candidate data

Your Answer:"""

    response = gemini_model.generate_content(prompt)
    return response.text


def process_chat_message(user_message, job_id, candidate_scores):
    """
    Main function called by chat_routes.py.
    Ties everything together:
      1. Search ChromaDB for relevant resume chunks
      2. Build context from chunks + scores
      3. Ask Gemini
      4. Return the response

    user_message     : the HR question (string)
    job_id           : optional - filters ChromaDB search to one job
    candidate_scores : list of score dicts sent from Spring (already from MySQL)
    """
    preview = user_message[:60] + ("..." if len(user_message) > 60 else "")
    print(f"[chat_service] Processing message: '{preview}'")

    # Search ChromaDB for relevant resume content
    search_results = search_all_candidates(
        query_text = user_message,
        job_id     = job_id,
        top_k      = 10
    )
    print(f"[chat_service] ChromaDB returned {len(search_results)} results")

    # Build combined context
    context = build_context(search_results, candidate_scores)

    # Ask Gemini
    response_text = ask_gemini(user_message, context)
    print(f"[chat_service] Gemini responded OK")

    return response_text