"""
Admin Dashboard Integration

Main integration module that provides a unified interface for integrating
admin dashboard functionality into the FastAPI application.
"""

from fastapi import FastAPI, APIRouter
from typing import List, Dict, Any, Optional
import logging

from .admin_dashboard_integration import create_admin_dashboard_integration
from .admin_compatibility_layer import create_compatibility_integration
from .admin_integration_manager import AdminIntegrationManager

logger = logging.getLogger(__name__)

class AdminDashboardIntegration:
    """Main class for admin dashboard integration"""
    
    def __init__(self):
        self.routers: List[APIRouter] = []
        self.compatibility_router: Optional[APIRouter] = None
        self.integration_manager: Optional[AdminIntegrationManager] = None
        self.is_initialized = False
    
    def initialize(self, app: FastAPI, enable_compatibility: bool = True) -> bool:
        """Initialize the admin dashboard integration"""
        try:
            logger.info("🚀 Initializing Admin Dashboard Integration...")
            
            # Create integration manager
            self.integration_manager = AdminIntegrationManager(app)
            
            # Initialize the integration manager
            if not self.integration_manager.initialize():
                logger.error("Failed to initialize integration manager")
                return False
            
            # Create modern FastAPI routers
            self.routers = create_admin_dashboard_integration()
            logger.info(f"✅ Created {len(self.routers)} FastAPI routers")
            
            # Create compatibility layer if enabled
            if enable_compatibility:
                self.compatibility_router = create_compatibility_integration()
                app.include_router(self.compatibility_router)
                logger.info("✅ Flask compatibility layer enabled")
            
            # Register all routers with the app
            for router in self.routers:
                app.include_router(router)
                logger.info(f"✅ Registered router: {router.prefix}")
            
            # Add health check endpoint
            self._add_health_endpoint(app)
            
            self.is_initialized = True
            logger.info("🎉 Admin Dashboard Integration completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Admin Dashboard Integration failed: {e}")
            return False
    
    def _add_health_endpoint(self, app: FastAPI):
        """Add health check endpoint for admin integration"""
        
        @app.get("/api/admin/integration/health")
        async def admin_integration_health():
            """Health check for admin dashboard integration"""
            if self.integration_manager:
                return self.integration_manager.get_health()
            else:
                return {
                    'status': 'unhealthy',
                    'error': 'Integration manager not available'
                }
        
        @app.get("/api/admin/integration/status")
        async def admin_integration_status():
            """Status information for admin dashboard integration"""
            return {
                'initialized': self.is_initialized,
                'routers_count': len(self.routers),
                'compatibility_enabled': self.compatibility_router is not None,
                'integration_manager_status': self.integration_manager.get_status() if self.integration_manager else None
            }
    
    def get_router_info(self) -> List[Dict[str, Any]]:
        """Get information about registered routers"""
        router_info = []
        
        for router in self.routers:
            router_info.append({
                'prefix': router.prefix,
                'tags': router.tags,
                'routes_count': len(router.routes)
            })
        
        if self.compatibility_router:
            router_info.append({
                'prefix': self.compatibility_router.prefix,
                'tags': self.compatibility_router.tags,
                'routes_count': len(self.compatibility_router.routes),
                'type': 'compatibility'
            })
        
        return router_info

# Global instance for easy access
_admin_integration_instance: Optional[AdminDashboardIntegration] = None

def setup_admin_dashboard_integration(app: FastAPI, enable_compatibility: bool = True) -> AdminDashboardIntegration:
    """Setup admin dashboard integration for a FastAPI application"""
    global _admin_integration_instance
    
    if _admin_integration_instance is None:
        _admin_integration_instance = AdminDashboardIntegration()
    
    success = _admin_integration_instance.initialize(app, enable_compatibility)
    
    if not success:
        logger.warning("Admin dashboard integration setup completed with errors")
    
    return _admin_integration_instance

