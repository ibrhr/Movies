"""
Standardized error handling for both web and API.
"""
from flask import jsonify, render_template, request
from werkzeug.exceptions import HTTPException


class AppError(Exception):
    """Base application error."""
    status_code = 400
    
    def __init__(self, message, status_code=None, payload=None):
        super().__init__()
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload or {}
    
    def to_dict(self):
        """Convert error to dictionary for JSON responses."""
        rv = dict(self.payload)
        rv['message'] = self.message
        rv['success'] = False
        rv['error_type'] = self.__class__.__name__
        return rv


class ValidationError(AppError):
    """Validation error (400)."""
    status_code = 400


class AuthenticationError(AppError):
    """Authentication error (401)."""
    status_code = 401


class AuthorizationError(AppError):
    """Authorization/permission error (403)."""
    status_code = 403


class NotFoundError(AppError):
    """Resource not found (404)."""
    status_code = 404


class ConflictError(AppError):
    """Resource conflict, e.g., duplicate email (409)."""
    status_code = 409


class RateLimitError(AppError):
    """Rate limit exceeded (429)."""
    status_code = 429


class ServerError(AppError):
    """Internal server error (500)."""
    status_code = 500


def wants_json():
    """Check if the client wants JSON response."""
    # Check Accept header
    best = request.accept_mimetypes.best_match(['application/json', 'text/html'])
    return (
        best == 'application/json' or
        (best and request.accept_mimetypes[best] > request.accept_mimetypes['text/html']) or
        request.path.startswith('/api/') or
        request.is_json or
        request.args.get('format') == 'json'
    )


def register_error_handlers(app):
    """Register error handlers with Flask app."""
    
    @app.errorhandler(AppError)
    def handle_app_error(error):
        """Handle custom application errors."""
        # Log errors appropriately based on status code
        if error.status_code >= 500:
            app.logger.error(f"Application error: {error.message}", extra={
                'extra_fields': {
                    'status_code': error.status_code,
                    'error_type': error.__class__.__name__,
                    'payload': error.payload
                }
            })
        elif error.status_code >= 400:
            app.logger.warning(f"Client error: {error.message}", extra={
                'extra_fields': {
                    'status_code': error.status_code,
                    'error_type': error.__class__.__name__,
                    'payload': error.payload
                }
            })
        
        if wants_json():
            response = jsonify(error.to_dict())
            response.status_code = error.status_code
            return response
        
        # For web requests, render error template
        return render_template('errors/error.html',
                             error_message=error.message,
                             status_code=error.status_code), error.status_code
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 Not Found."""
        if wants_json():
            return jsonify({
                'success': False,
                'message': 'Resource not found',
                'error_type': 'NotFoundError'
            }), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(403)
    def forbidden(error):
        """Handle 403 Forbidden."""
        if wants_json():
            return jsonify({
                'success': False,
                'message': 'Access forbidden',
                'error_type': 'ForbiddenError'
            }), 403
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server Error."""
        app.logger.error("Internal server error", extra={
            'extra_fields': {
                'error': str(error),
                'status_code': 500
            }
        })
        if wants_json():
            return jsonify({
                'success': False,
                'message': 'Internal server error',
                'error_type': 'ServerError'
            }), 500
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle standard HTTP exceptions."""
        if wants_json():
            return jsonify({
                'success': False,
                'message': error.description or str(error),
                'error_type': error.name
            }), error.code
        
        # Try to render specific error template, fallback to generic
        try:
            return render_template(f'errors/{error.code}.html'), error.code
        except:
            return render_template('errors/error.html',
                                 error_message=error.description,
                                 status_code=error.code), error.code
