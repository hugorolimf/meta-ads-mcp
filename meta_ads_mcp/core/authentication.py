"""Authentication-specific functionality for Meta Ads API.

The Meta Ads MCP server supports local OAuth flow:
- Uses local callback server on localhost:8080+ for OAuth redirect
- Requires META_ADS_DISABLE_CALLBACK_SERVER to NOT be set
- Best for local development and testing

Environment Variables:
- META_ACCESS_TOKEN: Direct Meta token (fallback)
- META_ADS_DISABLE_LOGIN_LINK: Hard-disables the get_login_link tool; returns a disabled message
"""

import json
from typing import Optional
import asyncio
import os
from .api import meta_api_tool
from . import auth
from .auth import start_callback_server, shutdown_callback_server, auth_manager
from .server import mcp_server
from .utils import logger, META_APP_SECRET

# Only register the login link tool if not explicitly disabled
ENABLE_LOGIN_LINK = not bool(os.environ.get("META_ADS_DISABLE_LOGIN_LINK", ""))


async def get_login_link(access_token: Optional[str] = None) -> str:
    """
    Get a clickable login link for Meta Ads authentication.
    
    This method generates an authentication link using the configured Meta app ID.
    
    Args:
        access_token: Meta API access token (optional - will use cached token if not provided)
    
    Returns:
        A clickable resource link for Meta authentication
    """
    # Check if callback server is disabled
    callback_server_disabled = bool(os.environ.get("META_ADS_DISABLE_CALLBACK_SERVER", ""))
    
    try:
        logger.info("Generating login link for Meta authentication")
        
        # If an access token was provided, this is likely a test - return success
        if access_token:
            return json.dumps({
                "message": "✅ Authentication Token Provided",
                "status": "Using provided access token for authentication",
                "token_info": f"Token preview: {access_token[:10]}...",
                "authentication_method": "manual_token",
                "ready_to_use": "You can now use all Meta Ads MCP tools and commands."
            }, indent=2)
        
        # Check if we already have a valid cached token
        from .auth import auth_manager
        token = auth_manager.get_access_token()
        if token:
            return json.dumps({
                "message": "✅ Already Authenticated",
                "status": "You're successfully authenticated with Meta Ads!",
                "token_info": f"Token preview: {token[:10]}...",
                "authentication_method": "cached_token",
                "ready_to_use": "You can now use all Meta Ads MCP tools and commands."
            }, indent=2)
        
        # Start OAuth flow
        auth_url = auth_manager.get_auth_url()
        
        if auth_url:
            return json.dumps({
                "message": "🔗 Click to Authenticate",
                "login_url": auth_url,
                "markdown_link": f"[🚀 Authenticate with Meta Ads]({auth_url})",
                "instructions": "Click the link above to complete authentication with Meta Ads.",
                "authentication_method": "oauth",
                "what_happens_next": "After clicking, you'll be redirected to Meta's authentication page. Once completed, your token will be automatically saved.",
                "token_duration": "Your token will be valid for approximately 60 days."
            }, indent=2)
        else:
            return json.dumps({
                "message": "❌ Authentication Error",
                "error": "Could not generate authentication URL",
                "troubleshooting": [
                    "Check that META_APP_ID is set correctly",
                    "Ensure your Meta app is properly configured",
                    "Try again in a few moments"
                ],
                "authentication_method": "oauth_failed"
            }, indent=2)
                
    except Exception as e:
        logger.error(f"Error generating login link: {e}")
        return json.dumps({
            "message": "❌ Authentication Error",
            "error": f"Failed to generate authentication link: {str(e)}",
            "troubleshooting": [
                "✅ Check that META_APP_ID environment variable is set",
                "🌐 Verify your network connectivity",
                "🔄 Restart the MCP server",
                "⏰ Try again in a moment"
            ],
            "get_help": "Check logs for more details",
            "authentication_method": "oauth_error"
        }, indent=2)

# Conditionally register as MCP tool only when enabled
if ENABLE_LOGIN_LINK:
    get_login_link = mcp_server.tool()(get_login_link)