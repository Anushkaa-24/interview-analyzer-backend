import re

CONFIDENCE_PHRASES = ["i believe","i'm confident","i demonstrated","i led","i achieved","i improved","i built","successfully"]
WEAK_PHRASES       = ["i think maybe","i'm not sure","i guess","kind of","sort of","i don't know"]
TECH_KEYWORDS      = ["api","database","algorithm","framework","python","javascript","sql","cloud","docker","git","testing","agile"]


def compute_local_scores(
    transcript: str,
    word_list: list[str],
    duration_seconds: float,
    filler_words_list: list,
    total_fillers: int,
    wpm: int,
    role: str,
) -> dict:
    text_lower = transcript.lower()
    word_count = len(word_list)

    filler_rate      = total_fillers / max(word_count, 1)
    confidence_hits  = sum(1 for p in CONFIDENCE_PHRASES if p in text_lower)
    weak_hits        = sum(1 for p in WEAK_PHRASES if p in text_lower)
    tech_hits        = sum(1 for k in TECH_KEYWORDS if k in text_lower)
    vocab_richness   = len(set(word_list)) / max(word_count, 1)

    score = 5.0
    score += min(confidence_hits * 0.4, 2.0)
    score -= min(weak_hits * 0.3, 1.5)
    score -= min(filler_rate * 20, 2.5)
    score += min(tech_hits * 0.3, 1.5)
    score += min((vocab_richness - 0.4) * 5, 1.0)
    if 120 <= wpm <= 160: score += 0.5
    overall = max(1, min(10, round(score)))

    sentences = [s.strip() for s in re.split(r'[.!?]', transcript) if len(s.strip()) > 20]
    questions = []
    for i, sent in enumerate(sentences[:4]):
        clarity   = min(10, max(1, 7 - int(filler_rate * 30)))
        depth     = min(10, max(1, 4 + tech_hits))
        relevance = min(10, max(1, 5 + confidence_hits))
        has_filler = any(fw["word"] in sent.lower() for fw in filler_words_list)
        minutes = int((duration_seconds / max(len(sentences), 1)) * i // 60)
        seconds = int((duration_seconds / max(len(sentences), 1)) * i % 60)
        questions.append({
            "number": i + 1,
            "question": f"Tell me about your experience — segment {i+1}",
            "clarity": clarity,
            "depth": depth,
            "relevance": relevance,
            "feedback": _feedback_for(clarity, depth, has_filler),
            "timestamp": f"{minutes}:{seconds:02d}",
            "pause_detected": has_filler,
        })

    weaknesses = []
    if filler_rate > 0.05:
        weaknesses.append({"name": "Excessive filler words", "impact": "high", "severity": min(95, int(filler_rate * 300))})
    if weak_hits > 1:
        weaknesses.append({"name": "Lack of confidence in language", "impact": "high", "severity": 75})
    if wpm > 170:
        weaknesses.append({"name": "Speaking too fast", "impact": "medium", "severity": 60})
    if wpm < 100:
        weaknesses.append({"name": "Speaking too slowly", "impact": "medium", "severity": 50})
    if tech_hits < 2:
        weaknesses.append({"name": "Shallow technical depth", "impact": "medium", "severity": 55})
    if confidence_hits < 2:
        weaknesses.append({"name": "Weak impact storytelling (no STAR structure)", "impact": "high", "severity": 70})
    if not weaknesses:
        weaknesses.append({"name": "Minor pacing issues", "impact": "low", "severity": 25})

    summary = (
        f"Your response showed {'good' if overall >= 7 else 'limited'} communication skills. "
        f"{'Reduce filler words and speak with more confidence.' if total_fillers > 5 else 'Continue building on your strong delivery.'}"
    )

    return {
        "overall_score": overall,
        "summary": summary,
        "total_fillers": total_fillers,
        "long_pauses": max(0, weak_hits),
        "confidence_drops": w
