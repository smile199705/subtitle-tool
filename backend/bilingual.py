"""
bilingual.py — Bilingual subtitle generation using Whisper transcribe + translate.

Runs the same audio through Whisper twice:
  1. task=transcribe  → original language, word-level timestamps (for segmentation)
  2. task=translate   → English translation, segment-level

Pairs translated segments onto the original segments by timestamp overlap,
then returns bilingual segment list: [{text_orig, text_trans, start, end}].

Note: Whisper's translate task always translates TO English.
"""
from __future__ import annotations
import shutil
from media_utils import extract_audio_if_video
from transcriber import transcribe_audio, _try_mlx, _try_openai_whisper
from segmenter import segment_words


def transcribe_bilingual(audio_path: str, language: str = 'zh') -> list[dict]:
    """
    Returns list of {text_orig, text_trans, start, end}.
    text_orig  — original language
    text_trans — English translation (via Whisper translate task)
    """
    lang = language.lower()
    if lang in ('zh', 'chinese', 'zh-cn'):
        lang = 'zh'
    elif lang in ('en', 'english'):
        lang = 'en'

    audio_path, tmp_dir = extract_audio_if_video(audio_path)
    try:
        # 1. Original transcription with word timestamps
        words = _try_mlx(audio_path, lang)
        if words is None:
            words = _try_openai_whisper(audio_path, lang)
        if not words:
            raise ValueError('No speech detected')

        # 2. English translation (segment-level, no word timestamps needed)
        trans_segs = _translate_to_english(audio_path, lang)

        # 3. Segment original words
        orig_segs = segment_words(words, lang)

        # 4. Pair by timestamp overlap
        return _pair_bilingual(orig_segs, trans_segs)
    finally:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)


def _translate_to_english(audio_path: str, lang: str) -> list[dict]:
    """Run Whisper with task=translate, return segment-level [{text, start, end}]."""
    # Try mlx first
    try:
        import mlx_whisper  # type: ignore
        print("[bilingual] translate via mlx-whisper...")
        result = mlx_whisper.transcribe(
            audio_path,
            path_or_hf_repo='mlx-community/whisper-large-v3-mlx',
            language=lang,
            task='translate',
        )
        return _extract_segs(result)
    except Exception as e:
        print(f"[bilingual] mlx-whisper translate unavailable: {e}")

    # Fallback to openai-whisper
    print("[bilingual] translate via openai-whisper (CPU)...")
    import whisper  # type: ignore
    model = whisper.load_model('large-v3')
    result = model.transcribe(audio_path, language=lang, task='translate')
    return _extract_segs(result)


def _extract_segs(result: dict) -> list[dict]:
    segs = []
    for s in result.get('segments', []):
        segs.append({
            'text': s.get('text', '').strip(),
            'start': float(s.get('start', 0)),
            'end': float(s.get('end', 0)),
        })
    return segs


def _pair_bilingual(orig_segs: list[dict], trans_segs: list[dict]) -> list[dict]:
    """
    For each orig segment, collect all translated segments that overlap with
    its time range and concatenate their text.
    """
    bilingual = []
    for seg in orig_segs:
        s, e = seg['start'], seg['end']
        # Collect translated text chunks that overlap with [s, e]
        trans_chunks = [
            t['text'] for t in trans_segs
            if t['end'] > s and t['start'] < e
        ]
        text_trans = ' '.join(trans_chunks).strip()
        bilingual.append({
            'text_orig': seg['text'],
            'text_trans': text_trans,
            'start': s,
            'end': e,
        })
    return bilingual
