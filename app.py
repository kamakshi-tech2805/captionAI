"""
CaptionAI — Flask backend
Generates platform-optimized captions, hashtags, and CTAs using
Groq's LLaMA 3.3-70B Versatile model.
"""

import os
import re
import json
import logging

from flask import Flask, render_template, request, jsonify
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("captionai")

app = Flask(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

if not GROQ_API_KEY:
    logger.warning("GROQ_API_KEY is not set. Requests to Groq will fail until it is configured in .env")

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

PLATFORMS = {"instagram", "twitter", "linkedin", "facebook", "tiktok"}
TONES = {"witty", "professional", "casual", "inspirational", "bold", "minimal"}

MAX_TOPIC_LEN = 400


# ---------------------------------------------------------------------------
# Input handling
# ---------------------------------------------------------------------------

def clean_input(text: str) -> str:
    """Strip control characters and cap length so user input can't be used
    to inject instructions or blow up the prompt."""
    if not text:
        return ""
    text = text.strip()
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    return text[:MAX_TOPIC_LEN]


def validate_request(data: dict):
    topic = clean_input(data.get("topic", ""))
    platform = (data.get("platform") or "instagram").strip().lower()
    tone = (data.get("tone") or "casual").strip().lower()

    if not topic:
        return None, "Please describe what your post is about."
    if platform not in PLATFORMS:
        return None, f"Unsupported platform. Choose one of: {', '.join(sorted(PLATFORMS))}"
    if tone not in TONES:
        return None, f"Unsupported tone. Choose one of: {', '.join(sorted(TONES))}"

    return {"topic": topic, "platform": platform, "tone": tone}, None


# ---------------------------------------------------------------------------
# Groq call helper
# ---------------------------------------------------------------------------

def call_groq(system_prompt: str, user_prompt: str, max_tokens: int = 500) -> dict:
    if client is None:
        raise RuntimeError("Groq client is not configured. Set GROQ_API_KEY in your .env file.")

    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.9,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )

    raw = completion.choices[0].message.content
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Model returned non-JSON output: %s", raw)
        raise RuntimeError("The model returned an unexpected response. Please try again.")


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

PLATFORM_NOTES = {
    "instagram": "Visual-first audience. Captions can run a little longer and lead with a hook line.",
    "twitter": "Tight character economy. Punchy, conversational, no fluff.",
    "linkedin": "Professional network. Value-driven, credible, no excessive emoji.",
    "facebook": "Community feel. Warm, conversational, invites comments.",
    "tiktok": "Fast, trend-aware, playful, speaks directly to the viewer.",
}


def caption_prompt(topic, platform, tone):
    system = (
        "You are CaptionAI's Caption Generator. You write scroll-stopping social "
        "media captions. Always respond with strict JSON only, no markdown, in the "
        'exact shape: {"captions": ["...", "...", "..."]}. Return exactly three '
        "captions. Each caption must be a complete, ready-to-post piece of text — "
        "no placeholders, no explanations, no labels like 'Option 1'."
    )
    user = (
        f"Platform: {platform} ({PLATFORM_NOTES.get(platform, '')})\n"
        f"Tone: {tone}\n"
        f"Post topic / context: {topic}\n\n"
        "Write three distinct captions that fit this platform and tone. "
        "Vary the angle across the three (e.g. a hook-first version, a "
        "story/relatable version, a direct/value version)."
    )
    return system, user


def hashtag_prompt(topic, platform, tone):
    system = (
        "You are CaptionAI's Hashtag Suggester. You produce a blended set of "
        "hashtags for social posts. Always respond with strict JSON only, no "
        'markdown, in the exact shape: {"hashtags": ["#tag1", "#tag2", ...]}. '
        "Return exactly ten hashtags, each starting with #, no spaces inside a tag."
    )
    user = (
        f"Platform: {platform}\n"
        f"Tone: {tone}\n"
        f"Post topic / context: {topic}\n\n"
        "Suggest ten hashtags: mix roughly 4 broad/popular tags with strong reach, "
        "4 niche/specific tags with less competition, and 2 community or "
        "branded-style tags relevant to this topic. No duplicates, no numbering."
    )
    return system, user


def cta_prompt(topic, platform, tone):
    system = (
        "You are CaptionAI's Call-to-Action Generator. You write short, punchy, "
        "action-oriented CTAs for social posts. Always respond with strict JSON "
        'only, no markdown, in the exact shape: {"ctas": ["...", "...", "..."]}. '
        "Return exactly three CTAs. Each should be a few words to one short "
        "sentence — no explanations."
    )
    user = (
        f"Platform: {platform} ({PLATFORM_NOTES.get(platform, '')})\n"
        f"Tone: {tone}\n"
        f"Post topic / context: {topic}\n\n"
        "Write three CTAs with different intents (e.g. drive comments, drive "
        "shares/saves, drive clicks/DMs), matching the tone and platform."
    )
    return system, user


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html", platforms=sorted(PLATFORMS), tones=sorted(TONES))


@app.route("/api/generate", methods=["POST"])
def generate():
    """Runs all three modules in one call so the UI can render a full result set."""
    data = request.get_json(silent=True) or {}
    payload, error = validate_request(data)
    if error:
        return jsonify({"error": error}), 400

    topic, platform, tone = payload["topic"], payload["platform"], payload["tone"]

    try:
        captions = call_groq(*caption_prompt(topic, platform, tone), max_tokens=500).get("captions", [])
        hashtags = call_groq(*hashtag_prompt(topic, platform, tone), max_tokens=250).get("hashtags", [])
        ctas = call_groq(*cta_prompt(topic, platform, tone), max_tokens=200).get("ctas", [])
    except RuntimeError as exc:
        logger.exception("Generation failed")
        return jsonify({"error": str(exc)}), 502
    except Exception:
        logger.exception("Unexpected error during generation")
        return jsonify({"error": "Something went wrong generating your content. Please try again."}), 500

    return jsonify({
        "captions": captions[:3],
        "hashtags": hashtags[:10],
        "ctas": ctas[:3],
    })


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok", "groq_configured": client is not None})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
