from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_migrate import Migrate
from flask_socketio import SocketIO
import os
import sys
import logging
import asyncio
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Add the parent directory to sys.path to allow importing from ai-agent backend
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)  # Insert at beginning to prioritize root backend

# Import local modules
from .config import Config, get_config
from .auth import auth_bp, token_required, admin_required
from flask_jwt_extended import JWTManager
from .admin import admin_bp
from .tickets import tickets_bp
from .integration import AI_AGENT_BACKEND_AVAILABLE

# Import database models
from .models import db, User
from .models_support import Ticket, TicketComment, TicketActivity

# Import new integration components
try:
    from .integration_manager import (
        AdminDashboardIntegration,
        IntegrationConfig,
        init_admin_integration,
        integration_context
    )
    from .error_handling import init_error_handler
    from .security import init_security_manager
    from .monitoring import init_monitoring_system
    from .data_pipeline import init_data_pipeline
    from .realtime_sync import init_sync_service
    INTEGRATION_AVAILABLE = True
except ImportError:
    # Suppress integration import warnings as they are optional
    INTEGRATION_AVAILABLE = False

# Try to import ai-agent backend modules
try:
    from backend.database import init_db as ai_agent_init_db
    AI_AGENT_DB_AVAILABLE = True
except ImportError:
    print("Warning: Could not import ai-agent backend database module")
    AI_AGENT_DB_AVAILABLE = False

# Global integration instance
admin_integration = None
socketio = None

def create_app(config_name=None):
    """Factory function to create the Flask application"""
    global admin_integration, socketio
    
    app = Flask(__name__, static_folder='../frontend', static_url_path='/')
    
    # Load configuration
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    app.config.from_object(get_config(config_name))
    
    # Initialize extensions
    db.init_app(app)
    CORS(app, origins="*", supports_credentials=True)
    Migrate(app, db)
    
    # Initialize JWTManager
    jwt = JWTManager()
    jwt.init_app(app)
    
    # Initialize SocketIO for real-time features
    socketio = SocketIO(
        app, 
        cors_allowed_origins="*",
        async_mode='threading',
        logger=True,
        engineio_logger=True
    )
    
    # Initialize integration system if available
    if INTEGRATION_AVAILABLE:
        @app.before_first_request
        def initialize_integration():
            """Initialize integration system on first request"""
            global admin_integration
            
            try:
                app.logger.info("Initializing admin dashboard integration...")
                
                # Create integration configuration
                integration_config = IntegrationConfig.from_flask_config(app)
                
                # Initialize integration system
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    admin_integration = loop.run_until_complete(
                        init_admin_integration(integration_config, app)
                    )
                    
                    # Store integration in app context
                    app.admin_integration = admin_integration
                    
                    app.logger.info("Admin dashboard integration initialized successfully")
                    
                finally:
                    loop.close()
                    
            except Exception as e:
                app.logger.error(f"Failed to initialize integration: {e}")
                # Continue without integration - basic functionality will still work
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(tickets_bp, url_prefix='/api/tickets')
    
    # Register integration routes if available
    if INTEGRATION_AVAILABLE:
        try:
            from .integration_routes import create_integration_blueprint
            if admin_integration:
                integration_mgmt_bp = create_integration_blueprint(admin_integration)
                app.register_blueprint(integration_mgmt_bp, url_prefix='/api/integration')
        except Exception as e:
            app.logger.warning(f"Could not register integration management routes: {e}")
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Initialize ai-agent backend database if available
    if AI_AGENT_DB_AVAILABLE:
        try:
            ai_agent_init_db()
            print("AI Agent backend database initialized successfully")
        except Exception as e:
            print(f"Error initializing AI Agent backend database: {e}")
    
    # Setup logging
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/admin_dashboard.log', 
            maxBytes=10240, 
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Admin Dashboard startup')
    
    # Basic routes
    @app.route('/')
    def index():
        return app.send_static_file('index.html')
    
    @app.route('/api/health')
    def health_check():
        """Health check endpoint"""
        try:
            # Check database connection
            db.session.execute(db.text('SELECT 1'))
            
            # Check integration status if available
            integration_status = 'not_available'
            if INTEGRATION_AVAILABLE and admin_integration:
                integration_health = admin_integration.get_health()
                integration_status = integration_health.get('status', 'unknown')
            elif INTEGRATION_AVAILABLE:
                integration_status = 'not_initialized'
            
            return jsonify({
                'status': 'ok',
                'timestamp': datetime.utcnow().isoformat(),
                'database': 'connected',
                'ai_agent_backend_available': AI_AGENT_BACKEND_AVAILABLE,
                'ai_agent_db_available': AI_AGENT_DB_AVAILABLE,
                'integration_available': INTEGRATION_AVAILABLE,
                'integration_status': integration_status,
                'version': '1.0.0'
            })
            
        except Exception as e:
            app.logger.error(f"Health check failed: {e}")
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 503
    
    @app.route('/api/status')
    def integration_status():
        """Get integration system status"""
        try:
            if INTEGRATION_AVAILABLE and admin_integration:
                return jsonify(admin_integration.get_status())
            else:
                return jsonify({
                    'status': 'not_available' if not INTEGRATION_AVAILABLE else 'not_initialized',
                    'message': 'Integration system not available' if not INTEGRATION_AVAILABLE else 'Integration system not initialized',
                    'integration_available': INTEGRATION_AVAILABLE
                })
        except Exception as e:
            app.logger.error(f"Status check failed: {e}")
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500
    
    # Enhanced error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Resource not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal server error: {error}")
        return jsonify({'error': 'Internal server error'}), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        app.logger.error(f"Unhandled exception: {error}")
        
        # Use integration error handler if available
        if INTEGRATION_AVAILABLE and admin_integration and admin_integration.error_handler:
            try:
                from .error_handling import ErrorContext, ErrorSeverity, ErrorCategory
                context = ErrorContext(
                    operation='flask_request',
                    component='admin_dashboard'
                )
                admin_integration.error_handler.handle_error(
                    error, context, ErrorSeverity.HIGH, ErrorCategory.APPLICATION
                )
            except Exception as e:
                app.logger.error(f"Error handler failed: {e}")
        
        return jsonify({'error': 'An unexpected error occurred'}), 500
    
    # Graceful shutdown handler
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db.session.remove()
    
    return app

