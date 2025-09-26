# Integration Routes
# REST API endpoints for integration management and monitoring

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import Blueprint, request, jsonify, current_app
from functools import wraps
import traceback

# Import local modules
from .security import require_auth, require_permission, Permission
from .error_handling import handle_api_error, ErrorCategory, ErrorSeverity
from .models import db
from .models_support import PerformanceMetric

# Setup logging
logger = logging.getLogger(__name__)

def create_integration_blueprint(integration_manager) -> Blueprint:
    """Create integration management blueprint"""
    
    bp = Blueprint('integration', __name__)
    
    def async_route(f):
        """Decorator to handle async routes in Flask"""
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(f(*args, **kwargs))
                finally:
                    loop.close()
            except Exception as e:
                logger.error(f"Async route error: {e}")
                return handle_api_error(e, ErrorCategory.APPLICATION, ErrorSeverity.HIGH)
        return wrapper
    
    @bp.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        try:
            health_status = integration_manager.get_health()
            status_code = 200 if health_status['status'] == 'healthy' else 503
            return jsonify(health_status), status_code
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return jsonify({
                'status': 'error',
                'message': 'Health check failed',
                'error': str(e)
            }), 500
    
    @bp.route('/status', methods=['GET'])
    @require_auth
    @require_permission(Permission.VIEW_SYSTEM_STATUS)
    def get_status():
        """Get comprehensive integration status"""
        try:
            status = integration_manager.get_status()
            return jsonify(status)
            
        except Exception as e:
            logger.error(f"Status retrieval error: {e}")
            return handle_api_error(e, ErrorCategory.APPLICATION, ErrorSeverity.MEDIUM)
    
    @bp.route('/components', methods=['GET'])
    @require_auth
    @require_permission(Permission.VIEW_SYSTEM_STATUS)
    def get_components():
        """Get detailed component status"""
        try:
            status = integration_manager.get_status()
            components = status.get('components', {})
            
            # Add additional component details
            detailed_components = {}
            for name, component in components.items():
                detailed_components[name] = {
                    **component,
                    'description': _get_component_description(name),
                    'critical': _is_critical_component(name),
                    'dependencies': _get_component_dependencies(name)
                }
            
            return jsonify({
                'components': detailed_components,
                'summary': {
                    'total': len(components),
                    'active': sum(1 for c in components.values() if c['status'] == 'active'),
                    'error': sum(1 for c in components.values() if c['status'] == 'error'),
                    'inactive': sum(1 for c in components.values() if c['status'] == 'inactive')
                }
            })
            
        except Exception as e:
            logger.error(f"Component status error: {e}")
            return handle_api_error(e, ErrorCategory.APPLICATION, ErrorSeverity.MEDIUM)
    
    @bp.route('/components/<component_name>/restart', methods=['POST'])
    @require_auth
    @require_permission(Permission.MANAGE_SYSTEM)
    @async_route
    async def restart_component(component_name: str):
        """Restart a specific component"""
        try:
            # Validate component name
            valid_components = ['sync_service', 'data_pipeline', 'monitoring_system']
            if component_name not in valid_components:
                return jsonify({
                    'error': 'Invalid component name',
                    'valid_components': valid_components
                }), 400
            
            # Restart component based on type
            success = False
            message = ""
            
            if component_name == 'sync_service' and integration_manager.sync_service:
                await integration_manager.sync_service.restart()
                success = True
                message = "Sync service restarted successfully"
                
            elif component_name == 'data_pipeline' and integration_manager.data_pipeline:
                integration_manager.data_pipeline.restart()
                success = True
                message = "Data pipeline restarted successfully"
                
            elif component_name == 'monitoring_system' and integration_manager.monitoring_system:
                integration_manager.monitoring_system.restart()
                success = True
                message = "Monitoring system restarted successfully"
            
            else:
                message = f"Component {component_name} not available or not initialized"
            
            return jsonify({
                'success': success,
                'message': message,
                'component': component_name,
                'timestamp': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Component restart error: {e}")
            return handle_api_error(e, ErrorCategory.APPLICATION, ErrorSeverity.HIGH)
    
    @bp.route('/metrics', methods=['GET'])
    @require_auth
    @require_permission(Permission.VIEW_ANALYTICS)
    def get_metrics():
        """Get integration metrics"""
        try:
            # Get query parameters
            hours = request.args.get('hours', 24, type=int)
            metric_type = request.args.get('type', 'all')
            
            # Calculate time range
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            # Query performance metrics
            query = db.session.query(PerformanceMetric).filter(
                PerformanceMetric.timestamp >= start_time,
                PerformanceMetric.timestamp <= end_time
            )
            
            if metric_type != 'all':
                query = query.filter(PerformanceMetric.metric_name.like(f"{metric_type}%"))
            
            metrics = query.order_by(PerformanceMetric.timestamp.desc()).limit(1000).all()
            
            # Format metrics data
            metrics_data = []
            for metric in metrics:
                metrics_data.append({
                    'id': metric.id,
                    'name': metric.metric_name,
                    'value': metric.value,
                    'timestamp': metric.timestamp.isoformat(),
                    'tags': json.loads(metric.tags) if metric.tags else {},
                    'metadata': json.loads(metric.metadata) if metric.metadata else {}
                })
            
            # Calculate summary statistics
            summary = _calculate_metrics_summary(metrics_data)
            
            return jsonify({
                'metrics': metrics_data,
                'summary': summary,
                'time_range': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat(),
                    'hours': hours
                },
                'total_count': len(metrics_data)
            })
            
        except Exception as e:
            logger.error(f"Metrics retrieval error: {e}")
            return handle_api_error(e, ErrorCategory.APPLICATION, ErrorSeverity.MEDIUM)
    
    @bp.route('/sync/status', methods=['GET'])
    @require_auth
    @require_permission(Permission.VIEW_SYSTEM_STATUS)
    def get_sync_status():
        """Get real-time sync status"""
        try:
            if not integration_manager.sync_service:
                return jsonify({
                    'enabled': False,
                    'message': 'Sync service not available'
                })
            
            sync_status = integration_manager.sync_service.get_status()
            
            return jsonify({
                'enabled': True,
                'status': sync_status,
                'last_sync': integration_manager.sync_service.last_sync_time.isoformat() if integration_manager.sync_service.last_sync_time else None,
                'connected_clients': len(integration_manager.sync_service.connected_clients),
                'event_queue_size': integration_manager.sync_service.get_queue_size()
            })
            
        except Exception as e:
            logger.error(f"Sync status error: {e}")
            return handle_api_error(e, ErrorCategory.APPLICATION, ErrorSeverity.MEDIUM)
    
    @bp.route('/sync/trigger', methods=['POST'])
    @require_auth
    @require_permission(Permission.MANAGE_SYSTEM)
    @async_route
    async def trigger_sync():
        """Manually trigger a sync operation"""
        try:
            if not integration_manager.sync_service:
                return jsonify({
                    'success': False,
                    'message': 'Sync service not available'
                }), 503
            
            # Get sync type from request
            data = request.get_json() or {}
            sync_type = data.get('type', 'full')  # 'full' or 'incremental'
            entity_types = data.get('entity_types', ['tickets', 'users'])
            
            # Trigger sync
            result = await integration_manager.sync_service.trigger_manual_sync(
                sync_type=sync_type,
                entity_types=entity_types
            )
            
            return jsonify({
                'success': True,
                'message': 'Sync triggered successfully',
                'sync_id': result.get('sync_id'),
                'type': sync_type,
                'entity_types': entity_types,
                'timestamp': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Sync trigger error: {e}")
            return handle_api_error(e, ErrorCategory.APPLICATION, ErrorSeverity.HIGH)
    
    @bp.route('/config', methods=['GET'])
    @require_auth
    @require_permission(Permission.VIEW_SYSTEM_CONFIG)
    def get_config():
        """Get integration configuration"""
        try:
            config = integration_manager.config
            
            # Return safe configuration (no secrets)
            safe_config = {
                'ai_agent_url': config.ai_agent_url,
                'ai_agent_timeout': config.ai_agent_timeout,
                'monitoring_enabled': config.monitoring_enabled,
                'metrics_retention_days': config.metrics_retention_days,
                'pipeline_max_workers': config.pipeline_max_workers,
                'pipeline_batch_size': config.pipeline_batch_size,
                'sync_enabled': config.sync_enabled,
                'sync_interval': config.sync_interval,
                'websocket_enabled': config.websocket_enabled,
                'max_retry_attempts': config.max_retry_attempts,
                'cache_enabled': config.cache_enabled,
                'cache_ttl': config.cache_ttl
            }
            
            return jsonify({
                'config': safe_config,
                'last_updated': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Config retrieval error: {e}")
            return handle_api_error(e, ErrorCategory.APPLICATION, ErrorSeverity.MEDIUM)
    
    @bp.route('/config', methods=['PUT'])
    @require_auth
    @require_permission(Permission.MANAGE_SYSTEM_CONFIG)
    def update_config():
        """Update integration configuration"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No configuration data provided'}), 400
            
            # Validate and update configuration
            config = integration_manager.config
            updated_fields = []
            
            # Update allowed fields
            updatable_fields = {
                'ai_agent_timeout': int,
                'monitoring_enabled': bool,
                'metrics_retention_days': int,
                'pipeline_max_workers': int,
                'pipeline_batch_size': int,
                'sync_enabled': bool,
                'sync_interval': int,
                'websocket_enabled': bool,
                'max_retry_attempts': int,
                'cache_enabled': bool,
                'cache_ttl': int
            }
            
            for field, field_type in updatable_fields.items():
                if field in data:
                    try:
                        value = field_type(data[field])
                        setattr(config, field, value)
                        updated_fields.append(field)
                    except (ValueError, TypeError) as e:
                        return jsonify({
                            'error': f'Invalid value for {field}: {e}'
                        }), 400
            
            if not updated_fields:
                return jsonify({'message': 'No valid fields to update'}), 400
            
            # Apply configuration changes
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_apply_config_changes(integration_manager, updated_fields))
            finally:
                loop.close()
            
            return jsonify({
                'success': True,
                'message': 'Configuration updated successfully',
                'updated_fields': updated_fields,
                'timestamp': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Config update error: {e}")
            return handle_api_error(e, ErrorCategory.APPLICATION, ErrorSeverity.HIGH)
    
    @bp.route('/logs', methods=['GET'])
    @require_auth
    @require_permission(Permission.VIEW_SYSTEM_LOGS)
    def get_logs():
        """Get integration system logs"""
        try:
            # Get query parameters
            level = request.args.get('level', 'INFO')
            hours = request.args.get('hours', 24, type=int)
            component = request.args.get('component', 'all')
            limit = request.args.get('limit', 100, type=int)
            
            # This would integrate with your logging system
            # For now, return a placeholder response
            logs = _get_integration_logs(level, hours, component, limit)
            
            return jsonify({
                'logs': logs,
                'filters': {
                    'level': level,
                    'hours': hours,
                    'component': component,
                    'limit': limit
                },
                'total_count': len(logs)
            })
            
        except Exception as e:
            logger.error(f"Logs retrieval error: {e}")
            return handle_api_error(e, ErrorCategory.APPLICATION, ErrorSeverity.MEDIUM)
    
    @bp.route('/test/connection', methods=['POST'])
    @require_auth
    @require_permission(Permission.MANAGE_SYSTEM)
    @async_route
    async def test_connection():
        """Test connection to AI Agent backend"""
        try:
            data = request.get_json() or {}
            test_url = data.get('url', integration_manager.config.ai_agent_url)
            timeout = data.get('timeout', integration_manager.config.ai_agent_timeout)
            
            # Test connection
            if integration_manager.integration_api:
                result = await integration_manager.integration_api.test_connection(
                    url=test_url,
                    timeout=timeout
                )
                
                return jsonify({
                    'success': result['success'],
                    'message': result['message'],
                    'response_time': result.get('response_time'),
                    'status_code': result.get('status_code'),
                    'url': test_url,
                    'timestamp': datetime.utcnow().isoformat()
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Integration API not available'
                }), 503
                
        except Exception as e:
            logger.error(f"Connection test error: {e}")
            return handle_api_error(e, ErrorCategory.APPLICATION, ErrorSeverity.MEDIUM)
    
    @bp.route('/maintenance', methods=['POST'])
    @require_auth
    @require_permission(Permission.MANAGE_SYSTEM)
    @async_route
    async def maintenance_mode():
        """Enable/disable maintenance mode"""
        try:
            data = request.get_json() or {}
            enable = data.get('enable', False)
            message = data.get('message', 'System maintenance in progress')
            
            if enable:
                integration_manager.status = integration_manager.IntegrationStatus.MAINTENANCE
                # Additional maintenance mode logic here
            else:
                integration_manager.status = integration_manager.IntegrationStatus.HEALTHY
                # Resume normal operations
            
            return jsonify({
                'success': True,
                'maintenance_mode': enable,
                'message': message,
                'timestamp': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Maintenance mode error: {e}")
            return handle_api_error(e, ErrorCategory.APPLICATION, ErrorSeverity.HIGH)
    
    # Helper functions
    def _get_component_description(name: str) -> str:
        """Get component description"""
        descriptions = {
            'redis': 'Redis cache and session storage',
            'database': 'PostgreSQL/SQLite database connection',
            'ai_agent_backend': 'AI Agent backend API connection',
            'error_handler': 'Error handling and logging system',
            'security_manager': 'Authentication and authorization system',
            'data_pipeline': 'Data processing and transformation pipeline',
            'monitoring_system': 'System monitoring and metrics collection',
            'integration_api': 'API integration management',
            'sync_service': 'Real-time data synchronization service'
        }
        return descriptions.get(name, 'Unknown component')
    
    def _is_critical_component(name: str) -> bool:
        """Check if component is critical"""
        critical_components = ['database', 'error_handler', 'security_manager']
        return name in critical_components
    
    def _get_component_dependencies(name: str) -> List[str]:
        """Get component dependencies"""
        dependencies = {
            'sync_service': ['redis', 'database'],
            'data_pipeline': ['redis', 'database'],
            'monitoring_system': ['redis'],
            'integration_api': ['ai_agent_backend'],
            'security_manager': ['redis', 'database']
        }
        return dependencies.get(name, [])
    
    def _calculate_metrics_summary(metrics_data: List[Dict]) -> Dict[str, Any]:
        """Calculate metrics summary statistics"""
        if not metrics_data:
            return {}
        
        # Group metrics by name
        grouped_metrics = {}
        for metric in metrics_data:
            name = metric['name']
            if name not in grouped_metrics:
                grouped_metrics[name] = []
            grouped_metrics[name].append(metric['value'])
        
        # Calculate statistics
        summary = {}
        for name, values in grouped_metrics.items():
            if values:
                summary[name] = {
                    'count': len(values),
                    'avg': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'latest': values[0] if values else None
                }
        
        return summary
    
    async def _apply_config_changes(integration_manager, updated_fields: List[str]):
        """Apply configuration changes to running components"""
        try:
            # Restart components that need configuration updates
            if any(field.startswith('sync_') for field in updated_fields):
                if integration_manager.sync_service:
                    await integration_manager.sync_service.restart()
            
            if any(field.startswith('pipeline_') for field in updated_fields):
                if integration_manager.data_pipeline:
                    integration_manager.data_pipeline.restart()
            
            if 'monitoring_enabled' in updated_fields:
                if integration_manager.monitoring_system:
                    if integration_manager.config.monitoring_enabled:
                        integration_manager.monitoring_system.start()
                    else:
                        integration_manager.monitoring_system.stop()
            
        except Exception as e:
            logger.error(f"Error applying config changes: {e}")
            raise
    
    def _get_integration_logs(level: str, hours: int, component: str, limit: int) -> List[Dict]:
        """Get integration logs (placeholder implementation)"""
        # This would integrate with your actual logging system
        # For now, return sample logs
        sample_logs = [
            {
                'timestamp': datetime.utcnow().isoformat(),
                'level': 'INFO',
                'component': 'integration_manager',
                'message': 'Integration system health check completed',
                'metadata': {'status': 'healthy'}
            },
            {
                'timestamp': (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
                'level': 'INFO',
                'component': 'sync_service',
                'message': 'Real-time sync completed successfully',
                'metadata': {'synced_entities': 15}
            }
        ]
        
        return sample_logs[:limit]
    
    return bp