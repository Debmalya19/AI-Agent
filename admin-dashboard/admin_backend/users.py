from flask import Blueprint, request, jsonify, current_app
from datetime import datetime

from .models import db, User
from .auth import jwt_required, admin_required

users_bp = Blueprint('users', __name__, url_prefix='/api/users')


@users_bp.route('', methods=['GET'])
@jwt_required
def get_users():
    """Get all users with optional filtering"""
    try:
        # Get query parameters for filtering
        username = request.args.get('username')
        email = request.args.get('email')
        is_admin = request.args.get('is_admin')
        is_active = request.args.get('is_active')
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Build query
        query = User.query
        
        if username:
            query = query.filter(User.username.ilike(f'%{username}%'))
        
        if email:
            query = query.filter(User.email.ilike(f'%{email}%'))
        
        if is_admin is not None:
            is_admin_bool = is_admin.lower() == 'true'
            query = query.filter(User.is_admin == is_admin_bool)
        
        if is_active is not None:
            is_active_bool = is_active.lower() == 'true'
            query = query.filter(User.is_active == is_active_bool)
        
        # Execute query with pagination
        users_pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page)
        
        # Prepare response
        users = [user.to_dict() for user in users_pagination.items]
        
        return jsonify({
            'users': users,
            'pagination': {
                'total': users_pagination.total,
                'pages': users_pagination.pages,
                'page': users_pagination.page,
                'per_page': users_pagination.per_page,
                'has_next': users_pagination.has_next,
                'has_prev': users_pagination.has_prev
            }
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"Error getting users: {str(e)}")
        return jsonify({'error': 'Failed to get users', 'details': str(e)}), 500


@users_bp.route('/<int:user_id>', methods=['GET'])
@jwt_required
def get_user(user_id):
    """Get user by ID"""
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if the requesting user is an admin or the user themselves
        current_user = request.current_user
        if not current_user.is_admin and current_user.id != user_id:
            return jsonify({'error': 'Unauthorized to view this user'}), 403
        
        return jsonify({'user': user.to_dict()}), 200
    
    except Exception as e:
        current_app.logger.error(f"Error getting user {user_id}: {str(e)}")
        return jsonify({'error': 'Failed to get user', 'details': str(e)}), 500


@users_bp.route('', methods=['POST'])
@admin_required
def create_user():
    """Create a new user (admin only)"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'username', 'password', 'full_name']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Field {field} is required'}), 400
        
        # Check if user already exists
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'User with this email already exists'}), 409
        
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'User with this username already exists'}), 409
        
        # Create new user
        new_user = User(
            email=data['email'],
            username=data['username'],
            full_name=data['full_name'],
            phone=data.get('phone'),
            is_admin=data.get('is_admin', False),
            is_active=data.get('is_active', True)
        )
        new_user.set_password(data['password'])
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            'message': 'User created successfully',
            'user': new_user.to_dict()
        }), 201
    
    except Exception as e:
        current_app.logger.error(f"Error creating user: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create user', 'details': str(e)}), 500


@users_bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required
def update_user(user_id):
    """Update user information"""
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if the requesting user is an admin or the user themselves
        current_user = request.current_user
        if not current_user.is_admin and current_user.id != user_id:
            return jsonify({'error': 'Unauthorized to update this user'}), 403
        
        data = request.get_json()
        
        # Update user fields
        if 'full_name' in data:
            user.full_name = data['full_name']
        
        if 'phone' in data:
            user.phone = data['phone']
        
        # Admin-only fields
        if current_user.is_admin:
            if 'email' in data and data['email'] != user.email:
                # Check if email is already taken
                if User.query.filter_by(email=data['email']).first():
                    return jsonify({'error': 'Email already in use'}), 409
                user.email = data['email']
            
            if 'username' in data and data['username'] != user.username:
                # Check if username is already taken
                if User.query.filter_by(username=data['username']).first():
                    return jsonify({'error': 'Username already in use'}), 409
                user.username = data['username']
            
            if 'is_admin' in data:
                user.is_admin = data['is_admin']
            
            if 'is_active' in data:
                user.is_active = data['is_active']
        
        db.session.commit()
        
        return jsonify({
            'message': 'User updated successfully',
            'user': user.to_dict()
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"Error updating user {user_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update user', 'details': str(e)}), 500


@users_bp.route('/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """Delete a user (admin only)"""
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Prevent deleting the last admin user
        if user.is_admin and User.query.filter_by(is_admin=True).count() <= 1:
            return jsonify({'error': 'Cannot delete the last admin user'}), 400
        
        # Store user info for response
        user_info = user.to_dict()
        
        # Delete user
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({
            'message': 'User deleted successfully',
            'user': user_info
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"Error deleting user {user_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to delete user', 'details': str(e)}), 500


@users_bp.route('/stats', methods=['GET'])
@admin_required
def get_user_stats():
    """Get user statistics (admin only)"""
    try:
        total_users = User.query.count()
        admin_users = User.query.filter_by(is_admin=True).count()
        active_users = User.query.filter_by(is_active=True).count()
        inactive_users = User.query.filter_by(is_active=False).count()
        
        # Get new users in the last 30 days
        thirty_days_ago = datetime.utcnow().date() - datetime.timedelta(days=30)
        new_users_30d = User.query.filter(User.created_at >= thirty_days_ago).count()
        
        return jsonify({
            'total_users': total_users,
            'admin_users': admin_users,
            'active_users': active_users,
            'inactive_users': inactive_users,
            'new_users_30d': new_users_30d
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"Error getting user stats: {str(e)}")
        return jsonify({'error': 'Failed to get user statistics', 'details': str(e)}), 500