"""
Flask application configuration.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project root directory (where config.py is located)
basedir = Path(__file__).parent.absolute()


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database configuration - PostgreSQL required
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError(
            "DATABASE_URL environment variable is required. "
            "Please set it in your .env file to your PostgreSQL connection string. "
            "Example: postgresql://user:password@localhost:5432/movies_db"
        )
    
    # Handle Heroku/Railway postgres:// URLs (needs postgresql://)
    if SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Connection pooling for production databases
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.environ.get('DB_POOL_SIZE', 10)),
        'pool_recycle': 3600,  # Recycle connections after 1 hour
        'pool_pre_ping': True,  # Verify connections before using
        'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', 20)),
    }
    
    # JWT Configuration - supports both web (cookies) and API (headers)
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key-change-in-production'
    JWT_TOKEN_LOCATION = ['headers', 'cookies']  # Support both authentication methods
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    
    # Cookie configuration for web browsers
    JWT_COOKIE_SECURE = False  # Set to True in production with HTTPS
    JWT_COOKIE_CSRF_PROTECT = False  # Disabled - using SameSite for CSRF protection
    JWT_ACCESS_COOKIE_NAME = 'access_token_cookie'
    JWT_COOKIE_SAMESITE = 'Lax'  # Protects against CSRF attacks
    JWT_SESSION_COOKIE = False  # Persistent cookies (not session-only)
    
    # Embeddings (in project root data directory)
    EMBEDDINGS_PATH = basedir / "data" / "embeddings.npy"
    # Note: Embedding metadata now stored in PostgreSQL (EmbeddingMetadata, MovieMetadata tables)
    
    # Pagination
    MOVIES_PER_PAGE = 20
    
    # Recommendation settings
    DEFAULT_LAMBDA = 0.7
    MAX_RECOMMENDATIONS = 20


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY')  # Must be set in production
    
    # Production should use PostgreSQL
    PREFERRED_URL_SCHEME = 'https'
    
    # JWT security for production
    JWT_COOKIE_SECURE = True  # Require HTTPS for cookies
    JWT_COOKIE_CSRF_PROTECT = False  # Disabled - using SameSite for CSRF protection


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
