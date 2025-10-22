"""
OAuth Service für ExamCraft AI
Google und Microsoft OAuth2 Integration
"""

from authlib.integrations.starlette_client import OAuth
from authlib.integrations.base_client import OAuthError
from starlette.config import Config
from typing import Optional, Dict, Any
import httpx
import os
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from models.auth import User, OAuthAccount, OAuthProvider, Institution, Role
from services.auth_service import AuthService


# OAuth Configuration
config = Config(environ=os.environ)

oauth = OAuth(config)

# Google OAuth2 Configuration
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# Microsoft OAuth2 Configuration
oauth.register(
    name='microsoft',
    client_id=os.getenv('MICROSOFT_CLIENT_ID'),
    client_secret=os.getenv('MICROSOFT_CLIENT_SECRET'),
    server_metadata_url='https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)


class OAuthService:
    """OAuth Service für Social Login"""

    def __init__(self, db: Session):
        self.db = db
    
    def get_authorization_url(self, provider: str, redirect_uri: str) -> str:
        """
        Generate OAuth authorization URL

        Args:
            provider: OAuth provider (google, microsoft)
            redirect_uri: Callback URL after OAuth authorization

        Returns:
            Authorization URL to redirect user to
        """
        if provider not in ['google', 'microsoft']:
            raise ValueError(f"Unsupported OAuth provider: {provider}")

        client = oauth.create_client(provider)

        # Manually construct authorization URL
        if provider == 'google':
            client_id = os.getenv('GOOGLE_CLIENT_ID')
            auth_url = (
                f"https://accounts.google.com/o/oauth2/v2/auth?"
                f"client_id={client_id}&"
                f"redirect_uri={redirect_uri}&"
                f"response_type=code&"
                f"scope=openid%20email%20profile"
            )
        elif provider == 'microsoft':
            client_id = os.getenv('MICROSOFT_CLIENT_ID')
            auth_url = (
                f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?"
                f"client_id={client_id}&"
                f"redirect_uri={redirect_uri}&"
                f"response_type=code&"
                f"scope=openid%20email%20profile"
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        return auth_url
    
    async def exchange_code_for_token(
        self,
        provider: str,
        code: str,
        redirect_uri: str
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access token

        Args:
            provider: OAuth provider (google, microsoft)
            code: Authorization code from OAuth callback
            redirect_uri: Callback URL (must match authorization request)

        Returns:
            Token response with access_token, id_token, etc.
        """
        if provider not in ['google', 'microsoft']:
            raise ValueError(f"Unsupported OAuth provider: {provider}")

        # Manually exchange code for token
        if provider == 'google':
            token_url = "https://oauth2.googleapis.com/token"
            client_id = os.getenv('GOOGLE_CLIENT_ID')
            client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        elif provider == 'microsoft':
            token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
            client_id = os.getenv('MICROSOFT_CLIENT_ID')
            client_secret = os.getenv('MICROSOFT_CLIENT_SECRET')
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    token_url,
                    data={
                        'code': code,
                        'client_id': client_id,
                        'client_secret': client_secret,
                        'redirect_uri': redirect_uri,
                        'grant_type': 'authorization_code'
                    }
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            raise ValueError(f"OAuth token exchange failed: {e.response.text}")
    
    async def get_user_info(self, provider: str, token: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get user information from OAuth provider
        
        Args:
            provider: OAuth provider (google, microsoft)
            token: OAuth token response
            
        Returns:
            User information from provider
        """
        if provider == 'google':
            return await self._get_google_user_info(token)
        elif provider == 'microsoft':
            return await self._get_microsoft_user_info(token)
        else:
            raise ValueError(f"Unsupported OAuth provider: {provider}")
    
    async def _get_google_user_info(self, token: Dict[str, Any]) -> Dict[str, Any]:
        """Get user info from Google OAuth"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                'https://www.googleapis.com/oauth2/v2/userinfo',
                headers={'Authorization': f"Bearer {token['access_token']}"}
            )
            response.raise_for_status()
            user_info = response.json()
            
            return {
                'provider_user_id': user_info['id'],
                'email': user_info['email'],
                'name': user_info.get('name', ''),
                'first_name': user_info.get('given_name', ''),
                'last_name': user_info.get('family_name', ''),
                'picture': user_info.get('picture'),
                'email_verified': user_info.get('verified_email', False),
                'raw_user_info': user_info
            }
    
    async def _get_microsoft_user_info(self, token: Dict[str, Any]) -> Dict[str, Any]:
        """Get user info from Microsoft OAuth"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                'https://graph.microsoft.com/v1.0/me',
                headers={'Authorization': f"Bearer {token['access_token']}"}
            )
            response.raise_for_status()
            user_info = response.json()
            
            return {
                'provider_user_id': user_info['id'],
                'email': user_info.get('mail') or user_info.get('userPrincipalName'),
                'name': user_info.get('displayName', ''),
                'first_name': user_info.get('givenName', ''),
                'last_name': user_info.get('surname', ''),
                'picture': None,  # Microsoft Graph requires separate call for photo
                'email_verified': True,  # Microsoft accounts are always verified
                'raw_user_info': user_info
            }
    
    def find_or_create_user_from_oauth(
        self,
        provider: str,
        user_info: Dict[str, Any],
        token: Dict[str, Any]
    ) -> User:
        """
        Find existing user by OAuth account or create new user
        
        Args:
            provider: OAuth provider (google, microsoft)
            user_info: User information from OAuth provider
            token: OAuth token response
            
        Returns:
            User object (existing or newly created)
        """
        # Check if OAuth account already exists
        oauth_account = self.db.query(OAuthAccount).filter(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == user_info['provider_user_id']
        ).first()
        
        if oauth_account:
            # Update OAuth account with new token
            oauth_account.access_token = token.get('access_token')
            oauth_account.refresh_token = token.get('refresh_token')
            oauth_account.token_expires_at = datetime.now(timezone.utc)  # TODO: Calculate from expires_in
            oauth_account.last_login_at = datetime.now(timezone.utc)
            oauth_account.email = user_info.get('email')
            oauth_account.name = user_info.get('name')
            oauth_account.picture = user_info.get('picture')
            self.db.commit()
            self.db.refresh(oauth_account)
            return oauth_account.user
        
        # Check if user with same email already exists
        existing_user = self.db.query(User).filter(User.email == user_info['email']).first()
        
        if existing_user:
            # Link OAuth account to existing user
            new_oauth_account = OAuthAccount(
                user_id=existing_user.id,
                provider=provider,
                provider_user_id=user_info['provider_user_id'],
                access_token=token.get('access_token'),
                refresh_token=token.get('refresh_token'),
                email=user_info.get('email'),
                name=user_info.get('name'),
                picture=user_info.get('picture'),
                last_login_at=datetime.now(timezone.utc)
            )
            self.db.add(new_oauth_account)
            self.db.commit()
            return existing_user
        
        # Create new user from OAuth
        # Get or create default institution
        default_institution = self.db.query(Institution).filter(
            Institution.name == "Default Institution"
        ).first()
        
        if not default_institution:
            default_institution = Institution(
                name="Default Institution",
                slug="default-institution",  # URL-friendly identifier
                domain="default.examcraft.ai",
                is_active=True
            )
            self.db.add(default_institution)
            self.db.commit()
            self.db.refresh(default_institution)
        
        # Create new user
        new_user = User(
            email=user_info['email'],
            first_name=user_info.get('first_name', 'Unknown'),
            last_name=user_info.get('last_name', 'User'),
            institution_id=default_institution.id,
            status='active',
            is_email_verified=user_info.get('email_verified', False),
            avatar_url=user_info.get('picture'),
            password_hash=None  # OAuth-only user, no password
        )
        self.db.add(new_user)
        self.db.flush()  # Get user.id
        
        # Assign default Viewer role
        viewer_role = self.db.query(Role).filter(Role.name == "Viewer").first()
        if viewer_role:
            new_user.roles.append(viewer_role)
        
        # Create OAuth account
        new_oauth_account = OAuthAccount(
            user_id=new_user.id,
            provider=provider,
            provider_user_id=user_info['provider_user_id'],
            access_token=token.get('access_token'),
            refresh_token=token.get('refresh_token'),
            email=user_info.get('email'),
            name=user_info.get('name'),
            picture=user_info.get('picture'),
            last_login_at=datetime.now(timezone.utc)
        )
        self.db.add(new_oauth_account)
        
        self.db.commit()
        self.db.refresh(new_user)
        
        return new_user

