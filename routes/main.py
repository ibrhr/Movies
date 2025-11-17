"""
Main routes (homepage, etc.).
"""
from flask import Blueprint, render_template
from utils.auth import get_current_user
from models import Movie, Interaction

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    """Homepage showing popular movies."""
    # Get popular movies (sorted by popularity or rating)
    popular_movies = Movie.query.order_by(Movie.popularity.desc()).limit(20).all()
    
    # Get user's watchlist movie IDs if authenticated
    current_user = get_current_user()
    watchlist_movie_ids = set()
    if current_user:
        watchlist_interactions = Interaction.query.filter_by(
            user_id=current_user.id,
            action='watchlist'
        ).all()
        watchlist_movie_ids = {interaction.movie_id for interaction in watchlist_interactions}
    
    return render_template('index.html', 
                         title='Home',
                         movies=popular_movies,
                         watchlist_movie_ids=watchlist_movie_ids)


@bp.route('/about')
def about():
    """About page."""
    return render_template('about.html', title='About')


@bp.route('/health')
def health():
    """Health check endpoint for Docker and cloud monitoring."""
    from models import db
    try:
        # Test database connection
        db.session.execute(db.text('SELECT 1'))
        return {
            'status': 'healthy',
            'database': 'connected'
        }, 200
    except Exception as e:
        return {
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e)
        }, 503