def get_admin_integration() -> Optional[AdminDashboardIntegration]:
    """Get the current admin integration instance"""
    return _admin_integration_instance

# Convenience functions for specific use cases

def add_admin_routes_only(app: FastAPI) -> bool:
    """Add only the modern FastAPI admin routes (no compatibility layer)"""
    try:
        routers = create_admin_dashboard_integration()
        
        for router in routers:
            app.include_router(router)
            logger.info(f"Added admin router: {router.prefix}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to add admin routes: {e}")
        return False

def add_compatibility_routes_only(app: FastAPI) -> bool:
    """Add only the Flask compatibility routes"""
    try:
        compatibility_router = create_compatibility_integration()
        app.include_router(compatibility_router)
        logger.info("Added Flask compatibility routes")
        return True
        
    except Exception as e:
        logger.error(f"Failed to add compatibility routes: {e}")
        return False

# Route discovery helper
def get_admin_route_list() -> List[Dict[str, str]]:
    """Get a list of all admin routes for documentation purposes"""
    routes = []
    
    # Modern FastAPI routes
    modern_routes = [
        {'path': '/api/admin/dashboard', 'method': 'GET', 'description': 'Admin dashboard statistics'},
        {'path': '/api/admin/users/', 'method': 'GET', 'description': 'Get all users with pagination'},
        {'path': '/api/admin/users/{user_id}', 'method': 'GET', 'description': 'Get user by ID'},
        {'path': '/api/admin/tickets/', 'method': 'GET', 'description': 'Get all tickets with filtering'},
        {'path': '/api/admin/tickets/{ticket_id}', 'method': 'GET', 'description': 'Get ticket by ID'},
        {'path': '/api/admin/tickets/', 'method': 'POST', 'description': 'Create new ticket'},
        {'path': '/api/admin/tickets/{ticket_id}', 'method': 'PUT', 'description': 'Update ticket'},
        {'path': '/api/admin/tickets/{ticket_id}/comments', 'method': 'POST', 'description': 'Add comment to ticket'},
        {'path': '/api/admin/tickets/stats/overview', 'method': 'GET', 'description': 'Get ticket statistics'},
        {'path': '/api/admin/analytics/performance-metrics', 'method': 'GET', 'description': 'Get performance metrics'},
        {'path': '/api/admin/analytics/customer-satisfaction', 'method': 'GET', 'description': 'Get satisfaction ratings'},
        {'path': '/api/admin/system/status', 'method': 'GET', 'description': 'Get system status'},
    ]
    
    # Compatibility routes
    compatibility_routes = [
        {'path': '/api/auth/login', 'method': 'POST', 'description': 'Flask-compatible login'},
        {'path': '/api/auth/logout', 'method': 'POST', 'description': 'Flask-compatible logout'},
        {'path': '/api/admin/register', 'method': 'POST', 'description': 'Flask-compatible admin registration'},
        {'path': '/api/admin/dashboard', 'method': 'GET', 'description': 'Flask-compatible dashboard'},
        {'path': '/api/admin/users', 'method': 'GET', 'description': 'Flask-compatible get users'},
        {'path': '/api/tickets/', 'method': 'GET', 'description': 'Flask-compatible get tickets'},
        {'path': '/api/tickets/{ticket_id}', 'method': 'GET', 'description': 'Flask-compatible get ticket'},
        {'path': '/api/tickets/', 'method': 'POST', 'description': 'Flask-compatible create ticket'},
        {'path': '/api/tickets/stats', 'method': 'GET', 'description': 'Flask-compatible ticket stats'},
    ]
    
    routes.extend([{**route, 'type': 'modern'} for route in modern_routes])
    routes.extend([{**route, 'type': 'compatibility'} for route in compatibility_routes])
    
    return routes

# Export main functions and classes
__all__ = [
    'AdminDashboardIntegration',
    'setup_admin_dashboard_integration',
    'get_admin_integration',
    'add_admin_routes_only',
    'add_compatibility_routes_only',
    'get_admin_route_list'
]