import re

STRONG_PUNCT = set('.!?。！？')
SOFT_PUNCT = set(',;:，；：')

MIN_DURATION = 0.8    # seconds - minimum subtitle segment duration
SOFT_MAX = 2.0        # seconds - max duration before soft punctuation triggers split
HARD_MAX = 5.0        # seconds - max duration before forced split
MERGE_MIN = 0.8       # seconds - merge segments shorter than this


def is_chinese(text: str) -> bool:
    return bool(re.search(r'[\u4e00-\u9fff]', text))


def segment_words(words: list, language: str = 'en') -> list:
    """
    Segment word-level timestamps into subtitle segments.

    words: list of {word: str, start: float, end: float}
    Returns: list of {text: str, start: float, end: float}
    """
    if not words:
        return []

    segments = []
    seg_words = []
    seg_start = words[0]['start']

    def flush(end_time):
        if not seg_words:
            return
        text = ''.join(seg_words) if is_chinese(' '.join(seg_words)) else ' '.join(seg_words)
        segments.append({
            'text': text.strip(),
            'start': seg_start,
            'end': end_time,
        })

    for i, w in enumerate(words):
        word = w['word'].strip()
        if not word:
            continue

        seg_words.append(word)
        duration = w['end'] - seg_start

        last_char = word.rstrip()[-1] if word.rstrip() else ''
        is_last = (i == len(words) - 1)

        if is_last:
            flush(w['end'])
            seg_words = []
        elif last_char in STRONG_PUNCT and duration >= MIN_DURATION:
            flush(w['end'])
            seg_words = []
            seg_start = words[i + 1]['start'] if i + 1 < len(words) else w['end']
        elif last_char in SOFT_PUNCT and duration >= SOFT_MAX:
            flush(w['end'])
            seg_words = []
            seg_start = words[i + 1]['start'] if i + 1 < len(words) else w['end']
        elif duration >= HARD_MAX:
            flush(w['end'])
            seg_words = []
            seg_start = words[i + 1]['start'] if i + 1 < len(words) else w['end']

    # Merge short trailing segments into previous
    result = []
    for seg in segments:
        dur = seg['end'] - seg['start']
        if result and dur < MERGE_MIN:
            prev = result[-1]
            sep = '' if is_chinese(seg['text']) else ' '
            result[-1] = {
                'text': prev['text'] + sep + seg['text'],
                'start': prev['start'],
                'end': seg['end'],
            }
        else:
            result.append(seg)

    return result
