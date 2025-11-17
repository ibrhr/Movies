"""
Movie routes (browse, detail, interact, recommendations).
Unified routes supporting both web UI and API.
"""
from flask import Blueprint, render_template, redirect, url_for, request, current_app, abort, flash
from datetime import datetime

from models import db, Movie, Genre, Credit, Interaction, Review, ReviewVote
from forms import RatingForm
from services.movie_service import MovieService
from services.recommendation_service import RecommendationService
from utils.auth import login_required, get_current_user
from utils.responses import wants_json, success_response, error_response, unified_response
from utils.errors import ValidationError

bp = Blueprint('movies', __name__, url_prefix='/movies')


@bp.route('/')
@login_required(optional=True)
def browse(current_user):
    """Browse all movies with pagination and filters - unified for web and API."""
    from flask import current_app
    from utils.validators import Validator
    
    # Validate pagination parameters
    try:
        page, per_page = Validator.validate_pagination()
    except ValidationError as e:
        if wants_json():
            return error_response(str(e), status_code=400)
        flash(str(e), 'error')
        return redirect(url_for('movies.browse'))
    
    # Get movies (caching removed)
    result = MovieService.get_movies(
        page=page,
        per_page=per_page,
        genre=request.args.get('genre'),
        search=request.args.get('search'),
        sort_by=request.args.get('sort', 'popularity'),
        min_rating=request.args.get('min_rating', type=float),
        year_from=request.args.get('year_from', type=int),
        year_to=request.args.get('year_to', type=int),
        min_votes=request.args.get('min_votes', type=int),
        content_rating=request.args.get('content_rating'),
        hide_watched=request.args.get('hide_watched', 'false').lower() == 'true',
        user_id=current_user.id if current_user else None
    )
    
    # Get user's watchlist for display
    watchlist_movie_ids = set()
    if current_user:
        watchlist_interactions = Interaction.query.filter_by(
            user_id=current_user.id,
            action='watchlist'
        ).all()
        watchlist_movie_ids = {interaction.movie_id for interaction in watchlist_interactions}
    
    # Check if any filters are active
    filters_active = any([
        request.args.get('min_rating'),
        request.args.get('year_from'),
        request.args.get('year_to'),
        request.args.get('min_votes'),
        request.args.get('content_rating'),
        request.args.get('hide_watched') == 'true'
    ])
    
    # For JSON responses
    if wants_json():
        movies_data = [MovieService.movie_to_dict(m) for m in result['movies']]
        return unified_response({
            'success': True,
            'movies': movies_data,
            'pagination': result['pagination'],
            'genres': result['genres'],
            'content_ratings': result['content_ratings']
        })
    
    # For HTML responses
    return render_template('movies/browse.html',
                         title='Browse Movies',
                         movies=result['pagination_obj'],
                         genres=result['genres'],
                         selected_genre=request.args.get('genre'),
                         sort_by=request.args.get('sort', 'popularity'),
                         watchlist_movie_ids=watchlist_movie_ids,
                         content_ratings=result['content_ratings'],
                         min_rating=request.args.get('min_rating', type=float),
                         year_from=request.args.get('year_from', type=int),
                         year_to=request.args.get('year_to', type=int),
                         min_votes=request.args.get('min_votes', type=int),
                         content_rating_filter=request.args.get('content_rating'),
                         hide_watched=request.args.get('hide_watched', 'false').lower() == 'true',
                         filters_active=filters_active)


