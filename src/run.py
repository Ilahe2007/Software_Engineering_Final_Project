"""Start the app.

Local development:   python src/run.py --dev
Docker / Render:     python run.py          (uses APP_ENV, production if not set)

Render gives the port in the PORT environment variable; locally it is 5000.
"""
import os
import sys

from app import create_app

app = create_app("development" if "--dev" in sys.argv else None)

if __name__ == "__main__":
    # 0.0.0.0 is required inside a Docker container and on Render; on 127.0.0.1
    # nothing outside the container could reach the app.
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))  # nosec B104
