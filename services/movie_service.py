"""
Movie service - handles movie browsing, search, interactions, and watchlist.
"""
from datetime import datetime
from sqlalchemy import or_, func

from models import db, Movie, Genre, Credit, Interaction, Review, ReviewVote


class MovieService:
    """Movie business logic."""
    
    @staticmethod
    def get_movies(page=1, per_page=20, genre=None, search=None, sort_by='popularity',
                   min_rating=None, year_from=None, year_to=None, min_votes=None,
                   content_rating=None, hide_watched=False, user_id=None):
        """
        Get paginated list of movies with filters.
        
        Returns:
            dict: {'movies': list, 'pagination': dict, 'genres': list}
        """
        query = Movie.query
        
        # Apply genre filter
        if genre:
            query = query.join(Genre).filter(Genre.genre_name == genre)
        
        # Apply search
        if search:
            search_pattern = f'%{search}%'
            
            # Search in credits too
            credit_matches = Credit.query.filter(
                Credit.person_name.ilike(search_pattern)
            ).all()
            credit_movie_ids = [c.movie_id for c in credit_matches]
            
            if credit_movie_ids:
                query = query.filter(
                    or_(
                        Movie.title.ilike(search_pattern),
                        Movie.overview.ilike(search_pattern),
                        Movie.id.in_(credit_movie_ids)
                    )
                )
            else:
                query = query.filter(
                    or_(
                        Movie.title.ilike(search_pattern),
                        Movie.overview.ilike(search_pattern)
                    )
                )
        
        # Apply rating filter
        if min_rating:
            query = query.filter(Movie.vote_average >= min_rating)
        
        # Apply year range filters
        if year_from:
            query = query.filter(func.substr(Movie.release_date, 1, 4) >= str(year_from))
        if year_to:
            query = query.filter(func.substr(Movie.release_date, 1, 4) <= str(year_to))
        
        # Apply minimum vote count filter
        if min_votes:
            query = query.filter(Movie.vote_count >= min_votes)
        
        # Apply content rating filter
        if content_rating:
            query = query.filter(Movie.content_rating == content_rating)
        
        # Apply hide watched filter
        if hide_watched and user_id:
            watched_movie_ids = db.session.query(Interaction.movie_id)\
                .filter(Interaction.user_id == user_id)\
                .filter(Interaction.action == 'watch')\
                .all()
            watched_ids = [movie_id[0] for movie_id in watched_movie_ids]
            if watched_ids:
                query = query.filter(~Movie.id.in_(watched_ids))
        
        # Apply sorting
        if sort_by == 'rating':
            query = query.order_by(Movie.vote_average.desc().nullslast())
        elif sort_by == 'release_date_desc':
            query = query.order_by(Movie.release_date.desc().nullslast())
        elif sort_by == 'release_date_asc':
            query = query.order_by(Movie.release_date.asc().nullslast())
        elif sort_by == 'release_date':
            query = query.order_by(Movie.release_date.desc().nullslast())
        elif sort_by == 'title':
            query = query.order_by(Movie.title.asc())
        elif sort_by == 'vote_count':
            query = query.order_by(Movie.vote_count.desc().nullslast())
        else:  # Default: popularity
            query = query.order_by(Movie.popularity.desc().nullslast())
        
        # Paginate
        try:
            pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
        except (AttributeError, TypeError):
            # Fallback for older Flask-SQLAlchemy
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Get all genres for filters
        all_genres = db.session.query(Genre.genre_name).distinct().order_by(Genre.genre_name).all()
        genres = [g[0] for g in all_genres]
        
        # Get available content ratings
        content_ratings = db.session.query(Movie.content_rating)\
            .filter(Movie.content_rating.isnot(None))\
            .distinct()\
            .order_by(Movie.content_rating)\
            .all()
        content_ratings = [r[0] for r in content_ratings]
        
        return {
            'movies': pagination.items,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev,
                'prev_num': pagination.prev_num,
                'next_num': pagination.next_num
            },
            'genres': genres,
            'content_ratings': content_ratings,
            'pagination_obj': pagination  # For template compatibility
        }
    
    @staticmethod
    def get_movie_details(movie_id, user_id=None):
        """
        Get detailed movie information.
        
        Returns:
            dict: {'movie': Movie, 'genres': list, 'cast': list, 'directors': list, 
                   'user_interaction': dict, 'similar_movies': list}
        """
        movie = Movie.query.get_or_404(movie_id)
        
        # Get genres
        genres = [g.genre_name for g in movie.genres]
        
        # Get cast (top 5 actors)
        cast = Credit.query.filter_by(movie_id=movie_id, role='actor')\
                          .order_by(Credit.credit_order).limit(5).all()
        
        # Get directors
        director_credits = Credit.query.filter_by(movie_id=movie_id, role='director').all()
        directors = [d.person_name for d in director_credits]
        
        # Get user interaction if authenticated
        user_interaction = None
        if user_id:
            interactions = Interaction.query.filter_by(
                user_id=user_id,
                movie_id=movie_id
            ).all()
            
            user_interaction = {
                'in_watchlist': any(i.action == 'watchlist' for i in interactions),
                'watched': any(i.action == 'watch' for i in interactions),
                'rating': next((i.rating for i in interactions if i.action == 'rate'), None),
                'skipped': any(i.action == 'skip' for i in interactions)
            }
        
        # Get similar movies
        similar_movies = []
        try:
            from recommender import get_similar_movies
            similar_movies = get_similar_movies(
                movie_id,
                num_similar=6,
                exclude_watched=user_id is not None,
                user_id=user_id
            )
        except Exception as e:
            print(f"Error getting similar movies: {e}")
        
        return {
            'movie': movie,
            'genres': genres,
            'cast': cast,
            'directors': directors,
            'director': director_credits[0] if director_credits else None,
            'user_interaction': user_interaction,
            'similar_movies': similar_movies
        }
    
    @staticmethod
    def mark_watched(user_id, movie_id):
        """
        Mark movie as watched.
        
        Returns:
            dict: {'success': bool, 'message': str, 'already_watched': bool}
        """
        movie = Movie.query.get_or_404(movie_id)
        
        existing = Interaction.query.filter_by(
            user_id=user_id,
            movie_id=movie_id,
            action='watch'
        ).first()
        
        if existing:
            return {
                'success': False,
                'message': f'You\'ve already watched "{movie.title}"',
                'already_watched': True
            }
        
        interaction = Interaction(
            user_id=user_id,
            movie_id=movie_id,
            action='watch',
            timestamp=datetime.utcnow()
        )
        db.session.add(interaction)
        db.session.commit()
        
        return {
            'success': True,
            'message': f'Added "{movie.title}" to your watch history!',
            'already_watched': False
        }
    
    @staticmethod
    def rate_movie(user_id, movie_id, rating):
        """
        Rate a movie (automatically marks as watched).
        
        Returns:
            dict: {'success': bool, 'message': str, 'is_update': bool}
        """
        from utils.errors import ValidationError
        from utils.validators import Validator
        
        movie = Movie.query.get_or_404(movie_id)
        
        # Validate rating
        try:
            rating = Validator.validate_rating(rating)
        except ValidationError as e:
            return {
                'success': False,
                'message': str(e)
            }
        
        # Check if already rated
        existing_rating = Interaction.query.filter_by(
            user_id=user_id,
            movie_id=movie_id,
            action='rate'
        ).first()
        
        if existing_rating:
            existing_rating.rating = rating
            existing_rating.timestamp = datetime.utcnow()
            message = f'Updated your rating for "{movie.title}" to {rating}/10!'
            is_update = True
        else:
            interaction = Interaction(
                user_id=user_id,
                movie_id=movie_id,
                action='rate',
                rating=rating,
                timestamp=datetime.utcnow()
            )
            db.session.add(interaction)
            message = f'Rated "{movie.title}" {rating}/10!'
            is_update = False
        
        # Auto-mark as watched
        existing_watch = Interaction.query.filter_by(
            user_id=user_id,
            movie_id=movie_id,
            action='watch'
        ).first()
        
        if not existing_watch:
            watch_interaction = Interaction(
                user_id=user_id,
                movie_id=movie_id,
                action='watch',
                timestamp=datetime.utcnow()
            )
            db.session.add(watch_interaction)
        
        db.session.commit()
        
        return {
            'success': True,
            'message': message,
            'is_update': is_update
        }
    
    @staticmethod
    def skip_movie(user_id, movie_id):
        """
        Mark movie as skipped/not interested.
        
        Returns:
            dict: {'success': bool, 'message': str}
        """
        movie = Movie.query.get_or_404(movie_id)
        
        existing = Interaction.query.filter_by(
            user_id=user_id,
            movie_id=movie_id,
            action='skip'
        ).first()
        
        if existing:
            return {
                'success': False,
                'message': f'You\'ve already skipped "{movie.title}"'
            }
        
        interaction = Interaction(
            user_id=user_id,
            movie_id=movie_id,
            action='skip',
            timestamp=datetime.utcnow()
        )
        db.session.add(interaction)
        db.session.commit()
        
        return {
            'success': True,
            'message': f'Marked "{movie.title}" as not interested.'
        }
    
    @staticmethod
    def get_watchlist(user_id, page=1, per_page=20):
        """
        Get user's watchlist.
        
        Returns:
            dict: {'movies': list, 'pagination': dict}
        """
        watchlist_query = db.session.query(Movie).join(Interaction).filter(
            Interaction.user_id == user_id,
            Interaction.action == 'watchlist'
        ).order_by(Interaction.timestamp.desc())
        
        try:
            pagination = db.paginate(watchlist_query, page=page, per_page=per_page, error_out=False)
        except (AttributeError, TypeError):
            total = watchlist_query.count()
            movies = watchlist_query.offset((page - 1) * per_page).limit(per_page).all()
            pagination = type('obj', (object,), {
                'items': movies,
                'total': total,
                'pages': (total + per_page - 1) // per_page,
                'page': page,
                'per_page': per_page,
                'has_next': page < (total + per_page - 1) // per_page,
                'has_prev': page > 1,
                'prev_num': page - 1 if page > 1 else None,
                'next_num': page + 1 if page < (total + per_page - 1) // per_page else None
            })()
        
        return {
            'movies': pagination.items,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev,
                'prev_num': pagination.prev_num,
                'next_num': pagination.next_num
            },
            'pagination_obj': pagination
        }
    
    @staticmethod
    def add_to_watchlist(user_id, movie_id):
        """
        Add movie to watchlist.
        
        Returns:
            dict: {'success': bool, 'message': str}
        """
        movie = Movie.query.get_or_404(movie_id)
        
        existing = Interaction.query.filter_by(
            user_id=user_id,
            movie_id=movie_id,
            action='watchlist'
        ).first()
        
        if existing:
            return {
                'success': False,
                'message': f'"{movie.title}" is already in your watchlist.'
            }
        
        interaction = Interaction(
            user_id=user_id,
            movie_id=movie_id,
            action='watchlist',
            timestamp=datetime.utcnow()
        )
        db.session.add(interaction)
        db.session.commit()
        
        return {
            'success': True,
            'message': f'Added "{movie.title}" to your watchlist!'
        }
    
    @staticmethod
    def remove_from_watchlist(user_id, movie_id):
        """
        Remove movie from watchlist.
        
        Returns:
            dict: {'success': bool, 'message': str}
        """
        movie = Movie.query.get_or_404(movie_id)
        
        interaction = Interaction.query.filter_by(
            user_id=user_id,
            movie_id=movie_id,
            action='watchlist'
        ).first()
        
        if not interaction:
            return {
                'success': False,
                'message': f'"{movie.title}" is not in your watchlist.'
            }
        
        db.session.delete(interaction)
        db.session.commit()
        
        return {
            'success': True,
            'message': f'Removed "{movie.title}" from your watchlist.'
        }
    
    @staticmethod
    def get_watched_movies(user_id, page=1, per_page=20, sort_by='watch_date'):
        """
        Get user's watch history.
        
        Returns:
            dict: {'movies': list, 'pagination': dict}
        """
        watched_query = db.session.query(Movie, Interaction).join(
            Interaction, Movie.id == Interaction.movie_id
        ).filter(
            Interaction.user_id == user_id,
            Interaction.action == 'watch'
        ).order_by(Interaction.timestamp.desc())
        
        # Get all watched movies for sorting
        all_watched = watched_query.all()
        
        if not all_watched:
            return {
                'movies': [],
                'pagination': {
                    'page': 1,
                    'per_page': per_page,
                    'total': 0,
                    'pages': 0,
                    'has_next': False,
                    'has_prev': False,
                    'prev_num': None,
                    'next_num': None
                }
            }
        
        # Get user ratings
        movie_ids = [m.id for m, _ in all_watched]
        rating_interactions = Interaction.query.filter_by(
            user_id=user_id,
            action='rate'
        ).filter(Interaction.movie_id.in_(movie_ids)).all()
        rating_data = {i.movie_id: i.rating for i in rating_interactions}
        
        # Create watched movies list with metadata
        watched_movies = []
        for movie, interaction in all_watched:
            watched_movies.append({
                'movie': movie,
                'watch_date': interaction.timestamp,
                'user_rating': rating_data.get(movie.id, None)
            })
        
        # Apply sorting
        if sort_by == 'watch_date':
            watched_movies.sort(key=lambda x: x['watch_date'], reverse=True)
        elif sort_by == 'user_rating':
            watched_movies.sort(key=lambda x: x['user_rating'] or 0, reverse=True)
        elif sort_by == 'movie_rating':
            watched_movies.sort(key=lambda x: x['movie'].vote_average or 0, reverse=True)
        elif sort_by == 'title':
            watched_movies.sort(key=lambda x: x['movie'].title)
        
        # Manual pagination
        total = len(watched_movies)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_movies = watched_movies[start:end]
        
        return {
            'movies': paginated_movies,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page if per_page > 0 else 0,
                'has_next': page < (total + per_page - 1) // per_page,
                'has_prev': page > 1,
                'prev_num': page - 1 if page > 1 else None,
                'next_num': page + 1 if page < (total + per_page - 1) // per_page else None
            }
        }
    
    @staticmethod
    def get_user_profile(user_id):
        """
        Get user profile with statistics.
        
        Returns:
            dict: {'statistics': dict, 'recent_interactions': list}
        """
        interactions = Interaction.query.filter_by(user_id=user_id).all()
        
        watchlist_count = sum(1 for i in interactions if i.action == 'watchlist')
        watched_count = sum(1 for i in interactions if i.action == 'watch')
        skipped_count = sum(1 for i in interactions if i.action == 'skip')
        ratings = [i.rating for i in interactions if i.action == 'rate' and i.rating]
        
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        # Get recent interactions
        recent = Interaction.query.filter_by(user_id=user_id)\
                                  .order_by(Interaction.timestamp.desc())\
                                  .limit(10).all()
        
        return {
            'statistics': {
                'watchlist_count': watchlist_count,
                'watched_count': watched_count,
                'rated_count': len(ratings),
                'skipped_count': skipped_count,
                'average_rating': round(avg_rating, 1)
            },
            'recent_interactions': recent
        }
    
    @staticmethod
    def delete_interaction(user_id, interaction_id):
        """
        Delete a specific interaction.
        
        Returns:
            dict: {'success': bool, 'message': str}
        """
        interaction = Interaction.query.get_or_404(interaction_id)
        
        if interaction.user_id != user_id:
            return {
                'success': False,
                'message': 'You can only delete your own interactions.'
            }
        
        movie_title = interaction.movie.title
        action = interaction.action
        
        db.session.delete(interaction)
        db.session.commit()
        
        return {
            'success': True,
            'message': f'Deleted your "{action}" action for "{movie_title}".'
        }
    
    @staticmethod
    def clear_all_data(user_id):
        """
        Clear all user activity data.
        
        Returns:
            dict: {'success': bool, 'message': str, 'count': int}
        """
        deleted_count = Interaction.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        
        return {
            'success': True,
            'message': f'Successfully deleted all your activity data ({deleted_count} interactions).',
            'count': deleted_count
        }
    
    @staticmethod
    def movie_to_dict(movie, detailed=False, user_interaction=None):
        """Convert Movie object to dictionary for API responses."""
        base_data = {
            'id': movie.id,
            'title': movie.title,
            'overview': movie.overview,
            'release_date': movie.release_date,
            'poster_path': movie.poster_path,
            'backdrop_path': movie.backdrop_path,
            'vote_average': float(movie.vote_average) if movie.vote_average else None,
            'vote_count': movie.vote_count,
            'popularity': float(movie.popularity) if movie.popularity else None,
            'content_rating': movie.content_rating,
            'poster_url': movie.get_poster_url(),
            'backdrop_url': movie.get_backdrop_url(),
            'genres': [genre.genre_name for genre in movie.genres]
        }
        
        if detailed:
            # Get cast and crew
            cast = []
            directors = []
            for credit in movie.credits:
                if credit.role == 'actor':
                    cast.append({
                        'name': credit.person_name,
                        'character': credit.character_name,
                        'order': credit.credit_order
                    })
                elif credit.role == 'director':
                    directors.append(credit.person_name)
            
            # Sort cast by order
            cast.sort(key=lambda x: x.get('order', 999))
            
            # Get keywords
            keywords = [kw.keyword for kw in movie.keywords]
            
            base_data.update({
                'cast': cast[:10],  # Top 10 cast members
                'directors': directors,
                'keywords': keywords
            })
        
        if user_interaction:
            base_data['user_interaction'] = user_interaction
        
        return base_data
    
    @staticmethod
    def get_user_stats(user_id):
        """
        Get user statistics and recent activity.
        
        Returns:
            dict: User statistics including counts and recent interactions
        """
        watched = Interaction.query.filter_by(user_id=user_id, action='watch').count()
        rated = Interaction.query.filter_by(user_id=user_id, action='rate').count()
        skipped = Interaction.query.filter_by(user_id=user_id, action='skip').count()
        watchlist_count = Interaction.query.filter_by(user_id=user_id, action='watchlist').count()
        
        # Get recent interactions
        recent_interactions = Interaction.query.filter_by(user_id=user_id)\
            .order_by(Interaction.timestamp.desc())\
            .limit(10).all()
        
        # Get average rating
        avg_rating = db.session.query(func.avg(Interaction.rating))\
            .filter(Interaction.user_id == user_id, Interaction.action == 'rate')\
            .scalar()
        
        return {
            'watched': watched,
            'rated': rated,
            'skipped': skipped,
            'watchlist_count': watchlist_count,
            'avg_rating': float(avg_rating) if avg_rating else None,
            'recent_interactions': recent_interactions
        }