@bp.route('/search')
@login_required(optional=True)
def search(current_user):
    """Search movies by title, overview, cast, or director - unified for web and API."""
    from utils.validators import Validator
    
    # Validate search query
    try:
        query = Validator.validate_search_query(request.args.get('q', '').strip())
    except ValidationError as e:
        if wants_json():
            return error_response(str(e), status_code=400)
        flash(str(e), 'error')
        return redirect(url_for('movies.browse'))
    
    # Validate pagination
    try:
        page, per_page = Validator.validate_pagination()
    except ValidationError as e:
        if wants_json():
            return error_response(str(e), status_code=400)
        flash(str(e), 'error')
        return redirect(url_for('movies.search', q=query))
    
    sort_by = request.args.get('sort', 'relevance')
    hide_watched = request.args.get('hide_watched', 'false').lower() == 'true'
    
    # Use MovieService for search
    result = MovieService.get_movies(
        page=page,
        per_page=per_page,
        search=query,
        sort_by=sort_by,
        hide_watched=hide_watched,
        user_id=current_user.id if current_user else None
    )
    
    # Use MovieService for search
    result = MovieService.get_movies(
        page=page,
        per_page=min(per_page, 100),
        search=query,
        sort_by=sort_by,
        hide_watched=hide_watched,
        user_id=current_user.id if current_user else None
    )
    
    # Get user's watchlist for display
    watchlist_movie_ids = set()
    if current_user:
        watchlist_interactions = Interaction.query.filter_by(
            user_id=current_user.id,
            action='watchlist'
        ).all()
        watchlist_movie_ids = {interaction.movie_id for interaction in watchlist_interactions}
    
    # For JSON responses
    if wants_json():
        movies_data = [MovieService.movie_to_dict(m) for m in result['movies']]
        return unified_response({
            'success': True,
            'query': query,
            'movies': movies_data,
            'pagination': result['pagination']
        })
    
    # For HTML responses
    return render_template('movies/search.html',
                         title=f'Search Results for "{query}"',
                         movies=result['pagination_obj'],
                         query=query,
                         sort_by=sort_by,
                         hide_watched=hide_watched,
                         watchlist_movie_ids=watchlist_movie_ids)


@bp.route('/<int:movie_id>')
@login_required(optional=True)
def detail(current_user, movie_id):
    """Movie detail page - unified for web and API."""
    # Use MovieService to get movie details (raises 404 if not found)
    result = MovieService.get_movie_details(
        movie_id=movie_id,
        user_id=current_user.id if current_user else None
    )
    
    movie = result['movie']
    
    # Similar movies are already included in result
    similar_movies = result.get('similar_movies', [])
    
    # Get reviews with pagination
    review_page = request.args.get('review_page', 1, type=int)
    per_page = 10
    reviews_query = Review.query.filter_by(movie_id=movie_id)\
        .order_by(Review.helpful_count.desc(), Review.created_at.desc())
    reviews = reviews_query.paginate(page=review_page, per_page=per_page, error_out=False)
    
    # Check if user has already reviewed
    user_review = None
    if current_user:
        user_review = Review.query.filter_by(
            user_id=current_user.id,
            movie_id=movie_id
        ).first()
    
    # For JSON responses
    if wants_json():
        movie_data = result.copy()
        movie_data['similar_movies'] = [MovieService.movie_to_dict(m) for m in similar_movies]
        movie_data['reviews'] = [{
            'id': r.id,
            'user_id': r.user_id,
            'username': r.user.username if r.user else None,
            'content': r.content,
            'rating': r.rating,
            'created_at': r.created_at.isoformat() if r.created_at else None,
            'helpful_count': r.helpful_count
        } for r in reviews.items]
        movie_data['reviews_pagination'] = {
            'page': reviews.page,
            'per_page': reviews.per_page,
            'total': reviews.total,
            'pages': reviews.pages
        }
        return unified_response(movie_data)
    
    # For HTML responses
    form = RatingForm()
    user_interaction = result.get('user_interaction') or {}
    
    return render_template('movies/detail.html',
                         title=movie.title,
                         movie=movie,
                         genres=result['genres'],
                         cast=result['cast'],
                         director=result['director'],
                         user_rating=user_interaction.get('rating'),
                         has_watched=user_interaction.get('watched', False),
                         in_watchlist=user_interaction.get('in_watchlist', False),
                         similar_movies=similar_movies,
                         reviews=reviews,
                         user_review=user_review,
                         form=form)


