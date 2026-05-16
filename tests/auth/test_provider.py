import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from the_curator.auth.provider import ACCESS_TOKEN_TTL, GoogleOAuthProvider


def _make_provider() -> GoogleOAuthProvider:
    """Create a provider with a mocked GCS client (no real GCS access)."""
    provider = GoogleOAuthProvider.__new__(GoogleOAuthProvider)
    provider._google_client_id = "test-client-id"
    provider._google_client_secret = "test-client-secret"
    provider._allowed_email = "allowed@example.com"
    provider._server_url = "https://example.com"
    provider._gcs_bucket = "test-bucket"
    provider._gcs_client = MagicMock()
    provider._clients = {}
    provider._auth_codes = {}
    provider._access_tokens = {}
    provider._refresh_tokens = {}
    provider._pending_auths = {}
    return provider


def _mock_gcs_client_empty(provider: GoogleOAuthProvider) -> None:
    """Configure the GCS mock so the state blob does not exist."""
    blob = MagicMock()
    blob.exists.return_value = False
    bucket = MagicMock()
    bucket.blob.return_value = blob
    provider._gcs_client.bucket.return_value = bucket


# ------------------------------------------------------------------
# GCS state load / save
# ------------------------------------------------------------------


def test_load_state_starts_fresh_when_blob_missing() -> None:
    provider = _make_provider()
    _mock_gcs_client_empty(provider)
    provider._load_state()
    assert provider._clients == {}
    assert provider._access_tokens == {}


def test_load_state_prunes_expired_access_tokens() -> None:
    import json

    provider = _make_provider()
    expired_tok = {
        "token": "expired",
        "client_id": "c1",
        "scopes": [],
        "expires_at": int(time.time()) - 10,
    }
    state = {
        "clients": {},
        "auth_codes": {},
        "access_tokens": {"expired": expired_tok},
        "refresh_tokens": {},
        "pending_auths": {},
    }
    blob = MagicMock()
    blob.exists.return_value = True
    blob.download_as_text.return_value = json.dumps(state)
    bucket = MagicMock()
    bucket.blob.return_value = blob
    provider._gcs_client.bucket.return_value = bucket

    provider._load_state()

    assert "expired" not in provider._access_tokens


def test_save_state_uploads_json_to_gcs() -> None:
    provider = _make_provider()
    blob = MagicMock()
    bucket = MagicMock()
    bucket.blob.return_value = blob
    provider._gcs_client.bucket.return_value = bucket

    provider._save_state()

    blob.upload_from_string.assert_called_once()
    content_type = blob.upload_from_string.call_args[1]["content_type"]
    assert content_type == "application/json"


def test_save_state_handles_gcs_error_gracefully() -> None:
    provider = _make_provider()
    provider._gcs_client.bucket.side_effect = Exception("GCS down")
    # Should not raise
    provider._save_state()


# ------------------------------------------------------------------
# Client registration
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_client_stores_and_persists() -> None:
    provider = _make_provider()
    blob = MagicMock()
    bucket = MagicMock()
    bucket.blob.return_value = blob
    provider._gcs_client.bucket.return_value = bucket

    client = MagicMock()
    client.client_id = "mcp-client-1"
    client.model_dump.return_value = {"client_id": "mcp-client-1"}

    await provider.register_client(client)

    assert "mcp-client-1" in provider._clients
    blob.upload_from_string.assert_called_once()


@pytest.mark.asyncio
async def test_get_client_returns_none_for_unknown() -> None:
    provider = _make_provider()
    result = await provider.get_client("unknown")
    assert result is None


# ------------------------------------------------------------------
# Authorization
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_authorize_raises_when_credentials_missing() -> None:
    from mcp.server.auth.provider import AuthorizeError

    provider = _make_provider()
    provider._google_client_id = ""

    with pytest.raises(AuthorizeError):
        await provider.authorize(MagicMock(), MagicMock())


@pytest.mark.asyncio
async def test_authorize_returns_google_url_and_saves_state() -> None:
    provider = _make_provider()
    blob = MagicMock()
    bucket = MagicMock()
    bucket.blob.return_value = blob
    provider._gcs_client.bucket.return_value = bucket

    client = MagicMock()
    client.client_id = "mcp-client-1"
    params = MagicMock()

    url = await provider.authorize(client, params)

    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth")
    assert len(provider._pending_auths) == 1


