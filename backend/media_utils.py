"""
media_utils.py — shared utility for video-to-audio extraction.
"""
from __future__ import annotations
import os
import tempfile
from pathlib import Path

VIDEO_EXTS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m2ts', '.ts', '.rmvb', '.rm'}


def extract_audio_if_video(audio_path: str) -> tuple[str, str | None]:
    """
    If audio_path is a video file, extract audio to a temp MP3 and return
    (mp3_path, tmp_dir). Caller must delete tmp_dir when done.

    If it is already an audio file, return (audio_path, None).
    """
    if Path(audio_path).suffix.lower() not in VIDEO_EXTS:
        return audio_path, None

    tmp_dir = tempfile.mkdtemp()
    mp3_path = os.path.join(tmp_dir, Path(audio_path).stem + '.mp3')
    ret = os.system(
        f'ffmpeg -y -i "{audio_path}" -vn -ar 44100 -ac 2 -b:a 192k "{mp3_path}" > /dev/null 2>&1'
    )
    if ret != 0:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise RuntimeError(
            'ffmpeg failed to extract audio from video. '
            'Make sure ffmpeg is installed: brew install ffmpeg'
        )
    print(f"[media_utils] video audio extracted: {audio_path} → {mp3_path}")
    return mp3_path, tmp_dir
