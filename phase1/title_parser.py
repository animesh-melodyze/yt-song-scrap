"""
LLM subagent: send raw YouTube video titles to GPT, get back structured metadata.
Processes titles in batches of 50 (one API call per batch) to keep cost low.

Returned fields per title:
  song_name  – cleaned song title
  artist     – original artist name
  is_cover   – whether this is a cover of an existing song
  confidence – "high" | "medium" | "low"
"""
import json
import sys

BATCH_SIZE = 50

_SYSTEM_PROMPT = """\
You are a music metadata extraction assistant.
Given a list of YouTube video titles, extract structured metadata for each one.
Respond ONLY with a JSON object: {"results": [ ... ]} with one entry per title in order.

Each entry must have:
  "index"          : 1-based position (int)
  "song_name"      : the song title (string, or null if unknown)
  "artist"         : the original performing artist (string, or null if unknown)
  "is_cover"       : true if this is a cover/arrangement of an existing song (bool)
  "confidence"     : "high", "medium", or "low"
  "genre"          : original song genre e.g. "Pop", "R&B", "Indie Pop" (string, or null)
  "key"            : musical root note e.g. "C", "F#", "Bb" (string, or null)
  "scale"          : "major" or "minor" (string, or null)
  "tempo_bpm"      : approximate BPM as an integer e.g. 120 (int, or null)
  "time_signature" : e.g. "4/4", "3/4", "6/8" (string, or null)

Rules:
- Strip channel-specific suffixes like "Piano Cover", "Piano Tutorial", "Sheet Music", "Lyrics", etc.
- If the title format is "Song - Artist", extract accordingly.
- If the format is "Artist - Song", detect and swap correctly.
- Never include instrument type or cover/tutorial labels in song_name or artist.
- For music theory fields (key, scale, tempo_bpm, time_signature) use your training knowledge
  about the original song. If genuinely unknown, use null — do not guess randomly.
- If truly ambiguous about the song itself, set confidence "low" and your best guess.
"""


def _get_client():
    try:
        from openai import OpenAI
    except ImportError:
        print("[error] openai not installed. Run: uv sync --group phase1", file=sys.stderr)
        raise

    from config import OPENAI_API_KEY
    return OpenAI(api_key=OPENAI_API_KEY)


def _parse_batch(client, titles: list[str], model: str) -> list[dict]:
    numbered = "\n".join(f'{i + 1}. "{t}"' for i, t in enumerate(titles))
    user_msg = f"Parse these {len(titles)} video titles:\n\n{numbered}"

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    raw = json.loads(response.choices[0].message.content)
    # Normalise: handle {"results": [...]} or {"titles": [...]} or bare [...]
    if isinstance(raw, list):
        return raw
    for key in ("results", "titles", "data", "items"):
        if key in raw and isinstance(raw[key], list):
            return raw[key]
    # Last resort: if it's a dict of index→entry
    return list(raw.values())


def parse_titles(titles: list[str], model: str = "gpt-4.1-nano") -> list[dict | None]:
    """
    Parse all titles via LLM in batches.
    Returns a list (same length as titles) of dicts or None on failure.
    """
    client = _get_client()
    results: list[dict | None] = []

    for start in range(0, len(titles), BATCH_SIZE):
        batch = titles[start: start + BATCH_SIZE]
        print(f"  [LLM] Parsing titles {start + 1}–{start + len(batch)} of {len(titles)} …")
        try:
            batch_results = _parse_batch(client, batch, model)
            # Pad/trim to match batch length in case LLM returns wrong count
            batch_results = (batch_results + [None] * len(batch))[: len(batch)]
            results.extend(batch_results)
        except Exception as e:
            print(f"  [warn] LLM batch failed: {e}", file=sys.stderr)
            results.extend([None] * len(batch))

    return results
