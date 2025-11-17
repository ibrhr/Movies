"""
Service layer for business logic.
Separates business logic from route handlers.
"""
from .auth_service import AuthService
from .movie_service import MovieService
from .recommendation_service import RecommendationService

__all__ = ['AuthService', 'MovieService', 'RecommendationService']
