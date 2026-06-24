import sys
import httpx2

# The ecosystem bridge: When Authlib looks for 'httpx', it gets 'httpx2'
sys.modules['httpx'] = httpx2 

import secrets
from authlib.integrations.starlette_client import OAuth
from kaptive_web.core.config import settings

API_KEY_PREFIX = "kw_live_"

def generate_api_key(length: int = 32) -> str:
    """
    Generates a secure API key.
    """
    random_part = secrets.token_urlsafe(length)
    return f"{API_KEY_PREFIX}{random_part}"

# Initialize Authlib
oauth = OAuth()

# Configure GitHub
oauth.register(
    name='github',
    client_id=settings.github_client_id,
    client_secret=settings.github_client_secret,
    access_token_url='https://github.com/login/oauth/access_token',
    access_token_params=None,
    authorize_url='https://github.com/login/oauth/authorize',
    authorize_params=None,
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'},
)

# Configure ORCID
oauth.register(
    name='orcid',
    client_id=settings.orcid_client_id,
    client_secret=settings.orcid_client_secret,
    access_token_url='https://orcid.org/oauth/token',
    authorize_url='https://orcid.org/oauth/authorize',
    api_base_url='https://pub.orcid.org/v3.0/',
    client_kwargs={'scope': '/authenticate'}
)