@bp.route('/<int:movie_id>/watch', methods=['POST'])
@login_required()
def watch(current_user, movie_id):
    """Mark movie as watched - unified for web and API."""
    result = MovieService.mark_watched(
        user_id=current_user.id,
        movie_id=movie_id
    )
    
    if not result['success']:
        return error_response(result['message'], 404 if 'not found' in result['message'].lower() else 400)
    
    if wants_json():
        return success_response(result['message'], {'watched': True})
    
    return redirect(url_for('movies.detail', movie_id=movie_id))


@bp.route('/<int:movie_id>/rate', methods=['POST'])
@login_required()
def rate(current_user, movie_id):
    """Rate a movie (automatically marks as watched) - unified for web and API."""
    # Get rating value from JSON or form
    if wants_json():
        data = request.get_json() or {}
        rating_value = data.get('rating')
        
        if rating_value is None:
            return error_response('Rating value is required', 400)
        
        try:
            rating_value = int(rating_value)
            if not (0 <= rating_value <= 10):
                return error_response('Rating must be between 0 and 10', 400)
        except (ValueError, TypeError):
            return error_response('Invalid rating value', 400)
    else:
        # For form requests, use WTForms validation
        form = RatingForm()
        if not form.validate_on_submit():
            return redirect(url_for('movies.detail', movie_id=movie_id))
        rating_value = form.rating.data
    
    # Use MovieService to rate movie
    result = MovieService.rate_movie(
        user_id=current_user.id,
        movie_id=movie_id,
        rating=rating_value
    )
    
    if not result['success']:
        return error_response(result['message'], 404 if 'not found' in result['message'].lower() else 400)
    
    if wants_json():
        return success_response(result['message'], {'rating': rating_value})
    
    return redirect(url_for('movies.detail', movie_id=movie_id))


@bp.route('/<int:movie_id>/skip', methods=['POST'])
@login_required()
def skip(current_user, movie_id):
    """Mark movie as skipped/not interested - unified for web and API."""
    result = MovieService.skip_movie(
        user_id=current_user.id,
        movie_id=movie_id
    )
    
    if not result['success']:
        return error_response(result['message'], 404 if 'not found' in result['message'].lower() else 400)
    
    if wants_json():
        return success_response(result['message'], {'skipped': True})
    
    return redirect(url_for('movies.browse'))


@bp.route('/watchlist')
@login_required()
def watchlist(current_user):
    """User's watchlist page - unified for web and API."""
    from utils.validators import Validator
    
    # Validate pagination
    try:
        page, per_page = Validator.validate_pagination()
    except ValidationError as e:
        if wants_json():
            return error_response(str(e), status_code=400)
        flash(str(e), 'error')
        return redirect(url_for('movies.watchlist'))
    
    # Use MovieService to get watchlist
    result = MovieService.get_watchlist(
        user_id=current_user.id,
        page=page,
        per_page=per_page
    )
    
    if wants_json():
        movies_data = [MovieService.movie_to_dict(m) for m in result['movies']]
        return unified_response({
            'success': True,
            'movies': movies_data,
            'pagination': result['pagination']
        })
    
    return render_template('movies/watchlist.html',
                         title='My Watchlist',
                         movies=result['pagination_obj'])


