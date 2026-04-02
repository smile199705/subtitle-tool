def format_time(seconds: float) -> str:
    """Convert seconds to SRT time format: HH:MM:SS,mmm"""
    ms = int((seconds % 1) * 1000)
    s = int(seconds) % 60
    m = int(seconds) // 60 % 60
    h = int(seconds) // 3600
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def to_srt(segments: list) -> str:
    """Convert segments list to SRT string.

    Each segment: {start: float, end: float, text: str}
    """
    lines = []
    for i, seg in enumerate(segments, 1):
        lines.append(str(i))
        lines.append(f"{format_time(seg['start'])} --> {format_time(seg['end'])}")
        lines.append(seg['text'].strip())
        lines.append("")
    return "\n".join(lines)


def to_srt_bilingual(bilingual_segments: list) -> str:
    """Convert bilingual segments to SRT string with two lines per block.

    Each segment: {start: float, end: float, text_orig: str, text_trans: str}
    Output format:
        1
        00:00:00,000 --> 00:00:03,200
        原文文本
        English translation
    """
    lines = []
    for i, seg in enumerate(bilingual_segments, 1):
        lines.append(str(i))
        lines.append(f"{format_time(seg['start'])} --> {format_time(seg['end'])}")
        lines.append(seg['text_orig'].strip())
        if seg.get('text_trans'):
            lines.append(seg['text_trans'].strip())
        lines.append("")
    return "\n".join(lines)

