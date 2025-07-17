import logging
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from datetime import datetime

 
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter( tags=["Home"])

@router.get("/", response_class=HTMLResponse)
async def root():
    """Simple HTML interface for testing"""
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Stock App</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .form-group { margin-bottom: 20px; }
            input, button { padding: 10px; margin: 5px; }
            .result { background: #f5f5f5; padding: 20px; margin-top: 20px; }
            .error { color: red; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Stock Information App</h1>
            <p>This app requires Azure AD authentication. Use the API endpoints with proper authorization.</p>
            
            <h2>API Endpoints:</h2>
            <ul>
                <li><strong>GET /api/token</strong> - Get access token</li>
                <li><strong>GET /api/stock/{symbol}</strong> - Get stock information</li>
                <li><strong>GET /api/stock/{symbol}/history</strong> - Get stock history</li>
            </ul>
            
            <h2>Authentication:</h2>
            <p>Include the access token in the Authorization header:</p>
            <code>Authorization: Bearer &lt;your-token&gt;</code>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_template)
# Health check endpoint
@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": settings.app_version,
        "uptime": "active"
    }