@bp.route('/watched')
@login_required()
def watched(current_user):
    """View all watched movies with sorting options - unified for web and API."""
    from utils.validators import Validator
    
    # Validate pagination
    try:
        page, per_page = Validator.validate_pagination()
    except ValidationError as e:
        if wants_json():
            return error_response(str(e), status_code=400)
        flash(str(e), 'error')
        return redirect(url_for('movies.watched'))
    
    sort_by = request.args.get('sort', 'watch_date')
    
    # Use MovieService to get watched movies
    result = MovieService.get_watched_movies(
        user_id=current_user.id,
        page=page,
        per_page=per_page,
        sort_by=sort_by
    )
    
    if wants_json():
        return unified_response({
            'success': True,
            'movies': result['movies'],  # Already includes watch_date and user_rating
            'pagination': result['pagination']
        })
    
    # Create a simple pagination object for the template
    class SimplePagination:
        def __init__(self, items, page, per_page, total):
            self.items = items
            self.page = page
            self.per_page = per_page
            self.total = total
            self.pages = (total + per_page - 1) // per_page if per_page > 0 else 0
            self.has_next = page < self.pages
            self.has_prev = page > 1
            self.prev_num = page - 1 if self.has_prev else None
            self.next_num = page + 1 if self.has_next else None
        
        def iter_pages(self, left_edge=1, right_edge=1, left_current=1, right_current=2):
            """Generator for page numbers (mimics Flask-SQLAlchemy pagination)."""
            last = 0
            for num in range(1, self.pages + 1):
                if num <= left_edge or \
                   (num > self.page - left_current - 1 and num < self.page + right_current) or \
                   num > self.pages - right_edge:
                    if last + 1 != num:
                        yield None
                    yield num
                    last = num
    
    pagination = SimplePagination(
        items=result['movies'],
        page=result['pagination']['page'],
        per_page=result['pagination']['per_page'],
        total=result['pagination']['total']
    )
    
    return render_template('movies/watched.html',
                         title='Watched Movies',
                         movies=pagination,
                         sort_by=sort_by)


@bp.route('/<int:movie_id>/watchlist/add', methods=['POST'])
@bp.route('/<int:movie_id>/add-to-watchlist', methods=['POST'])  # Legacy route
@login_required()
def add_to_watchlist(current_user, movie_id):
    """Add movie to watchlist - unified for web and API."""
    result = MovieService.add_to_watchlist(
        user_id=current_user.id,
        movie_id=movie_id
    )
    
    if not result['success']:
        return error_response(result['message'], 404 if 'not found' in result['message'].lower() else 400)
    
    if wants_json():
        return success_response(result['message'], {'in_watchlist': True})
    
    return redirect(request.referrer or url_for('movies.detail', movie_id=movie_id))


@bp.route('/<int:movie_id>/watchlist/remove', methods=['POST'])
@bp.route('/<int:movie_id>/remove-from-watchlist', methods=['POST'])  # Legacy route
@login_required()
def remove_from_watchlist(current_user, movie_id):
    """Remove movie from watchlist - unified for web and API."""
    result = MovieService.remove_from_watchlist(
        user_id=current_user.id,
        movie_id=movie_id
    )
    
    if not result['success']:
        return error_response(result['message'], 404 if 'not found' in result['message'].lower() else 400)
    
    if wants_json():
        return success_response(result['message'], {'in_watchlist': False})
    
    return redirect(request.referrer or url_for('movies.detail', movie_id=movie_id))


@bp.route('/recommendations')
@login_required()
def recommendations(current_user):
    """Get personalized recommendations - unified for web and API."""
    lambda_param = request.args.get('lambda', 0.7, type=float)
    lambda_param = max(0.0, min(1.0, lambda_param))
    
    num_recommendations = request.args.get('num', 10, type=int)
    num_recommendations = max(1, min(50, num_recommendations))
    
    # Use RecommendationService
    result = RecommendationService.get_recommendations(
        user_id=current_user.id,
        num_recommendations=num_recommendations,
        lambda_param=lambda_param
    )
    
    if not result['success']:
        if wants_json():
            return error_response(result['message'], 400)
        return redirect(url_for('main.index'))
    
    if wants_json():
        return unified_response({
            'success': True,
            'recommendations': result['recommendations'],
            'lambda_param': lambda_param
        })
    
    return render_template('movies/recommendations.html',
                         title='Recommendations',
                         recommendations=result['recommendations'],
                         lambda_param=lambda_param)


@bp.route('/profile')
@login_required()
def profile(current_user):
    """User profile page with stats - unified for web and API."""
    # Get user statistics using MovieService
    stats = MovieService.get_user_stats(user_id=current_user.id)
    
    if wants_json():
        return unified_response({
            'success': True,
            'stats': stats
        })
    
    return render_template('movies/profile.html',
                         title='My Profile',
                         watched=stats['watched'],
                         rated=stats['rated'],
                         skipped=stats['skipped'],
                         watchlist_count=stats['watchlist_count'],
                         avg_rating=stats['avg_rating'],
                         recent_interactions=stats['recent_interactions'])


