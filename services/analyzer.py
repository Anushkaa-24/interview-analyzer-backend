import os, json, re
from services.scorer import compute_local_scores

FILLER_WORDS = ["um","uh","like","basically","actually","so","you know","right","mean","literally"]


def analyze_interview(
    transcript: str,
    word_list: list[str],
    duration_seconds: float,
    role: str, interview_type: str, round: str,
    format: str, tier: str, experience: str,
) -> dict:

    filler_counts = {}
    text_lower = transcript.lower()
    for fw in FILLER_WORDS:
        count = len(re.findall(r'\b' + re.escape(fw) + r'\b', text_lower))
        if count > 0:
            filler_counts[fw] = count

    filler_words_list = [{"word": w, "count": c} for w, c in sorted(filler_counts.items(), key=lambda x: -x[1])]
    total_fillers = sum(filler_counts.values())

    wpm = int(len(word_list) / (duration_seconds / 60)) if duration_seconds > 0 else 0

    context = f"""
Role: {role or 'Not specified'}
Interview type: {interview_type or 'General'}
Round: {round or 'Not specified'}
Format: {format or 'Not specified'}
Company tier: {tier or 'Not specified'}
Experience level: {experience or 'Not specified'}
Duration: {int(duration_seconds)}s | WPM: {wpm} | Total fillers: {total_fillers}

TRANSCRIPT:
{transcript}
""".strip()

    api_key = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        try:
            result = _ai_analyze(context, role, filler_words_list, total_fillers, api_key)
            return result
        except Exception as e:
            print(f"AI analysis failed: {e} — using local fallback")

    return compute_local_scores(
        transcript=transcript,
        word_list=word_list,
        duration_seconds=duration_seconds,
        filler_words_list=filler_words_list,
        total_fillers=total_fillers,
        wpm=wpm,
        role=role,
    )


def _ai_analyze(context: str, role: str, filler_words_list: list, total_fillers: int, api_key: str) -> dict:
    prompt = f"""You are an expert interview coach analyzing a real interview transcript.

{context}

Return ONLY valid JSON (no markdown, no explanation) with this exact structure:
{{
  "overall_score": <int 1-10>,
  "summary": "<2 honest sentences about performance>",
  "total_fillers": {total_fillers},
  "long_pauses": <int>,
  "confidence_drops": <int>,
  "filler_words": {json.dumps(filler_words_list)},
  "questions": [
    {{
      "number": 1,
      "question": "<likely interview question asked>",
      "clarity": <int 1-10>,
      "depth": <int 1-10>,
      "relevance": <int 1-10>,
      "feedback": "<1-2 sentence specific critique>",
      "timestamp": "<estimated MM:SS>",
      "pause_detected": <true|false>
    }}
  ],
  "weaknesses": [
    {{"name": "<weakness>", "impact": "<high|medium|low>", "severity": <int 0-100>}}
  ],
  "improvement_plan": [
    {{"week": "Week 1-2", "goal": "<goal>", "tasks": ["<task1>", "<task2>", "<task3>"]}}
  ]
}}

Generate 3-5 questions, 4-5 weaknesses, and 4 improvement plan weeks based on actual transcript content."""

    if os.getenv("GROQ_API_KEY"):
        return _call_groq(prompt)

    if os.getenv("OPENAI_API_KEY"):
        return _call_openai(prompt)

    if os.getenv("ANTHROPIC_API_KEY"):
        return _call_anthropic(prompt)


def _call_groq(prompt: str) -> dict:
    from groq import Groq
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    resp = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    raw = resp.choices[0].message.content.strip()
    return json.loads(raw.replace("```json", "").replace("```", "").strip())


def _call_openai(prompt: str) -> dict:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    raw = resp.choices[0].message.content.strip()
    return json.loads(raw.replace("```json", "").replace("```", "").strip())


def _call_anthropic(prompt: str) -> dict:
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    resp = client.messages.create(
        model="claude-haiku-20240307",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.content[0].text.strip()
    return json.loads(raw.replace("```json", "").replace("```", "").strip())
