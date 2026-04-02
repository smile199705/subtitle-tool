# Subtitle Production Tool

> Local · Private · Apple Silicon Native

A local subtitle generation tool powered by Whisper large-v3 and WhisperX. Supports **speech recognition (ASR)** and **forced alignment** (audio + transcript → precise timestamps), for both English and Chinese, with single-file and batch modes. Outputs standard SRT files.

---

## Capabilities

| Feature | Description |
|---|---|
| 🎙 Speech Recognition (ASR) | Upload audio, auto-transcribe to SRT — no transcript needed |
| 📝 Forced Alignment | Provide a known transcript, get word-level precise timestamps |
| 📦 Batch Processing | Process multiple files; map transcripts to audio via CSV/Excel |
| 🌐 Bilingual | English and Chinese supported in all modes |
| 🔒 Fully Local | No cloud API, no remote inference — data never leaves your machine |
| ⚡ M1 Acceleration | mlx-whisper uses Apple GPU — 3–5× faster than CPU |
| 🔗 Workflow Integration | Async HTTP API — plug into n8n, Make, or any custom agent |

---

## Project Structure

```
subtitle-tool/
├── backend/
│   ├── server.py          FastAPI service (port 8765)
│   ├── transcriber.py     ASR: mlx-whisper → openai-whisper fallback
│   ├── aligner.py         Forced alignment: WhisperX (en + zh)
│   ├── segmenter.py       Subtitle segmentation algorithm
│   ├── srt_writer.py      SRT formatter
│   └── requirements.txt   Python dependencies
├── panel/
│   └── index.html         Web panel (served by FastAPI)
├── output/                Generated SRT files
├── start.sh               One-command startup
└── stop.sh                Stop the service
```

---

## 1. System Prerequisites

> Must be installed manually before running `start.sh`. Cannot be handled by pip.

### 1.1 Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/homebrew/install/HEAD/install.sh)"
```

### 1.2 ffmpeg (required)

```bash
brew install ffmpeg
ffmpeg -version   # verify
```

### 1.3 Python 3.10 (recommended)

WhisperX is sensitive to Python version. Python 3.10 is recommended to avoid compatibility issues with 3.12+.

**Option A: pyenv (recommended)**

```bash
brew install pyenv
pyenv install 3.10.14
pyenv local 3.10.14
python3 --version   # → Python 3.10.14
```

**Option B: system Python (≥ 3.9)**

```bash
python3 --version   # confirm ≥ 3.9
```

---

## 2. Model Deployment

### 2.1 Model List

| Purpose | HuggingFace Repo | Size | Acceleration |
|---|---|---|---|
| ASR (Apple Silicon) | `mlx-community/whisper-large-v3-mlx` | ~3.1 GB | Apple MLX GPU |
| ASR (CPU fallback) | `openai/whisper-large-v3` | ~3.1 GB | CPU |
| English alignment | `jonatasgrosman/wav2vec2-large-960h-lv60-self` | ~1.3 GB | MPS / CPU |
| Chinese alignment | `jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn` | ~1.3 GB | MPS / CPU |

Total disk usage: **~6–8 GB**.

### 2.2 Cache Locations

```
~/.cache/huggingface/hub/   ← Whisper MLX, wav2vec2 alignment models
~/.cache/whisper/           ← openai-whisper model
```

### 2.3 Automatic Download (default)

Models are downloaded from HuggingFace on first use and cached for offline use. A stable internet connection is required for the first run.

### 2.4 Manual Pre-download (slow/offline environments)

```bash
cd ~/Desktop/自媒体/subtitle-tool
source .venv/bin/activate

python3 -c "import whisper; whisper.load_model('large-v3')"
python3 -c "import mlx_whisper; mlx_whisper.transcribe('', path_or_hf_repo='mlx-community/whisper-large-v3-mlx')" 2>/dev/null || true
python3 -c "import whisperx; whisperx.load_align_model('en', device='cpu')"
python3 -c "import whisperx; whisperx.load_align_model('zh', device='cpu')"
```

### 2.5 HuggingFace Token (if you get 401 Unauthorized)

```bash
pip install huggingface_hub
huggingface-cli login   # paste your Access Token (read permission)
```

Get a token: HuggingFace → Settings → Access Tokens → New token.

---

## 3. Deployment

### 3.1 One-command Startup

```bash
cd ~/Desktop/自媒体/subtitle-tool
./start.sh
```

On success, the browser opens `http://127.0.0.1:8765` automatically. The top status bar shows **"服务已连接"** (Service Connected) when ready.

