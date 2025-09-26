"""
Integration Example for Admin Dashboard

This file shows how to integrate the admin dashboard API layer into the main FastAPI application.
This is an example that can be used as a reference for the actual integration.
"""

from fastapi import FastAPI
import logging

# Import the admin integration module
from .admin_integration import setup_admin_dashboard_integration, get_admin_route_list

logger = logging.getLogger(__name__)

def integrate_admin_dashboard_into_main_app(app: FastAPI) -> bool:
    """
    Integrate admin dashboard functionality into the main FastAPI application.
    
    Args:
        app: The main FastAPI application instance
        
    Returns:
        bool: True if integration was successful, False otherwise
    """
    try:
        logger.info("🚀 Starting Admin Dashboard Integration...")
        
        # Setup the complete admin dashboard integration
        admin_integration = setup_admin_dashboard_integration(
            app=app,
            enable_compatibility=True  # Enable Flask compatibility layer
        )
        
        if admin_integration.is_initialized:
            logger.info("✅ Admin Dashboard Integration completed successfully!")
            
            # Log the registered routes for debugging
            router_info = admin_integration.get_router_info()
            logger.info(f"📋 Registered {len(router_info)} router groups:")
            
            for router in router_info:
                logger.info(f"  - {router['prefix']} ({router['routes_count']} routes)")
            
            # Log all available admin routes
            all_routes = get_admin_route_list()
            logger.info(f"🔗 Total admin routes available: {len(all_routes)}")
            
            return True
        else:
            logger.error("❌ Admin Dashboard Integration failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Admin Dashboard Integration error: {e}")
        return False

def add_admin_dashboard_to_existing_app():
    """
    Example of how to add admin dashboard to an existing FastAPI app.
    This function demonstrates the integration process.
    """
    
    # This is how you would integrate it into main.py
    # 
    # In your main.py file, add these imports:
    # from backend.integrate_admin_dashboard import integrate_admin_dashboard_into_main_app
    #
    # Then in your app creation section, add:
    # 
    # # Create FastAPI app
    # app = FastAPI(title="AI Agent Customer Support", version="1.0.0")
    # 
    # # Add CORS middleware, etc.
    # app.add_middleware(CORSMiddleware, ...)
    # 
    # # Integrate admin dashboard
    # admin_success = integrate_admin_dashboard_into_main_app(app)
    # if admin_success:
    #     logger.info("Admin dashboard integrated successfully")
    # else:
    #     logger.warning("Admin dashboard integration failed")
    # 
    # # Continue with your existing setup...
    
    pass

# Example of manual integration for more control
def manual_admin_integration_example(app: FastAPI):
    """
    Example of manual integration with more control over the process.
    """
    from .admin_integration import AdminDashboardIntegration
    
    try:
        # Create the integration instance
        admin_integration = AdminDashboardIntegration()
        
        # Initialize with custom settings
        success = admin_integration.initialize(
            app=app,
            enable_compatibility=True  # Can be set to False if compatibility not needed
        )
        
        if success:
            logger.info("✅ Manual admin integration successful")
            
            # You can access the integration manager for health checks
            if admin_integration.integration_manager:
                health = admin_integration.integration_manager.get_health()
                logger.info(f"Admin integration health: {health['status']}")
            
            return admin_integration
        else:
            logger.error("❌ Manual admin integration failed")
            return None
            
    except Exception as e:
        logger.error(f"Manual admin integration error: {e}")
        return None

# Example of adding only specific parts
def selective_admin_integration_example(app: FastAPI):
    """
    Example of adding only specific admin functionality.
    """
    from .admin_integration import add_admin_routes_only, add_compatibility_routes_only
    
    try:
        # Option 1: Add only modern FastAPI routes
        modern_success = add_admin_routes_only(app)
        
        # Option 2: Add only Flask compatibility routes
        compat_success = add_compatibility_routes_only(app)
        
        logger.info(f"Modern routes: {'✅' if modern_success else '❌'}")
        logger.info(f"Compatibility routes: {'✅' if compat_success else '❌'}")
        
        return modern_success or compat_success
        
    except Exception as e:
        logger.error(f"Selective admin integration error: {e}")
        return False

# Health check integration example
def add_admin_health_monitoring(app: FastAPI):
    """
    Example of adding health monitoring for admin integration.
    """
    from .admin_integration import get_admin_integration
    
    @app.get("/health/admin")
    async def admin_health_check():
        """Health check endpoint specifically for admin functionality"""
        admin_integration = get_admin_integration()
        
        if admin_integration and admin_integration.integration_manager:
            return admin_integration.integration_manager.get_health()
        else:
            return {
                'status': 'unavailable',
                'message': 'Admin integration not initialized'
            }
    
    @app.get("/status/admin")
    async def admin_status_check():
        """Status endpoint for admin integration"""
        admin_integration = get_admin_integration()
        
        if admin_integration:
            return {
                'initialized': admin_integration.is_initialized,
                'routers': admin_integration.get_router_info(),
                'routes': get_admin_route_list()
            }
        else:
            return {
                'initialized': False,
                'message': 'Admin integration not available'
            }

# Export the main integration function
__all__ = [
    'integrate_admin_dashboard_into_main_app',
    'add_admin_dashboard_to_existing_app',
    'manual_admin_integration_example',
    'selective_admin_integration_example',
    'add_admin_health_monitoring'
]