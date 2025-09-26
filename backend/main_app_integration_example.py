"""
Example of how to integrate admin dashboard into main.py

This file shows the exact code changes needed to integrate the admin dashboard
API layer into the main FastAPI application.
"""

# ==================== MAIN.PY INTEGRATION EXAMPLE ====================

# Add these imports to your main.py file:
"""
# Add to imports section in main.py
from backend.admin_integration import setup_admin_dashboard_integration
"""

# Add this code after creating your FastAPI app but before starting the server:
"""
# In main.py, after creating the app:
app = FastAPI(
    title="AI Agent Customer Support", 
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# *** ADD ADMIN DASHBOARD INTEGRATION HERE ***
try:
    logger.info("🚀 Setting up Admin Dashboard Integration...")
    admin_integration = setup_admin_dashboard_integration(
        app=app,
        enable_compatibility=True  # Enable Flask compatibility layer
    )
    
    if admin_integration.is_initialized:
        logger.info("✅ Admin Dashboard Integration completed successfully!")
        
        # Log registered routes for debugging
        router_info = admin_integration.get_router_info()
        logger.info(f"📋 Registered {len(router_info)} admin router groups")
        
        for router in router_info:
            logger.info(f"  - {router['prefix']} ({router['routes_count']} routes)")
    else:
        logger.warning("⚠️ Admin Dashboard Integration failed to initialize")
        
except Exception as e:
    logger.error(f"❌ Admin Dashboard Integration error: {e}")
    logger.warning("Continuing without admin dashboard functionality")

# Continue with your existing setup...
# Include voice assistant router
app.include_router(voice_router)

# ... rest of your main.py code
"""

# ==================== ALTERNATIVE MINIMAL INTEGRATION ====================

def minimal_integration_example():
    """
    Minimal integration example - just add the routes without full management
    """
    
    # Add this to main.py for minimal integration:
    """
    from backend.admin_integration import add_admin_routes_only
    
    # After creating your FastAPI app:
    try:
        success = add_admin_routes_only(app)
        if success:
            logger.info("✅ Admin routes added successfully")
        else:
            logger.warning("⚠️ Failed to add admin routes")
    except Exception as e:
        logger.error(f"❌ Error adding admin routes: {e}")
    """

# ==================== HEALTH CHECK INTEGRATION ====================

def health_check_integration_example():
    """
    Example of adding health checks for admin integration
    """
    
    # Add this to main.py for health monitoring:
    """
    from backend.admin_integration import get_admin_integration
    
    @app.get("/health/admin")
    async def admin_health():
        admin_integration = get_admin_integration()
        if admin_integration and admin_integration.integration_manager:
            return admin_integration.integration_manager.get_health()
        else:
            return {"status": "unavailable", "message": "Admin integration not initialized"}
    """

# ==================== COMPLETE INTEGRATION TEMPLATE ====================

COMPLETE_INTEGRATION_CODE = '''
# Add these imports to main.py
from backend.admin_integration import setup_admin_dashboard_integration, get_admin_integration

# Add this code after creating your FastAPI app
try:
    logger.info("🚀 Setting up Admin Dashboard Integration...")
    
    # Setup complete admin dashboard integration
    admin_integration = setup_admin_dashboard_integration(
        app=app,
        enable_compatibility=True  # Set to False if you don't need Flask compatibility
    )
    
    if admin_integration.is_initialized:
        logger.info("✅ Admin Dashboard Integration completed successfully!")
        
        # Optional: Log integration details
        router_info = admin_integration.get_router_info()
        logger.info(f"📋 Admin integration registered {len(router_info)} router groups")
        
        # Add health check endpoint
        @app.get("/health/admin")
        async def admin_health_check():
            """Health check for admin dashboard integration"""
            if admin_integration.integration_manager:
                return admin_integration.integration_manager.get_health()
            else:
                return {"status": "unavailable"}
        
        # Add status endpoint
        @app.get("/status/admin")
        async def admin_status():
            """Status information for admin dashboard integration"""
            return {
                "initialized": admin_integration.is_initialized,
                "routers": admin_integration.get_router_info()
            }
            
    else:
        logger.warning("⚠️ Admin Dashboard Integration failed to initialize")
        
except Exception as e:
    logger.error(f"❌ Admin Dashboard Integration error: {e}")
    logger.warning("Continuing without admin dashboard functionality")
'''

# ==================== TESTING THE INTEGRATION ====================

def test_integration_in_main():
    """
    Test function to verify the integration works in main.py context
    """
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    import logging
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Create FastAPI app (similar to main.py)
    app = FastAPI(title="AI Agent Customer Support", version="1.0.0")
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Execute the integration code
    try:
        logger.info("🚀 Setting up Admin Dashboard Integration...")
        
        from backend.admin_integration import setup_admin_dashboard_integration
        
        admin_integration = setup_admin_dashboard_integration(
            app=app,
            enable_compatibility=True
        )
        
        if admin_integration.is_initialized:
            logger.info("✅ Admin Dashboard Integration completed successfully!")
            
            router_info = admin_integration.get_router_info()
            logger.info(f"📋 Admin integration registered {len(router_info)} router groups")
            
            # Add health check endpoint
            @app.get("/health/admin")
            async def admin_health_check():
                if admin_integration.integration_manager:
                    return admin_integration.integration_manager.get_health()
                else:
                    return {"status": "unavailable"}
            
            return True
        else:
            logger.warning("⚠️ Admin Dashboard Integration failed to initialize")
            return False
            
    except Exception as e:
        logger.error(f"❌ Admin Dashboard Integration error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Admin Dashboard Integration in main.py context...")
    
    success = test_integration_in_main()
    
    if success:
        print("✅ Integration test successful!")
        print("\n📋 Integration code ready for main.py:")
        print("=" * 60)
        print(COMPLETE_INTEGRATION_CODE)
        print("=" * 60)
    else:
        print("❌ Integration test failed!")
    
    print("\n📖 Next steps:")
    print("1. Copy the integration code above into your main.py file")
    print("2. Add it after creating your FastAPI app but before starting the server")
    print("3. Test the admin endpoints at /api/admin/dashboard")
    print("4. Check health at /health/admin")
    print("5. View all routes at /docs (FastAPI automatic documentation)")