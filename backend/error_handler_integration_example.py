"""
Error Handler Integration Example

This module demonstrates how to integrate the unified error handling system
with the main FastAPI application and existing components.

Requirements: 4.4, 1.4, 3.4
"""

import logging
from fastapi import FastAPI, Depends, HTTPException
from contextlib import asynccontextmanager

# Import error handling components
from .unified_error_handler import setup_error_handler, get_error_handler
from .error_middleware import setup_error_middleware, create_error_handlers
from .error_monitoring_routes import setup_error_monitoring_routes
from .error_integration_utils import setup_error_integrations

# Import existing components that need error handling integration
from .unified_auth import UnifiedAuthService
from .data_sync_service import DataSyncService
from .admin_dashboard_integration import AdminDashboardManager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan_with_error_handling(app: FastAPI):
    """
    Enhanced lifespan function that includes error handling system setup
    """
    # Startup
    try:
        logger.info("Starting AI Agent with unified error handling...")
        
        # Setup error handling system
        error_handler = setup_error_handler(
            logger=logger,
            log_file_path="logs/unified_errors.log"
        )
        
        # Setup error integrations
        setup_error_integrations(error_handler)
        
        # Setup monitoring routes
        setup_error_monitoring_routes(app)
        
        logger.info("✅ Unified error handling system initialized")
        
        # Initialize other services with error handling
        await initialize_services_with_error_handling()
        
        logger.info("🚀 Application started with comprehensive error handling")
        
    except Exception as e:
        logger.error(f"Failed to initialize error handling system: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down error handling system...")
    
    # Generate final health report
    try:
        error_handler = get_error_handler()
        final_report = error_handler.get_health_report()
        logger.info(f"Final system health report: {final_report}")
    except Exception as e:
        logger.error(f"Error generating final health report: {e}")


def create_app_with_error_handling() -> FastAPI:
    """
    Create FastAPI application with comprehensive error handling
    """
    # Create FastAPI app with error-aware lifespan
    app = FastAPI(
        title="AI Agent Customer Support with Error Handling",
        version="1.0.0",
        lifespan=lifespan_with_error_handling
    )
    
    # Setup error handler first
    error_handler = setup_error_handler()
    
    # Setup error middleware
    setup_error_middleware(app, error_handler)
    
    # Create exception handlers
    create_error_handlers(app, error_handler)
    
    # Add existing routes with error handling integration
    setup_enhanced_routes(app)
    
    return app


async def initialize_services_with_error_handling():
    """
    Initialize existing services with error handling integration
    """
    from .error_integration_utils import (
        get_admin_error_integration,
        get_sync_error_integration,
        get_db_error_integration,
        get_auth_error_integration
    )
    
    # Initialize admin service with error handling
    admin_integration = get_admin_error_integration()
    logger.info("Admin dashboard error integration initialized")
    
    # Initialize sync service with error handling
    sync_integration = get_sync_error_integration()
    logger.info("Data sync error integration initialized")
    
    # Initialize database error handling
    db_integration = get_db_error_integration()
    logger.info("Database error integration initialized")
    
    # Initialize auth error handling
    auth_integration = get_auth_error_integration()
    logger.info("Authentication error integration initialized")