@bp.route('/interaction/<int:interaction_id>/delete', methods=['POST'])
@login_required()
def delete_interaction(current_user, interaction_id):
    """Delete a specific interaction - unified for web and API."""
    interaction = Interaction.query.get_or_404(interaction_id)
    
    # Verify the interaction belongs to the current user
    if interaction.user_id != current_user.id:
        if wants_json():
            return error_response('You can only delete your own interactions', 403)
        return redirect(url_for('movies.profile'))
    
    movie_title = interaction.movie.title
    action = interaction.action
    
    db.session.delete(interaction)
    db.session.commit()
    
    if wants_json():
        return success_response(f'Deleted your "{action}" action for "{movie_title}"')
    
    return redirect(url_for('movies.profile'))


@bp.route('/clear-all-data', methods=['POST'])
@login_required()
def clear_all_data(current_user):
    """Clear all user activity data - unified for web and API."""
    # Delete all interactions for current user
    deleted_count = Interaction.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    
    if wants_json():
        return success_response(f'Successfully deleted all your activity data ({deleted_count} interactions)')
    
    return redirect(url_for('movies.profile'))


@bp.route('/smart-search')
def smart_search():
    """Smart search using semantic similarity with embeddings."""
    from flask import current_app
    from utils.validators import Validator
    
    # Get query - don't validate if empty, just show the search form
    query = request.args.get('q', '').strip()
    
    # Validate pagination
    try:
        page, per_page = Validator.validate_pagination(default_per_page=20)
    except ValidationError as e:
        page = 1
        per_page = 20
    
    # Get filter parameters
    content_rating = request.args.get('rating', '')
    year_from = request.args.get('year_from', type=int)
    year_to = request.args.get('year_to', type=int)
    
    current_app.logger.info(f"=== Smart Search Request ===")
    current_app.logger.info(f"Query: '{query}'")
    current_app.logger.info(f"Page: {page}")
    current_app.logger.info(f"Filters - Rating: {content_rating}, Year: {year_from}-{year_to}")
    
    # Get available content ratings for filter dropdown
    available_ratings = db.session.query(Movie.content_rating)\
                                  .filter(Movie.content_rating.isnot(None))\
                                  .distinct()\
                                  .order_by(Movie.content_rating)\
                                  .all()
    available_ratings = [r[0] for r in available_ratings]
    
    if not query:
        return render_template('movies/smart_search.html',
                             title='Smart Search',
                             query='',
                             movies=[],
                             page=page,
                             total_pages=0,
                             total_results=0,
                             available_ratings=available_ratings,
                             selected_rating=content_rating,
                             year_from=year_from,
                             year_to=year_to)
    
    # Validate query length
    if len(query) < 3:
        flash('Search query must be at least 3 characters long', 'error')
        return render_template('movies/smart_search.html',
                             title='Smart Search',
                             query=query,
                             movies=[],
                             page=page,
                             total_pages=0,
                             total_results=0,
                             available_ratings=available_ratings,
                             selected_rating=content_rating,
                             year_from=year_from,
                             year_to=year_to)
    
    try:
        # Import here to avoid circular imports
        import os
        import numpy as np
        import requests
        from pathlib import Path
        from models import EmbeddingMetadata
        
        # Load embeddings from file
        embeddings_file = current_app.config['EMBEDDINGS_PATH']
        
        current_app.logger.info(f"Embeddings file: {embeddings_file}")
        current_app.logger.info(f"Embeddings file exists: {embeddings_file.exists()}")
        
        if not embeddings_file.exists():
            current_app.logger.warning("Embeddings file missing")
            flash('Smart search is not available yet. Movie embeddings need to be generated first.', 'warning')
            return render_template('movies/smart_search.html',
                                 title='Smart Search',
                                 query=query,
                                 movies=[],
                                 page=page,
                                 total_pages=0,
                                 total_results=0,
                                 available_ratings=available_ratings,
                                 selected_rating=content_rating,
                                 year_from=year_from,
                                 year_to=year_to)
        
        # Load embeddings and index from database
        current_app.logger.info("Loading embeddings...")
        embeddings = np.load(embeddings_file)
        current_app.logger.info(f"Embeddings shape: {embeddings.shape}")
        
        # Get embedding metadata from database
        embedding_metas = EmbeddingMetadata.query.all()
        if not embedding_metas:
            current_app.logger.warning("No embedding metadata in database")
            flash('Smart search is not available yet. Please regenerate embeddings.', 'warning')
            return render_template('movies/smart_search.html',
                                 title='Smart Search',
                                 query=query,
                                 movies=[],
                                 page=page,
                                 total_pages=0,
                                 total_results=0,
                                 available_ratings=available_ratings,
                                 selected_rating=content_rating,
                                 year_from=year_from,
                                 year_to=year_to)
        
        # Create mapping: embedding_index -> movie_id
        idx_to_movie_id = {meta.embedding_index: meta.movie_id for meta in embedding_metas}
        current_app.logger.info(f"Movie index loaded: {len(idx_to_movie_id)} movies")
        
        # Get query embedding from OpenRouter
        api_key = os.getenv('OPENROUTER_API_KEY')
        current_app.logger.info(f"API Key present: {api_key is not None}")
        current_app.logger.info(f"API Key length: {len(api_key) if api_key else 0}")
        
        if not api_key:
            current_app.logger.error("OPENROUTER_API_KEY not found in environment")
            flash('Smart search is not configured properly. Missing API key.', 'error')
            return render_template('movies/smart_search.html',
                                 title='Smart Search',
                                 query=query,
                                 movies=[],
                                 page=page,
                                 total_pages=0,
                                 total_results=0,
                                 available_ratings=available_ratings,
                                 selected_rating=content_rating,
                                 year_from=year_from,
                                 year_to=year_to)
        
        current_app.logger.info("Sending request to OpenRouter API...")
        response = requests.post(
            'https://openrouter.ai/api/v1/embeddings',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'openai/text-embedding-3-small',
                'input': query
            },
            timeout=10
        )
        
        current_app.logger.info(f"OpenRouter API response status: {response.status_code}")
        
        if response.status_code != 200:
            current_app.logger.error(f"OpenRouter API error: {response.text}")
            flash('Smart search failed. Please try again.', 'error')
            return render_template('movies/smart_search.html',
                                 title='Smart Search',
                                 query=query,
                                 movies=[],
                                 page=page,
                                 total_pages=0,
                                 total_results=0,
                                 available_ratings=available_ratings,
                                 selected_rating=content_rating,
                                 year_from=year_from,
                                 year_to=year_to)
        
        query_embedding = np.array(response.json()['data'][0]['embedding'])
        current_app.logger.info(f"Query embedding shape: {query_embedding.shape}")
        
        # Calculate cosine similarity with all movie embeddings
        current_app.logger.info("Calculating similarities...")
        similarities = np.dot(embeddings, query_embedding) / (
            np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_embedding)
        )
        current_app.logger.info(f"Similarities calculated: min={similarities.min():.4f}, max={similarities.max():.4f}")
        
        # Get top results (iterate until we have enough valid movies)
        all_indices = np.argsort(similarities)[::-1]
        
        # Get movie IDs from index, filtering out indices not in our mapping
        movie_ids = []
        for idx in all_indices:
            idx_int = int(idx)
            if idx_int in idx_to_movie_id:
                movie_ids.append(idx_to_movie_id[idx_int])
                if len(movie_ids) >= 40:  # Limit to top 40 valid movies
                    break
        
        current_app.logger.info(f"Found {len(movie_ids)} valid movies from embeddings")
        current_app.logger.info(f"Top 5 movie IDs: {movie_ids[:5]}")
        
        # Apply filters before pagination
        filtered_movie_ids = []
        for movie_id in movie_ids:
            movie = Movie.query.get(movie_id)
            if not movie:
                continue
            
            # Apply content rating filter
            if content_rating and movie.content_rating != content_rating:
                continue
            
            # Apply year filters
            if movie.release_date:
                movie_year = int(movie.release_date[:4]) if len(movie.release_date) >= 4 else None
                if movie_year:
                    if year_from and movie_year < year_from:
                        continue
                    if year_to and movie_year > year_to:
                        continue
            
            filtered_movie_ids.append(movie_id)
        
        current_app.logger.info(f"After filters: {len(filtered_movie_ids)} movies (from {len(movie_ids)})")
        
        # Paginate results
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_movie_ids = filtered_movie_ids[start_idx:end_idx]
        
        # Fetch movies from database
        movies = Movie.query.filter(Movie.id.in_(page_movie_ids)).all()
        
        # Sort by similarity (maintain order)
        movies_dict = {m.id: m for m in movies}
        sorted_movies = [movies_dict[mid] for mid in page_movie_ids if mid in movies_dict]
        
        # Add similarity scores to movies for display
        # Create reverse mapping: movie_id -> embedding_index
        movie_id_to_idx = {movie_id: idx for idx, movie_id in idx_to_movie_id.items()}
        for movie in sorted_movies:
            if movie.id in movie_id_to_idx:
                embedding_idx = movie_id_to_idx[movie.id]
                movie.similarity_score = float(similarities[embedding_idx])
            else:
                movie.similarity_score = 0.0
        
        total_results = len(filtered_movie_ids)
        total_pages = (total_results + per_page - 1) // per_page
        
        current_app.logger.info(f"Returning {len(sorted_movies)} movies for page {page}/{total_pages}")
        current_app.logger.info("=== Smart Search Complete ===")
        
        return render_template('movies/smart_search.html',
                             title='Smart Search',
                             query=query,
                             movies=sorted_movies,
                             page=page,
                             total_pages=total_pages,
                             total_results=total_results,
                             available_ratings=available_ratings,
                             selected_rating=content_rating,
                             year_from=year_from,
                             year_to=year_to)
        
    except Exception as e:
        current_app.logger.error(f"Smart search exception: {str(e)}", exc_info=True)
        flash(f'An error occurred during smart search: {str(e)}', 'error')
        return render_template('movies/smart_search.html',
                             title='Smart Search',
                             query=query,
                             movies=[],
                             page=page,
                             total_pages=0,
                             total_results=0,
                             available_ratings=available_ratings,
                             selected_rating=content_rating,
                             year_from=year_from,
                             year_to=year_to)