def create_socketio_app(config_name=None):
    """Create Flask app with SocketIO support"""
    app = create_app(config_name)
    return app, socketio

async def run_with_integration(config_name=None, host='0.0.0.0', port=5000, debug=True):
    """Run application with full integration support"""
    if not INTEGRATION_AVAILABLE:
        raise RuntimeError("Integration components not available")
    
    try:
        # Create app
        app = create_app(config_name)
        
        # Create integration configuration
        integration_config = IntegrationConfig.from_flask_config(app)
        
        # Run with integration context
        async with integration_context(integration_config, app) as integration:
            app.logger.info(f"Starting admin dashboard with integration on {host}:{port}")
            
            # Store integration reference
            app.admin_integration = integration
            
            # Run the app (this would need to be adapted for production)
            if socketio:
                socketio.run(app, host=host, port=port, debug=debug)
            else:
                app.run(host=host, port=port, debug=debug)
                
    except Exception as e:
        print(f"Failed to run application with integration: {e}")
        raise

# Create the app
app = create_app()

if __name__ == '__main__':
    import sys
    
    # Check if running with integration
    if '--with-integration' in sys.argv and INTEGRATION_AVAILABLE:
        # Run with full integration support
        asyncio.run(run_with_integration())
    else:
        # Run basic Flask app
        if socketio:
            socketio.run(app, debug=True, host='0.0.0.0', port=5000)
        else:
            app.run(debug=True, host='0.0.0.0', port=5000)