# ------------------------------------------------------------------
# Google callback — email validation
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_google_callback_rejects_unknown_state() -> None:
    provider = _make_provider()
    with pytest.raises(ValueError, match="Invalid or expired OAuth state"):
        await provider.handle_google_callback(code="code", state="bad-state")


@pytest.mark.asyncio
async def test_handle_google_callback_rejects_wrong_email() -> None:
    provider = _make_provider()
    blob = MagicMock()
    bucket = MagicMock()
    bucket.blob.return_value = blob
    provider._gcs_client.bucket.return_value = bucket

    provider._pending_auths["valid-state"] = ("client-1", MagicMock())

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        token_resp = MagicMock()
        token_resp.status_code = 200
        token_resp.json.return_value = {"access_token": "google-tok"}
        mock_http.post = AsyncMock(return_value=token_resp)

        userinfo_resp = MagicMock()
        userinfo_resp.status_code = 200
        userinfo_resp.json.return_value = {"email": "wrong@example.com"}
        mock_http.get = AsyncMock(return_value=userinfo_resp)

        with pytest.raises(ValueError, match="not authorized"):
            await provider.handle_google_callback(code="code", state="valid-state")


@pytest.mark.asyncio
async def test_handle_google_callback_issues_mcp_code_for_allowed_email() -> None:
    from mcp.server.auth.provider import AuthorizationParams

    provider = _make_provider()
    blob = MagicMock()
    bucket = MagicMock()
    bucket.blob.return_value = blob
    provider._gcs_client.bucket.return_value = bucket

    params = MagicMock(spec=AuthorizationParams)
    params.redirect_uri = "https://mcp-client.example.com/callback"
    params.redirect_uri_provided_explicitly = True
    params.code_challenge = "challenge"
    params.scopes = ["podcast:read"]
    params.state = "mcp-state"
    params.resource = None

    provider._pending_auths["google-state"] = ("client-1", params)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        token_resp = MagicMock()
        token_resp.status_code = 200
        token_resp.json.return_value = {"access_token": "google-tok"}
        mock_http.post = AsyncMock(return_value=token_resp)

        userinfo_resp = MagicMock()
        userinfo_resp.status_code = 200
        userinfo_resp.json.return_value = {"email": "allowed@example.com"}
        mock_http.get = AsyncMock(return_value=userinfo_resp)

        redirect = await provider.handle_google_callback(code="google-code", state="google-state")

    assert len(provider._auth_codes) == 1
    assert redirect.startswith("https://mcp-client.example.com/callback")


# ------------------------------------------------------------------
# Token exchange
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_exchange_authorization_code_issues_tokens() -> None:
    from mcp.server.auth.provider import AuthorizationCode

    provider = _make_provider()
    blob = MagicMock()
    bucket = MagicMock()
    bucket.blob.return_value = blob
    provider._gcs_client.bucket.return_value = bucket

    client = MagicMock()
    client.client_id = "c1"

    auth_code = AuthorizationCode(
        code="mcp-code",
        client_id="c1",
        redirect_uri="https://client.example.com/cb",  # type: ignore[arg-type]
        redirect_uri_provided_explicitly=True,
        code_challenge="challenge",
        scopes=["podcast:read"],
        expires_at=time.time() + 60,
        resource=None,
    )

    token = await provider.exchange_authorization_code(client, auth_code)

    assert token.token_type == "Bearer"
    assert token.expires_in == ACCESS_TOKEN_TTL
    assert token.refresh_token is not None
    assert "mcp-code" not in provider._auth_codes


# ------------------------------------------------------------------
# Access token expiry
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_access_token_returns_none_for_expired() -> None:
    from mcp.server.auth.provider import AccessToken

    provider = _make_provider()
    blob = MagicMock()
    bucket = MagicMock()
    bucket.blob.return_value = blob
    provider._gcs_client.bucket.return_value = bucket

    provider._access_tokens["expired-tok"] = AccessToken(
        token="expired-tok",
        client_id="c1",
        scopes=[],
        expires_at=int(time.time()) - 10,
    )

    result = await provider.load_access_token("expired-tok")

    assert result is None
    assert "expired-tok" not in provider._access_tokens


@pytest.mark.asyncio
async def test_load_access_token_returns_valid_token() -> None:
    from mcp.server.auth.provider import AccessToken

    provider = _make_provider()

    provider._access_tokens["valid-tok"] = AccessToken(
        token="valid-tok",
        client_id="c1",
        scopes=[],
        expires_at=int(time.time()) + 3600,
    )

    result = await provider.load_access_token("valid-tok")

    assert result is not None
    assert result.token == "valid-tok"
