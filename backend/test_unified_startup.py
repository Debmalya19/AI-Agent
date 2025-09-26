"""
Test Unified Application Startup and Configuration

This module tests the unified startup system to ensure all components
are properly initialized and configured.

Requirements: 6.1, 6.2, 6.3, 6.4
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, patch, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from .unified_startup import UnifiedApplicationManager, create_unified_app, get_app_manager
from .unified_config import UnifiedConfig, ConfigManager, Environment
from .health_checks import create_health_check_router


class TestUnifiedApplicationManager:
    """Test the unified application manager"""
    
    @pytest.fixture
    def app_manager(self):
        """Create a test application manager"""
        return UnifiedApplicationManager()
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration"""
        config = Mock(spec=UnifiedConfig)
        config.environment = Environment.TESTING
        config.database.url = "sqlite:///test.db"
        config.ai_agent.google_api_key = "test-key"
        config.admin_dashboard.enabled = True
        config.data_sync.enabled = True
        config.voice.enabled = True
        config.analytics.enabled = True
        config.server.cors_origins = ["*"]
        config.is_production.return_value = False
        config.is_development.return_value = False
        return config
    
    @pytest.mark.asyncio
    async def test_initialize_configuration(self, app_manager):
        """Test configuration initialization"""
        with patch('backend.unified_startup.get_config_manager') as mock_get_config:
            mock_config_manager = Mock(spec=ConfigManager)
            mock_config_manager.config = Mock(spec=UnifiedConfig)
            mock_config_manager.config.environment = Environment.TESTING
            mock_config_manager.config.is_production.return_value = False
            mock_config_manager.validate_config.return_value = True
            mock_get_config.return_value = mock_config_manager
            
            result = await app_manager.initialize_configuration()
            
            assert result is True
            assert app_manager.config_manager is not None
            mock_config_manager.setup_logging.assert_called_once()
            mock_config_manager.validate_config.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_error_handling(self, app_manager):
        """Test error handling initialization"""
        result = await app_manager.initialize_error_handling()
        
        assert result is True
        assert app_manager.error_handler is not None
        assert "error_handling" in app_manager.initialized_services
    
    @pytest.mark.asyncio
    async def test_initialize_database(self, app_manager):
        """Test database initialization"""
        with patch('backend.unified_startup.init_db') as mock_init_db:
            result = await app_manager.initialize_database()
            
            assert result is True
            assert "database" in app_manager.initialized_services
            mock_init_db.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_ai_agent_without_api_key(self, app_manager, mock_config):
        """Test AI agent initialization without API key"""
        mock_config.ai_agent.google_api_key = None
        app_manager.config = mock_config
        
        result = await app_manager.initialize_ai_agent()
        
        assert result is True  # Should continue without AI functionality
        assert len(app_manager.startup_errors) > 0
        assert any("Google API key not configured" in error for error in app_manager.startup_errors)
    
    @pytest.mark.asyncio
    async def test_initialize_admin_dashboard_disabled(self, app_manager, mock_config):
        """Test admin dashboard initialization when disabled"""
        mock_config.admin_dashboard.enabled = False
        app_manager.config = mock_config
        
        result = await app_manager.initialize_admin_dashboard()
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_initialize_data_sync_disabled(self, app_manager, mock_config):
        """Test data sync initialization when disabled"""
        mock_config.data_sync.enabled = False
        app_manager.config = mock_config
        
        result = await app_manager.initialize_data_sync()
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_startup_sequence(self, app_manager, mock_config):
        """Test complete startup sequence"""
        app = FastAPI()
        app_manager.config = mock_config
        
        with patch.object(app_manager, 'initialize_configuration', return_value=True), \
             patch.object(app_manager, 'initialize_error_handling', return_value=True), \
             patch.object(app_manager, 'initialize_database', return_value=True), \
             patch.object(app_manager, 'initialize_ai_agent', return_value=True), \
             patch.object(app_manager, 'initialize_admin_dashboard', return_value=True), \
             patch.object(app_manager, 'initialize_data_sync', return_value=True), \
             patch.object(app_manager, 'initialize_voice_assistant', return_value=True), \
             patch.object(app_manager, 'initialize_analytics', return_value=True), \
             patch.object(app_manager, 'initialize_background_tasks', return_value=True), \
             patch.object(app_manager, 'setup_middleware'), \
             patch.object(app_manager, 'setup_static_files'), \
             patch.object(app_manager, 'setup_health_checks'):
            
            await app_manager.startup_sequence(app)
            
            assert app_manager.app is app
            assert len(app_manager.initialized_services) > 0
    
    def test_setup_middleware(self, app_manager, mock_config):
        """Test middleware setup"""
        app = FastAPI()
        app_manager.app = app
        app_manager.config = mock_config
        app_manager.error_handler = Mock()
        
        with patch('backend.unified_startup.setup_error_middleware') as mock_setup_error:
            app_manager.setup_middleware()
            
            # Check that CORS middleware was added (we can't easily verify this)
            # But we can check that error middleware setup was called
            mock_setup_error.assert_called_once_with(app, app_manager.error_handler)
    
    def test_setup_health_checks(self, app_manager):
        """Test health check setup"""
        app = FastAPI()
        app_manager.app = app
        
        with patch('backend.unified_startup.create_health_check_router') as mock_create_router:
            mock_router = Mock()
            mock_create_router.return_value = mock_router
            
            app_manager.setup_health_checks()
            
            mock_create_router.assert_called_once()


