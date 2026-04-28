"""
LLM subagent: batch-parse YouTube video titles into structured song metadata.
One API call per 50 titles — works for any channel title format.
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
- Strip suffixes like "Piano Cover", "Piano Tutorial", "Sheet Music", "Lyrics", etc.
- Detect title format (Song - Artist vs Artist - Song) and extract correctly.
- Never include instrument type or cover/tutorial labels in song_name or artist.
- For music theory fields use your training knowledge about the original song.
  If genuinely unknown, use null — do not guess randomly.
- If truly ambiguous about the song itself, set confidence "low".
"""


def _get_client():
    try:
        from openai import OpenAI
    except ImportError:
        print("[error] openai not installed. Run: uv sync --group gpu", file=sys.stderr)
        raise
    from config import OPENAI_API_KEY
    return OpenAI(api_key=OPENAI_API_KEY)


def _parse_batch(client, titles: list[str], model: str) -> list[dict]:
    numbered = "\n".join(f'{i + 1}. "{t}"' for i, t in enumerate(titles))
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Parse these {len(titles)} video titles:\n\n{numbered}"},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    raw = json.loads(response.choices[0].message.content)
    if isinstance(raw, list):
        return raw
    for key in ("results", "titles", "data", "items"):
        if key in raw and isinstance(raw[key], list):
            return raw[key]
    return list(raw.values())


def parse_title(title: str, model: str = "gpt-4.1-nano") -> dict | None:
    """Parse a single video title. Called per-song during pipeline processing."""
    results = parse_titles([title], model=model)
    return results[0] if results else None


def parse_titles(titles: list[str], model: str = "gpt-4.1-nano") -> list[dict | None]:
    """Parse a list of titles in batches. Returns list of same length as input."""
    client = _get_client()
    results: list[dict | None] = []
    for start in range(0, len(titles), BATCH_SIZE):
        batch = titles[start: start + BATCH_SIZE]
        print(f"  [LLM] Parsing titles {start + 1}–{start + len(batch)} of {len(titles)} …")
        try:
            batch_results = _parse_batch(client, batch, model)
            batch_results = (batch_results + [None] * len(batch))[: len(batch)]
            results.extend(batch_results)
        except Exception as e:
            print(f"  [warn] LLM batch failed: {e}", file=sys.stderr)
            results.extend([None] * len(batch))
    return results
