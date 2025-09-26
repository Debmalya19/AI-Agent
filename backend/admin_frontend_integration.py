"""
Admin Dashboard Frontend Integration
Integrates the admin dashboard frontend with the main FastAPI application
"""

import os
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import logging

logger = logging.getLogger(__name__)

class AdminFrontendIntegration:
    """Handles integration of admin dashboard frontend with main FastAPI app"""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.admin_frontend_path = Path("admin-dashboard/frontend")
        self.setup_static_files()
        self.setup_routes()
    
    def setup_static_files(self):
        """Configure static file serving for admin dashboard assets"""
        try:
            # Mount admin dashboard static files
            admin_static_path = self.admin_frontend_path
            if admin_static_path.exists():
                # Mount CSS files
                css_path = admin_static_path / "css"
                if css_path.exists():
                    self.app.mount("/admin/css", StaticFiles(directory=str(css_path)), name="admin_css")
                
                # Mount JS files
                js_path = admin_static_path / "js"
                if js_path.exists():
                    self.app.mount("/admin/js", StaticFiles(directory=str(js_path)), name="admin_js")
                
                # Mount admin assets (images, fonts, etc.)
                admin_assets_path = admin_static_path / "admin"
                if admin_assets_path.exists():
                    self.app.mount("/admin/assets", StaticFiles(directory=str(admin_assets_path)), name="admin_assets")
                
                logger.info("Admin dashboard static files mounted successfully")
            else:
                logger.warning(f"Admin frontend path not found: {admin_static_path}")
                
        except Exception as e:
            logger.error(f"Failed to setup admin static files: {e}")
    
    def setup_routes(self):
        """Setup routes for admin dashboard SPA"""
        
        @self.app.get("/admin")
        async def admin_dashboard():
            """Serve admin dashboard main page"""
            return await self.serve_admin_page("index.html")
        
        @self.app.get("/admin/")
        async def admin_dashboard_slash():
            """Serve admin dashboard main page with trailing slash"""
            return await self.serve_admin_page("index.html")
        
        @self.app.get("/admin/dashboard")
        async def admin_dashboard_page():
            """Serve admin dashboard page"""
            return await self.serve_admin_page("index.html")
        
        @self.app.get("/admin/tickets")
        async def admin_tickets_page():
            """Serve admin tickets page"""
            return await self.serve_admin_page("tickets.html")
        
        @self.app.get("/admin/users")
        async def admin_users_page():
            """Serve admin users page"""
            return await self.serve_admin_page("users.html")
        
        @self.app.get("/admin/integration")
        async def admin_integration_page():
            """Serve admin integration page"""
            return await self.serve_admin_page("integration.html")
        
        @self.app.get("/admin/settings")
        async def admin_settings_page():
            """Serve admin settings page"""
            return await self.serve_admin_page("settings.html")
        
        @self.app.get("/admin/register")
        async def admin_register_page():
            """Serve admin registration page"""
            return await self.serve_admin_page("register.html")
        
        @self.app.get("/admin/register.html")
        async def admin_register_html_page():
            """Serve admin registration page with .html extension"""
            return await self.serve_admin_page("register.html")
        
        # Catch-all route for SPA routing
        @self.app.get("/admin/{path:path}")
        async def admin_spa_routes(path: str):
            """Handle SPA routes for admin dashboard"""
            # For SPA routes, serve the main index.html and let frontend routing handle it
            if not path or path.endswith('/'):
                return await self.serve_admin_page("index.html")
            
            # Check if it's a specific page
            if path in ['tickets', 'users', 'integration', 'settings', 'register']:
                return await self.serve_admin_page(f"{path}.html")
            
            # Check for .html files
            if path.endswith('.html'):
                return await self.serve_admin_page(path)
            
            # For other paths, serve index.html for SPA routing
            return await self.serve_admin_page("index.html")
    
    async def serve_admin_page(self, filename: str):
        """Serve an admin dashboard HTML page"""
        try:
            file_path = self.admin_frontend_path / filename
            if file_path.exists():
                return FileResponse(str(file_path), media_type="text/html")
            else:
                logger.warning(f"Admin page not found: {filename}")
                raise HTTPException(status_code=404, detail=f"Admin page not found: {filename}")
        except Exception as e:
            logger.error(f"Error serving admin page {filename}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")


def setup_admin_frontend_integration(app: FastAPI):
    """Setup admin dashboard frontend integration with FastAPI app"""
    try:
        integration = AdminFrontendIntegration(app)
        logger.info("Admin dashboard frontend integration setup completed")
        return integration
    except Exception as e:
        logger.error(f"Failed to setup admin frontend integration: {e}")
        raise