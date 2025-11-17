"""
Recommendation engine adapted for Flask and SQLAlchemy.

The embeddings used in this recommender are composite embeddings that combine
multiple movie features with the following weights:

Embedding Components & Weights:
  • Plot (overview text): 30%
  • Genre (genre names): 25%
  • Cast (top 5 actors): 15%
  • Director (director name): 10%
  • Keywords (keyword tags): 8%
  • Vote Average (rating score): 7%
  • Release Year: 5%

These embeddings are pre-computed by scripts/generate_embeddings_fresh.py and
loaded from the embeddings.npy file. The composite nature allows for similarity
matching across multiple dimensions of movie content and metadata.
"""
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from flask import current_app

from models import db, User, Movie, Interaction, Genre, MovieMetadata, EmbeddingMetadata


# Global variables for embeddings (loaded once)
_embeddings = None
_movie_to_idx = None
_idx_to_movie = None
_metadata = None


def load_embeddings():
    """Load embeddings from file and metadata from database (called once on first use)."""
    global _embeddings, _movie_to_idx, _idx_to_movie, _metadata
    
    if _embeddings is not None:
        return  # Already loaded
    
    # Load embeddings from numpy file
    embeddings_path = current_app.config['EMBEDDINGS_PATH']
    _embeddings = np.load(embeddings_path)
    
    # Load embedding metadata from database
    embedding_metas = EmbeddingMetadata.query.all()
    
    if not embedding_metas:
        raise ValueError(
            "No embedding metadata found in database. "
            "Please run 'python scripts/generate_embeddings_fresh.py' first."
        )
    
    # Create movie_id -> embedding_index mapping
    _movie_to_idx = {
        meta.movie_id: meta.embedding_index 
        for meta in embedding_metas
    }
    _idx_to_movie = {v: k for k, v in _movie_to_idx.items()}
    
    # Load movie metadata from database (for genres)
    movie_metas = MovieMetadata.query.all()
    _metadata = {
        str(meta.movie_id): {
            'genres': meta.genres or [],
            'release_date': meta.release_date
        }
        for meta in movie_metas
    }
    
    print(f"✅ Embeddings loaded: {_embeddings.shape[0]} movies from database")


def get_user_interactions(user_id):
    """Get user's interactions from database."""
    watched = []
    ratings = {}
    skipped = []
    
    interactions = Interaction.query.filter_by(user_id=user_id).all()
    
    for interaction in interactions:
        if interaction.action == 'watch':
            watched.append({
                'movie_id': interaction.movie_id,
                'timestamp': interaction.timestamp
            })
        elif interaction.action == 'rate':
            ratings[interaction.movie_id] = interaction.rating
        elif interaction.action == 'skip':
            skipped.append(interaction.movie_id)
    
    return watched, ratings, skipped


def compute_interest_vector(watched, ratings):
    """Interest Vector: Content-based similarity to watched movies."""
    if not watched:
        return np.zeros(len(_embeddings))
    
    # Get embeddings for watched movies
    watched_indices = [
        _movie_to_idx[item['movie_id']] for item in watched 
        if item['movie_id'] in _movie_to_idx
    ]
    
    if not watched_indices:
        return np.zeros(len(_embeddings))
    
    watched_embeddings = _embeddings[watched_indices]
    
    # Apply time decay and rating weights
    weights = []
    for item in watched:
        if item['movie_id'] in _movie_to_idx:
            # Time decay
            days_ago = (datetime.utcnow() - item['timestamp']).days
            time_weight = 0.5 ** (days_ago / 14)
            
            # Rating weight
            rating_weight = ratings.get(item['movie_id'], 5.0) / 10.0
            
            weights.append(time_weight * rating_weight)
    
    weights = np.array(weights)
    if len(weights) > 0:
        weights = weights / weights.sum()
    
    # Weighted average
    user_vector = np.average(watched_embeddings, axis=0, weights=weights)
    similarities = _embeddings @ user_vector
    
    return similarities


