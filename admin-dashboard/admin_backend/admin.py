from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash
from .models import db, User
from .models_support import Ticket, TicketComment, TicketActivity, PerformanceMetric, CustomerSatisfaction
from .auth import token_required, admin_required
from datetime import datetime, timedelta
import os
import sys

# Add the parent directory to sys.path to allow importing from ai-agent backend
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Try to import from ai-agent backend
try:
    from backend.models import Customer as AIAgentCustomer
    AI_AGENT_BACKEND_AVAILABLE = True
except ImportError:
    AI_AGENT_BACKEND_AVAILABLE = False

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/register', methods=['POST'])
def admin_register():
    """Register a new admin user"""
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        full_name = data.get('full_name')
        phone = data.get('phone')
        password = data.get('password')

        if not username or not email or not password:
            return jsonify({'success': False, 'message': 'Username, email, and password are required'}), 400

        # Check if user already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            return jsonify({'success': False, 'message': 'User with this username or email already exists'}), 400

        # Create new user
        new_user = User(
            username=username,
            email=email,
            full_name=full_name,
            phone=phone,
            is_admin=True,
            password=generate_password_hash(password)
        )

        db.session.add(new_user)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Admin user registered successfully'}), 201

    except Exception as e:
        current_app.logger.error(f"Error registering admin user: {e}")
        return jsonify({'success': False, 'message': 'Failed to register admin user'}), 500

