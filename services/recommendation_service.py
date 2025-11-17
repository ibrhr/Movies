"""
Recommendation service - handles personalized recommendations.
"""
from models import Interaction
import recommender


class RecommendationService:
    """Recommendation business logic."""
    
    @staticmethod
    def get_recommendations(user_id, num_recommendations=20, lambda_param=0.7, exclude_watched=True):
        """
        Get personalized movie recommendations for user.
        
        Args:
            user_id: User ID
            num_recommendations: Number of recommendations to return
            lambda_param: Diversity parameter (0.0 = relevant, 1.0 = diverse)
            exclude_watched: Whether to exclude watched movies
        
        Returns:
            dict: {'success': bool, 'recommendations': list, 'message': str}
        """
        # Get user interactions
        interactions = Interaction.query.filter_by(user_id=user_id).all()
        
        if not interactions:
            return {
                'success': True,
                'recommendations': [],
                'message': 'No interaction history. Please rate or watch some movies first.'
            }
        
        try:
            # Load embeddings if not already loaded
            recommender.load_embeddings()
            
            # Get recommendations using the recommender module
            recs = recommender.get_recommendations(
                user_id=user_id,
                num_recommendations=num_recommendations,
                lambda_param=lambda_param
            )
            
            # Get watched movie IDs for filtering
            if exclude_watched:
                watched_ids = set(i.movie_id for i in interactions if i.action in ['watch', 'rate'])
                recs = [r for r in recs if r['movie'].id not in watched_ids]
            
            # Limit to requested number
            recs = recs[:num_recommendations]
            
            return {
                'success': True,
                'recommendations': recs,
                'message': None
            }
        
        except Exception as e:
            return {
                'success': False,
                'recommendations': [],
                'message': f'Failed to generate recommendations: {str(e)}'
            }
    
    @staticmethod
    def recommendation_to_dict(rec):
        """Convert recommendation to dictionary for API responses."""
        from services.movie_service import MovieService
        
        movie_data = MovieService.movie_to_dict(rec['movie'])
        movie_data.update({
            'recommendation_score': float(rec['final_score']),
            'explanation': {
                'interest_score': float(rec.get('interest_score', 0)),
                'discovery_score': float(rec.get('discovery_score', 0)),
                'collaborative_score': float(rec.get('collaborative_score', 0)),
                'category_score': float(rec.get('category_score', 0))
            }
        })
        
        return movie_data