# ============ Review Routes ============

@bp.route('/<int:movie_id>/review/add', methods=['POST'])
@login_required()
def add_review(current_user, movie_id):
    """Add a review for a movie - unified for web and API."""
    movie = Movie.query.get_or_404(movie_id)
    
    # Get data from JSON or form
    if wants_json():
        data = request.get_json() or {}
        review_text = data.get('review_text', '').strip()
        rating = int(data.get('rating', 0)) if data.get('rating') else None
    else:
        review_text = request.form.get('review_text', '').strip()
        rating = request.form.get('rating', type=int)
    
    if not review_text:
        if wants_json():
            return error_response('Review text cannot be empty', 400)
        return redirect(url_for('movies.detail', movie_id=movie_id))
    
    if len(review_text) < 10:
        if wants_json():
            return error_response('Review must be at least 10 characters long', 400)
        return redirect(url_for('movies.detail', movie_id=movie_id))
    
    # Check if user already has a review for this movie
    existing_review = Review.query.filter_by(
        user_id=current_user.id,
        movie_id=movie_id
    ).first()
    
    if existing_review:
        if wants_json():
            return error_response('You have already reviewed this movie', 400)
        return redirect(url_for('movies.detail', movie_id=movie_id))
    
    # Create new review
    review = Review(
        user_id=current_user.id,
        movie_id=movie_id,
        rating=rating,
        review_text=review_text
    )
    
    db.session.add(review)
    db.session.commit()
    
    if wants_json():
        return success_response('Your review has been posted!', {'review_id': review.id})
    
    return redirect(url_for('movies.detail', movie_id=movie_id))


