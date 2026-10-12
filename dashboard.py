from flask import Flask, render_template

from db import fetch_recent


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates")

    @app.route("/")
    def index():
        snippets = fetch_recent(limit=20)
        return render_template("index.html", snippets=snippets)

    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app