### 3.2 Stop the Service

```bash
./stop.sh
```

### 3.3 Manual Startup (fallback)

```bash
cd ~/Desktop/自媒体/subtitle-tool
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
pip install mlx-whisper          # Apple Silicon only; safe to skip on failure
.venv/bin/python backend/server.py
# in a new terminal tab:
open http://127.0.0.1:8765
```

### 3.4 View Logs

```bash
tail -f /tmp/subtitle-tool.log
```

### 3.5 Change Port

1. Edit the port in the last line of `backend/server.py`
2. Update `const API = 'http://127.0.0.1:8765'` in `panel/index.html` to match

---

## 4. Usage

Open `http://127.0.0.1:8765` in your browser. When the top status bar shows **Service Connected**, the tool is ready.

### Mode 1: Speech Recognition (ASR)

1. Switch to the **🎙 语音识别** tab
2. Upload an audio file (MP3 / WAV / M4A / MP4, etc.)
3. Select language, click **开始识别**
4. Download the SRT or find it in the `output/` directory

### Mode 2: Forced Alignment

1. Switch to the **📝 语音+文本对齐** tab
2. Upload audio and paste the full transcript
3. Select language, click **开始对齐**

### Mode 3: Batch Processing

**Batch ASR:**
1. Switch to **📦 批量处理** → **批量语音识别**
2. Drag and drop or select multiple audio files
3. Click **开始批量处理** — per-file progress shown in real time
4. Download individually or click **下载全部 SRT**

**Batch Forced Alignment:**
1. Switch to **📦 批量处理** → **批量语音+文本对齐**
2. Upload a CSV or Excel mapping file
3. Upload the corresponding audio files — the panel shows match status automatically
4. Confirm all files show **✓ 已匹配**, then click **开始批量处理**

**CSV / Excel mapping format:**

```csv
filename,text
episode1.mp3,Hello world. This is the transcript for episode one.
episode2.mp3,第二集的文字稿在这里，中文也支持。
```

- Filename column (case-insensitive): `filename` / `file` / `name` / `文件名` / `音频`
- Text column: `text` / `transcript` / `content` / `文稿` / `文本` / `字幕`
- If headers are missing: column 0 = filename, column 1 = text
- Excel `.xlsx` / `.xls` supported (SheetJS loaded from CDN on first use)
- A **Download CSV Template** button is built into the panel

---

## 5. Architecture

```
Browser / Workflow Client
        │  HTTP
        ▼
FastAPI + uvicorn  (127.0.0.1:8765)
        │
        ├─ GET  /                  Web panel
        ├─ GET  /health            Health check
        │
        ├─ POST /transcribe        Sync ASR (web panel)
        ├─ POST /align             Sync forced alignment (web panel)
        │
        ├─ POST /jobs/transcribe   Async ASR (workflow)
        ├─ POST /jobs/align        Async forced alignment (workflow)
        ├─ GET  /jobs/{job_id}     Poll job status
        └─ GET  /jobs              Job list
                │
                └── Thread Pool (run_in_executor)
                        ├── transcriber.py
                        │       ├── mlx-whisper large-v3  [Apple MLX GPU]
                        │       └── openai-whisper large-v3  [CPU fallback]
                        └── aligner.py
                                └── whisperx.align()
                                        ├── wav2vec2-large (English)  [MPS/CPU]
                                        └── wav2vec2-xlsr-chinese (Chinese)  [MPS/CPU]

Inference result → segmenter.py → srt_writer.py → output/
```

### Subtitle Segmentation Rules

| Trigger | Threshold |
|---|---|
| Strong punctuation (`.!?。！？`) | Minimum duration ≥ 0.8 s |
| Soft punctuation (`,;:，；：`) | Accumulated duration ≥ 2 s |
| No punctuation (forced break) | Accumulated duration ≥ 5 s |
| Short segment merge | Duration < 0.8 s → merged into previous |

---

## 6. API Reference

Base URL: `http://127.0.0.1:8765`

Two sets of endpoints are available: **synchronous** (waits for inference to complete) and **async** (returns `job_id` immediately, poll for result). The web panel uses sync endpoints; workflows and agents should use the async endpoints.

---

### Synchronous Endpoints

#### GET /health
```json
{ "status": "ok" }
```

#### POST /transcribe

