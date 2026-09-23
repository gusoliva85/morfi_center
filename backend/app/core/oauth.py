from authlib.integrations.starlette_client import OAuth

from app.core.config import settings

# Endpoints de Google puestos de forma explícita en vez de usar su documento de
# descubrimiento (`server_metadata_url`): así ni el arranque ni el primer login
# dependen de una llamada extra a Google, y los tests no tocan la red.
GOOGLE_ISSUER = "https://accounts.google.com"
GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_JWKS_URI = "https://www.googleapis.com/oauth2/v3/certs"

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    authorize_url=GOOGLE_AUTHORIZE_URL,
    access_token_url=GOOGLE_TOKEN_URL,
    jwks_uri=GOOGLE_JWKS_URI,
    client_kwargs={
        "scope": "openid email profile",
        # PKCE: el navegador manda un desafío al ir y la prueba al volver, así el
        # código de autorización no sirve si alguien lo intercepta en el camino.
        "code_challenge_method": "S256",
    },
)


def google_is_configured() -> bool:
    """Sin credenciales cargadas (`.env` del servidor) el login con Google no
    puede funcionar; conviene decirlo claro y no fallar con un error interno."""
    return bool(settings.google_client_id and settings.google_client_secret)