@admin_bp.route('/dashboard', methods=['GET'])
@token_required
@admin_required
def admin_dashboard(current_user):
    """Get admin dashboard statistics"""
    try:
        # Get user counts
        total_users = User.query.count()
        admin_users = User.query.filter_by(is_admin=True).count()
        regular_users = total_users - admin_users
        
        # Get ticket counts
        total_tickets = Ticket.query.count()
        open_tickets = Ticket.query.filter(Ticket.status != 'RESOLVED').count()
        resolved_tickets = Ticket.query.filter_by(status='RESOLVED').count()
        
        # Get recent users
        recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
        
        # Get recent tickets
        recent_tickets = Ticket.query.order_by(Ticket.created_at.desc()).limit(5).all()
        
        # Get system status
        system_status = {
            'ai_agent_integration': AI_AGENT_BACKEND_AVAILABLE,
            'database_status': 'online',
            'last_backup': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return jsonify({
            'success': True,
            'stats': {
                'users': {
                    'total': total_users,
                    'admin': admin_users,
                    'regular': regular_users
                },
                'tickets': {
                    'total': total_tickets,
                    'open': open_tickets,
                    'resolved': resolved_tickets
                },
                'recent_users': [{
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'created_at': user.created_at
                } for user in recent_users],
                'recent_tickets': [ticket.to_dict() for ticket in recent_tickets],
                'system_status': system_status
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error getting admin dashboard: {str(e)}'
        }), 500

@admin_bp.route('/users', methods=['GET'])
@token_required
@admin_required
def get_all_users(current_user):
    """Get all users with pagination"""
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '')
        
        # Base query
        query = User.query
        
        # Apply search filter
        if search:
            search_term = f'%{search}%'
            query = query.filter(
                (User.username.ilike(search_term)) |
                (User.email.ilike(search_term)) |
                (User.full_name.ilike(search_term))
            )
        
        # Get paginated results
        users_pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page)
        
        return jsonify({
            'success': True,
            'users': [{
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_admin': user.is_admin,
                'full_name': user.full_name,
                'phone': user.phone,
                'created_at': user.created_at,
                'last_login': user.last_login,
                'ai_agent_customer_id': user.ai_agent_customer_id
            } for user in users_pagination.items],
            'pagination': {
                'total': users_pagination.total,
                'pages': users_pagination.pages,
                'page': page,
                'per_page': per_page,
                'has_next': users_pagination.has_next,
                'has_prev': users_pagination.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error getting users: {str(e)}'
        }), 500

@admin_bp.route('/system/status', methods=['GET'])
@token_required
@admin_required
def get_system_status(current_user):
    """Get system status information"""
    try:
        # Get database stats
        user_count = User.query.count()
        ticket_count = Ticket.query.count()
        comment_count = TicketComment.query.count()
        activity_count = TicketActivity.query.count()
        
        # Get integration status
        integration_status = {
            'ai_agent_backend_available': AI_AGENT_BACKEND_AVAILABLE
        }
        
        # Get system info
        system_info = {
            'python_version': sys.version,
            'flask_version': current_app.config.get('FLASK_VERSION', 'Unknown'),
            'database_type': 'SQLite' if 'sqlite' in current_app.config.get('SQLALCHEMY_DATABASE_URI', '').lower() else 'PostgreSQL',
            'environment': current_app.config.get('ENV', 'production')
        }
        
        return jsonify({
            'success': True,
            'system_status': {
                'database_stats': {
                    'users': user_count,
                    'tickets': ticket_count,
                    'comments': comment_count,
                    'activities': activity_count
                },
                'integration_status': integration_status,
                'system_info': system_info,
                'uptime': '1 day, 2 hours, 34 minutes',  # This would be dynamic in a real implementation
                'last_backup': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')  # This would be dynamic in a real implementation
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error getting system status: {str(e)}'
        }), 500

@admin_bp.route('/system/sync-with-ai-agent', methods=['POST'])
@token_required
@admin_required
def sync_with_ai_agent(current_user):
    """Manually trigger synchronization with ai-agent backend"""
    if not AI_AGENT_BACKEND_AVAILABLE:
        return jsonify({
            'success': False,
            'message': 'AI Agent backend is not available'
        }), 400
    
    try:
        # Import integration functions
        from integration import sync_all_customers_to_ai_agent, sync_all_tickets_to_ai_agent
        
        # Sync all customers
        customer_count = sync_all_customers_to_ai_agent()
        
        # Sync all tickets
        ticket_count = sync_all_tickets_to_ai_agent()
        
        return jsonify({
            'success': True,
            'message': 'Synchronization completed successfully',
            'sync_results': {
                'customers_synced': customer_count,
                'tickets_synced': ticket_count
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error during synchronization: {str(e)}'
        }), 500

@admin_bp.route('/performance-metrics', methods=['GET'])
@token_required
@admin_required
def get_performance_metrics(current_user):
    """Get support team performance metrics"""
    try:
        # Get query parameters
        period = request.args.get('period', 'week')  # week, month, year
        
        # Calculate date range based on period
        end_date = datetime.utcnow()
        if period == 'week':
            start_date = end_date - timedelta(days=7)
        elif period == 'month':
            start_date = end_date - timedelta(days=30)
        elif period == 'year':
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=7)  # Default to week
        
        # Get performance metrics from the database
        metrics = PerformanceMetric.query.filter(
            PerformanceMetric.date >= start_date,
            PerformanceMetric.date <= end_date
        ).order_by(PerformanceMetric.date).all()
        
        # Get customer satisfaction ratings
        satisfaction_ratings = CustomerSatisfaction.query.filter(
            CustomerSatisfaction.created_at >= start_date,
            CustomerSatisfaction.created_at <= end_date
        ).all()
        
        # Calculate average satisfaction rating
        avg_satisfaction = sum(rating.rating for rating in satisfaction_ratings) / len(satisfaction_ratings) if satisfaction_ratings else 0
        
        # Calculate response time metrics
        response_times = [metric.avg_response_time for metric in metrics]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Calculate resolution time metrics
        resolution_times = [metric.avg_resolution_time for metric in metrics]
        avg_resolution_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0
        
        return jsonify({
            'success': True,
            'performance_metrics': {
                'period': period,
                'start_date': start_date,
                'end_date': end_date,
                'metrics_by_date': [{
                    'date': metric.date,
                    'tickets_opened': metric.tickets_opened,
                    'tickets_resolved': metric.tickets_resolved,
                    'avg_response_time': metric.avg_response_time,
                    'avg_resolution_time': metric.avg_resolution_time
                } for metric in metrics],
                'summary': {
                    'avg_satisfaction': round(avg_satisfaction, 2),
                    'avg_response_time': round(avg_response_time, 2),
                    'avg_resolution_time': round(avg_resolution_time, 2),
                    'total_tickets_opened': sum(metric.tickets_opened for metric in metrics),
                    'total_tickets_resolved': sum(metric.tickets_resolved for metric in metrics)
                }
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error getting performance metrics: {str(e)}'
        }), 500

@admin_bp.route('/customer-satisfaction', methods=['GET'])
@token_required
@admin_required
def get_customer_satisfaction(current_user):
    """Get customer satisfaction ratings"""
    try:
        # Get query parameters
        period = request.args.get('period', 'month')  # week, month, year
        
        # Calculate date range based on period
        end_date = datetime.utcnow()
        if period == 'week':
            start_date = end_date - timedelta(days=7)
        elif period == 'month':
            start_date = end_date - timedelta(days=30)
        elif period == 'year':
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=30)  # Default to month
        
        # Get customer satisfaction ratings
        ratings = CustomerSatisfaction.query.filter(
            CustomerSatisfaction.created_at >= start_date,
            CustomerSatisfaction.created_at <= end_date
        ).order_by(CustomerSatisfaction.created_at).all()
        
        # Calculate average rating
        avg_rating = sum(rating.rating for rating in ratings) / len(ratings) if ratings else 0
        
        # Count ratings by score (1-5)
        rating_counts = {i: 0 for i in range(1, 6)}
        for rating in ratings:
            rating_counts[rating.rating] = rating_counts.get(rating.rating, 0) + 1
        
        return jsonify({
            'success': True,
            'customer_satisfaction': {
                'period': period,
                'start_date': start_date,
                'end_date': end_date,
                'average_rating': round(avg_rating, 2),
                'rating_counts': rating_counts,
                'total_ratings': len(ratings),
                'recent_ratings': [{
                    'id': rating.id,
                    'ticket_id': rating.ticket_id,
                    'rating': rating.rating,
                    'feedback': rating.feedback,
                    'created_at': rating.created_at
                } for rating in ratings[-10:]]
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error getting customer satisfaction: {str(e)}'
        }), 500
