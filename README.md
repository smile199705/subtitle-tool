# 字幕生产工具

> 本地运行 · 数据不出机器 · Apple Silicon 原生加速

基于 Whisper large-v3 与 WhisperX 构建的本地字幕生成服务。支持纯语音识别（ASR）与语音+文本强制对齐两种核心模式，中英双语，提供 Web 操作面板与 HTTP API 双接入方式，可独立使用，也可作为工作流或自动化管线中的字幕处理节点。

---

## 核心能力

| 能力 | 说明 |
|---|---|
| 🎙 语音识别（ASR） | 上传音频，自动转写为 SRT，无需提供文稿 |
| 📝 强制对齐 | 提供已知文稿，精准生成词级时间轴 |
| 📦 批量处理 | 多文件并发处理，支持 CSV / Excel 映射文稿 |
| 🌐 中英双语 | 两种模式均支持 English 与中文 |
| 🔒 完全本地 | 无云端 API，推理不联网，数据不离开本机 |
| ⚡ M1 原生加速 | mlx-whisper 直接调用 Apple GPU，较 CPU 快 3–5 倍 |
| 🔗 工作流集成 | 提供异步 HTTP API，可接入 n8n、Make 或自定义 Agent |

---

## 目录结构

```
subtitle-tool/
├── backend/
│   ├── server.py          FastAPI 服务（port 8765）
│   ├── transcriber.py     ASR：mlx-whisper → openai-whisper 降级
│   ├── aligner.py         Forced Alignment：WhisperX (en + zh)
│   ├── segmenter.py       字幕分段算法
│   ├── srt_writer.py      SRT 格式输出
│   └── requirements.txt   Python 依赖
├── panel/
│   └── index.html         Web 操作面板（由服务托管）
├── output/                生成的 SRT 文件
├── start.sh               一键启动脚本
├── stop.sh                停止服务脚本
├── README.md              中文文档
└── README.en.md           English Documentation
```

---

## 一、系统前置依赖

> 以下依赖必须在运行 `start.sh` 前手动安装，无法通过 pip 替代。

### 1.1 Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/homebrew/install/HEAD/install.sh)"
```

### 1.2 ffmpeg

Whisper 与 WhisperX 底层均依赖 ffmpeg 进行音频解码，缺少此依赖将直接报错退出。

```bash
brew install ffmpeg
ffmpeg -version    # 输出版本号即表示安装成功
```

### 1.3 Python 3.10（推荐）

WhisperX 对 Python 版本敏感，推荐使用 3.10，避免 3.12+ 带来的兼容性问题。

**方式 A：pyenv（推荐，多版本隔离）**

```bash
brew install pyenv
pyenv install 3.10.14
pyenv local 3.10.14
python3 --version    # → Python 3.10.14
```

**方式 B：系统 Python（≥ 3.9 均可）**

```bash
python3 --version    # 确认版本 ≥ 3.9
```

---

## 二、模型部署

### 2.1 模型清单

| 用途 | HuggingFace 仓库 | 大小 | 加速方式 |
|---|---|---|---|
| ASR（Apple Silicon 优化） | `mlx-community/whisper-large-v3-mlx` | ~3.1 GB | Apple MLX GPU |
| ASR（CPU 降级备用） | `openai/whisper-large-v3` | ~3.1 GB | CPU |
| 英文强制对齐 | `jonatasgrosman/wav2vec2-large-960h-lv60-self` | ~1.3 GB | MPS / CPU |
| 中文强制对齐 | `jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn` | ~1.3 GB | MPS / CPU |

> 磁盘总占用约 **6–8 GB**，请预留充足空间。

### 2.2 缓存路径

```
~/.cache/huggingface/hub/    ← Whisper MLX、wav2vec2 对齐模型
~/.cache/whisper/            ← openai-whisper 模型
```

### 2.3 自动下载（默认行为）

首次调用接口时，服务自动从 HuggingFace 下载对应模型并缓存，后续离线可用。首次启动需要稳定的网络连接，国内环境建议配置代理。

### 2.4 手动预下载（弱网 / 离线部署）

在正式使用前提前拉取所有模型：

```bash
cd ~/Desktop/自媒体/subtitle-tool
source .venv/bin/activate