@bp.route('/review/<int:review_id>/edit', methods=['GET', 'POST'])
@login_required()
def edit_review(current_user, review_id):
    """Edit a review - unified for web and API."""
    review = Review.query.get_or_404(review_id)
    
    # Check if user owns this review
    if review.user_id != current_user.id:
        if wants_json():
            return error_response('You can only edit your own reviews', 403)
        return redirect(url_for('movies.detail', movie_id=review.movie_id))
    
    if request.method == 'POST':
        # Get data from JSON or form
        if wants_json():
            data = request.get_json() or {}
            review_text = data.get('review_text', '').strip()
            rating = int(data.get('rating', 0)) if data.get('rating') else None
        else:
            review_text = request.form.get('review_text', '').strip()
            rating = request.form.get('rating', type=int)
        
        if not review_text:
            if wants_json():
                return error_response('Review text cannot be empty', 400)
            return redirect(url_for('movies.edit_review', review_id=review_id))
        
        if len(review_text) < 10:
            if wants_json():
                return error_response('Review must be at least 10 characters long', 400)
            return redirect(url_for('movies.edit_review', review_id=review_id))
        
        review.review_text = review_text
        review.rating = rating
        review.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        if wants_json():
            return success_response('Your review has been updated!', {'review_id': review.id})
        
        return redirect(url_for('movies.detail', movie_id=review.movie_id))
    
    # GET request - show edit form (HTML only)
    movie = Movie.query.get_or_404(review.movie_id)
    return render_template('movies/edit_review.html',
                         title=f'Edit Review - {movie.title}',
                         review=review,
                         movie=movie)


