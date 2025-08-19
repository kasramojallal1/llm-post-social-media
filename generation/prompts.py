# generation/prompts.py
from __future__ import annotations

SYSTEM_PROMPT = """You are a writing assistant that crafts concise, evidence-grounded LinkedIn posts.
Always use the provided persona and retrieval snippets. Do not invent facts.
Output ONLY a JSON object matching the requested schema. No extra text."""

USER_PROMPT_TEMPLATE = """Persona:
- Name: Kasra Mojallal
- Summary: ML researcher/engineer focused on LLM robustness, federated learning, and AI security.
- Audience: recruiters, hiring managers, ML engineers.

Task:
Write a LinkedIn post draft about: "{topic}"

Constraints:
- Tone: {tone}  | Length: {length}  | Emojis: {emojis}  | Hashtags enabled: {hashtags}
- 120–180 words for "short".
- Cite at least 1–2 sources explicitly from the snippets; do not fabricate URLs.
- Include a one-line hook, then body, then hashtags (3–6) if enabled.

Retrieval snippets (top-{top_k}):
{snippets_block}

Return JSON with fields:
topic, audience, style, retrieval (with the snippets you used), draft {{ one_liner, body, hashtags, citations[] }}."""

def build_user_prompt(*, topic: str, tone: str, length: str, emojis: bool, hashtags: bool, top_k: int, snippets_block: str) -> str:
    return USER_PROMPT_TEMPLATE.format(
        topic=topic,
        tone=tone,
        length=length,
        emojis=str(emojis).lower(),
        hashtags=str(hashtags).lower(),
        top_k=top_k,
        snippets_block=snippets_block
    )