def setup_enhanced_routes(app: FastAPI):
    """
    Setup existing routes with enhanced error handling
    """
    from .error_integration_utils import get_admin_error_integration
    
    admin_integration = get_admin_error_integration()
    
    # Enhanced admin routes with error handling
    @app.get("/api/admin/users")
    @admin_integration.wrap_admin_api_call
    async def get_admin_users():
        """Get admin users with automatic error handling"""
        # This function is automatically wrapped with error handling
        # Errors are caught, logged, and recovery attempted
        try:
            # Simulate admin API call
            users = await fetch_admin_users()
            return {"users": users, "status": "success"}
        except Exception as e:
            # Error is automatically handled by the wrapper
            raise e
    
    @app.post("/api/admin/tickets")
    @admin_integration.wrap_admin_api_call
    async def create_admin_ticket(ticket_data: dict):
        """Create admin ticket with automatic error handling"""
        try:
            ticket = await create_ticket_in_admin_system(ticket_data)
            return {"ticket": ticket, "status": "created"}
        except Exception as e:
            # Error handling includes fallback to queue ticket for later processing
            raise e
    
    # Enhanced sync routes with error handling
    from .error_integration_utils import get_sync_error_integration
    
    sync_integration = get_sync_error_integration()
    
    @app.post("/api/sync/tickets")
    async def sync_tickets():
        """Sync tickets with comprehensive error handling"""
        try:
            # Perform sync operation
            result = await perform_ticket_sync()
            return {"status": "success", "synced": result}
        except Exception as e:
            # Handle sync error with automatic retry queuing
            sync_result = await sync_integration.handle_sync_error(
                e, "ticket_sync", entity_type="ticket"
            )
            return {"status": "error", "sync_result": sync_result}
    
    # Enhanced database routes with error handling
    from .error_integration_utils import get_db_error_integration
    
    db_integration = get_db_error_integration()
    
    @app.get("/api/users/{user_id}")
    async def get_user(user_id: str):
        """Get user with database error handling"""
        try:
            user = await fetch_user_from_database(user_id)
            return {"user": user, "status": "success"}
        except Exception as e:
            # Handle database error with fallback strategies
            db_result = await db_integration.handle_database_error(
                e, "user_fetch", table_name="users"
            )
            
            if db_result.get('recovery_available'):
                # Try fallback (cache, etc.)
                cached_user = await fetch_user_from_cache(user_id)
                if cached_user:
                    return {"user": cached_user, "status": "cached", "note": "Database temporarily unavailable"}
            
            raise HTTPException(status_code=503, detail="User service temporarily unavailable")


# Example service functions with error handling integration
async def fetch_admin_users():
    """Example admin user fetch with potential errors"""
    # Simulate potential errors
    import random
    if random.random() < 0.1:  # 10% chance of error
        raise Exception("Admin API temporarily unavailable")
    
    return [
        {"id": 1, "username": "admin1", "role": "admin"},
        {"id": 2, "username": "admin2", "role": "moderator"}
    ]


async def create_ticket_in_admin_system(ticket_data: dict):
    """Example ticket creation with potential errors"""
    import random
    if random.random() < 0.15:  # 15% chance of error
        raise Exception("Ticket creation service unavailable")
    
    return {
        "id": 123,
        "title": ticket_data.get("title", "New Ticket"),
        "status": "open",
        "created_at": "2024-01-15T10:30:00Z"
    }


async def perform_ticket_sync():
    """Example sync operation with potential errors"""
    import random
    if random.random() < 0.2:  # 20% chance of error
        raise Exception("Sync service connection failed")
    
    return {"tickets_synced": 25, "conflicts_resolved": 2}


async def fetch_user_from_database(user_id: str):
    """Example database fetch with potential errors"""
    import random
    if random.random() < 0.05:  # 5% chance of database error
        from sqlalchemy.exc import OperationalError
        raise OperationalError("Database connection timeout", None, None)
    
    return {
        "id": user_id,
        "username": f"user_{user_id}",
        "email": f"user_{user_id}@example.com"
    }


async def fetch_user_from_cache(user_id: str):
    """Example cache fallback"""
    # Simulate cache lookup
    return {
        "id": user_id,
        "username": f"user_{user_id}",
        "email": f"user_{user_id}@example.com",
        "cached": True
    }


