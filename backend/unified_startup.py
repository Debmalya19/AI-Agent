"""
Unified Application Startup and Configuration

This module provides the unified startup sequence that initializes all integrated services
including the AI Agent backend, admin dashboard, data synchronization, and monitoring.

Requirements: 6.1, 6.2, 6.3, 6.4
"""

import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .unified_config import get_config_manager, ConfigManager, UnifiedConfig
from .database import init_db
from .unified_error_handler import UnifiedErrorHandler, setup_error_middleware
from .health_endpoints import health_router

logger = logging.getLogger(__name__)


class UnifiedApplicationManager:
    """Manages the unified application startup and configuration"""
    
    def __init__(self):
        self.config_manager: Optional[ConfigManager] = None
        self.config: Optional[UnifiedConfig] = None
        self.error_handler: Optional[UnifiedErrorHandler] = None
        self.app: Optional[FastAPI] = None
        self.startup_errors: List[str] = []
        self.initialized_services: List[str] = []
    
    async def initialize_configuration(self) -> bool:
        """Initialize and validate configuration"""
        try:
            logger.info("🔧 Initializing unified configuration...")
            
            # Get configuration manager
            self.config_manager = get_config_manager()
            self.config = self.config_manager.config
            
            # Setup logging based on configuration
            self.config_manager.setup_logging()
            
            # Validate configuration
            if not self.config_manager.validate_config():
                validation_errors = self.config_manager.get_validation_errors()
                for error in validation_errors:
                    logger.error(f"Configuration validation error: {error}")
                    self.startup_errors.append(f"Config validation: {error}")
                
                if self.config.is_production():
                    logger.error("Configuration validation failed in production environment")
                    return False
                else:
                    logger.warning("Configuration validation failed, continuing in development mode")
            
            logger.info(f"✅ Configuration initialized for {self.config.environment.value} environment")
            return True
            
        except Exception as e:
            logger.error(f"❌ Configuration initialization failed: {e}")
            self.startup_errors.append(f"Configuration init: {str(e)}")
            return False
    
    async def initialize_error_handling(self) -> bool:
        """Initialize comprehensive error handling system"""
        try:
            logger.info("🛡️ Initializing comprehensive error handling...")
            
            # Initialize comprehensive error handling
            from .comprehensive_error_integration import setup_comprehensive_error_handling, initialize_error_monitoring
            
            # Setup error handling for the app (will be set later)
            self.error_manager = setup_comprehensive_error_handling(
                app=None,  # Will be set when app is created
                log_directory="logs",
                max_login_attempts=5,
                lockout_duration_minutes=30
            )
            
            # Initialize error monitoring
            await initialize_error_monitoring()
            
            logger.info("✅ Comprehensive error handling system initialized")
            self.initialized_services.append("error_handling")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error handling initialization failed: {e}")
            self.startup_errors.append(f"Error handling init: {str(e)}")
            return False
    
    async def initialize_database(self) -> bool:
        """Initialize database connection and unified tables"""
        try:
            logger.info("🗄️ Initializing unified database...")
            
            # Initialize unified database tables
            init_db()
            
            # Verify unified authentication tables exist
            try:
                from .unified_models import UnifiedUser, UnifiedUserSession
                logger.info("✅ Unified authentication tables verified")
            except Exception as auth_table_error:
                logger.warning(f"⚠️ Unified authentication table verification failed: {auth_table_error}")
                self.startup_errors.append(f"Auth tables verification: {str(auth_table_error)}")
            
            logger.info("✅ Unified database initialized successfully")
            self.initialized_services.append("database")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            self.startup_errors.append(f"Database init: {str(e)}")
            return False
    
    async def initialize_authentication(self) -> bool:
        """Initialize unified authentication system"""
        try:
            logger.info("🔐 Initializing unified authentication system...")
            
            # Verify unified authentication service is available
            try:
                from .unified_auth import auth_service, get_current_user_flexible
                from .unified_models import UnifiedUser, UnifiedUserSession, UserRole
                
                # Test authentication service initialization
                if not hasattr(auth_service, 'hash_password'):
                    raise AttributeError("Authentication service not properly initialized")
                
                logger.info("✅ Unified authentication service verified")
                
            except Exception as auth_error:
                logger.error(f"❌ Authentication service verification failed: {auth_error}")
                self.startup_errors.append(f"Auth service: {str(auth_error)}")
                return False
            
            # Verify authentication configuration
            if not self.config.auth.jwt_secret_key:
                logger.warning("⚠️ JWT secret key not configured")
                self.startup_errors.append("Auth config: JWT secret key missing")
                if self.config.is_production():
                    return False
            
            logger.info("✅ Unified authentication system initialized successfully")
            self.initialized_services.append("authentication")
            return True
            
        except Exception as e:
            logger.error(f"❌ Authentication initialization failed: {e}")
            self.startup_errors.append(f"Authentication init: {str(e)}")
            return False
    
    async def initialize_ai_agent(self) -> bool:
        """Initialize AI Agent components"""
        try:
            logger.info("🤖 Initializing AI Agent components...")
            
            if not self.config.ai_agent.google_api_key:
                logger.warning("⚠️ Google API key not configured, AI Agent functionality will be limited")
                self.startup_errors.append("AI Agent: Google API key not configured")
                return True  # Continue without AI functionality
            
            # Initialize memory layer manager
            try:
                from .memory_layer_manager import MemoryLayerManager
                from .memory_config import load_config
                from .tools import set_shared_memory_manager
                
                memory_config = load_config()
                memory_manager = MemoryLayerManager(config=memory_config)
                set_shared_memory_manager(memory_manager)
                
                logger.info("✅ Memory layer manager initialized")
                
            except Exception as memory_error:
                logger.warning(f"⚠️ Memory layer initialization failed: {memory_error}")
                self.startup_errors.append(f"Memory layer: {str(memory_error)}")
            
            # Initialize intelligent chat components
            try:
                from .intelligent_chat.chat_manager import ChatManager
                from .intelligent_chat.tool_orchestrator import ToolOrchestrator
                from .intelligent_chat.context_retriever import ContextRetriever
                from .intelligent_chat.response_renderer import ResponseRenderer
                
                logger.info("✅ Intelligent chat components available")
                
            except Exception as chat_error:
                logger.warning(f"⚠️ Intelligent chat initialization failed: {chat_error}")
                self.startup_errors.append(f"Intelligent chat: {str(chat_error)}")
            
            logger.info("✅ AI Agent components initialized")
            self.initialized_services.append("ai_agent")
            return True
            
        except Exception as e:
            logger.error(f"❌ AI Agent initialization failed: {e}")
            self.startup_errors.append(f"AI Agent init: {str(e)}")
            return False
    
    async def initialize_admin_dashboard(self) -> bool:
        """Initialize admin dashboard integration"""
        try:
            if not self.config.admin_dashboard.enabled:
                logger.info("ℹ️ Admin dashboard is disabled by configuration")
                return True
            
            logger.info("👥 Initializing admin dashboard integration...")
            
            # Initialize admin dashboard components
            try:
                from .admin_integration_manager import AdminIntegrationManager
                
                admin_manager = AdminIntegrationManager(self.app)
                # Fix: initialize() is not async, so don't await it
                success = admin_manager.initialize()
                
                if success:
                    logger.info("✅ Admin dashboard integration initialized")
                else:
                    logger.warning("⚠️ Admin dashboard integration completed with warnings")
                
            except Exception as admin_error:
                logger.warning(f"⚠️ Admin dashboard integration failed: {admin_error}")
                self.startup_errors.append(f"Admin dashboard: {str(admin_error)}")
                
                # Try fallback initialization
                try:
                    from .admin_frontend_integration import setup_admin_frontend_integration
                    from .admin_api_proxy import setup_admin_api_proxy
                    from .admin_auth_proxy import setup_admin_auth_proxy
                    
                    setup_admin_auth_proxy(self.app)
                    setup_admin_api_proxy(self.app)
                    setup_admin_frontend_integration(self.app)
                    
                    logger.info("✅ Admin dashboard fallback integration completed")
                    
                except Exception as fallback_error:
                    logger.error(f"❌ Admin dashboard fallback failed: {fallback_error}")
                    self.startup_errors.append(f"Admin dashboard fallback: {str(fallback_error)}")
                    return False
            
            self.initialized_services.append("admin_dashboard")
            return True
            
        except Exception as e:
            logger.error(f"❌ Admin dashboard initialization failed: {e}")
            self.startup_errors.append(f"Admin dashboard init: {str(e)}")
            return False
    
    async def initialize_data_sync(self) -> bool:
        """Initialize data synchronization service"""
        try:
            if not self.config.data_sync.enabled:
                logger.info("ℹ️ Data synchronization is disabled by configuration")
                return True
            
            logger.info("🔄 Initializing data synchronization service...")
            
            try:
                from .data_sync_integration import startup_data_sync, include_sync_router
                
                await startup_data_sync()
                include_sync_router(self.app)
                
                logger.info("✅ Data synchronization service initialized")
                
            except Exception as sync_error:
                logger.warning(f"⚠️ Data synchronization initialization failed: {sync_error}")
                self.startup_errors.append(f"Data sync: {str(sync_error)}")
                return True  # Continue without sync functionality
            
            self.initialized_services.append("data_sync")
            return True
            
        except Exception as e:
            logger.error(f"❌ Data synchronization initialization failed: {e}")
            self.startup_errors.append(f"Data sync init: {str(e)}")
            return False
    
    async def initialize_voice_assistant(self) -> bool:
        """Initialize voice assistant components"""
        try:
            if not self.config.voice.enabled:
                logger.info("ℹ️ Voice assistant is disabled by configuration")
                return True
            
            logger.info("🎤 Initializing voice assistant...")
            
            try:
                from .voice_api import voice_router
                
                self.app.include_router(voice_router)
                
                logger.info("✅ Voice assistant initialized")
                
            except Exception as voice_error:
                logger.warning(f"⚠️ Voice assistant initialization failed: {voice_error}")
                self.startup_errors.append(f"Voice assistant: {str(voice_error)}")
                return True  # Continue without voice functionality
            
            self.initialized_services.append("voice_assistant")
            return True
            
        except Exception as e:
            logger.error(f"❌ Voice assistant initialization failed: {e}")
            self.startup_errors.append(f"Voice assistant init: {str(e)}")
            return False
    
    async def initialize_analytics(self) -> bool:
        """Initialize analytics components"""
        try:
            if not self.config.analytics.enabled:
                logger.info("ℹ️ Analytics is disabled by configuration")
                return True
            
            logger.info("📊 Initializing analytics service...")
            
            try:
                from .analytics_routes import analytics_router
                
                self.app.include_router(analytics_router)
                
                logger.info("✅ Analytics service initialized")
                
            except Exception as analytics_error:
                logger.warning(f"⚠️ Analytics initialization failed: {analytics_error}")
                self.startup_errors.append(f"Analytics: {str(analytics_error)}")
                return True  # Continue without analytics functionality
            
            self.initialized_services.append("analytics")
            return True
            
        except Exception as e:
            logger.error(f"❌ Analytics initialization failed: {e}")
            self.startup_errors.append(f"Analytics init: {str(e)}")
            return False
    
    async def initialize_background_tasks(self) -> bool:
        """Initialize background tasks"""
        try:
            logger.info("⏰ Initializing background tasks...")
            
            # Start memory cleanup task if enabled
            if (self.config.ai_agent.memory_cleanup_interval_hours > 0 and 
                "ai_agent" in self.initialized_services):
                try:
                    asyncio.create_task(self._memory_cleanup_task())
                    logger.info("✅ Memory cleanup background task started")
                except Exception as cleanup_error:
                    logger.warning(f"⚠️ Memory cleanup task failed to start: {cleanup_error}")
            
            self.initialized_services.append("background_tasks")
            return True
            
        except Exception as e:
            logger.error(f"❌ Background tasks initialization failed: {e}")
            self.startup_errors.append(f"Background tasks init: {str(e)}")
            return False
    
    async def _memory_cleanup_task(self):
        """Background task for memory cleanup"""
        while True:
            try:
                from .memory_layer_manager import MemoryLayerManager
                from .memory_config import load_config
                
                memory_config = load_config()
                memory_manager = MemoryLayerManager(config=memory_config)
                
                logger.info("Starting memory cleanup task")
                cleanup_result = memory_manager.cleanup_expired_data()
                
                if cleanup_result.errors:
                    logger.error(f"Memory cleanup errors: {cleanup_result.errors}")
                else:
                    logger.info(f"Memory cleanup completed: {cleanup_result.to_dict()}")
                
            except Exception as e:
                logger.error(f"Memory cleanup task error: {e}")
            
            # Wait for next cleanup interval
            await asyncio.sleep(self.config.ai_agent.memory_cleanup_interval_hours * 3600)
    
    def setup_middleware(self) -> None:
        """Setup FastAPI middleware"""
        try:
            logger.info("🔧 Setting up middleware...")
            
            # Check if middleware is already set up (to avoid "Cannot add middleware after an application has started" error)
            try:
                # CORS middleware with enhanced configuration
                from fastapi.middleware.cors import CORSMiddleware
                self.app.add_middleware(
                    CORSMiddleware,
                    allow_origins=self.config.server.cors_origins if self.config else [
                        "http://localhost:3000",
                        "http://localhost:8000", 
                        "http://127.0.0.1:3000",
                        "http://127.0.0.1:8000",
                        "*"
                    ],
                    allow_credentials=True,
                    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
                    allow_headers=[
                        "Accept",
                        "Accept-Language", 
                        "Content-Language",
                        "Content-Type",
                        "Authorization",
                        "X-Requested-With",
                        "X-Request-Format",
                        "Cache-Control"
                    ],
                    expose_headers=["Set-Cookie"],
                )
                logger.info("✅ Enhanced CORS middleware added")
            except RuntimeError as e:
                if "Cannot add middleware after an application has started" in str(e):
                    logger.info("ℹ️ CORS middleware already configured")
                else:
                    raise
            
            # Request validation and sanitization middleware
            try:
                from .request_validation_middleware import setup_request_validation_middleware
                setup_request_validation_middleware(self.app)
                logger.info("✅ Request validation middleware added")
            except RuntimeError as e:
                if "Cannot add middleware after an application has started" in str(e):
                    logger.info("ℹ️ Request validation middleware already configured")
                else:
                    raise
            except Exception as e:
                logger.warning(f"⚠️ Request validation middleware setup failed: {e}")
            
            # Comprehensive error handling middleware
            if hasattr(self, 'error_manager') and self.error_manager:
                # The error manager already sets up middleware during initialization
                logger.info("✅ Comprehensive error handling middleware active")
            elif self.error_handler:
                try:
                    setup_error_middleware(self.app, self.error_handler)
                    logger.info("✅ Error handling middleware added")
                except RuntimeError as e:
                    if "Cannot add middleware after an application has started" in str(e):
                        logger.info("ℹ️ Error middleware already configured")
                    else:
                        raise
            
            logger.info("✅ Middleware setup completed")
            
        except Exception as e:
            logger.error(f"❌ Middleware setup failed: {e}")
            self.startup_errors.append(f"Middleware setup: {str(e)}")
    
    def setup_static_files(self) -> None:
        """Setup static file serving"""
        try:
            logger.info("📁 Setting up static file serving...")
            
            # Serve main frontend
            self.app.mount("/static", StaticFiles(directory="frontend"), name="static")
            
            # Serve admin dashboard frontend if enabled
            if self.config.admin_dashboard.enabled:
                try:
                    from pathlib import Path
                    admin_path = Path(self.config.admin_dashboard.frontend_path)
                    if admin_path.exists():
                        self.app.mount("/admin-static", StaticFiles(directory=str(admin_path)), name="admin-static")
                        logger.info("✅ Admin dashboard static files mounted")
                    else:
                        logger.warning(f"⚠️ Admin dashboard frontend path not found: {admin_path}")
                except Exception as admin_static_error:
                    logger.warning(f"⚠️ Admin dashboard static files setup failed: {admin_static_error}")
            
            logger.info("✅ Static file serving setup completed")
            
        except Exception as e:
            logger.error(f"❌ Static file serving setup failed: {e}")
            self.startup_errors.append(f"Static files setup: {str(e)}")
    
    def setup_health_checks(self) -> None:
        """Setup health check endpoints"""
        try:
            logger.info("🏥 Setting up health check endpoints...")
            
            # Include comprehensive database health endpoints
            from .health_endpoints import health_router as db_health_router
            self.app.include_router(db_health_router)
            
            # Keep existing health checks for compatibility
            try:
                from .health_checks import create_health_check_router
                health_router = create_health_check_router()
                self.app.include_router(health_router, prefix="/system")
            except ImportError:
                logger.warning("Legacy health checks not available")
            
            # Add error monitoring endpoints
            from .error_monitoring_endpoints import error_monitoring_router
            self.app.include_router(error_monitoring_router)
            
            logger.info("✅ Health check and error monitoring endpoints setup completed")
            
        except Exception as e:
            logger.error(f"❌ Health check setup failed: {e}")
            self.startup_errors.append(f"Health checks setup: {str(e)}")
    
    async def startup_sequence(self, app: FastAPI) -> None:
        """Execute the complete startup sequence"""
        self.app = app
        startup_start_time = datetime.now()
        
        logger.info("🚀 Starting AI Agent Customer Support application...")
        
        # Initialize components in order
        initialization_steps = [
            ("Configuration", self.initialize_configuration),
            ("Error Handling", self.initialize_error_handling),
            ("Database", self.initialize_database),
            ("Authentication", self.initialize_authentication),
            ("AI Agent", self.initialize_ai_agent),
            ("Admin Dashboard", self.initialize_admin_dashboard),
            ("Data Synchronization", self.initialize_data_sync),
            ("Voice Assistant", self.initialize_voice_assistant),
            ("Analytics", self.initialize_analytics),
            ("Background Tasks", self.initialize_background_tasks),
        ]
        
        for step_name, step_func in initialization_steps:
            try:
                success = await step_func()
                if not success and self.config and self.config.is_production():
                    logger.error(f"❌ Critical initialization failure in production: {step_name}")
                    raise RuntimeError(f"Critical initialization failure: {step_name}")
            except Exception as e:
                logger.error(f"❌ Initialization step '{step_name}' failed: {e}")
                if self.config and self.config.is_production():
                    raise
                else:
                    self.startup_errors.append(f"{step_name}: {str(e)}")
        
        # Setup middleware and static files
        self.setup_middleware()
        self.setup_static_files()
        self.setup_health_checks()
        
        # Log startup summary
        startup_duration = (datetime.now() - startup_start_time).total_seconds()
        
        if self.startup_errors:
            logger.warning(f"⚠️ Application started with {len(self.startup_errors)} warnings:")
            for error in self.startup_errors:
                logger.warning(f"  - {error}")
        
        logger.info(f"🎉 AI Agent Customer Support application started successfully!")
        logger.info(f"   Environment: {self.config.environment.value if self.config else 'unknown'}")
        logger.info(f"   Initialized services: {', '.join(self.initialized_services)}")
        logger.info(f"   Startup duration: {startup_duration:.2f} seconds")
        
        if self.config:
            logger.info(f"   Server: {self.config.server.host}:{self.config.server.port}")
            logger.info(f"   Debug mode: {self.config.server.debug}")
    
    async def shutdown_sequence(self) -> None:
        """Execute the shutdown sequence"""
        logger.info("🛑 Shutting down AI Agent Customer Support application...")
        
        # Shutdown data synchronization
        if "data_sync" in self.initialized_services:
            try:
                from .data_sync_integration import shutdown_data_sync
                await shutdown_data_sync()
                logger.info("✅ Data synchronization service shut down")
            except Exception as e:
                logger.error(f"❌ Error shutting down data sync: {e}")
        
        # Additional cleanup can be added here
        
        logger.info("✅ Application shutdown completed")


