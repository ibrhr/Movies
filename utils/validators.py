"""
Input validation utilities.
"""
import re
from flask import request
from utils.errors import ValidationError


class Validator:
    """Request validation helper."""
    
    @staticmethod
    def validate_pagination(default_page=1, default_per_page=20, max_per_page=100):
        """
        Validate pagination parameters from request args.
        
        Returns:
            tuple: (page, per_page)
        
        Raises:
            ValidationError: If parameters are invalid
        """
        page = request.args.get('page', default_page, type=int)
        per_page = request.args.get('per_page', default_per_page, type=int)
        
        if page < 1:
            raise ValidationError('Page must be >= 1')
        if per_page < 1:
            raise ValidationError('Per page must be >= 1')
        if per_page > max_per_page:
            raise ValidationError(f'Per page cannot exceed {max_per_page}')
        
        return page, per_page
    
    @staticmethod
    def validate_rating(rating):
        """
        Validate movie rating (0-10).
        
        Args:
            rating: Rating value to validate
        
        Returns:
            int: Validated rating
        
        Raises:
            ValidationError: If rating is invalid
        """
        if rating is None:
            raise ValidationError('Rating is required')
        
        try:
            rating = int(rating)
        except (ValueError, TypeError):
            raise ValidationError('Rating must be a number')
        
        if not 0 <= rating <= 10:
            raise ValidationError('Rating must be between 0 and 10')
        
        return rating
    
    @staticmethod
    def validate_email(email):
        """
        Validate email format.
        
        Args:
            email: Email address to validate
        
        Returns:
            str: Lowercase email address
        
        Raises:
            ValidationError: If email format is invalid
        """
        if not email:
            raise ValidationError('Email is required')
        
        # Basic email regex pattern
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            raise ValidationError('Invalid email format')
        
        return email.lower().strip()
    
    @staticmethod
    def validate_username(username):
        """
        Validate username (3-20 chars, alphanumeric + underscore).
        
        Args:
            username: Username to validate
        
        Returns:
            str: Validated username
        
        Raises:
            ValidationError: If username is invalid
        """
        if not username:
            raise ValidationError('Username is required')
        
        username = username.strip()
        
        if len(username) < 3:
            raise ValidationError('Username must be at least 3 characters')
        if len(username) > 20:
            raise ValidationError('Username cannot exceed 20 characters')
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValidationError('Username can only contain letters, numbers, and underscores')
        
        return username
    
    @staticmethod
    def validate_password(password):
        """
        Validate password strength.
        
        Args:
            password: Password to validate
        
        Returns:
            str: Validated password
        
        Raises:
            ValidationError: If password is too weak
        """
        if not password:
            raise ValidationError('Password is required')
        
        if len(password) < 6:
            raise ValidationError('Password must be at least 6 characters')
        
        if len(password) > 128:
            raise ValidationError('Password is too long')
        
        return password
    
    @staticmethod
    def validate_review_content(content):
        """
        Validate review/comment content.
        
        Args:
            content: Review text to validate
        
        Returns:
            str: Validated and stripped content
        
        Raises:
            ValidationError: If content is invalid
        """
        if not content:
            raise ValidationError('Review content cannot be empty')
        
        content = content.strip()
        
        if len(content) < 10:
            raise ValidationError('Review must be at least 10 characters')
        
        if len(content) > 5000:
            raise ValidationError('Review is too long (max 5000 characters)')
        
        return content
    
    @staticmethod
    def validate_search_query(query, min_length=1, max_length=200):
        """
        Validate search query.
        
        Args:
            query: Search query string
            min_length: Minimum query length
            max_length: Maximum query length
        
        Returns:
            str: Validated query
        
        Raises:
            ValidationError: If query is invalid
        """
        if not query:
            raise ValidationError('Search query is required')
        
        query = query.strip()
        
        if len(query) < min_length:
            raise ValidationError(f'Search query must be at least {min_length} character(s)')
        
        if len(query) > max_length:
            raise ValidationError(f'Search query is too long (max {max_length} characters)')
        
        return query
    
    @staticmethod
    def validate_year(year):
        """
        Validate movie release year.
        
        Args:
            year: Year to validate
        
        Returns:
            int: Validated year
        
        Raises:
            ValidationError: If year is invalid
        """
        if year is None:
            return None
        
        try:
            year = int(year)
        except (ValueError, TypeError):
            raise ValidationError('Year must be a number')
        
        if year < 1800 or year > 2100:
            raise ValidationError('Year must be between 1800 and 2100')
        
        return year
    
    @staticmethod
    def validate_sort_option(sort_by, allowed_options):
        """
        Validate sort parameter.
        
        Args:
            sort_by: Sort option to validate
            allowed_options: List of allowed sort options
        
        Returns:
            str: Validated sort option
        
        Raises:
            ValidationError: If sort option is invalid
        """
        if sort_by not in allowed_options:
            raise ValidationError(
                f'Invalid sort option. Allowed: {", ".join(allowed_options)}'
            )
        
        return sort_by