def compute_discovery_vector(skipped, ratings):
    """Discovery Vector: Dissimilarity to skipped/disliked movies."""
    disliked = skipped + [mid for mid, rating in ratings.items() if rating < 5.0]
    
    if not disliked:
        return np.zeros(len(_embeddings))
    
    disliked_indices = [
        _movie_to_idx[mid] for mid in disliked 
        if mid in _movie_to_idx
    ]
    
    if not disliked_indices:
        return np.zeros(len(_embeddings))
    
    disliked_embeddings = _embeddings[disliked_indices]
    bad_vector = np.mean(disliked_embeddings, axis=0)
    dissimilarities = -(_embeddings @ bad_vector)
    
    # Normalize
    dissimilarities = (dissimilarities - dissimilarities.min()) / \
                     (dissimilarities.max() - dissimilarities.min() + 1e-8)
    
    return dissimilarities


def compute_collaborative_vector(watched):
    """Collaborative Vector: Simple item-item similarity."""
    if not watched:
        return np.zeros(len(_embeddings))
    
    watched_indices = [
        _movie_to_idx[item['movie_id']] for item in watched 
        if item['movie_id'] in _movie_to_idx
    ]
    
    if not watched_indices:
        return np.zeros(len(_embeddings))
    
    watched_embeddings = _embeddings[watched_indices]
    similarity_matrix = _embeddings @ watched_embeddings.T
    avg_similarity = similarity_matrix.mean(axis=1)
    
    return avg_similarity


def compute_category_vector(watched):
    """Category Vector: Genre preferences."""
    if not watched:
        return np.zeros(len(_embeddings))
    
    # Count genre frequencies
    genre_counts = defaultdict(int)
    for item in watched:
        movie_id = str(item['movie_id'])
        if movie_id in _metadata:
            for genre in _metadata[movie_id]["genres"]:
                genre_counts[genre] += 1
    
    if not genre_counts:
        return np.zeros(len(_embeddings))
    
    total = len(watched)
    genre_prefs = {genre: count / total for genre, count in genre_counts.items()}
    
    # Score each movie
    scores = np.zeros(len(_embeddings))
    for idx, movie_id in _idx_to_movie.items():
        if str(movie_id) in _metadata:
            movie_genres = _metadata[str(movie_id)]["genres"]
            score = sum(genre_prefs.get(g, 0) for g in movie_genres)
            scores[idx] = score
    
    if scores.max() > 0:
        scores = scores / scores.max()
    
    return scores


def compute_adaptive_weights(n_interactions):
    """Compute adaptive weights based on interaction count."""
    if n_interactions < 5:
        return {"interest": 0.2, "discovery": 0.1, "collaborative": 0.3, "category": 0.4}
    elif n_interactions < 20:
        return {"interest": 0.35, "discovery": 0.25, "collaborative": 0.25, "category": 0.15}
    else:
        return {"interest": 0.4, "discovery": 0.3, "collaborative": 0.2, "category": 0.1}


def mmr_rerank(candidate_indices, relevance_scores, k, lambda_param):
    """MMR diversity re-ranking."""
    if len(candidate_indices) == 0:
        return []
    
    selected = []
    remaining = set(candidate_indices)
    
    # Select first item
    first_idx = candidate_indices[np.argmax(relevance_scores[candidate_indices])]
    selected.append(int(first_idx))
    remaining.remove(first_idx)
    
    # Iteratively select
    while len(selected) < k and remaining:
        mmr_scores = {}
        selected_embeddings = _embeddings[selected]
        
        for idx in remaining:
            relevance = relevance_scores[idx]
            similarities = _embeddings[idx] @ selected_embeddings.T
            max_sim = similarities.max()
            mmr = lambda_param * relevance - (1 - lambda_param) * max_sim
            mmr_scores[idx] = mmr
        
        best_idx = max(mmr_scores, key=mmr_scores.get)
        selected.append(int(best_idx))
        remaining.remove(best_idx)
    
    return selected