python3 -c "import whisper; whisper.load_model('large-v3')"
python3 -c "import mlx_whisper; mlx_whisper.transcribe('', path_or_hf_repo='mlx-community/whisper-large-v3-mlx')" 2>/dev/null || true
python3 -c "import whisperx; whisperx.load_align_model('en', device='cpu')"
python3 -c "import whisperx; whisperx.load_align_model('zh', device='cpu')"
```

### 2.5 HuggingFace 认证（报 401 时）

部分对齐模型需要账号授权访问：

```bash
pip install huggingface_hub
huggingface-cli login    # 粘贴 Access Token（read 权限即可）
```

Token 申请路径：HuggingFace → Settings → Access Tokens → New token。

---

## 三、服务部署

### 3.1 一键启动

```bash
cd ~/Desktop/自媒体/subtitle-tool
./start.sh
```

启动成功后浏览器自动打开 `http://127.0.0.1:8765`，顶部状态栏显示「服务已连接」即可使用。

`start.sh` 执行步骤：

| 步骤 | 操作 |
|---|---|
| 1 | 检测 python3 是否可用 |
| 2 | 创建虚拟环境 `.venv`（已存在则跳过） |
| 3 | 安装 Python 依赖 |
| 4 | 安装 mlx-whisper（Apple Silicon 专用，失败自动跳过） |
| 5 | 停止已有服务进程 |
| 6 | 以 `.venv/bin/python` 启动 FastAPI 服务（后台运行） |
| 7 | 以 `nc -z` 探测端口，等待服务就绪 |
| 8 | 打开浏览器面板 |

### 3.2 停止服务

```bash
./stop.sh
```

### 3.3 手动启动（备用方式）

```bash
cd ~/Desktop/自媒体/subtitle-tool
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
pip install mlx-whisper               # Apple Silicon 专用，失败可跳过
.venv/bin/python backend/server.py    # 前台运行，Ctrl+C 停止

# 另开终端标签页
open http://127.0.0.1:8765
```

### 3.4 查看运行日志

```bash
tail -f /tmp/subtitle-tool.log
```

### 3.5 修改端口

1. 修改 `backend/server.py` 末行 `port=8765` 为目标端口
2. 修改 `panel/index.html` 首行 JS 中 `const API = 'http://127.0.0.1:8765'` 为相同端口

---

## 四、使用说明

浏览器访问 `http://127.0.0.1:8765`，面板提供三种处理模式。

### 模式一：语音识别（ASR）

1. 切换至「🎙 语音识别」Tab
2. 上传音频文件（支持 MP3 / WAV / M4A / MP4 等格式）
3. 选择语言（English / 中文），点击「开始识别」
4. 识别完成后下载 SRT，文件同时保存至 `output/` 目录

### 模式二：语音 + 文本强制对齐

1. 切换至「📝 语音+文本对齐」Tab
2. 上传音频，粘贴完整文稿
3. 选择语言，点击「开始对齐」

### 模式三：批量处理

**批量语音识别：**
1. 切换至「📦 批量处理」→「批量语音识别」
2. 拖拽或多选音频文件，点击「开始批量处理」
3. 每个文件独立显示处理进度，完成后支持单独或全部下载

**批量强制对齐：**
1. 切换至「📦 批量处理」→「批量语音+文本对齐」
2. 上传文稿映射表（CSV 或 Excel）
3. 上传对应音频文件，面板自动校验匹配状态
4. 确认全部显示「✓ 已匹配」后点击「开始批量处理」

**映射表格式（CSV）：**

```csv
filename,text
episode1.mp3,Hello world. This is the transcript for episode one.
episode2.mp3,第二集的完整文字稿内容。
```

| 列名识别规则 | 可接受的列名（不区分大小写） |
|---|---|
| 文件名列 | `filename` / `file` / `name` / `文件名` / `音频` |
| 文本列 | `text` / `transcript` / `content` / `文稿` / `文本` / `字幕` |

- 列名缺失时默认：第 0 列 = 文件名，第 1 列 = 文稿
- 支持 `.xlsx` / `.xls`（首次使用需联网加载 SheetJS 解析库）
- 面板内置「下载 CSV 模板」按钮

---

## 五、技术架构

