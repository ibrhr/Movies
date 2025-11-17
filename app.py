"""
Flask application factory and initialization.
"""
import os
import logging
import json
from datetime import datetime
from flask import Flask, request, g
from flask_migrate import Migrate
from flask_cors import CORS
from flask_jwt_extended import JWTManager
# Flask-Limiter removed per request
from flask_talisman import Talisman
# Flask-Caching removed per request

from models import db, User
from config import config

# Initialize extensions
migrate = Migrate()
jwt = JWTManager()
talisman = Talisman()


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add request context if available
        try:
            if hasattr(g, 'request_id'):
                log_entry['request_id'] = g.request_id
        except RuntimeError:
            # Outside of application context
            pass
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry)


def setup_logging(app):
    """Setup structured JSON logging."""
    # Remove default handlers
    for handler in app.logger.handlers[:]:
        app.logger.removeHandler(handler)
    
    # Create JSON formatter
    json_formatter = JSONFormatter()
    
    # Console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(json_formatter)
    console_handler.setLevel(logging.INFO)
    
    # File handler for production
    if not app.debug:
        file_handler = logging.FileHandler('logs/app.log')
        file_handler.setFormatter(json_formatter)
        file_handler.setLevel(logging.WARNING)
        app.logger.addHandler(file_handler)
    
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.INFO)
    
    # Log application startup
    app.logger.info("Application started", extra={
        'extra_fields': {
            'debug': app.debug,
            'testing': app.testing
        }
    })


def log_request_response(app):
    """Log requests and responses."""
    @app.before_request
    def log_request():
        g.request_start_time = datetime.utcnow()
        g.request_id = f"{datetime.utcnow().timestamp()}-{os.getpid()}"
        
        app.logger.info("Request started", extra={
            'extra_fields': {
                'method': request.method,
                'url': request.url,
                'remote_addr': request.remote_addr,
                'user_agent': request.headers.get('User-Agent'),
                'content_length': request.content_length,
            }
        })
    
    @app.after_request
    def log_response(response):
        duration = (datetime.utcnow() - g.request_start_time).total_seconds() * 1000
        
        # Safely get content length - handle direct passthrough mode for static files
        try:
            content_length = len(response.get_data()) if response.get_data() else 0
        except RuntimeError:
            # Response is in direct passthrough mode (e.g., static files)
            content_length = response.content_length or 0
        
        app.logger.info("Request completed", extra={
            'extra_fields': {
                'status_code': response.status_code,
                'duration_ms': round(duration, 2),
                'content_length': content_length,
            }
        })
        
        return response


def create_app(config_name='development'):
    """Application factory pattern."""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Setup structured logging
    setup_logging(app)
    log_request_response(app)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    # limiter and cache initialization removed per request
    
    # Initialize security headers (Talisman)
    # Disable Talisman in development, enable in production with proper CSP
    if app.debug:
        # In development, disable Talisman completely to avoid CSP issues
        pass
    else:
        # Configure CSP for production
        csp = {
            'default-src': "'self'",
            # Allow Tailwind's CDN + common CDNs used for icons/fonts
            'script-src': "'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net https://cdn.tailwindcss.com",
            'style-src': "'self' 'unsafe-inline' https://fonts.googleapis.com",
            'font-src': "'self' https://fonts.gstatic.com",
            'img-src': "'self' data: https: http:",
            'connect-src': "'self' https://openrouter.ai",
        }
        
        talisman.init_app(app, 
            content_security_policy=csp,
            content_security_policy_nonce_in=['script-src', 'style-src']
        )
    
    # Enable CORS for API access (mobile apps using JSON responses)
    # Web browsers using cookies don't need CORS (same-origin)
    # Configure origins for production: os.getenv('ALLOWED_ORIGINS', '*').split(',')
    CORS(app, resources={
        r"/movies/*": {
            "origins": "*",  # TODO: Configure for production
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        },
        r"/auth/*": {
            "origins": "*",  # TODO: Configure for production
            "methods": ["POST", "GET", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })
    
    # JWT user loader callback
    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data["sub"]
        # Identity is stored as string, convert to int for query
        user_id = int(identity) if isinstance(identity, str) else identity
        return User.query.filter_by(id=user_id).first()
    
    # Context processor to make current_user available in templates
    @app.context_processor
    def inject_current_user():
        from utils.auth import get_current_user
        return {'current_user': get_current_user()}
    
    # Register blueprints
    from routes import auth, movies, main
    app.register_blueprint(auth.bp)
    app.register_blueprint(movies.bp)
    app.register_blueprint(main.bp)
    
    # Register error handlers
    from utils.errors import register_error_handlers
    register_error_handlers(app)
    
    # Create tables if they don't exist
    with app.app_context():
        db.create_all()
    
    return app
