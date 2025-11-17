"""
SQLAlchemy database models.
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from flask import current_app

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for authentication."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    interactions = db.relationship('Interaction', backref='user', lazy='dynamic', 
                                   cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='user', lazy='dynamic',
                             cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash."""
        return check_password_hash(self.password_hash, password)
    
    def generate_reset_token(self):
        """Generate a password reset token."""
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return serializer.dumps(self.email, salt='password-reset-salt')
    
    @staticmethod
    def verify_reset_token(token, expiration=3600):
        """Verify password reset token (default 1 hour expiration)."""
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            email = serializer.loads(token, salt='password-reset-salt', max_age=expiration)
        except:
            return None
        return User.query.filter_by(email=email).first()
    
    def __repr__(self):
        return f'<User {self.username}>'


class Movie(db.Model):
    """Movie model - maps to existing movies table."""
    __tablename__ = 'movies'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False, index=True)  # For search queries
    overview = db.Column(db.Text)
    release_date = db.Column(db.String(20), index=True)  # For year filtering
    vote_average = db.Column(db.Float, index=True)  # For rating sorting
    vote_count = db.Column(db.Integer, index=True)  # For popularity filtering
    popularity = db.Column(db.Float, index=True)  # For popularity sorting
    poster_path = db.Column(db.String(255))
    backdrop_path = db.Column(db.String(255))
    content_rating = db.Column(db.String(10), index=True)  # For content rating filtering
    
    # Relationships
    genres = db.relationship('Genre', backref='movie', lazy='dynamic')
    keywords = db.relationship('Keyword', backref='movie', lazy='dynamic')
    credits = db.relationship('Credit', backref='movie', lazy='dynamic')
    interactions = db.relationship('Interaction', backref='movie', lazy='dynamic')
    reviews = db.relationship('Review', backref='movie', lazy='dynamic')
    
    def get_poster_url(self, size='w500'):
        """Get full poster URL from TMDB."""
        if self.poster_path:
            return f"https://image.tmdb.org/t/p/{size}{self.poster_path}"
        return None
    
    def get_backdrop_url(self, size='w1280'):
        """Get full backdrop URL from TMDB."""
        if self.backdrop_path:
            return f"https://image.tmdb.org/t/p/{size}{self.backdrop_path}"
        return None
    
    def __repr__(self):
        return f'<Movie {self.title}>'


class Genre(db.Model):
    """Genre model - maps to existing genres table (no id column in original)."""
    __tablename__ = 'genres'
    __table_args__ = {'extend_existing': True}
    
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), primary_key=True)
    genre_id = db.Column(db.Integer, primary_key=True)
    genre_name = db.Column(db.String(50), index=True)  # For genre filtering
    
    def __repr__(self):
        return f'<Genre {self.genre_name}>'


class Keyword(db.Model):
    """Keyword model - maps to existing keywords table (no id column in original)."""
    __tablename__ = 'keywords'
    __table_args__ = {'extend_existing': True}
    
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), primary_key=True)
    keyword_id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(100))
    
    def __repr__(self):
        return f'<Keyword {self.keyword}>'


class Credit(db.Model):
    """Credit model - maps to existing credits table (no id column in original)."""
    __tablename__ = 'credits'
    __table_args__ = {'extend_existing': True}
    
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), primary_key=True)
    person_id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), primary_key=True)  # 'director' or 'actor'
    person_name = db.Column(db.String(255))
    character_name = db.Column(db.Text)  # Changed to Text to handle long character names
    credit_order = db.Column(db.Integer)
    
    def __repr__(self):
        return f'<Credit {self.person_name} - {self.role}>'


class Interaction(db.Model):
    """User interaction model (watch, rate, skip)."""
    __tablename__ = 'interactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), nullable=False, index=True)
    action = db.Column(db.String(20), nullable=False)  # 'watch', 'rate', 'skip'
    rating = db.Column(db.Float)  # 0-10 scale
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    watch_duration_minutes = db.Column(db.Integer)
    
    # Composite index for efficient queries
    __table_args__ = (
        db.Index('idx_interaction_user_movie', 'user_id', 'movie_id'),
        db.Index('idx_user_action_timestamp', 'user_id', 'action', 'timestamp'),
    )
    
    def __repr__(self):
        return f'<Interaction {self.user_id} - {self.action} - {self.movie_id}>'


class Review(db.Model):
    """User review/comment model."""
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), nullable=False, index=True)
    rating = db.Column(db.Integer)  # 1-10 scale (optional, can be None)
    review_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Helpful voting
    helpful_count = db.Column(db.Integer, default=0)
    not_helpful_count = db.Column(db.Integer, default=0)
    
    # Composite index for efficient queries
    __table_args__ = (
        db.Index('idx_movie_created', 'movie_id', 'created_at'),
        db.Index('idx_review_user_movie', 'user_id', 'movie_id'),
    )
    
    def __repr__(self):
        return f'<Review {self.user_id} - {self.movie_id}>'


class ReviewVote(db.Model):
    """Track user votes on reviews (helpful/not helpful)."""
    __tablename__ = 'review_votes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    review_id = db.Column(db.Integer, db.ForeignKey('reviews.id'), nullable=False)
    is_helpful = db.Column(db.Boolean, nullable=False)  # True=helpful, False=not helpful
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensure user can only vote once per review
    __table_args__ = (
        db.UniqueConstraint('user_id', 'review_id', name='unique_user_review_vote'),
    )
    
    def __repr__(self):
        return f'<ReviewVote {self.user_id} - {self.review_id}>'


class MovieMetadata(db.Model):
    """Movie metadata from movie_metadata.json - now in database."""
    __tablename__ = 'movie_metadata'
    
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), primary_key=True)
    genres = db.Column(db.JSON)  # Array of genre strings: ["Action", "Drama"]
    release_date = db.Column(db.String(20))  # YYYY-MM-DD format
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<MovieMetadata {self.movie_id}>'


class EmbeddingMetadata(db.Model):
    """Embedding index mapping - tracks which movies have embeddings."""
    __tablename__ = 'embedding_metadata'
    
    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), nullable=False, unique=True, index=True)
    title = db.Column(db.String(255), nullable=False)
    embedding_index = db.Column(db.Integer, nullable=False, index=True)  # Index in embeddings.npy
    model = db.Column(db.String(100), default='openai/text-embedding-3-small')
    dimension = db.Column(db.Integer, default=1536)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<EmbeddingMetadata {self.movie_id}>'


class EmbeddingConfig(db.Model):
    """Global embedding configuration (one record)."""
    __tablename__ = 'embedding_config'
    
    id = db.Column(db.Integer, primary_key=True, default=1)
    model = db.Column(db.String(100), default='openai/text-embedding-3-small')
    dimension = db.Column(db.Integer, default=1536)
    total_embeddings = db.Column(db.Integer, default=0)
    embeddings_file = db.Column(db.String(255), default='embeddings.npy')
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<EmbeddingConfig {self.model} - {self.dimension}d>'