```
浏览器 / 工作流客户端
        │  HTTP
        ▼
FastAPI + uvicorn  (127.0.0.1:8765)
        │
        ├─ GET  /                  Web 操作面板
        ├─ GET  /health            服务健康检查
        │
        ├─ POST /transcribe        同步 ASR（面板使用）
        ├─ POST /align             同步强制对齐（面板使用）
        │
        ├─ POST /jobs/transcribe   异步 ASR（工作流使用）
        ├─ POST /jobs/align        异步强制对齐（工作流使用）
        ├─ GET  /jobs/{job_id}     轮询任务状态
        └─ GET  /jobs              任务列表
                │
                └── Thread Pool（run_in_executor）
                        ├── transcriber.py
                        │       ├── mlx-whisper large-v3  [Apple MLX GPU]
                        │       └── openai-whisper large-v3  [CPU 降级]
                        └── aligner.py
                                └── whisperx.align()
                                        ├── wav2vec2-large (英文)  [MPS/CPU]
                                        └── wav2vec2-xlsr-chinese (中文)  [MPS/CPU]

推理结果 → segmenter.py（分段）→ srt_writer.py（SRT 格式化）→ output/
```

### 字幕分段规则

| 触发条件 | 阈值 |
|---|---|
| 强标点（`.!?。！？`） | 当前段时长 ≥ 0.8 s 时断句 |
| 软标点（`,;:，；：`） | 累计时长 ≥ 2 s 时断句 |
| 无标点强制断句 | 累计时长 ≥ 5 s |
| 短段合并 | 时长 < 0.8 s 的段合并至前一段 |

---

## 六、HTTP API

**Base URL：** `http://127.0.0.1:8765`

提供同步与异步两套接口：
- **同步接口**：请求阻塞至推理完成，适合面板与简单脚本调用
- **异步接口**：立即返回 `job_id`，通过轮询获取结果，适合工作流与 Agent 集成

---

### 同步接口

#### `GET /health`

服务健康检查。

**Response `200`**
```json
{ "status": "ok" }
```

---

#### `POST /transcribe`

提交语音识别任务，同步等待结果。

**Request** `multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `audio` | File | ✓ | 音频文件 |
| `language` | string | — | `en`（默认）或 `zh` |

**Response `200`**
```json
{
  "srt": "1\n00:00:00,000 --> 00:00:03,200\nHello world.\n\n2\n...",
  "segments": [
    { "text": "Hello world.", "start": 0.0, "end": 3.2 }
  ],
  "output_file": "/path/to/output/episode1_20260402_143022.srt"
}
```

---

#### `POST /align`

提交强制对齐任务，同步等待结果。

**Request** `multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `audio` | File | ✓ | 音频文件 |
| `text` | string | ✓ | 完整文稿 |
| `language` | string | — | `en`（默认）或 `zh` |

**Response `200`**

格式同 `/transcribe`，`output_file` 文件名含 `_aligned` 后缀。

---

### 异步接口

#### `POST /jobs/transcribe`

提交语音识别任务，立即返回任务 ID。

**Request** `multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `audio` | File | ✓ | 音频文件 |
| `language` | string | — | `en`（默认）或 `zh` |

**Response `202`**
```json
{
  "job_id": "e3b0c442-98fb-4c5a-a9d1-3c7f2e1b0d5a",
  "status": "pending"
}
```

---

#### `POST /jobs/align`

提交强制对齐任务，立即返回任务 ID。

**Request** `multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `audio` | File | ✓ | 音频文件 |
| `text` | string | ✓ | 完整文稿 |
| `language` | string | — | `en`（默认）或 `zh` |

**Response `202`**
```json
{
  "job_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "status": "pending"
}
```

---

#### `GET /jobs/{job_id}`

查询指定任务的状态与结果。`status` 枚举值：`pending` / `running` / `done` / `error`。

**Response `200` — 处理中**
```json
{
  "job_id": "e3b0c442-...",
  "status": "running",
  "created_at": "2026-04-02T14:30:00.123456",
  "result": null,
  "error": null
}
```

