# Multi-layered Security System
# Implements RBAC, JWT/OAuth 2.0 authentication, and data encryption

import jwt
import bcrypt
import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from functools import wraps
import logging
import redis
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import os
from flask import request, jsonify, current_app, g
import ipaddress
from urllib.parse import urlparse
import re

# Import local modules
from .models import db, User
from .error_handling import error_handler, ErrorCategory, ErrorSeverity, ErrorContext

# Setup logging
logger = logging.getLogger(__name__)

class Permission(Enum):
    """System permissions"""
    # User management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_LIST = "user:list"
    
    # Ticket management
    TICKET_CREATE = "ticket:create"
    TICKET_READ = "ticket:read"
    TICKET_UPDATE = "ticket:update"
    TICKET_DELETE = "ticket:delete"
    TICKET_LIST = "ticket:list"
    TICKET_ASSIGN = "ticket:assign"
    
    # Comment management
    COMMENT_CREATE = "comment:create"
    COMMENT_READ = "comment:read"
    COMMENT_UPDATE = "comment:update"
    COMMENT_DELETE = "comment:delete"
    
    # System administration
    SYSTEM_CONFIG = "system:config"
    SYSTEM_MONITOR = "system:monitor"
    SYSTEM_BACKUP = "system:backup"
    SYSTEM_LOGS = "system:logs"
    
    # Integration management
    INTEGRATION_MANAGE = "integration:manage"
    INTEGRATION_SYNC = "integration:sync"
    INTEGRATION_MONITOR = "integration:monitor"
    
    # Analytics and reporting
    ANALYTICS_VIEW = "analytics:view"
    ANALYTICS_EXPORT = "analytics:export"
    REPORTS_GENERATE = "reports:generate"

class Role(Enum):
    """System roles with associated permissions"""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    AGENT = "agent"
    USER = "user"
    READONLY = "readonly"

# Role-Permission mapping
ROLE_PERMISSIONS = {
    Role.SUPER_ADMIN: list(Permission),  # All permissions
    Role.ADMIN: [
        Permission.USER_CREATE, Permission.USER_READ, Permission.USER_UPDATE, Permission.USER_LIST,
        Permission.TICKET_CREATE, Permission.TICKET_READ, Permission.TICKET_UPDATE, Permission.TICKET_DELETE, Permission.TICKET_LIST, Permission.TICKET_ASSIGN,
        Permission.COMMENT_CREATE, Permission.COMMENT_READ, Permission.COMMENT_UPDATE, Permission.COMMENT_DELETE,
        Permission.SYSTEM_CONFIG, Permission.SYSTEM_MONITOR, Permission.SYSTEM_LOGS,
        Permission.INTEGRATION_MANAGE, Permission.INTEGRATION_SYNC, Permission.INTEGRATION_MONITOR,
        Permission.ANALYTICS_VIEW, Permission.ANALYTICS_EXPORT, Permission.REPORTS_GENERATE
    ],
    Role.MANAGER: [
        Permission.USER_READ, Permission.USER_LIST,
        Permission.TICKET_CREATE, Permission.TICKET_READ, Permission.TICKET_UPDATE, Permission.TICKET_LIST, Permission.TICKET_ASSIGN,
        Permission.COMMENT_CREATE, Permission.COMMENT_READ, Permission.COMMENT_UPDATE,
        Permission.SYSTEM_MONITOR,
        Permission.INTEGRATION_MONITOR,
        Permission.ANALYTICS_VIEW, Permission.REPORTS_GENERATE
    ],
    Role.AGENT: [
        Permission.USER_READ,
        Permission.TICKET_CREATE, Permission.TICKET_READ, Permission.TICKET_UPDATE, Permission.TICKET_LIST,
        Permission.COMMENT_CREATE, Permission.COMMENT_READ, Permission.COMMENT_UPDATE,
        Permission.ANALYTICS_VIEW
    ],
    Role.USER: [
        Permission.TICKET_CREATE, Permission.TICKET_READ,
        Permission.COMMENT_CREATE, Permission.COMMENT_READ
    ],
    Role.READONLY: [
        Permission.USER_READ,
        Permission.TICKET_READ, Permission.TICKET_LIST,
        Permission.COMMENT_READ,
        Permission.ANALYTICS_VIEW
    ]
}