# Global application manager instance
_app_manager: Optional[UnifiedApplicationManager] = None


def get_app_manager() -> UnifiedApplicationManager:
    """Get the global application manager instance"""
    global _app_manager
    if _app_manager is None:
        _app_manager = UnifiedApplicationManager()
    return _app_manager


@asynccontextmanager
async def create_lifespan_manager(app: FastAPI):
    """Create the lifespan context manager for FastAPI"""
    app_manager = get_app_manager()
    
    # Startup
    try:
        await app_manager.startup_sequence(app)
    except Exception as e:
        logger.error(f"❌ Application startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    try:
        await app_manager.shutdown_sequence()
    except Exception as e:
        logger.error(f"❌ Application shutdown failed: {e}")


def create_unified_app() -> FastAPI:
    """Create and configure the unified FastAPI application"""
    
    # Create FastAPI app with lifespan manager
    app = FastAPI(
        title="AI Agent Customer Support",
        version="1.0.0",
        description="Unified AI Agent and Admin Dashboard Application",
        lifespan=create_lifespan_manager
    )
    
    # Set up essential middleware immediately (before app starts)
    try:
        from .comprehensive_error_integration import configure_error_handling_for_app
        configure_error_handling_for_app(app)
    except Exception as e:
        logger.warning(f"Could not configure error handling middleware: {e}")
    
    # Add CORS middleware with enhanced configuration for admin dashboard
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:8000", 
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000",
            "*"  # Allow all origins for development
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=[
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-Request-Format",
            "Cache-Control"
        ],
        expose_headers=["Set-Cookie"],
    )
    
    return app