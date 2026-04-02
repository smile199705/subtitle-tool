"""
transcriber.py — ASR using mlx-whisper (M1 optimised) with fallback to openai-whisper.
"""
from __future__ import annotations


def transcribe_audio(audio_path: str, language: str = 'en') -> list[dict]:
    """
    Transcribe audio file and return word-level timestamps.

    Returns: list of {word: str, start: float, end: float}
    """
    lang = language.lower()
    if lang in ('zh', 'chinese', 'zh-cn'):
        lang = 'zh'
    elif lang in ('en', 'english'):
        lang = 'en'

    words = _try_mlx(audio_path, lang)
    if words is None:
        words = _try_openai_whisper(audio_path, lang)
    return words


def _try_mlx(audio_path: str, lang: str):
    try:
        import mlx_whisper  # type: ignore
        print("[transcriber] Using mlx-whisper (M1)...")
        result = mlx_whisper.transcribe(
            audio_path,
            path_or_hf_repo='mlx-community/whisper-large-v3-mlx',
            language=lang,
            word_timestamps=True,
        )
        return _extract_words_mlx(result)
    except Exception as e:
        print(f"[transcriber] mlx-whisper unavailable: {e}")
        return None


def _extract_words_mlx(result: dict) -> list[dict]:
    words = []
    for seg in result.get('segments', []):
        for w in seg.get('words', []):
            words.append({
                'word': w.get('word', ''),
                'start': float(w.get('start', 0)),
                'end': float(w.get('end', 0)),
            })
    return words


def _try_openai_whisper(audio_path: str, lang: str) -> list[dict]:
    print("[transcriber] Falling back to openai-whisper (CPU)...")
    import whisper  # type: ignore
    model = whisper.load_model('large-v3')
    result = model.transcribe(audio_path, language=lang, word_timestamps=True)
    return _extract_words_mlx(result)  # same structure