def get_recommendations(user_id, num_recommendations=10, lambda_param=0.7):
    """Generate recommendations for a user."""
    load_embeddings()  # Ensure embeddings are loaded
    
    # Get user interactions
    watched, ratings, skipped = get_user_interactions(user_id)
    
    # If no interactions, return popular movies
    if not watched and not skipped:
        popular = Movie.query.order_by(Movie.popularity.desc()).limit(num_recommendations).all()
        return [{
            'movie': movie,
            'score': movie.popularity / 1000,  # Normalize
            'explanation': {
                'interest': 0,
                'discovery': 0,
                'collaborative': 0,
                'category': 0,
                'total': movie.popularity / 1000
            }
        } for movie in popular]
    
    # Compute vectors
    interest_scores = compute_interest_vector(watched, ratings)
    discovery_scores = compute_discovery_vector(skipped, ratings)
    collaborative_scores = compute_collaborative_vector(watched)
    category_scores = compute_category_vector(watched)
    
    # Adaptive weighting
    weights = compute_adaptive_weights(len(watched))
    
    # Combine
    combined_scores = (
        weights["interest"] * interest_scores +
        weights["discovery"] * discovery_scores +
        weights["collaborative"] * collaborative_scores +
        weights["category"] * category_scores
    )
    
    # Filter watched movies
    watched_ids = set(item['movie_id'] for item in watched)
    candidate_indices = np.array([
        idx for idx in range(len(combined_scores))
        if _idx_to_movie.get(idx) not in watched_ids
    ])
    
    # MMR re-ranking
    selected_indices = mmr_rerank(candidate_indices, combined_scores, num_recommendations, lambda_param)
    
    # Create result objects
    recommendations = []
    for idx in selected_indices:
        movie_id = _idx_to_movie[idx]
        movie = Movie.query.get(movie_id)
        
        if movie:
            explanation = {
                "interest": float(weights["interest"] * interest_scores[idx]),
                "discovery": float(weights["discovery"] * discovery_scores[idx]),
                "collaborative": float(weights["collaborative"] * collaborative_scores[idx]),
                "category": float(weights["category"] * category_scores[idx]),
                "total": float(combined_scores[idx])
            }
            
            recommendations.append({
                'movie': movie,
                'score': float(combined_scores[idx]),
                'explanation': explanation
            })
    
    return recommendations


def get_similar_movies(movie_id, num_similar=6, exclude_watched=False, user_id=None):
    """
    Find movies similar to the given movie using cosine similarity.
    
    Args:
        movie_id: ID of the movie to find similar movies for
        num_similar: Number of similar movies to return
        exclude_watched: Whether to exclude watched movies (requires user_id)
        user_id: User ID for filtering watched movies
    
    Returns:
        List of similar movies with similarity scores
    """
    load_embeddings()  # Ensure embeddings are loaded
    
    # Check if movie has an embedding
    if movie_id not in _movie_to_idx:
        return []
    
    # Get the movie's embedding
    movie_idx = _movie_to_idx[movie_id]
    movie_embedding = _embeddings[movie_idx]
    
    # Calculate cosine similarity with all movies
    similarities = _embeddings @ movie_embedding
    
    # Get indices sorted by similarity (excluding the movie itself)
    similar_indices = np.argsort(similarities)[::-1]
    
    # Filter out watched movies if requested
    watched_ids = set()
    if exclude_watched and user_id:
        watched_interactions = Interaction.query.filter_by(
            user_id=user_id,
            action='watch'
        ).all()
        watched_ids = {interaction.movie_id for interaction in watched_interactions}
    
    # Collect similar movies
    similar_movies = []
    for idx in similar_indices:
        candidate_movie_id = _idx_to_movie[idx]
        
        # Skip the movie itself
        if candidate_movie_id == movie_id:
            continue
        
        # Skip watched movies if filtering
        if exclude_watched and candidate_movie_id in watched_ids:
            continue
        
        # Get movie from database
        movie = Movie.query.get(candidate_movie_id)
        if movie:
            similar_movies.append({
                'movie': movie,
                'similarity': float(similarities[idx])
            })
        
        # Stop when we have enough
        if len(similar_movies) >= num_similar:
            break
    
    return similar_movies
