import logging
import os
import sys
from datetime import datetime, timezone
from urllib.parse import quote_plus, urlencode

from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix


load_dotenv()


# Send application logs to stdout.
# Azure App Service can collect stdout/stderr as AppServiceConsoleLogs.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
    force=True,
)


# Check required environment variables before starting the app.
required_variables = [
    "AUTH0_DOMAIN",
    "AUTH0_CLIENT_ID",
    "AUTH0_CLIENT_SECRET",
    "AUTH0_SECRET",
    "AUTH0_REDIRECT_URI",
]

missing_variables = [
    variable for variable in required_variables if not os.getenv(variable)
]

if missing_variables:
    raise RuntimeError(
        "Missing required environment variables: "
        + ", ".join(missing_variables)
    )


app = Flask(__name__)
app.secret_key = os.environ["AUTH0_SECRET"]

# Azure App Service uses a reverse proxy.
# ProxyFix allows Flask to correctly understand forwarded HTTPS requests.
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,
    x_proto=1,
    x_host=1,
)

is_production = os.getenv("APP_ENV", "development").lower() == "production"

app.config.update(
    SESSION_COOKIE_SECURE=is_production,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)


# Configure Auth0 through Authlib.
oauth = OAuth(app)

oauth.register(
    name="auth0",
    client_id=os.environ["AUTH0_CLIENT_ID"],
    client_secret=os.environ["AUTH0_CLIENT_SECRET"],
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=(
        f"https://{os.environ['AUTH0_DOMAIN']}"
        "/.well-known/openid-configuration"
    ),
)


def get_timestamp() -> str:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def get_client_ip() -> str:
    """Return the original client IP when running behind Azure."""
    forwarded_for = request.headers.get("X-Forwarded-For")

    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    return request.remote_addr or "unknown"


def get_current_user():
    """Return the authenticated user stored in the Flask session."""
    return session.get("user")


def log_unauthorized_access(route: str) -> None:
    """Create a structured warning log for unauthorized access."""
    app.logger.warning(
        "UNAUTHORIZED_ACCESS route=%s ip=%s timestamp=%s",
        route,
        get_client_ip(),
        get_timestamp(),
    )


@app.route("/")
def index():
    """Display the home page."""
    return render_template(
        "index.html",
        user=get_current_user(),
    )


@app.route("/login")
def login():
    """Redirect the user to the Auth0 Universal Login page."""
    redirect_uri = os.environ["AUTH0_REDIRECT_URI"]

    return oauth.auth0.authorize_redirect(
        redirect_uri=redirect_uri
    )


@app.route("/callback")
def callback():
    """Process the authorization response returned by Auth0."""
    try:
        token = oauth.auth0.authorize_access_token()
        user_info = token.get("userinfo")

        if not user_info:
            app.logger.error(
                "LOGIN_ERROR reason=no_userinfo ip=%s timestamp=%s",
                get_client_ip(),
                get_timestamp(),
            )
            return "Authentication error: user information was not returned.", 400

        user = dict(user_info)
        session["user"] = user

        app.logger.info(
            "LOGIN_SUCCESS user_id=%s email=%s ip=%s timestamp=%s",
            user.get("sub", "unknown"),
            user.get("email", "unknown"),
            get_client_ip(),
            get_timestamp(),
        )

        # Return to /protected or /profile if login started there.
        next_url = session.pop("next_url", url_for("index"))
        return redirect(next_url)

    except Exception as error:
        app.logger.exception(
            "LOGIN_ERROR error=%s ip=%s timestamp=%s",
            str(error),
            get_client_ip(),
            get_timestamp(),
        )

        return f"Authentication error: {str(error)}", 400


@app.route("/profile")
def profile():
    """Display the authenticated user's profile."""
    user = get_current_user()

    if not user:
        log_unauthorized_access("/profile")
        session["next_url"] = url_for("profile")
        return redirect(url_for("login"))

    return render_template(
        "profile.html",
        user=user,
    )


@app.route("/protected")
def protected():
    """Allow only authenticated users to access the protected page."""
    user = get_current_user()

    if not user:
        log_unauthorized_access("/protected")
        session["next_url"] = url_for("protected")
        return redirect(url_for("login"))

    app.logger.info(
        "PROTECTED_ACCESS user_id=%s email=%s route=/protected "
        "ip=%s timestamp=%s",
        user.get("sub", "unknown"),
        user.get("email", "unknown"),
        get_client_ip(),
        get_timestamp(),
    )

    return render_template(
        "protected.html",
        user=user,
    )


@app.route("/logout")
def logout():
    """Clear the local session and end the Auth0 session."""
    user = get_current_user()

    if user:
        app.logger.info(
            "LOGOUT user_id=%s email=%s ip=%s timestamp=%s",
            user.get("sub", "unknown"),
            user.get("email", "unknown"),
            get_client_ip(),
            get_timestamp(),
        )

    session.clear()

    return_to = os.getenv(
        "AUTH0_LOGOUT_RETURN_TO",
        url_for("index", _external=True),
    )

    query_string = urlencode(
        {
            "returnTo": return_to,
            "client_id": os.environ["AUTH0_CLIENT_ID"],
        },
        quote_via=quote_plus,
    )

    logout_url = (
        f"https://{os.environ['AUTH0_DOMAIN']}"
        f"/v2/logout?{query_string}"
    )

    return redirect(logout_url)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=not is_production,
    )