from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.security import APIKeyHeader
from authlib.integrations.starlette_client import OAuthError

from kaptive_web.core.config import settings
from kaptive_web.core.auth import Authorizer
from kaptive_web.db.repository import Repository, User

router = APIRouter(prefix="/auth", tags=["auth"])

api_key_header = APIKeyHeader(name="X-API-Key")

def get_repository() -> Repository:
    return Repository(settings.database_url.replace("sqlite+aiosqlite:///", ""))

async def get_current_user(api_key: str = Depends(api_key_header), repo: Repository = Depends(get_repository)) -> User:
    user = await repo.get_user_by_api_key(api_key)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return user

@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    """Returns the current user's profile."""
    return {
        "id": user.id,
        "api_key": user.api_key
    }

@router.delete("/me")
async def delete_me(user: User = Depends(get_current_user), repo: Repository = Depends(get_repository)):
    """Deletes the current user and all associated data."""
    await repo.delete_user_cascade(user.id)
    return {"status": "deleted"}

async def handle_user_login(repo: Repository, scoped_id: str):
    """Helper method to check the DB, generate API keys, and redirect."""
    user = await repo.get_user_by_id(scoped_id)
    if not user:
        api_key = Authorizer.generate_api_key()
        await repo.create_user(scoped_id, api_key)
        return RedirectResponse(f"/?api_key={api_key}")
    else:
        return RedirectResponse(f"/?api_key={user.api_key}")

# --- ORCID Logic ---
@router.get("/orcid/login")
async def orcid_login(request: Request):
    """Redirects the user to ORCID for authentication."""
    redirect_uri = str(request.url_for("orcid_callback"))
    return await Authorizer.oauth.orcid.authorize_redirect(request, redirect_uri)

@router.get("/orcid/callback")
async def orcid_callback(request: Request, repo: Repository = Depends(get_repository)):
    """Handles the ORCID OAuth2 callback."""
    try:
        token = await Authorizer.oauth.orcid.authorize_access_token(request)
        
        # ORCID's token response includes the 'orcid' ID and 'name' directly
        orcid_str = token.get("orcid")
        name = token.get("name")
        
        if not orcid_str:
            raise ValueError("ORCID iD not found in token response.")
            
    except OAuthError as e:
        raise HTTPException(status_code=400, detail=f"OAuth Error: {e.error}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"ORCID Auth Failed: {str(e)}")

    orcid_id = f"orcid_{orcid_str}"
    
    return await handle_user_login(repo, orcid_id)

# --- GitHub Logic ---
@router.get("/github/login")
async def github_login(request: Request):
    """Redirects the user to GitHub for authentication."""
    redirect_uri = str(request.url_for("github_callback"))
    return await Authorizer.oauth.github.authorize_redirect(request, redirect_uri)

@router.get("/github/callback")
async def github_callback(request: Request, repo: Repository = Depends(get_repository)):
    """Handles the GitHub OAuth2 callback."""
    try:
        token = await Authorizer.oauth.github.authorize_access_token(request)
        
        # For GitHub, we use the token to fetch the user profile
        resp = await Authorizer.oauth.github.get('user', token=token)
        resp.raise_for_status()
        user_data = resp.json()
        
        github_str = str(user_data["id"])
        
    except OAuthError as e:
        raise HTTPException(status_code=400, detail=f"OAuth Error: {e.error}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"GitHub Auth Failed: {str(e)}")

    github_id = f"github_{github_str}"
    return await handle_user_login(repo, github_id)
