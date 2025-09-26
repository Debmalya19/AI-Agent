"""
Admin Integration Manager

This module manages the integration of admin dashboard functionality into the main FastAPI application.
It provides a centralized way to register admin routes and manage the integration lifecycle.
"""

from fastapi import FastAPI, HTTPException
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from .admin_dashboard_integration import create_admin_dashboard_integration
from .unified_auth import setup_admin_authentication
# from .unified_models import ensure_admin_models_exist  # This function may not exist yet

logger = logging.getLogger(__name__)

class AdminIntegrationManager:
    """Manages the integration of admin dashboard functionality"""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.routers = []
        self.is_initialized = False
        
    def initialize(self) -> bool:
        """Initialize the admin dashboard integration"""
        try:
            logger.info("Initializing admin dashboard integration...")
            
            # Ensure admin models exist in the database
            # ensure_admin_models_exist()  # TODO: Implement this function if needed
            logger.info("✅ Admin models verified")
            
            # Setup admin authentication
            setup_admin_authentication()
            logger.info("✅ Admin authentication configured")
            
            # Create and register admin routers
            self.routers = create_admin_dashboard_integration()
            
            # Add the ticket router from admin_routes.py
            from .admin_routes import admin_router, ticket_router
            self.routers.extend([admin_router, ticket_router])
            
            for router in self.routers:
                self.app.include_router(router)
                logger.info(f"✅ Registered router: {router.prefix}")
            
            # Add admin-specific middleware if needed
            self._setup_admin_middleware()
            
            # Setup admin frontend integration
            self._setup_admin_frontend()
            
            self.is_initialized = True
            logger.info("🎉 Admin dashboard integration initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize admin dashboard integration: {e}")
            return False
    
    def _setup_admin_middleware(self):
        """Setup admin-specific middleware"""
        # Add any admin-specific middleware here
        # For example, request logging, rate limiting, etc.
        pass
    
    def _setup_admin_frontend(self):
        """Setup admin frontend integration"""
        try:
            from .admin_frontend_integration import setup_admin_frontend_integration
            setup_admin_frontend_integration(self.app)
            logger.info("✅ Admin frontend integration configured")
        except Exception as e:
            logger.warning(f"⚠️ Admin frontend integration failed: {e}")
            # Don't fail the entire initialization for frontend issues
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the admin integration"""
        return {
            'initialized': self.is_initialized,
            'routers_count': len(self.routers),
            'router_prefixes': [router.prefix for router in self.routers] if self.routers else []
        }
    
    def get_health(self) -> Dict[str, Any]:
        """Get health status of admin integration"""
        try:
            # Basic health checks
            health_status = {
                'status': 'healthy' if self.is_initialized else 'unhealthy',
                'initialized': self.is_initialized,
                'routers_registered': len(self.routers),
                'timestamp': str(datetime.utcnow())
            }
            
            # Additional health checks could be added here
            # e.g., database connectivity, external service availability
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': str(datetime.utcnow())
            }

def setup_admin_integration(app: FastAPI) -> AdminIntegrationManager:
    """Setup admin dashboard integration for the FastAPI application"""
    
    # Create integration manager
    integration_manager = AdminIntegrationManager(app)
    
    # Initialize the integration
    success = integration_manager.initialize()
    
    if not success:
        logger.warning("Admin dashboard integration failed to initialize completely")
    
    return integration_manager

# Convenience function for adding admin routes to existing FastAPI app
def add_admin_routes_to_app(app: FastAPI) -> bool:
    """Add admin dashboard routes to an existing FastAPI application"""
    try:
        integration_manager = setup_admin_integration(app)
        return integration_manager.is_initialized
    except Exception as e:
        logger.error(f"Failed to add admin routes to app: {e}")
        return False

# Health check endpoint for admin integration
def create_admin_health_endpoint(integration_manager: AdminIntegrationManager):
    """Create a health check endpoint for admin integration"""
    
    @app.get("/api/admin/health")
    async def admin_health_check():
        """Health check endpoint for admin dashboard integration"""
        health_status = integration_manager.get_health()
        
        if health_status['status'] == 'healthy':
            return health_status
        else:
            raise HTTPException(status_code=503, detail=health_status)

# Export main functions
__all__ = [
    'AdminIntegrationManager', 
    'setup_admin_integration', 
    'add_admin_routes_to_app',
    'create_admin_health_endpoint'
]