@dataclass
class TokenClaims:
    """JWT token claims"""
    user_id: int
    username: str
    email: str
    roles: List[str]
    permissions: List[str]
    session_id: str
    issued_at: datetime
    expires_at: datetime
    issuer: str = "admin_dashboard"
    audience: str = "admin_dashboard_api"

@dataclass
class SecurityContext:
    """Security context for requests"""
    user_id: int
    username: str
    roles: Set[Role]
    permissions: Set[Permission]
    session_id: str
    ip_address: str
    user_agent: str
    authenticated_at: datetime
    last_activity: datetime

class EncryptionManager:
    """Manages data encryption and decryption"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.master_key = self._get_or_generate_master_key()
        self.fernet = Fernet(self.master_key)
        
        # Initialize RSA keys for asymmetric encryption
        self.private_key, self.public_key = self._get_or_generate_rsa_keys()
    
    def _get_or_generate_master_key(self) -> bytes:
        """Get or generate master encryption key"""
        key_file = self.config.get('master_key_file', 'master.key')
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            os.chmod(key_file, 0o600)  # Restrict permissions
            return key
    
    def _get_or_generate_rsa_keys(self):
        """Get or generate RSA key pair"""
        private_key_file = self.config.get('private_key_file', 'private.pem')
        public_key_file = self.config.get('public_key_file', 'public.pem')
        
        if os.path.exists(private_key_file) and os.path.exists(public_key_file):
            # Load existing keys
            with open(private_key_file, 'rb') as f:
                private_key = serialization.load_pem_private_key(f.read(), password=None)
            
            with open(public_key_file, 'rb') as f:
                public_key = serialization.load_pem_public_key(f.read())
            
            return private_key, public_key
        else:
            # Generate new keys
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            public_key = private_key.public_key()
            
            # Save keys
            with open(private_key_file, 'wb') as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            os.chmod(private_key_file, 0o600)
            
            with open(public_key_file, 'wb') as f:
                f.write(public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ))
            
            return private_key, public_key
    
    def encrypt_data(self, data: Union[str, bytes]) -> str:
        """Encrypt data using symmetric encryption"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        encrypted = self.fernet.encrypt(data)
        return base64.b64encode(encrypted).decode('utf-8')
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt data using symmetric encryption"""
        encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
        decrypted = self.fernet.decrypt(encrypted_bytes)
        return decrypted.decode('utf-8')
    
    def encrypt_with_rsa(self, data: Union[str, bytes]) -> str:
        """Encrypt data using RSA public key"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        encrypted = self.public_key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return base64.b64encode(encrypted).decode('utf-8')
    
    def decrypt_with_rsa(self, encrypted_data: str) -> str:
        """Decrypt data using RSA private key"""
        encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
        decrypted = self.private_key.decrypt(
            encrypted_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return decrypted.decode('utf-8')
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure token"""
        return secrets.token_urlsafe(length)

class SessionManager:
    """Manages user sessions with Redis backend"""
    
    def __init__(self, redis_client, config: Dict[str, Any]):
        self.redis_client = redis_client
        self.config = config
        self.session_timeout = config.get('session_timeout', 3600)  # 1 hour
        self.max_sessions_per_user = config.get('max_sessions_per_user', 5)
    
    def create_session(self, user_id: int, ip_address: str, user_agent: str) -> str:
        """Create a new session"""
        session_id = secrets.token_urlsafe(32)
        session_data = {
            'user_id': user_id,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'created_at': datetime.utcnow().isoformat(),
            'last_activity': datetime.utcnow().isoformat()
        }
        
        # Store session
        session_key = f"session:{session_id}"
        self.redis_client.setex(
            session_key,
            self.session_timeout,
            json.dumps(session_data)
        )
        
        # Track user sessions
        user_sessions_key = f"user_sessions:{user_id}"
        self.redis_client.sadd(user_sessions_key, session_id)
        self.redis_client.expire(user_sessions_key, self.session_timeout)
        
        # Enforce session limit
        self._enforce_session_limit(user_id)
        
        logger.info(f"Created session {session_id} for user {user_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        session_key = f"session:{session_id}"
        session_data = self.redis_client.get(session_key)
        
        if session_data:
            return json.loads(session_data)
        return None
    
    def update_session_activity(self, session_id: str):
        """Update session last activity"""
        session_data = self.get_session(session_id)
        if session_data:
            session_data['last_activity'] = datetime.utcnow().isoformat()
            session_key = f"session:{session_id}"
            self.redis_client.setex(
                session_key,
                self.session_timeout,
                json.dumps(session_data)
            )
    
    def invalidate_session(self, session_id: str):
        """Invalidate a session"""
        session_data = self.get_session(session_id)
        if session_data:
            user_id = session_data['user_id']
            
            # Remove from Redis
            session_key = f"session:{session_id}"
            self.redis_client.delete(session_key)
            
            # Remove from user sessions
            user_sessions_key = f"user_sessions:{user_id}"
            self.redis_client.srem(user_sessions_key, session_id)
            
            logger.info(f"Invalidated session {session_id} for user {user_id}")
    
    def invalidate_user_sessions(self, user_id: int):
        """Invalidate all sessions for a user"""
        user_sessions_key = f"user_sessions:{user_id}"
        session_ids = self.redis_client.smembers(user_sessions_key)
        
        for session_id in session_ids:
            self.invalidate_session(session_id)
        
        logger.info(f"Invalidated all sessions for user {user_id}")
    
    def _enforce_session_limit(self, user_id: int):
        """Enforce maximum sessions per user"""
        user_sessions_key = f"user_sessions:{user_id}"
        session_ids = list(self.redis_client.smembers(user_sessions_key))
        
        if len(session_ids) > self.max_sessions_per_user:
            # Remove oldest sessions
            sessions_to_remove = session_ids[:-self.max_sessions_per_user]
            for session_id in sessions_to_remove:
                self.invalidate_session(session_id)

class SecurityManager:
    """Main security manager"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.jwt_secret = config.get('jwt_secret', secrets.token_urlsafe(64))
        self.jwt_algorithm = config.get('jwt_algorithm', 'HS256')
        self.token_expiry = config.get('token_expiry', 3600)  # 1 hour
        self.refresh_token_expiry = config.get('refresh_token_expiry', 86400 * 7)  # 7 days
        
        # Initialize components
        self.encryption_manager = EncryptionManager(config.get('encryption', {}))
        
        # Initialize Redis for sessions
        redis_url = config.get('redis_url', 'redis://localhost:6379')
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.session_manager = SessionManager(self.redis_client, config.get('sessions', {}))
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
            self.session_manager = None
        
        # Security policies
        self.password_policy = config.get('password_policy', {
            'min_length': 8,
            'require_uppercase': True,
            'require_lowercase': True,
            'require_numbers': True,
            'require_special': True
        })
        
        self.rate_limits = config.get('rate_limits', {
            'login_attempts': {'max': 5, 'window': 300},  # 5 attempts per 5 minutes
            'api_requests': {'max': 1000, 'window': 3600}  # 1000 requests per hour
        })
    
    def authenticate_user(self, username: str, password: str, ip_address: str, 
                         user_agent: str) -> Optional[Dict[str, Any]]:
        """Authenticate user and create session"""
        try:
            # Check rate limiting
            if not self._check_rate_limit('login', ip_address):
                raise Exception("Too many login attempts")
            
            # Find user
            user = User.query.filter_by(username=username).first()
            if not user:
                self._record_failed_login(username, ip_address, "User not found")
                return None
            
            # Verify password
            if not self.encryption_manager.verify_password(password, user.password):
                self._record_failed_login(username, ip_address, "Invalid password")
                return None
            
            # Check if user is active
            if not getattr(user, 'is_active', True):
                self._record_failed_login(username, ip_address, "Account disabled")
                return None
            
            # Create session
            session_id = None
            if self.session_manager:
                session_id = self.session_manager.create_session(
                    user.id, ip_address, user_agent
                )
            
            # Get user roles and permissions
            user_roles = self._get_user_roles(user)
            user_permissions = self._get_user_permissions(user_roles)
            
            # Create tokens
            access_token = self._create_access_token(user, user_roles, user_permissions, session_id)
            refresh_token = self._create_refresh_token(user, session_id)
            
            # Update last login
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"User {username} authenticated successfully from {ip_address}")
            
            return {
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'full_name': user.full_name,
                    'roles': [role.value for role in user_roles],
                    'permissions': [perm.value for perm in user_permissions]
                },
                'access_token': access_token,
                'refresh_token': refresh_token,
                'session_id': session_id,
                'expires_in': self.token_expiry
            }
            
        except Exception as e:
            context = ErrorContext(
                operation='authenticate_user',
                component='security_manager',
                additional_data={'username': username, 'ip_address': ip_address}
            )
            if error_handler:
                error_handler.handle_error(e, context, ErrorSeverity.MEDIUM, ErrorCategory.AUTHENTICATION)
            raise
    
    def _get_user_roles(self, user: User) -> Set[Role]:
        """Get user roles"""
        roles = set()
        
        # Check if user is admin
        if getattr(user, 'is_admin', False):
            roles.add(Role.ADMIN)
        
        # Add default user role
        roles.add(Role.USER)
        
        # TODO: Implement proper role assignment from database
        # This is a simplified implementation
        
        return roles
    
    def _get_user_permissions(self, roles: Set[Role]) -> Set[Permission]:
        """Get permissions for roles"""
        permissions = set()
        
        for role in roles:
            if role in ROLE_PERMISSIONS:
                permissions.update(ROLE_PERMISSIONS[role])
        
        return permissions
    
    def _create_access_token(self, user: User, roles: Set[Role], 
                           permissions: Set[Permission], session_id: str) -> str:
        """Create JWT access token"""
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=self.token_expiry)
        
        claims = {
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'roles': [role.value for role in roles],
            'permissions': [perm.value for perm in permissions],
            'session_id': session_id,
            'iat': now,
            'exp': expires_at,
            'iss': 'admin_dashboard',
            'aud': 'admin_dashboard_api'
        }
        
        return jwt.encode(claims, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def _create_refresh_token(self, user: User, session_id: str) -> str:
        """Create refresh token"""
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=self.refresh_token_expiry)
        
        claims = {
            'user_id': user.id,
            'session_id': session_id,
            'type': 'refresh',
            'iat': now,
            'exp': expires_at,
            'iss': 'admin_dashboard'
        }
        
        return jwt.encode(claims, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def verify_token(self, token: str) -> Optional[TokenClaims]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            # Verify session if session manager is available
            session_id = payload.get('session_id')
            if session_id and self.session_manager:
                session_data = self.session_manager.get_session(session_id)
                if not session_data:
                    return None
                
                # Update session activity
                self.session_manager.update_session_activity(session_id)
            
            return TokenClaims(
                user_id=payload['user_id'],
                username=payload['username'],
                email=payload['email'],
                roles=payload['roles'],
                permissions=payload['permissions'],
                session_id=payload['session_id'],
                issued_at=datetime.fromtimestamp(payload['iat']),
                expires_at=datetime.fromtimestamp(payload['exp']),
                issuer=payload.get('iss', ''),
                audience=payload.get('aud', '')
            )
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Refresh access token using refresh token"""
        try:
            payload = jwt.decode(refresh_token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            if payload.get('type') != 'refresh':
                return None
            
            user_id = payload['user_id']
            session_id = payload['session_id']
            
            # Verify session
            if self.session_manager:
                session_data = self.session_manager.get_session(session_id)
                if not session_data or session_data['user_id'] != user_id:
                    return None
            
            # Get user and create new access token
            user = User.query.get(user_id)
            if not user:
                return None
            
            user_roles = self._get_user_roles(user)
            user_permissions = self._get_user_permissions(user_roles)
            
            return self._create_access_token(user, user_roles, user_permissions, session_id)
            
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return None
    
    def logout_user(self, session_id: str):
        """Logout user and invalidate session"""
        if self.session_manager:
            self.session_manager.invalidate_session(session_id)
    
    def validate_password(self, password: str) -> Dict[str, Any]:
        """Validate password against policy"""
        policy = self.password_policy
        errors = []
        
        if len(password) < policy['min_length']:
            errors.append(f"Password must be at least {policy['min_length']} characters long")
        
        if policy['require_uppercase'] and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if policy['require_lowercase'] and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if policy['require_numbers'] and not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
        
        if policy['require_special'] and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _check_rate_limit(self, action: str, identifier: str) -> bool:
        """Check rate limit for action"""
        if not self.redis_client or action not in self.rate_limits:
            return True
        
        limit_config = self.rate_limits[action]
        key = f"rate_limit:{action}:{identifier}"
        
        try:
            current = self.redis_client.get(key)
            if current is None:
                self.redis_client.setex(key, limit_config['window'], 1)
                return True
            elif int(current) >= limit_config['max']:
                return False
            else:
                self.redis_client.incr(key)
                return True
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return True  # Allow on error
    
    def _record_failed_login(self, username: str, ip_address: str, reason: str):
        """Record failed login attempt"""
        logger.warning(f"Failed login attempt for {username} from {ip_address}: {reason}")
        
        # TODO: Store in database for analysis
        # This could be used for security monitoring and alerting

# Global security manager instance
security_manager = None

def init_security_manager(config: Dict[str, Any]):
    """Initialize the global security manager"""
    global security_manager
    security_manager = SecurityManager(config)
    return security_manager

# Decorators for authentication and authorization

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authentication required', 'error_code': 'AUTH_REQUIRED'}), 401
        
        token = auth_header.split(' ')[1]
        
        if not security_manager:
            return jsonify({'error': 'Security system unavailable', 'error_code': 'SECURITY_UNAVAILABLE'}), 500
        
        token_claims = security_manager.verify_token(token)
        if not token_claims:
            return jsonify({'error': 'Invalid or expired token', 'error_code': 'INVALID_TOKEN'}), 401
        
        # Create security context
        g.security_context = SecurityContext(
            user_id=token_claims.user_id,
            username=token_claims.username,
            roles={Role(role) for role in token_claims.roles},
            permissions={Permission(perm) for perm in token_claims.permissions},
            session_id=token_claims.session_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            authenticated_at=token_claims.issued_at,
            last_activity=datetime.utcnow()
        )
        
        return f(*args, **kwargs)
    
    return decorated_function

def require_permission(permission: Permission):
    """Decorator to require specific permission"""
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'security_context'):
                return jsonify({'error': 'Security context not available', 'error_code': 'NO_SECURITY_CONTEXT'}), 500
            
            if permission not in g.security_context.permissions:
                return jsonify({
                    'error': 'Insufficient permissions', 
                    'error_code': 'INSUFFICIENT_PERMISSIONS',
                    'required_permission': permission.value
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def require_role(role: Role):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'security_context'):
                return jsonify({'error': 'Security context not available', 'error_code': 'NO_SECURITY_CONTEXT'}), 500
            
            if role not in g.security_context.roles:
                return jsonify({
                    'error': 'Insufficient role', 
                    'error_code': 'INSUFFICIENT_ROLE',
                    'required_role': role.value
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

# Security middleware
def security_middleware():
    """Security middleware for request processing"""
    # Add security headers
    @current_app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = "default-src 'self'"
        return response
    
    # Rate limiting middleware
    @current_app.before_request
    def rate_limit_middleware():
        if security_manager:
            ip_address = request.remote_addr
            if not security_manager._check_rate_limit('api_requests', ip_address):
                return jsonify({
                    'error': 'Rate limit exceeded', 
                    'error_code': 'RATE_LIMIT_EXCEEDED'
                }), 429

# Health check for security system
def get_security_health():
    """Get health status of security system"""
    if not security_manager:
        return {'status': 'unhealthy', 'reason': 'Security manager not initialized'}
    
    try:
        health_data = {
            'status': 'healthy',
            'encryption_available': security_manager.encryption_manager is not None,
            'session_manager_available': security_manager.session_manager is not None,
            'redis_connected': security_manager.redis_client is not None
        }
        
        if security_manager.redis_client:
            try:
                security_manager.redis_client.ping()
                health_data['redis_status'] = 'connected'
            except:
                health_data['redis_status'] = 'disconnected'
        
        return health_data
    except Exception as e:
        return {'status': 'unhealthy', 'reason': str(e)}