**Response `200` — 已完成**
```json
{
  "job_id": "e3b0c442-...",
  "status": "done",
  "created_at": "2026-04-02T14:30:00.123456",
  "result": {
    "srt": "1\n00:00:00,000 --> 00:00:03,200\nHello world.\n\n...",
    "segments": [{ "text": "Hello world.", "start": 0.0, "end": 3.2 }],
    "output_file": "/path/to/output/episode1_20260402_143022.srt"
  },
  "error": null
}
```

**Response `200` — 失败**
```json
{
  "job_id": "e3b0c442-...",
  "status": "error",
  "created_at": "2026-04-02T14:30:00.123456",
  "result": null,
  "error": "No speech detected"
}
```

**Response `404`** — job_id 不存在

---

#### `GET /jobs`

获取全部任务列表（不含 `result` 字段，按创建时间倒序）。

**Response `200`**
```json
[
  {
    "job_id": "e3b0c442-...",
    "status": "done",
    "created_at": "2026-04-02T14:35:00.000000",
    "error": null
  },
  {
    "job_id": "a1b2c3d4-...",
    "status": "running",
    "created_at": "2026-04-02T14:30:00.000000",
    "error": null
  }
]
```

---

### 调用示例

**Python — 异步提交 + 轮询**

```python
import requests
import time

BASE = 'http://127.0.0.1:8765'

# 提交任务
with open('episode1.mp3', 'rb') as f:
    resp = requests.post(
        f'{BASE}/jobs/transcribe',
        files={'audio': f},
        data={'language': 'zh'}
    )
resp.raise_for_status()
job_id = resp.json()['job_id']

# 轮询直到完成
while True:
    job = requests.get(f'{BASE}/jobs/{job_id}').json()
    if job['status'] == 'done':
        print(job['result']['srt'])
        break
    if job['status'] == 'error':
        raise RuntimeError(job['error'])
    time.sleep(3)
```

**curl — 同步调用**

```bash
curl -X POST http://127.0.0.1:8765/transcribe \
  -F "audio=@episode1.mp3" \
  -F "language=zh"
```

---

## 七、环境要求

| 项目 | 要求 |
|---|---|
| 硬件 | Apple Silicon Mac（M1 / M2 / M3）推荐；Intel Mac 可用，速度慢 3–5 倍 |
| 操作系统 | macOS 12+ |
| Python | 3.9 – 3.11（推荐 3.10） |
| ffmpeg | 必须，通过 `brew install ffmpeg` 安装 |
| 磁盘空间 | ≥ 10 GB 可用空间（模型 ~7 GB + 虚拟环境 ~2 GB） |
| 内存 | 推荐 16 GB+（large-v3 运行时占用约 5–6 GB） |

---

## 八、常见问题

**`ffmpeg not found` 或音频解码报错**
执行 `brew install ffmpeg` 安装。

**首次启动耗时很长**
正在下载 torch 与模型文件，总计约 8 GB，需稳定网络连接，国内建议配置代理。

**下载模型时报 `401 Unauthorized`**
需要 HuggingFace Access Token，参见「2.5」章节。

**浏览器显示「服务未连接」**
确认访问地址为 `http://127.0.0.1:8765` 而非本地文件路径。查看日志：`cat /tmp/subtitle-tool.log`。

**端口 8765 被占用**
执行 `lsof -i :8765` 查看占用进程，`kill <PID>` 释放端口，或参照「3.5」修改端口。

**`whisperx` 安装失败**
通常为 torch 版本不兼容，指定版本后重试：
```bash
pip install torch==2.1.0 torchaudio==2.1.0 && pip install whisperx
```

**批量对齐提示「✗ 缺失」**
CSV 中 `filename` 列的值须与上传的音频文件名完全一致（含扩展名），匹配不区分大小写。

**Excel 文件解析失败**
首次使用需联网加载 SheetJS 解析库，离线环境请改用 CSV 格式。

---

## 九、输出文件规范

所有生成的 SRT 文件保存至 `output/` 目录，命名规则：

```
{原文件名}_{YYYYMMDD_HHMMSS}.srt              # 语音识别模式
{原文件名}_aligned_{YYYYMMDD_HHMMSS}.srt      # 强制对齐模式
```

示例：
```
output/
├── episode1_20260402_143022.srt
└── episode2_aligned_20260402_143055.srt
```
