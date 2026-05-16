"""Google OAuth 2.0 delegation provider for the MCP authorization server.

Implements OAuthAuthorizationServerProvider so the MCP SDK handles all
protocol-level OAuth 2.1 machinery. Identity verification is delegated
to Google; only the configured allowed_email can authenticate.

State is persisted to a GCS blob so tokens survive Cloud Run restarts.
"""

import json
import logging
import secrets
import time
from typing import Any
from urllib.parse import urlencode

import httpx
from google.cloud import storage
from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    AuthorizeError,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    RegistrationError,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

ACCESS_TOKEN_TTL = 3600  # 1 hour
REFRESH_TOKEN_TTL = 86400 * 30  # 30 days
AUTH_CODE_TTL = 300  # 5 minutes
STATE_BLOB_NAME = "oauth-state/state.json"


class GoogleOAuthProvider(
    OAuthAuthorizationServerProvider[AuthorizationCode, RefreshToken, AccessToken]
):
    """OAuth provider that delegates identity verification to Google.

    Single-user: only allowed_email can authenticate. All OAuth state is
    kept in memory and persisted to GCS after every mutation so container
    restarts don't invalidate active sessions.
    """

    def __init__(
        self,
        google_client_id: str,
        google_client_secret: str,
        allowed_email: str,
        server_url: str,
        gcs_bucket: str,
    ) -> None:
        self._google_client_id = google_client_id
        self._google_client_secret = google_client_secret
        self._allowed_email = allowed_email
        self._server_url = server_url.rstrip("/")
        self._gcs_bucket = gcs_bucket
        self._gcs_client = storage.Client()

        self._clients: dict[str, OAuthClientInformationFull] = {}
        self._auth_codes: dict[str, AuthorizationCode] = {}
        self._access_tokens: dict[str, AccessToken] = {}
        self._refresh_tokens: dict[str, RefreshToken] = {}
        # Maps Google state param → (client_id, AuthorizationParams)
        self._pending_auths: dict[str, tuple[str, AuthorizationParams]] = {}

        self._load_state()

    # ------------------------------------------------------------------
    # State persistence (GCS)
    # ------------------------------------------------------------------

    def _load_state(self) -> None:
        try:
            bucket = self._gcs_client.bucket(self._gcs_bucket)
            blob = bucket.blob(STATE_BLOB_NAME)
            if not blob.exists():
                logger.info("No OAuth state in GCS — starting fresh")
                return
            raw = json.loads(blob.download_as_text())
        except Exception as exc:
            logger.warning("Failed to load OAuth state from GCS: %s — starting fresh", exc)
            return

        now = int(time.time())

        for client_id, data in raw.get("clients", {}).items():
            try:
                self._clients[client_id] = OAuthClientInformationFull.model_validate(data)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping invalid client %s: %s", client_id, exc)

        for code, data in raw.get("auth_codes", {}).items():
            try:
                ac = AuthorizationCode.model_validate(data)
                if ac.expires_at > now:
                    self._auth_codes[code] = ac
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping invalid auth code: %s", exc)

        for token, data in raw.get("access_tokens", {}).items():
            try:
                at = AccessToken.model_validate(data)
                if at.expires_at is None or at.expires_at > now:
                    self._access_tokens[token] = at
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping invalid access token: %s", exc)

        for token, data in raw.get("refresh_tokens", {}).items():
            try:
                rt = RefreshToken.model_validate(data)
                if rt.expires_at is None or rt.expires_at > now:
                    self._refresh_tokens[token] = rt
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping invalid refresh token: %s", exc)

        pending_ttl = 600
        for state_key, data in raw.get("pending_auths", {}).items():
            try:
                client_id = data["client_id"]
                created_at = data.get("created_at", 0)
                params = AuthorizationParams.model_validate(data["params"])
                if now - created_at < pending_ttl:
                    self._pending_auths[state_key] = (client_id, params)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping invalid pending auth: %s", exc)

        logger.info(
            "Loaded OAuth state: %d clients, %d access tokens, %d refresh tokens",
            len(self._clients),
            len(self._access_tokens),
            len(self._refresh_tokens),
        )

    def _save_state(self) -> None:
        state: dict[str, Any] = {
            "clients": {
                cid: client.model_dump(mode="json") for cid, client in self._clients.items()
            },
            "auth_codes": {
                code: ac.model_dump(mode="json") for code, ac in self._auth_codes.items()
            },
            "access_tokens": {
                tok: at.model_dump(mode="json") for tok, at in self._access_tokens.items()
            },
            "refresh_tokens": {
                tok: rt.model_dump(mode="json") for tok, rt in self._refresh_tokens.items()
            },
            "pending_auths": {
                sk: {
                    "client_id": cid,
                    "params": params.model_dump(mode="json"),
                    "created_at": int(time.time()),
                }
                for sk, (cid, params) in self._pending_auths.items()
            },
        }
        try:
            bucket = self._gcs_client.bucket(self._gcs_bucket)
            blob = bucket.blob(STATE_BLOB_NAME)
            blob.upload_from_string(json.dumps(state, indent=2), content_type="application/json")
        except Exception as exc:
            logger.error("Failed to persist OAuth state to GCS: %s", exc)

    # ------------------------------------------------------------------
    # Dynamic Client Registration
    # ------------------------------------------------------------------

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return self._clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        if client_info.client_id is None:
            raise RegistrationError(
                error="invalid_client_metadata",
                error_description="client_id is required",
            )
        logger.info("Registering MCP client: %s", client_info.client_id)
        self._clients[client_info.client_id] = client_info
        self._save_state()

    # ------------------------------------------------------------------
    # Authorization
    # ------------------------------------------------------------------

    async def authorize(
        self,
        client: OAuthClientInformationFull,
        params: AuthorizationParams,
    ) -> str:
        if not self._google_client_id or not self._google_client_secret:
            raise AuthorizeError(
                error="server_error",
                error_description="Google OAuth credentials not configured",
            )

        google_state = secrets.token_urlsafe(32)
        self._pending_auths[google_state] = (client.client_id, params)
        self._save_state()

        query = urlencode(
            {
                "client_id": self._google_client_id,
                "redirect_uri": f"{self._server_url}/oauth2/callback",
                "response_type": "code",
                "scope": "openid email profile",
                "state": google_state,
                "access_type": "offline",
                "prompt": "consent",
            }
        )
        return f"{GOOGLE_AUTH_URL}?{query}"

    # ------------------------------------------------------------------
    # Google OAuth Callback
    # ------------------------------------------------------------------

    async def handle_google_callback(self, code: str, state: str) -> str:
        """Exchange Google code for identity, verify email, mint MCP auth code.

        Returns the redirect URL to send the browser back to the MCP client.
        Raises ValueError if state is invalid or the user is not authorized.
        """
        pending = self._pending_auths.pop(state, None)
        if pending is None:
            raise ValueError("Invalid or expired OAuth state")

        client_id, auth_params = pending

        async with httpx.AsyncClient() as http:
            token_resp = await http.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self._google_client_id,
                    "client_secret": self._google_client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": f"{self._server_url}/oauth2/callback",
                },
            )

        if token_resp.status_code != 200:
            logger.error("Google token exchange failed: %s", token_resp.text)
            raise ValueError("Failed to exchange Google authorization code")

        google_access_token = token_resp.json()["access_token"]

        async with httpx.AsyncClient() as http:
            userinfo_resp = await http.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {google_access_token}"},
            )

        if userinfo_resp.status_code != 200:
            raise ValueError("Failed to retrieve Google user info")

        email = userinfo_resp.json().get("email", "")
        if email != self._allowed_email:
            logger.warning("Unauthorized email attempted MCP auth: %s", email)
            raise ValueError(f"Email {email!r} is not authorized")

        logger.info("Google OAuth verified for: %s", email)

        mcp_code = secrets.token_urlsafe(32)
        self._auth_codes[mcp_code] = AuthorizationCode(
            code=mcp_code,
            client_id=client_id,
            redirect_uri=auth_params.redirect_uri,
            redirect_uri_provided_explicitly=auth_params.redirect_uri_provided_explicitly,
            code_challenge=auth_params.code_challenge,
            scopes=auth_params.scopes or [],
            expires_at=time.time() + AUTH_CODE_TTL,
            resource=auth_params.resource,
        )
        self._save_state()

        return construct_redirect_uri(
            str(auth_params.redirect_uri),
            code=mcp_code,
            state=auth_params.state,
        )

    # ------------------------------------------------------------------
    # Token Exchange
    # ------------------------------------------------------------------

    async def load_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: str,
    ) -> AuthorizationCode | None:
        code = self._auth_codes.get(authorization_code)
        if code is None or code.client_id != client.client_id:
            return None
        return code

    async def exchange_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: AuthorizationCode,
    ) -> OAuthToken:
        self._auth_codes.pop(authorization_code.code, None)
        now = int(time.time())

        access_token_str = secrets.token_urlsafe(32)
        self._access_tokens[access_token_str] = AccessToken(
            token=access_token_str,
            client_id=client.client_id,
            scopes=authorization_code.scopes,
            expires_at=now + ACCESS_TOKEN_TTL,
            resource=authorization_code.resource,
        )

        refresh_token_str = secrets.token_urlsafe(32)
        self._refresh_tokens[refresh_token_str] = RefreshToken(
            token=refresh_token_str,
            client_id=client.client_id,
            scopes=authorization_code.scopes,
            expires_at=now + REFRESH_TOKEN_TTL,
        )

        self._save_state()

        return OAuthToken(
            access_token=access_token_str,
            token_type="Bearer",  # noqa: S106
            expires_in=ACCESS_TOKEN_TTL,
            refresh_token=refresh_token_str,
            scope=" ".join(authorization_code.scopes) if authorization_code.scopes else None,
        )

    # ------------------------------------------------------------------
    # Refresh Token
    # ------------------------------------------------------------------

    async def load_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: str,
    ) -> RefreshToken | None:
        token = self._refresh_tokens.get(refresh_token)
        if token is None or token.client_id != client.client_id:
            return None
        if token.expires_at is not None and token.expires_at < int(time.time()):
            self._refresh_tokens.pop(refresh_token, None)
            self._save_state()
            return None
        return token

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        self._refresh_tokens.pop(refresh_token.token, None)
        now = int(time.time())
        effective_scopes = scopes or refresh_token.scopes

        access_token_str = secrets.token_urlsafe(32)
        self._access_tokens[access_token_str] = AccessToken(
            token=access_token_str,
            client_id=client.client_id,
            scopes=effective_scopes,
            expires_at=now + ACCESS_TOKEN_TTL,
        )

        new_refresh_str = secrets.token_urlsafe(32)
        self._refresh_tokens[new_refresh_str] = RefreshToken(
            token=new_refresh_str,
            client_id=client.client_id,
            scopes=effective_scopes,
            expires_at=now + REFRESH_TOKEN_TTL,
        )

        self._save_state()

        return OAuthToken(
            access_token=access_token_str,
            token_type="Bearer",  # noqa: S106
            expires_in=ACCESS_TOKEN_TTL,
            refresh_token=new_refresh_str,
            scope=" ".join(effective_scopes) if effective_scopes else None,
        )

    # ------------------------------------------------------------------
    # Token Verification
    # ------------------------------------------------------------------

    async def load_access_token(self, token: str) -> AccessToken | None:
        access_token = self._access_tokens.get(token)
        if access_token is None:
            return None
        if access_token.expires_at is not None and access_token.expires_at < int(time.time()):
            self._access_tokens.pop(token, None)
            self._save_state()
            return None
        return access_token

    # ------------------------------------------------------------------
    # Revocation
    # ------------------------------------------------------------------

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        if isinstance(token, AccessToken):
            self._access_tokens.pop(token.token, None)
            to_remove = [
                k for k, v in self._refresh_tokens.items() if v.client_id == token.client_id
            ]
            for k in to_remove:
                self._refresh_tokens.pop(k, None)
        elif isinstance(token, RefreshToken):
            self._refresh_tokens.pop(token.token, None)
            to_remove = [
                k for k, v in self._access_tokens.items() if v.client_id == token.client_id
            ]
            for k in to_remove:
                self._access_tokens.pop(k, None)
        self._save_state()