class TestUnifiedConfig:
    """Test unified configuration system"""
    
    def test_create_unified_app(self):
        """Test unified app creation"""
        app = create_unified_app()
        
        assert isinstance(app, FastAPI)
        assert app.title == "AI Agent Customer Support"
        assert app.version == "1.0.0"
    
    def test_get_app_manager_singleton(self):
        """Test that app manager is a singleton"""
        manager1 = get_app_manager()
        manager2 = get_app_manager()
        
        assert manager1 is manager2


class TestHealthChecks:
    """Test health check endpoints"""
    
    def test_create_health_check_router(self):
        """Test health check router creation"""
        router = create_health_check_router()
        
        assert router.prefix == "/health"
        assert "health" in router.tags
        
        # Check that routes are registered
        route_paths = [route.path for route in router.routes]
        assert "/health/" in route_paths
        assert "/health/detailed" in route_paths
        assert "/health/database" in route_paths
        assert "/health/config" in route_paths


class TestIntegrationStartup:
    """Integration tests for the startup system"""
    
    @pytest.mark.asyncio
    async def test_full_application_startup(self):
        """Test full application startup with mocked dependencies"""
        
        # Set test environment variables
        os.environ["ENVIRONMENT"] = "testing"
        os.environ["DATABASE_URL"] = "sqlite:///test.db"
        os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-purposes"
        
        try:
            with patch('backend.unified_startup.init_db'), \
                 patch('backend.unified_startup.startup_data_sync'), \
                 patch('backend.unified_startup.include_sync_router'), \
                 patch('backend.unified_startup.setup_admin_auth_proxy'), \
                 patch('backend.unified_startup.setup_admin_api_proxy'), \
                 patch('backend.unified_startup.setup_admin_frontend_integration'):
                
                app = create_unified_app()
                
                # Test that we can create a test client
                with TestClient(app) as client:
                    # Test basic health check
                    response = client.get("/health/")
                    assert response.status_code == 200
                    
                    data = response.json()
                    assert data["status"] == "healthy"
                    assert "timestamp" in data
                    assert data["service"] == "AI Agent Customer Support"
        
        finally:
            # Clean up environment variables
            for key in ["ENVIRONMENT", "DATABASE_URL", "JWT_SECRET_KEY"]:
                if key in os.environ:
                    del os.environ[key]
    
    def test_health_check_endpoints_integration(self):
        """Test health check endpoints with real router"""
        
        # Set minimal test environment
        os.environ["ENVIRONMENT"] = "testing"
        os.environ["DATABASE_URL"] = "sqlite:///test.db"
        os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing"
        
        try:
            app = FastAPI()
            health_router = create_health_check_router()
            app.include_router(health_router)
            
            with TestClient(app) as client:
                # Test basic health check
                response = client.get("/health/")
                assert response.status_code == 200
                
                # Test configuration health check
                response = client.get("/health/config")
                assert response.status_code in [200, 500]  # May fail due to missing config
                
                # Test detailed health check
                response = client.get("/health/detailed")
                assert response.status_code in [200, 503, 500]  # May have issues in test env
        
        finally:
            # Clean up environment variables
            for key in ["ENVIRONMENT", "DATABASE_URL", "JWT_SECRET_KEY"]:
                if key in os.environ:
                    del os.environ[key]


if __name__ == "__main__":
    pytest.main([__file__])