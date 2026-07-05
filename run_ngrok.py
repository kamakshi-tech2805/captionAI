"""
Runs the Flask app and exposes it publicly through ngrok.
Usage: python run_ngrok.py
"""

import os
from dotenv import load_dotenv
from pyngrok import ngrok
from app import app

load_dotenv()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))

    authtoken = os.getenv("NGROK_AUTHTOKEN")
    if authtoken:
        ngrok.set_auth_token(authtoken)

    domain = os.getenv("NGROK_DOMAIN")
    tunnel = ngrok.connect(port, domain=domain) if domain else ngrok.connect(port)

    print(f"\n🚀 CaptionAI is live at: {tunnel.public_url}\n")

    app.run(host="0.0.0.0", port=port)
