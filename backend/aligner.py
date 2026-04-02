"""
aligner.py — Forced alignment using WhisperX (en + zh).
"""
from __future__ import annotations
import torch


def _get_device() -> str:
    if torch.backends.mps.is_available():
        return 'mps'
    if torch.cuda.is_available():
        return 'cuda'
    return 'cpu'


def get_audio_duration(audio_path: str) -> float:
    import torchaudio  # type: ignore
    info = torchaudio.info(audio_path)
    return info.num_frames / info.sample_rate


def align_audio_text(audio_path: str, text: str, language: str = 'en') -> list[dict]:
    """
    Forced alignment: given audio + known transcript text, return word-level timestamps.

    Returns: list of {word: str, start: float, end: float}
    """
    import whisperx  # type: ignore

    lang = language.lower()
    if lang in ('zh', 'chinese', 'zh-cn'):
        lang = 'zh'
    elif lang in ('en', 'english'):
        lang = 'en'

    device = _get_device()
    print(f"[aligner] device={device}, language={lang}")

    duration = get_audio_duration(audio_path)

    # Build a pseudo-segment spanning the whole file
    pseudo_segments = [{'text': text, 'start': 0.0, 'end': duration}]

    # Load alignment model
    align_model, align_metadata = whisperx.load_align_model(
        language_code=lang,
        device=device,
    )

    # Load audio
    audio = whisperx.load_audio(audio_path)

    # Align
    result = whisperx.align(
        pseudo_segments,
        align_model,
        align_metadata,
        audio,
        device,
        return_char_alignments=False,
    )

    words = []
    for seg in result.get('segments', []):
        for w in seg.get('words', []):
            words.append({
                'word': w.get('word', ''),
                'start': float(w.get('start', 0)),
                'end': float(w.get('end', 0)),
            })
    return words