# Enhanced authentication with error handling
class EnhancedAuthService:
    """
    Enhanced authentication service with integrated error handling
    """
    
    def __init__(self):
        from .error_integration_utils import get_auth_error_integration
        self.auth_integration = get_auth_error_integration()
    
    async def authenticate_user(self, credentials: dict):
        """Authenticate user with comprehensive error handling"""
        try:
            # Perform authentication
            user = await self._perform_authentication(credentials)
            
            # Reset failed attempts on successful auth
            if user:
                self.auth_integration.reset_failed_attempts(credentials.get('username'))
            
            return user
            
        except Exception as e:
            # Handle authentication error
            auth_result = await self.auth_integration.handle_auth_error(
                e, credentials.get('username'), 'login'
            )
            
            if auth_result.get('should_lock_account'):
                raise HTTPException(
                    status_code=429,
                    detail="Account temporarily locked due to multiple failed attempts"
                )
            else:
                raise HTTPException(
                    status_code=401,
                    detail=auth_result.get('message', 'Authentication failed')
                )
    
    async def _perform_authentication(self, credentials: dict):
        """Internal authentication logic"""
        import random
        if random.random() < 0.1:  # 10% chance of auth error
            raise Exception("Authentication service unavailable")
        
        # Simulate authentication
        username = credentials.get('username')
        password = credentials.get('password')
        
        if username == "test" and password == "password":
            return {"id": 1, "username": "test", "role": "user"}
        else:
            raise Exception("Invalid credentials")


# Enhanced data sync service with error handling
class EnhancedDataSyncService:
    """
    Enhanced data sync service with integrated error handling
    """
    
    def __init__(self):
        from .error_integration_utils import get_sync_error_integration
        self.sync_integration = get_sync_error_integration()
    
    async def sync_conversation_to_ticket(self, conversation_id: int, ticket_data: dict):
        """Sync conversation to ticket with error handling"""
        try:
            # Perform sync operation
            result = await self._perform_conversation_sync(conversation_id, ticket_data)
            return result
            
        except Exception as e:
            # Handle sync error with automatic retry queuing
            sync_result = await self.sync_integration.handle_sync_error(
                e, "conversation_to_ticket", entity_id=conversation_id, entity_type="conversation"
            )
            
            return {
                "success": False,
                "error": "Sync failed",
                "sync_result": sync_result,
                "will_retry": sync_result.get('queued_for_retry', False)
            }
    
    async def _perform_conversation_sync(self, conversation_id: int, ticket_data: dict):
        """Internal sync logic"""
        import random
        if random.random() < 0.15:  # 15% chance of sync error
            raise Exception("Sync service connection failed")
        
        return {
            "success": True,
            "ticket_id": 456,
            "conversation_id": conversation_id,
            "synced_at": "2024-01-15T10:30:00Z"
        }


# Example of integrating with existing main.py
def integrate_with_existing_main():
    """
    Example of how to integrate error handling with existing main.py
    """
    
    # In your existing main.py, replace the lifespan function:
    """
    # OLD:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # existing startup code
        yield
        # existing shutdown code
    
    # NEW:
    from backend.error_handler_integration_example import lifespan_with_error_handling
    
    app = FastAPI(lifespan=lifespan_with_error_handling)
    """
    
    # Add error handling setup after app creation:
    """
    from backend.unified_error_handler import setup_error_handler
    from backend.error_middleware import setup_error_middleware
    from backend.error_monitoring_routes import setup_error_monitoring_routes
    
    # Setup error handling
    error_handler = setup_error_handler()
    setup_error_middleware(app, error_handler)
    setup_error_monitoring_routes(app)
    """
    
    # Wrap existing route functions with error handling:
    """
    from backend.error_integration_utils import get_admin_error_integration
    
    admin_integration = get_admin_error_integration()
    
    # Wrap existing admin functions
    @admin_integration.wrap_admin_api_call
    async def existing_admin_function():
        # existing code
        pass
    """
    
    pass


if __name__ == "__main__":
    # Example of running the enhanced application
    import uvicorn
    
    app = create_app_with_error_handling()
    
    # Run with error handling
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )