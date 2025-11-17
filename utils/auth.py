"""
Authentication decorators for unified routes.
Works with both JWT tokens (headers or cookies).
"""
from functools import wraps
from flask import redirect, url_for, flash
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from flask_jwt_extended.exceptions import NoAuthorizationError
from jwt.exceptions import ExpiredSignatureError

from utils.responses import wants_json, error_response
from services.auth_service import AuthService


def login_required(optional=False):
    """
    Decorator for routes requiring authentication.
    Works with both web (cookies) and API (headers).
    
    Args:
        optional: If True, authentication is optional (user may be None)
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                # Verify JWT token (from header or cookie)
                verify_jwt_in_request(optional=optional)
                
                # Get user ID from token
                user_id = get_jwt_identity()
                
                if user_id:
                    # Get user object and pass it to route
                    user = AuthService.get_user_by_id(user_id)
                    if not user:
                        if optional:
                            return fn(*args, current_user=None, **kwargs)
                        
                        if wants_json():
                            return error_response('User not found', status_code=401)
                        
                        flash('Your session has expired. Please log in again.', 'warning')
                        return redirect(url_for('auth.login'))
                    
                    return fn(*args, current_user=user, **kwargs)
                
                elif optional:
                    return fn(*args, current_user=None, **kwargs)
                
                else:
                    if wants_json():
                        return error_response('Authentication required', status_code=401)
                    
                    flash('Please log in to access this page.', 'info')
                    return redirect(url_for('auth.login'))
            
            except NoAuthorizationError:
                if optional:
                    return fn(*args, current_user=None, **kwargs)
                
                if wants_json():
                    return error_response('Missing authorization token', status_code=401)
                
                flash('Please log in to access this page.', 'info')
                return redirect(url_for('auth.login'))
            
            except ExpiredSignatureError:
                if optional:
                    return fn(*args, current_user=None, **kwargs)
                
                if wants_json():
                    return error_response('Token has expired', status_code=401)
                
                flash('Your session has expired. Please log in again.', 'warning')
                return redirect(url_for('auth.login'))
            
            except Exception as e:
                # Log the actual error for debugging
                from flask import current_app
                current_app.logger.error(f'Authentication exception: {type(e).__name__}: {str(e)}', exc_info=True)
                
                if optional:
                    return fn(*args, current_user=None, **kwargs)
                
                if wants_json():
                    return error_response(f'Authentication error: {str(e)}', status_code=401)
                
                flash('Authentication error. Please log in again.', 'danger')
                return redirect(url_for('auth.login'))
        
        return wrapper
    return decorator


def get_current_user_id():
    """
    Get current user ID from JWT token (if authenticated).
    Returns None if not authenticated.
    """
    try:
        verify_jwt_in_request(optional=True)
        return get_jwt_identity()
    except:
        return None


def get_current_user():
    """
    Get current user object from JWT token (if authenticated).
    Returns None if not authenticated.
    """
    user_id = get_current_user_id()
    if user_id:
        return AuthService.get_user_by_id(user_id)
    return None
