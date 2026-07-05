# CaptionAI

Generative AI-powered social media content assistant. Given a topic, platform,
and tone, it produces:

- **Caption Generator** — 3 unique, platform-optimized captions
- **Hashtag Suggester** — 10 hashtags blending popular and niche tags
- **Call-to-Action Generator** — 3 punchy, action-oriented CTAs

Built with **Flask**, powered by **Groq's LLaMA 3.3-70B Versatile** model,
deployable publicly via **Ngrok**.

## Project structure

```
captionai/
├── app.py                 # Flask app, Groq integration, prompt logic
├── run_ngrok.py            # Runs the app and exposes it via ngrok
├── requirements.txt
├── .env.example
├── templates/
│   └── index.html
└── static/
    ├── css/style.css
    └── js/script.js
```

## Setup

1. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables**

   ```bash
   cp .env.example .env
   ```

   Then edit `.env` and set:

   ```
   GROQ_API_KEY=your_groq_api_key_here
   ```

   Get a free key at [console.groq.com/keys](https://console.groq.com/keys).
   Never commit `.env` — it's already listed in `.gitignore`.

3. **Run locally**

   ```bash
   python app.py
   ```

   Visit `http://localhost:5000`.

4. **Deploy publicly with ngrok** (optional)

   ```bash
   ngrok config add-authtoken <your-authtoken>   # one-time setup
   python run_ngrok.py
   ```

   This prints a public URL (e.g. `https://xxxx.ngrok-free.app`) that tunnels
   to your local Flask server.

## How it works

- `POST /api/generate` accepts `{ topic, platform, tone }`, validates and
  sanitizes the input, then makes three separate calls to Groq — one per
  module — each with a dedicated system prompt and a strict JSON
  `response_format` so the output is easy to parse and render.
- Input is trimmed to 400 characters and stripped of control characters
  before being sent to the model, to keep requests well-formed and
  reduce the risk of prompt injection through user input.
- Supported platforms: `instagram`, `twitter`, `linkedin`, `facebook`, `tiktok`.
- Supported tones: `witty`, `professional`, `casual`, `inspirational`, `bold`, `minimal`.

## Notes on API key security

- The Groq API key is read from the environment (`.env`) on the server side
  only. It is never sent to or exposed in the browser.
- `.env` is excluded from version control via `.gitignore`.

## Extending

- Swap or add tones/platforms by editing the `TONES` / `PLATFORMS` sets and
  `PLATFORM_NOTES` dict in `app.py`.
- Each module's prompt lives in its own function (`caption_prompt`,
  `hashtag_prompt`, `cta_prompt`) so you can tune them independently.
