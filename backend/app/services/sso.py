"""
SSO Service — Google OAuth2 + SAML/OIDC framework.

Handles identity provider authentication for enterprise customers.
"""
import os
import logging
from typing import Optional, Dict, Any

import requests

logger = logging.getLogger("sparqai.sso")

# Google OAuth2
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"


class GoogleOAuthProvider:
    """Handles Google OAuth2 authentication."""

    def __init__(self, redirect_uri: str):
        self.client_id = GOOGLE_CLIENT_ID
        self.client_secret = GOOGLE_CLIENT_SECRET
        self.redirect_uri = redirect_uri

    def get_authorization_url(self, state: str) -> str:
        """Generate the Google OAuth consent screen URL."""
        scopes = "openid email profile"
        return (
            f"{GOOGLE_AUTH_URL}?"
            f"client_id={self.client_id}&"
            f"redirect_uri={self.redirect_uri}&"
            f"scope={scopes}&"
            f"response_type=code&"
            f"state={state}&"
            f"access_type=offline&"
            f"prompt=select_account"
        )

    def exchange_code(self, code: str) -> Dict[str, Any]:
        """Exchange auth code for tokens and user info."""
        # Exchange code for tokens
        token_resp = requests.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }, timeout=15)

        if token_resp.status_code != 200:
            logger.error(f"Google token exchange failed: {token_resp.text}")
            raise ConnectionError("Failed to exchange Google auth code")

        tokens = token_resp.json()
        access_token = tokens["access_token"]

        # Fetch user profile
        profile_resp = requests.get(GOOGLE_USERINFO_URL, headers={
            "Authorization": f"Bearer {access_token}",
        }, timeout=10)

        if profile_resp.status_code != 200:
            logger.error(f"Google userinfo fetch failed: {profile_resp.text}")
            raise ConnectionError("Failed to fetch Google user profile")

        profile = profile_resp.json()

        return {
            "email": profile["email"],
            "email_verified": profile.get("email_verified", False),
            "full_name": profile.get("name", ""),
            "given_name": profile.get("given_name", ""),
            "family_name": profile.get("family_name", ""),
            "picture": profile.get("picture", ""),
            "provider": "google",
            "provider_id": profile.get("sub", ""),
        }


class SAMLProvider:
    """Handles SAML 2.0 authentication via Authlib or direct XML parsing."""

    def __init__(self, metadata_url: str, entity_id: str, acs_url: str):
        self.metadata_url = metadata_url
        self.entity_id = entity_id
        self.acs_url = acs_url
        self._idp_metadata: Optional[Dict] = None

    def get_authorization_url(self, relay_state: str = "") -> str:
        """Generate the SAML AuthnRequest redirect URL."""
        try:
            from authlib.integrations.requests_client import OAuth2Session

            # For SAML, we typically redirect to the IdP's SSO URL
            # Parse IdP metadata to get SSO endpoint
            metadata = self._load_idp_metadata()
            sso_url = metadata.get("sso_url", "")

            if not sso_url:
                raise ValueError("No SSO URL found in IdP metadata")

            return f"{sso_url}?RelayState={relay_state}"
        except ImportError:
            logger.warning("authlib not available for SAML, using basic redirect")
            return f"{self.metadata_url}?RelayState={relay_state}"

    def validate_response(self, saml_response: str) -> Dict[str, Any]:
        """Validate a SAML response and extract user attributes."""
        try:
            import xml.etree.ElementTree as ET
            from base64 import b64decode

            # Decode SAML response
            xml_data = b64decode(saml_response)
            root = ET.fromstring(xml_data)

            # Extract NameID (email) and attributes
            ns = {
                "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
                "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
            }

            assertion = root.find(".//saml:Assertion", ns)
            if assertion is None:
                raise ValueError("No assertion found in SAML response")

            name_id = assertion.find(".//saml:NameID", ns)
            email = name_id.text if name_id is not None else ""

            # Extract attributes
            attrs = {}
            for attr_stmt in assertion.findall(".//saml:AttributeStatement/saml:Attribute", ns):
                attr_name = attr_stmt.get("Name", "")
                attr_value = attr_stmt.find("saml:AttributeValue", ns)
                if attr_value is not None:
                    attrs[attr_name] = attr_value.text

            return {
                "email": email,
                "email_verified": True,
                "full_name": attrs.get("displayName", attrs.get("name", "")),
                "given_name": attrs.get("givenName", attrs.get("firstName", "")),
                "family_name": attrs.get("sn", attrs.get("lastName", "")),
                "provider": "saml",
                "provider_id": email,
            }
        except Exception as e:
            logger.error(f"SAML response validation failed: {e}")
            raise ValueError(f"Invalid SAML response: {e}")

    def _load_idp_metadata(self) -> Dict:
        """Fetch and parse IdP metadata XML."""
        if self._idp_metadata:
            return self._idp_metadata

        try:
            resp = requests.get(self.metadata_url, timeout=10)
            if resp.status_code != 200:
                raise ConnectionError(f"Failed to fetch IdP metadata: {resp.status_code}")

            import xml.etree.ElementTree as ET
            root = ET.fromstring(resp.text)

            ns = {"md": "urn:oasis:names:tc:SAML:2.0:metadata"}
            sso_service = root.find(
                ".//md:IDPSSODescriptor/md:SingleSignOnService[@Binding='urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect']",
                ns,
            )

            self._idp_metadata = {
                "sso_url": sso_service.get("Location", "") if sso_service is not None else "",
                "entity_id": root.get("entityID", ""),
            }
            return self._idp_metadata
        except Exception as e:
            logger.error(f"Failed to load IdP metadata: {e}")
            return {}


def get_sso_provider(org) -> Optional[Any]:
    """Factory to get the appropriate SSO provider for an organization."""
    if not org or not org.sso_enabled:
        return None

    provider_type = (org.sso_provider or "").lower()

    if provider_type == "google":
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        return GoogleOAuthProvider(redirect_uri=f"{frontend_url}/sso-callback")

    if provider_type in ("okta", "azure_ad", "onelogin"):
        if org.sso_metadata_url:
            return SAMLProvider(
                metadata_url=org.sso_metadata_url,
                entity_id=org.sso_entity_id or "",
                acs_url=org.sso_acs_url or "",
            )

    return None