| Field | Type | Description |
|---|---|---|
| `audio` | File | Audio file |
| `language` | string | `en` or `zh` |

```json
{
  "srt": "1\n00:00:00,000 --> 00:00:03,200\nHello world.\n\n...",
  "segments": [{ "text": "Hello world.", "start": 0.0, "end": 3.2 }],
  "output_file": "/path/to/output/audio_20260402_120000.srt"
}
```

#### POST /align

| Field | Type | Description |
|---|---|---|
| `audio` | File | Audio file |
| `text` | string | Full transcript |
| `language` | string | `en` or `zh` |

Response format same as above; filename includes `_aligned` suffix.

---

### Async Endpoints (recommended for workflows / agents)

#### POST /jobs/transcribe → 202

Submit an ASR job. Returns immediately without waiting for inference.

| Field | Type | Description |
|---|---|---|
| `audio` | File | Audio file |
| `language` | string | `en` or `zh` |

```json
{ "job_id": "e3b0c442-...", "status": "pending" }
```

#### POST /jobs/align → 202

Submit a forced-alignment job. Returns immediately.

| Field | Type | Description |
|---|---|---|
| `audio` | File | Audio file |
| `text` | string | Full transcript |
| `language` | string | `en` or `zh` |

```json
{ "job_id": "a1b2c3d4-...", "status": "pending" }
```

#### GET /jobs/{job_id}

Poll job status. `status` values: `pending` / `running` / `done` / `error`.

**In progress:**
```json
{ "job_id": "...", "status": "running", "created_at": "2026-04-02T14:30:00", "result": null, "error": null }
```

**Completed:**
```json
{
  "job_id": "...",
  "status": "done",
  "created_at": "2026-04-02T14:30:00",
  "result": {
    "srt": "1\n00:00:00,000 --> ...",
    "segments": [...],
    "output_file": "/path/to/output/audio_20260402_143022.srt"
  },
  "error": null
}
```

**Failed:**
```json
{ "job_id": "...", "status": "error", "result": null, "error": "No speech detected" }
```

#### GET /jobs

List all jobs (without result content).

```json
[
  { "job_id": "...", "status": "done",    "created_at": "..." },
  { "job_id": "...", "status": "running", "created_at": "..." }
]
```

---

### Workflow Integration Example (Python)

```python
import requests, time

BASE = 'http://127.0.0.1:8765'

# 1. Submit job
with open('episode1.mp3', 'rb') as f:
    resp = requests.post(f'{BASE}/jobs/transcribe',
                         files={'audio': f},
                         data={'language': 'en'})
job_id = resp.json()['job_id']

# 2. Poll until done
while True:
    job = requests.get(f'{BASE}/jobs/{job_id}').json()
    if job['status'] == 'done':
        srt = job['result']['srt']
        break
    if job['status'] == 'error':
        raise RuntimeError(job['error'])
    time.sleep(3)

print(srt)
```

---

## 7. Requirements

| Item | Requirement |
|---|---|
| Hardware | Apple Silicon Mac (M1/M2/M3) recommended; Intel Mac works but 3–5× slower |
| OS | macOS 12+ |
| Python | 3.9 – 3.11 (3.10 recommended) |
| ffmpeg | Required — `brew install ffmpeg` |
| Disk | ≥ 10 GB free space |
| RAM | 16 GB+ recommended |

---

## 8. Troubleshooting

**`ffmpeg not found` or audio decode error**
`brew install ffmpeg`

**First startup is very slow**
Downloading torch and model weights (~8 GB total). Wait with a stable connection.

**`401 Unauthorized` when downloading models**
HuggingFace token required. See section 2.5.

**Panel shows "Service Disconnected"**
Confirm you are accessing `http://127.0.0.1:8765`. Check logs: `cat /tmp/subtitle-tool.log`

**Port 8765 in use**
`lsof -i :8765` to find the process, `kill <PID>` to free it. See section 3.5 to change port.

**`whisperx` installation fails**
Pin the torch version:
```bash
pip install torch==2.1.0 torchaudio==2.1.0 && pip install whisperx
```

**Batch alignment shows ✗ for some files**
The `filename` column must exactly match the uploaded audio filename including extension. Case-insensitive.

**Excel parsing fails**
SheetJS requires internet access on first use. Switch to CSV format if offline.

---

## 9. Output Files

```
output/
├── episode1_20260402_143022.srt
└── episode2_aligned_20260402_143055.srt
```
