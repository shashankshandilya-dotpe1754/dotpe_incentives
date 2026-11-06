"""
Sales incentive portal.

Run locally with sample data:   DEMO_MODE=1 COOKIE_SECURE=0 python app.py
Run in production:              gunicorn -w 1 --threads 8 -b 0.0.0.0:8000 app:app
"""
from __future__ import annotations

import hmac
import logging
import secrets
from datetime import timedelta

from flask import (Flask, abort, jsonify, redirect, render_template, request,
                   session, url_for)

from config import Config
from service import Portal, PortalError
from sheets import make_source

log = logging.getLogger("incentive-portal")


def create_app(cfg=Config, source=None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(cfg)
    if not app.config["SECRET_KEY"]:
        if cfg.DEMO_MODE:
            app.config["SECRET_KEY"] = secrets.token_hex(32)
        else:
            raise RuntimeError("Set SECRET_KEY to a long random string.")
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=cfg.COOKIE_SECURE,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    )
    portal = Portal(source or make_source(cfg), cfg)
    app.extensions["portal"] = portal

    oauth = None
    if not cfg.DEMO_MODE:
        from authlib.integrations.flask_client import OAuth
        oauth = OAuth(app)
        oauth.register(
            name="google",
            client_id=cfg.GOOGLE_CLIENT_ID,
            client_secret=cfg.GOOGLE_CLIENT_SECRET,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )

    # ---------------------------------------------------------------- helpers

    def current_email() -> str | None:
        return session.get("email")

    def csrf_token() -> str:
        if "csrf" not in session:
            session["csrf"] = secrets.token_urlsafe(32)
        return session["csrf"]

    def sign_in(email: str):
        session.clear()
        session.permanent = True
        session["email"] = email.strip().lower()

    @app.context_processor
    def inject():
        return {"csrf_token": csrf_token, "demo": cfg.DEMO_MODE}

    @app.after_request
    def headers(resp):
        resp.headers["Cache-Control"] = "no-store"          # pages hold private pay data
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "same-origin"
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self' https://fonts.googleapis.com; "
            "font-src https://fonts.gstatic.com; img-src 'self' data:; frame-ancestors 'none'"
        )
        return resp

    # ----------------------------------------------------------------- routes

    @app.get("/")
    def home():
        email = current_email()
        if not email:
            return render_template("login.html")
        try:
            data = portal.dashboard(email)
        except Exception:
            log.exception("Failed to load dashboard for %s", email)
            return render_template("error.html", email=email), 503
        if data is None:
            return render_template("denied.html", email=email), 403
        return render_template("dashboard.html", **data, saved=request.args.get("saved") == "1")

    @app.get("/login")
    def login():
        if cfg.DEMO_MODE:
            return redirect(url_for("home"))
        return oauth.google.authorize_redirect(
            url_for("auth_callback", _external=True), hd=cfg.ALLOWED_DOMAIN, prompt="select_account")

    @app.get("/auth/callback")
    def auth_callback():
        if cfg.DEMO_MODE:
            abort(404)
        token = oauth.google.authorize_access_token()
        info = token.get("userinfo") or {}
        email = str(info.get("email", "")).lower()
        if not info.get("email_verified") or not email.endswith("@" + cfg.ALLOWED_DOMAIN):
            session.clear()
            return render_template("denied.html", email=email or "an unknown account",
                                   wrong_domain=True), 403
        sign_in(email)
        return redirect(url_for("home"))

    @app.post("/demo-login")
    def demo_login():
        if not cfg.DEMO_MODE:
            abort(404)
        sign_in(request.form.get("email", ""))
        return redirect(url_for("home"))

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("home"))

    @app.post("/api/salary")
    def save_salary():
        email = current_email()
        if not email:
            return jsonify(error="Your session has ended. Sign in again."), 401
        sent = request.headers.get("X-CSRF-Token", "")
        expected = session.get("csrf", "")
        if not sent or not expected or not hmac.compare_digest(sent, expected):
            return jsonify(error="This page is out of date. Refresh and try again."), 400
        body = request.get_json(silent=True) or {}
        try:
            portal.save_salaries(email, body.get("salaries"))
        except PortalError as e:
            return jsonify(error=str(e)), 400
        except Exception:
            log.exception("Failed to save salary for %s", email)
            return jsonify(error="Your salary couldn’t be saved because the sheet didn’t respond. "
                                 "Try again in a minute."), 503
        return jsonify(ok=True)

    @app.get("/healthz")
    def health():
        return "ok"

    return app


app = create_app()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(debug=Config.DEMO_MODE, port=5000)