@bp.route('/review/<int:review_id>/delete', methods=['POST'])
@login_required()
def delete_review(current_user, review_id):
    """Delete a review - unified for web and API."""
    review = Review.query.get_or_404(review_id)
    
    # Check if user owns this review
    if review.user_id != current_user.id:
        if wants_json():
            return error_response('You can only delete your own reviews', 403)
        return redirect(url_for('movies.detail', movie_id=review.movie_id))
    
    movie_id = review.movie_id
    db.session.delete(review)
    db.session.commit()
    
    if wants_json():
        return success_response('Your review has been deleted')
    
    return redirect(url_for('movies.detail', movie_id=movie_id))


@bp.route('/review/<int:review_id>/vote', methods=['POST'])
@login_required()
def vote_review(current_user, review_id):
    """Vote on a review (helpful/not helpful) - unified for web and API."""
    review = Review.query.get_or_404(review_id)
    
    # Get is_helpful from JSON or form
    if wants_json():
        data = request.get_json() or {}
        is_helpful = data.get('is_helpful') == True
    else:
        is_helpful = request.form.get('is_helpful') == 'true'
    
    # Check if user has already voted on this review
    existing_vote = ReviewVote.query.filter_by(
        user_id=current_user.id,
        review_id=review_id
    ).first()
    
    if existing_vote:
        # Update existing vote
        if existing_vote.is_helpful != is_helpful:
            # Change vote
            if existing_vote.is_helpful:
                review.helpful_count -= 1
                review.not_helpful_count += 1
            else:
                review.not_helpful_count -= 1
                review.helpful_count += 1
            existing_vote.is_helpful = is_helpful
        # else: same vote, no change
    else:
        # Create new vote
        vote = ReviewVote(
            user_id=current_user.id,
            review_id=review_id,
            is_helpful=is_helpful
        )
        if is_helpful:
            review.helpful_count += 1
        else:
            review.not_helpful_count += 1
        db.session.add(vote)
    
    db.session.commit()
    
    if wants_json():
        return success_response('Vote recorded', {
            'helpful_count': review.helpful_count,
            'not_helpful_count': review.not_helpful_count
        })
    
    return redirect(url_for('movies.detail', movie_id=review.movie_id))
