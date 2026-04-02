"""
server.py — FastAPI backend for subtitle-tool (port 8765).
"""
from __future__ import annotations
import os
import sys
import uuid
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from functools import partial
import asyncio
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
import uvicorn

ROOT = Path(__file__).parent.parent
OUTPUT_DIR = ROOT / 'output'
OUTPUT_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(Path(__file__).parent))
from transcriber import transcribe_audio
from aligner import align_audio_text
from segmenter import segment_words
from srt_writer import to_srt


_VIDEO_EXTS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m2ts', '.ts', '.rmvb', '.rm'}

def _maybe_extract_audio(audio_path: str, tmp_dir: str) -> str:
    """If the file is a video format, extract audio to MP3 via ffmpeg and return the new path."""
    if Path(audio_path).suffix.lower() not in _VIDEO_EXTS:
        return audio_path
    mp3_path = os.path.join(tmp_dir, Path(audio_path).stem + '.mp3')
    ret = os.system(f'ffmpeg -y -i "{audio_path}" -vn -ar 44100 -ac 2 -b:a 192k "{mp3_path}" > /dev/null 2>&1')
    if ret != 0:
        raise RuntimeError('ffmpeg failed to extract audio. Make sure ffmpeg is installed: brew install ffmpeg')
    print(f"[server] video audio extracted to MP3: {mp3_path}")
    return mp3_path

app = FastAPI(title='subtitle-tool', version='1.0.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

# ── In-memory job store ──────────────────────────────────────────────────────
# { job_id: { status, created_at, result, error } }
_jobs: dict[str, dict] = {}


def _new_job() -> str:
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        'job_id': job_id,
        'status': 'pending',       # pending | running | done | error
        'created_at': datetime.now().isoformat(),
        'result': None,
        'error': None,
    }
    return job_id


def _save_srt(srt_text: str, stem: str, suffix: str = '') -> str:
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    name = f'{stem}{suffix}_{ts}.srt'
    out_path = OUTPUT_DIR / name
    out_path.write_text(srt_text, encoding='utf-8')
    return str(out_path)


# ── Shared inference helpers ─────────────────────────────────────────────────

async def _run_transcribe(audio_path: str, language: str, stem: str) -> dict:
    loop = asyncio.get_event_loop()
    words = await loop.run_in_executor(
        None, partial(transcribe_audio, audio_path, language)
    )
    if not words:
        raise ValueError('No speech detected')
    segments = segment_words(words, language)
    srt_text = to_srt(segments)
    output_file = _save_srt(srt_text, stem)
    return {'srt': srt_text, 'segments': segments, 'output_file': output_file}


async def _run_align(audio_path: str, text: str, language: str, stem: str) -> dict:
    loop = asyncio.get_event_loop()
    words = await loop.run_in_executor(
        None, partial(align_audio_text, audio_path, text, language)
    )
    if not words:
        raise ValueError('Alignment produced no words')
    segments = segment_words(words, language)
    srt_text = to_srt(segments)
    output_file = _save_srt(srt_text, stem, '_aligned')
    return {'srt': srt_text, 'segments': segments, 'output_file': output_file}


# ── Panel ────────────────────────────────────────────────────────────────────

@app.get('/', response_class=HTMLResponse)
def panel():
    return (ROOT / 'panel' / 'index.html').read_text(encoding='utf-8')


# ── Health ───────────────────────────────────────────────────────────────────

@app.get('/health')
def health():
    return {'status': 'ok'}


# ── Sync endpoints (used by the web panel) ───────────────────────────────────

@app.post('/transcribe')
async def transcribe(
    audio: UploadFile = File(...),
    language: str = Form('en'),
):
    tmp_dir = tempfile.mkdtemp()
    try:
        audio_path = os.path.join(tmp_dir, audio.filename or 'audio.wav')
        with open(audio_path, 'wb') as f:
            shutil.copyfileobj(audio.file, f)
        audio_path = _maybe_extract_audio(audio_path, tmp_dir)
        stem = Path(audio.filename or 'audio').stem
        result = await _run_transcribe(audio_path, language, stem)
        return JSONResponse(result)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.post('/align')
async def align(
    audio: UploadFile = File(...),
    text: str = Form(...),
    language: str = Form('en'),
):
    tmp_dir = tempfile.mkdtemp()
    try:
        audio_path = os.path.join(tmp_dir, audio.filename or 'audio.wav')
        with open(audio_path, 'wb') as f:
            shutil.copyfileobj(audio.file, f)
        audio_path = _maybe_extract_audio(audio_path, tmp_dir)
        stem = Path(audio.filename or 'audio').stem
        result = await _run_align(audio_path, text, language, stem)
        return JSONResponse(result)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ── Async job endpoints (used by workflows / agents) ─────────────────────────

@app.post('/jobs/transcribe', status_code=202)
async def job_transcribe(
    audio: UploadFile = File(...),
    language: str = Form('en'),
):
    """Submit an ASR job. Returns job_id immediately; poll /jobs/{job_id} for result."""
    job_id = _new_job()
    tmp_dir = tempfile.mkdtemp()

    # Read file into memory so the upload stream can be closed right away
    audio_bytes = await audio.read()
    filename = audio.filename or 'audio.wav'
    stem = Path(filename).stem

    async def _run():
        _jobs[job_id]['status'] = 'running'
        audio_path = os.path.join(tmp_dir, filename)
        try:
            with open(audio_path, 'wb') as f:
                f.write(audio_bytes)
            audio_path = _maybe_extract_audio(audio_path, tmp_dir)
            result = await _run_transcribe(audio_path, language, stem)
            _jobs[job_id].update(status='done', result=result)
        except Exception as e:
            _jobs[job_id].update(status='error', error=str(e))
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    asyncio.create_task(_run())
    return JSONResponse({'job_id': job_id, 'status': 'pending'}, status_code=202)


@app.post('/jobs/align', status_code=202)
async def job_align(
    audio: UploadFile = File(...),
    text: str = Form(...),
    language: str = Form('en'),
):
    """Submit a forced-alignment job. Returns job_id immediately; poll /jobs/{job_id} for result."""
    job_id = _new_job()
    tmp_dir = tempfile.mkdtemp()

    audio_bytes = await audio.read()
    filename = audio.filename or 'audio.wav'
    stem = Path(filename).stem

    async def _run():
        _jobs[job_id]['status'] = 'running'
        audio_path = os.path.join(tmp_dir, filename)
        try:
            with open(audio_path, 'wb') as f:
                f.write(audio_bytes)
            audio_path = _maybe_extract_audio(audio_path, tmp_dir)
            result = await _run_align(audio_path, text, language, stem)
            _jobs[job_id].update(status='done', result=result)
        except Exception as e:
            _jobs[job_id].update(status='error', error=str(e))
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    asyncio.create_task(_run())
    return JSONResponse({'job_id': job_id, 'status': 'pending'}, status_code=202)


@app.get('/jobs/{job_id}')
def job_status(job_id: str):
    """Poll job status. Returns full result when status == done."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')
    return JSONResponse(job)


@app.get('/jobs')
def job_list():
    """List all jobs (id, status, created_at)."""
    summary = [
        {k: v for k, v in j.items() if k != 'result'}
        for j in _jobs.values()
    ]
    return JSONResponse(sorted(summary, key=lambda x: x['created_at'], reverse=True))


if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8765)
