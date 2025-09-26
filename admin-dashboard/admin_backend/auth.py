from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from .models import db, User
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from datetime import datetime, timedelta
from functools import wraps
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

auth_bp = Blueprint('auth', __name__)

# Decorator for verifying the JWT
def token_required(f):
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        try:
            user_id = get_jwt_identity()
            current_user = User.query.filter_by(id=user_id).first()

            if not current_user:
                return jsonify({
                    'success': False,
                    'message': 'User not found!'
                }), 401

        except Exception as e:
            return jsonify({
                'success': False,
                'message': 'Invalid token!'
            }), 401

        return f(current_user, *args, **kwargs)

    return decorated

# Decorator for admin-only routes
def admin_required(f):
    @wraps(f)
    def decorated(current_user, *args, **kwargs):
        if not current_user.is_admin:
            return jsonify({
                'success': False,
                'message': 'Admin privileges required!'
            }), 403
        return f(current_user, *args, **kwargs)
    return decorated

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()
    
    # Validate required fields
    if not all(k in data for k in ('username', 'email', 'password')):
        return jsonify({
            'success': False,
            'message': 'Missing required fields'
        }), 400
    
    # Check if user already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({
            'success': False,
            'message': 'User with this email already exists'
        }), 409
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({
            'success': False,
            'message': 'Username already taken'
        }), 409
    
    try:
        # Create new user
        hashed_password = generate_password_hash(data['password'])
        
        # By default, new users are not admins
        is_admin = data.get('is_admin', False)
        
        # Allow admin creation if no users exist yet (first user setup)
        if is_admin and User.query.filter_by(is_admin=True).count() > 0:
            is_admin = False
        
        new_user = User(
            username=data['username'],
            email=data['email'],
            password=hashed_password,
            is_admin=is_admin,
            full_name=data.get('full_name', ''),
            phone=data.get('phone', '')
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        # Check if user exists in ai-agent backend
        if AI_AGENT_BACKEND_AVAILABLE:
            try:
                ai_agent_customer = AIAgentCustomer.query.filter_by(email=data['email']).first()
                if ai_agent_customer:
                    new_user.ai_agent_customer_id = ai_agent_customer.id
                    db.session.commit()
            except Exception as e:
                current_app.logger.error(f"Error checking ai-agent backend for customer: {e}")
        
        return jsonify({
            'success': True,
            'message': 'User registered successfully',
            'user': {
                'id': new_user.id,
                'username': new_user.username,
                'email': new_user.email,
                'is_admin': new_user.is_admin
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error registering user: {str(e)}'
        }), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login a user"""
    data = request.get_json()
    
    # Validate required fields
    if not all(k in data for k in ('email', 'password')):
        return jsonify({
            'success': False,
            'message': 'Missing required fields'
        }), 400
    
    try:
        # Find user by email
        user = User.query.filter_by(email=data['email']).first()
        
        if not user or not check_password_hash(user.password, data['password']):
            return jsonify({
                'success': False,
                'message': 'Invalid email or password'
            }), 401
        
        # Generate JWT token - identity must be string
        token = create_access_token(identity=str(user.id), expires_delta=timedelta(hours=24))
        
        # Update last login timestamp
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_admin': user.is_admin,
                'full_name': user.full_name
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error logging in: {str(e)}'
        }), 500

@auth_bp.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    """Get the current user's profile"""
    return jsonify({
        'success': True,
        'user': {
            'id': current_user.id,
            'username': current_user.username,
            'email': current_user.email,
            'is_admin': current_user.is_admin,
            'full_name': current_user.full_name,
            'phone': current_user.phone,
            'created_at': current_user.created_at,
            'last_login': current_user.last_login
        }
    }), 200

@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user(current_user):
    """Get current user information"""
    return jsonify({
        'success': True,
        'user': {
            'id': current_user.id,
            'username': current_user.username,
            'email': current_user.email,
            'is_admin': current_user.is_admin,
            'full_name': current_user.full_name,
            'phone': current_user.phone
        }
    }), 200

@auth_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile(current_user):
    """Update the current user's profile"""
    data = request.get_json()
    
    try:
        # Update user fields
        if 'username' in data and data['username'] != current_user.username:
            # Check if username is already taken
            if User.query.filter_by(username=data['username']).first():
                return jsonify({
                    'success': False,
                    'message': 'Username already taken'
                }), 409
            current_user.username = data['username']
        
        if 'email' in data and data['email'] != current_user.email:
            # Check if email is already taken
            if User.query.filter_by(email=data['email']).first():
                return jsonify({
                    'success': False,
                    'message': 'Email already taken'
                }), 409
            current_user.email = data['email']
        
        if 'full_name' in data:
            current_user.full_name = data['full_name']
        
        if 'phone' in data:
            current_user.phone = data['phone']
        
        if 'password' in data and data['password']:
            current_user.password = generate_password_hash(data['password'])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'user': {
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email,
                'is_admin': current_user.is_admin,
                'full_name': current_user.full_name,
                'phone': current_user.phone
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating profile: {str(e)}'
        }), 500

@auth_bp.route('/users', methods=['GET'])
@token_required
@admin_required
def get_users(current_user):
    """Get all users (admin only)"""
    users = User.query.all()
    return jsonify({
        'success': True,
        'users': [{
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_admin': user.is_admin,
            'full_name': user.full_name,
            'created_at': user.created_at,
            'last_login': user.last_login
        } for user in users]
    }), 200

@auth_bp.route('/users/<int:user_id>', methods=['PUT'])
@token_required
@admin_required
def update_user(current_user, user_id):
    """Update a user (admin only)"""
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    try:
        # Update user fields
        if 'username' in data and data['username'] != user.username:
            # Check if username is already taken
            if User.query.filter_by(username=data['username']).first():
                return jsonify({
                    'success': False,
                    'message': 'Username already taken'
                }), 409
            user.username = data['username']
        
        if 'email' in data and data['email'] != user.email:
            # Check if email is already taken
            if User.query.filter_by(email=data['email']).first():
                return jsonify({
                    'success': False,
                    'message': 'Email already taken'
                }), 409
            user.email = data['email']
        
        if 'full_name' in data:
            user.full_name = data['full_name']
        
        if 'phone' in data:
            user.phone = data['phone']
        
        if 'is_admin' in data:
            # Prevent removing admin status from the last admin
            if user.is_admin and not data['is_admin']:
                admin_count = User.query.filter_by(is_admin=True).count()
                if admin_count <= 1:
                    return jsonify({
                        'success': False,
                        'message': 'Cannot remove admin status from the last admin'
                    }), 400
            user.is_admin = data['is_admin']
        
        if 'password' in data and data['password']:
            user.password = generate_password_hash(data['password'])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'User updated successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_admin': user.is_admin,
                'full_name': user.full_name,
                'phone': user.phone
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating user: {str(e)}'
        }), 500

@auth_bp.route('/users/<int:user_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_user(current_user, user_id):
    """Delete a user (admin only)"""
    # Prevent deleting yourself
    if user_id == current_user.id:
        return jsonify({
            'success': False,
            'message': 'Cannot delete your own account'
        }), 400
    
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting the last admin
    if user.is_admin:
        admin_count = User.query.filter_by(is_admin=True).count()
        if admin_count <= 1:
            return jsonify({
                'success': False,
                'message': 'Cannot delete the last admin'
            }), 400
    
    try:
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'User deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error deleting user: {str(e)}'
        }), 500