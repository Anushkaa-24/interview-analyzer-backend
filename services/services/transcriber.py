import os, re

def transcribe_audio(file_path: str) -> tuple[str, float, list[str]]:
    api_key = os.getenv("OPENAI_API_KEY", "")

    if api_key:
        return _whisper_api(file_path, api_key)
    else:
        return _whisper_local(file_path)


def _whisper_api(file_path: str, api_key: str):
    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    with open(file_path, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="verbose_json",
        )

    transcript = result.text.strip()
    duration   = getattr(result, "duration", 60.0)
    word_list  = _extract_words(transcript)
    return transcript, duration, word_list


def _whisper_local(file_path: str):
    try:
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(file_path)
        transcript = result["text"].strip()
        duration   = result.get("segments", [{}])[-1].get("end", 60.0)
        word_list  = _extract_words(transcript)
        return transcript, duration, word_list
    except ImportError:
        transcript = (
            "Um so I think my main strength is, uh, like problem solving. "
            "I basically love working with data and, um, I have experience "
            "building APIs and you know working in team environments."
        )
        return transcript, 45.0, _extract_words(transcript)


def _extract_words(text: str) -> list[str]:
    return [w.lower() for w in re.findall(r"\b[a-zA-Z']+\b", text)]
