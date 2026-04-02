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
