import datetime
import logging
import os

from google.cloud import storage
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import TransportSecuritySettings
from pydantic import AnyHttpUrl
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.routing import Route

from the_curator.auth.provider import GoogleOAuthProvider
from the_curator.podcast_generation import PodcastGeneration

logger = logging.getLogger(__name__)

_server_url = os.environ.get("SERVER_URL", "http://localhost:8080")

oauth_provider = GoogleOAuthProvider(
    google_client_id=os.environ.get("GOOGLE_CLIENT_ID", ""),
    google_client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", ""),
    allowed_email=os.environ.get("ALLOWED_EMAIL", ""),
    server_url=_server_url,
    gcs_bucket=os.environ.get("OAUTH_STATE_BUCKET", "the-curator-oauth-state"),
)

_parsed_host = AnyHttpUrl(_server_url).host or "localhost"

mcp = FastMCP(
    "The Curator",
    auth_server_provider=oauth_provider,
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(_server_url),
        resource_server_url=AnyHttpUrl(_server_url),
        client_registration_options=ClientRegistrationOptions(
            enabled=True,
            valid_scopes=["podcast:read", "podcast:write"],
            default_scopes=["podcast:read", "podcast:write"],
        ),
        revocation_options=RevocationOptions(enabled=True),
        required_scopes=[],
    ),
    transport_security=TransportSecuritySettings(
        allowed_hosts=[_parsed_host],
    ),
)

generator = PodcastGeneration()


@mcp.tool()
def create_podcast_transcript(topic: str) -> list[tuple[str, str]]:
    """Create a podcast transcript on the given topic."""
    return generator.generate_transcript(topic)


@mcp.tool()
def create_podcast_episode(title: str, transcript: list[tuple[str, str]]) -> dict[str, str]:
    """Create a podcast episode with the given title and transcript."""
    audio_file_name = generator.generate_podcast(transcript)

    storage_client = storage.Client()
    bucket_name = os.environ.get("GCS_BUCKET_NAME", "the-curator-podcast-data")
    print(f"Uploading {audio_file_name} to bucket {bucket_name}...")
    bucket = storage_client.bucket(bucket_name)
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    destination_blob_name = f"episodes/{ts}/{title.replace(' ', '_')}.wav"
    print(f"Uploading file to {destination_blob_name}...")
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(audio_file_name)
    print(f"File {audio_file_name} uploaded to {blob.name}.")

    return {"episode_id": audio_file_name, "status": "created"}


async def health(request: Request) -> JSONResponse:
    return JSONResponse({"service": "the-curator", "status": "ok"})


async def google_callback(request: Request) -> Response:
    error = request.query_params.get("error")
    if error:
        logger.error("Google OAuth error: %s", error)
        return Response(content=f"Google OAuth error: {error}", status_code=400)

    code = request.query_params.get("code")
    state = request.query_params.get("state")

    if not code or not state:
        return Response(content="Missing code or state parameter", status_code=400)

    try:
        redirect_url = await oauth_provider.handle_google_callback(code=code, state=state)
        return RedirectResponse(url=redirect_url, status_code=302)
    except ValueError as exc:
        logger.error("OAuth callback failed: %s", exc)
        return Response(content=f"Authorization failed: {exc}", status_code=403)


# mcp.sse_app() includes OAuth discovery, registration, authorize, and token endpoints.
# Insert our custom routes at the front so they take precedence.
app = mcp.sse_app()
app.routes.insert(0, Route("/oauth2/callback", google_callback, methods=["GET"]))
app.routes.insert(0, Route("/health", health))

if __name__ == "__main__":
    mcp.run(transport="stdio")
