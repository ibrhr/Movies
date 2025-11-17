"""
Authentication service - handles user registration, login, and password management.
"""
from datetime import timedelta
from flask_jwt_extended import create_access_token
from werkzeug.security import check_password_hash

from models import db, User
from utils.errors import ValidationError
from utils.validators import Validator


class AuthService:
    """Authentication business logic."""
    
    @staticmethod
    def register_user(username, email, password):
        """
        Register a new user.
        
        Returns:
            dict: {'success': bool, 'message': str, 'user': User, 'token': str}
        """
        # Validate input
        try:
            username = Validator.validate_username(username)
            email = Validator.validate_email(email)
            password = Validator.validate_password(password)
        except ValidationError as e:
            return {
                'success': False,
                'message': str(e),
                'user': None,
                'token': None
            }
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            return {
                'success': False,
                'message': 'Email already registered',
                'user': None,
                'token': None
            }
        
        if User.query.filter_by(username=username).first():
            return {
                'success': False,
                'message': 'Username already taken',
                'user': None,
                'token': None
            }
        
        # Create new user
        user = User(username=username, email=email)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Create JWT token (identity must be a string)
        access_token = create_access_token(
            identity=str(user.id),
            expires_delta=timedelta(days=30)
        )
        
        # Send welcome email (optional - don't fail if email fails)
        try:
            from utils.email import send_welcome_email
            send_welcome_email(user.email, user.username)
        except Exception as e:
            print(f"Failed to send welcome email: {e}")
        
        return {
            'success': True,
            'message': f'Account created successfully! Welcome, {user.username}!',
            'user': user,
            'token': access_token
        }
    
    @staticmethod
    def login_user(email, password):
        """
        Authenticate user and return token.
        
        Returns:
            dict: {'success': bool, 'message': str, 'user': User, 'token': str}
        """
        # Validate email format
        try:
            email = Validator.validate_email(email)
        except ValidationError as e:
            return {
                'success': False,
                'message': str(e),
                'user': None,
                'token': None
            }
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            return {
                'success': False,
                'message': 'Invalid email or password',
                'user': None,
                'token': None
            }
        
        # Create JWT token (identity must be a string)
        access_token = create_access_token(
            identity=str(user.id),
            expires_delta=timedelta(days=30)
        )
        
        return {
            'success': True,
            'message': f'Welcome back, {user.username}!',
            'user': user,
            'token': access_token
        }
    
    @staticmethod
    def change_password(user, current_password, new_password):
        """
        Change user password.
        
        Returns:
            dict: {'success': bool, 'message': str}
        """
        # Validate new password
        try:
            new_password = Validator.validate_password(new_password)
        except ValidationError as e:
            return {
                'success': False,
                'message': str(e)
            }
        
        if not user.check_password(current_password):
            return {
                'success': False,
                'message': 'Current password is incorrect'
            }
        
        user.set_password(new_password)
        db.session.commit()
        
        return {
            'success': True,
            'message': 'Your password has been updated successfully!'
        }
    
    @staticmethod
    def request_password_reset(email):
        """
        Generate password reset token and send email.
        
        Returns:
            dict: {'success': bool, 'message': str, 'token': str, 'user': User}
        """
        user = User.query.filter_by(email=email).first()
        
        if user:
            token = user.generate_reset_token()
            
            # Try to send email
            try:
                from utils.email import send_password_reset_email
                from flask import url_for
                reset_url = url_for('auth.reset_password', token=token, _external=True)
                send_password_reset_email(user.email, reset_url, user.username)
                email_sent = True
            except Exception as e:
                print(f"Failed to send password reset email: {e}")
                email_sent = False
            
            return {
                'success': True,
                'message': f'Password reset instructions have been sent to {email}.',
                'token': token,
                'user': user,
                'email_sent': email_sent
            }
        
        # Don't reveal if email exists (security best practice)
        return {
            'success': True,
            'message': f'If an account exists with {email}, password reset instructions have been sent.',
            'token': None,
            'user': None,
            'email_sent': False
        }
    
    @staticmethod
    def reset_password(token, new_password):
        """
        Reset password using token.
        
        Returns:
            dict: {'success': bool, 'message': str}
        """
        user = User.verify_reset_token(token)
        
        if not user:
            return {
                'success': False,
                'message': 'Invalid or expired password reset link'
            }
        
        user.set_password(new_password)
        db.session.commit()
        
        return {
            'success': True,
            'message': 'Your password has been reset successfully! You can now log in.'
        }
    
    @staticmethod
    def delete_account(user):
        """
        Delete user account and all associated data.
        
        Returns:
            dict: {'success': bool, 'message': str}
        """
        username = user.username
        email = user.email
        
        # Delete user (cascade will delete all interactions)
        db.session.delete(user)
        db.session.commit()
        
        # Send confirmation email
        try:
            from utils.email import send_account_deleted_email
            send_account_deleted_email(email, username)
        except Exception as e:
            print(f"Failed to send account deletion email: {e}")
        
        return {
            'success': True,
            'message': f'Account "{username}" has been permanently deleted.'
        }
    
    @staticmethod
    def get_user_by_id(user_id):
        """Get user by ID (handles both int and str)."""
        if isinstance(user_id, str):
            user_id = int(user_id)
        return User.query.get(user_id)
    
    @staticmethod
    def user_to_dict(user):
        """Convert user to dictionary for API responses."""
        return {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'created_at': user.created_at.isoformat() if hasattr(user, 'created_at') else None
        }
