"""
Generate embeddings for movies using OpenRouter API and store in PostgreSQL.
This script will:
1. Fetch all movies from PostgreSQL
2. Generate embeddings using OpenRouter (OpenAI text-embedding-3-small) in PARALLEL
3. Combine with metadata features (vote_average, release_year)
4. Store embeddings metadata in PostgreSQL
5. Save the actual embedding vectors to embeddings.npy
6. Checkpoint progress to resume on failure

Embedding Components & Weights:
  • Plot (overview): 30%
  • Genre: 25%
  • Cast: 15%
  • Director: 10%
  • Keywords: 8%
  • Vote Average: 7%
  • Release Year: 5%
"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
import json
import numpy as np
import time
import pickle
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# Load environment variables
env_file = Path(__file__).parent.parent / '.env'
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if line.strip() and not line.startswith('#') and '=' in line:
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

from app import create_app
from models import db, Movie, Genre, Keyword, Credit, MovieMetadata, EmbeddingMetadata, EmbeddingConfig

# OpenRouter API configuration
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
EMBEDDING_MODEL = "openai/text-embedding-3-small"
EMBEDDING_DIMENSION = 1536

# Embedding component weights
EMBEDDING_WEIGHTS = {
    'plot': 0.30,           # overview text
    'genre': 0.25,          # genre names
    'cast': 0.15,           # actor names
    'director': 0.10,       # director name
    'keywords': 0.08,       # keyword tags
    'vote_average': 0.07,   # rating score
    'release_year': 0.05,   # release year
}

if not OPENROUTER_API_KEY:
    print("❌ OPENROUTER_API_KEY not found in environment!")
    sys.exit(1)

print("=" * 80)
print("GENERATE EMBEDDINGS FOR MOVIES (PARALLEL)")
print("=" * 80)
print(f"Model: {EMBEDDING_MODEL}")
print(f"Dimension: {EMBEDDING_DIMENSION}")
print()

app = create_app('development')
embedding_lock = Lock()

# Checkpoint file for resuming
CHECKPOINT_FILE = Path(__file__).parent.parent / 'data' / 'embeddings_checkpoint.pkl'

def load_checkpoint():
    """Load checkpoint if exists."""
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, 'rb') as f:
                return pickle.load(f)
        except:
            return {}
    return {}

def save_checkpoint(embeddings_dict, movie_metadata_map):
    """Save checkpoint with embeddings generated so far."""
    CHECKPOINT_FILE.parent.mkdir(exist_ok=True)
    with open(CHECKPOINT_FILE, 'wb') as f:
        pickle.dump({
            'embeddings_dict': embeddings_dict,
            'movie_metadata_map': movie_metadata_map
        }, f)

def clear_checkpoint():
    """Clear checkpoint file."""
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()


def normalize_embedding(embedding):
    """Normalize an embedding vector."""
    norm = np.linalg.norm(embedding)
    if norm == 0:
        return embedding
    return embedding / norm


def encode_numerical_feature(value, min_val, max_val, embedding_dim=1536):
    """Encode numerical features into embedding space."""
    if value is None:
        return np.zeros(embedding_dim)
    
    # Normalize to [0, 1]
    normalized = (value - min_val) / (max_val - min_val) if max_val > min_val else 0.5
    normalized = np.clip(normalized, 0, 1)
    
    # Create embedding vector
    embedding = np.full(embedding_dim, normalized)
    return normalize_embedding(embedding)


def get_movie_text(movie, genres_list, cast_list, director_name, keywords_list):
    """Create comprehensive text representation of movie for embedding."""
    parts = []
    
    # Title
    parts.append(f"Title: {movie.title}")
    
    # Overview (plot)
    if movie.overview:
        parts.append(f"Plot: {movie.overview}")
    
    # Genres
    if genres_list:
        parts.append(f"Genres: {', '.join(genres_list)}")
    
    # Cast
    if cast_list:
        parts.append(f"Cast: {', '.join(cast_list)}")
    
    # Director
    if director_name:
        parts.append(f"Director: {director_name}")
    
    # Keywords
    if keywords_list:
        parts.append(f"Keywords: {', '.join(keywords_list)}")
    
    return " | ".join(parts)


def generate_embedding(text, retries=3):
    """Generate embedding using OpenRouter API with retry logic."""
    for attempt in range(retries):
        try:
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": EMBEDDING_MODEL,
                "input": text
            }
            
            response = requests.post(
                "https://openrouter.ai/api/v1/embeddings",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            # Extract embedding from response
            embedding = data['data'][0]['embedding']
            return np.array(embedding, dtype=np.float32)
            
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            print(f"    ❌ Timeout after {retries} attempts")
            return None
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            print(f"    ❌ API Error: {e}")
            return None
        except Exception as e:
            print(f"    ❌ Unexpected error: {e}")
            return None
    
    return None


def process_movie_embedding(movie_data, idx, total, min_vote, max_vote, min_year, max_year):
    """Process embedding for a single movie."""
    movie_id, title, movie_text, vote_average, year = movie_data
    
    try:
        # Generate base text embedding
        base_embedding = generate_embedding(movie_text)
        if base_embedding is None:
            return None, f"[{idx}/{total}] ❌ Failed: {title}"
        
        # Generate numerical feature embeddings
        vote_emb = encode_numerical_feature(vote_average, min_vote, max_vote, EMBEDDING_DIMENSION)
        year_emb = encode_numerical_feature(year, min_year, max_year, EMBEDDING_DIMENSION)
        
        # Combine embeddings with weights
        # Base embedding already includes: plot, genre, cast, director, keywords
        base_weight = (EMBEDDING_WEIGHTS['plot'] + EMBEDDING_WEIGHTS['genre'] + 
                      EMBEDDING_WEIGHTS['cast'] + EMBEDDING_WEIGHTS['director'] + 
                      EMBEDDING_WEIGHTS['keywords'])
        
        composite_embedding = (
            base_weight * normalize_embedding(base_embedding) +
            EMBEDDING_WEIGHTS['vote_average'] * vote_emb +
            EMBEDDING_WEIGHTS['release_year'] * year_emb
        )
        
        # Normalize final embedding
        composite_embedding = normalize_embedding(composite_embedding)
        
        return (movie_id, title, composite_embedding, idx), f"[{idx}/{total}] ✓ {title}"
    except Exception as e:
        return None, f"[{idx}/{total}] ❌ Error: {title} - {e}"


def main():
    """Main execution function with parallel processing and checkpointing."""
    # Load checkpoint
    checkpoint = load_checkpoint()
    embeddings_dict = checkpoint.get('embeddings_dict', {})
    movie_metadata_map = checkpoint.get('movie_metadata_map', {})
    
    if embeddings_dict:
        print(f"📋 Resuming from checkpoint: {len(embeddings_dict)} embeddings already generated\n")
    
    with app.app_context():
        # Get all movies
        print("[1/6] Fetching movies from database...")
        movies = Movie.query.all()
        print(f"✓ Found {len(movies)} movies\n")
        
        if len(movies) == 0:
            print("❌ No movies found! Run fetch_fresh_tmdb_data.py first.")
            return
        
        # Collect statistics for numerical features
        print("[2/5] Collecting metadata statistics...")
        vote_averages = [m.vote_average for m in movies if m.vote_average is not None]
        min_vote = min(vote_averages) if vote_averages else 0
        max_vote = max(vote_averages) if vote_averages else 10
        min_year = 1900
        max_year = datetime.now().year + 2
        
        print(f"✓ Vote average range: {min_vote:.1f} - {max_vote:.1f}")
        print(f"✓ Year range: {min_year} - {max_year}\n")
        
        # Prepare movie data for processing
        print("[3/5] Preparing movie data...")
        movies_data = []
        movie_metadata_map = {}
        
        for movie in movies:
            # Get genres
            genres = Genre.query.filter_by(movie_id=movie.id).all()
            genres_list = [g.genre_name for g in genres]
            
            # Get cast (top 5)
            cast = Credit.query.filter_by(movie_id=movie.id, role='actor').order_by(Credit.credit_order).limit(5).all()
            cast_list = [c.person_name for c in cast if c.person_name]
            
            # Get director
            director = Credit.query.filter_by(movie_id=movie.id, role='director').first()
            director_name = director.person_name if director and director.person_name else None
            
            # Get keywords (top 10)
            keywords = Keyword.query.filter_by(movie_id=movie.id).limit(10).all()
            keywords_list = [k.keyword for k in keywords if k.keyword]
            
            # Extract year
            year = None
            if movie.release_date:
                try:
                    year = int(movie.release_date.split('-')[0])
                except:
                    pass
            
            movie_metadata_map[movie.id] = {
                'genres': genres_list,
                'release_date': movie.release_date,
                'title': movie.title
            }
            
            # Create text for main embedding
            movie_text = get_movie_text(movie, genres_list, cast_list, director_name, keywords_list)
            movies_data.append((movie.id, movie.title, movie_text, movie.vote_average, year))
        
        # Filter out already processed
        remaining_data = [m for m in movies_data if m[0] not in embeddings_dict]
        print(f"✓ Prepared {len(movies_data)} movies")
        print(f"Remaining to process: {len(remaining_data)}\n")
        
        if not remaining_data:
            print("✅ All embeddings already generated! Saving to database...")
        else:
            # Generate embeddings in parallel
            print(f"[4/6] Generating embeddings (PARALLEL with {min(30, len(remaining_data))} workers)...")
        
        success_count = len(embeddings_dict)  # Count already completed
        failed_count = 0
        checkpoint_interval = 100  # Save checkpoint every 100 embeddings
        
        if remaining_data:
        
            with ThreadPoolExecutor(max_workers=30) as executor:
                futures = {
                    executor.submit(process_movie_embedding, movie_data, idx, len(movies_data), min_vote, max_vote, min_year, max_year): movie_data
                    for idx, movie_data in enumerate(remaining_data, 1 + len(embeddings_dict))
                }
                
                for future in as_completed(futures):
                    result, message = future.result()
                    print(message)
                    
                    if result:
                        movie_id, title, embedding, idx = result
                        embeddings_dict[movie_id] = {
                            'embedding': embedding,
                            'title': title,
                            'original_idx': idx - 1
                        }
                        success_count += 1
                        
                        # Checkpoint every N embeddings
                        if success_count % checkpoint_interval == 0:
                            save_checkpoint(embeddings_dict, movie_metadata_map)
                            print(f"\n💾 Checkpoint saved: {success_count}/{len(movies_data)} embeddings\n")
                        
                        if success_count % 100 == 0:
                            print(f"\n💾 Progress: {success_count} embeddings generated...\n")
                    else:
                        failed_count += 1
        
        
        print(f"\n✓ Total embeddings: {success_count} ({failed_count} failed)\n")
        
        # Save final checkpoint before database operations
        save_checkpoint(embeddings_dict, movie_metadata_map)
        
        # Prepare data structures
        print("[5/6] Preparing data for saving...")
        embeddings_list = []
        metadata_list = []
        movie_metadata_list = []
        
        # Sort by movie_id to maintain consistency
        for embedding_idx, movie_id in enumerate(sorted(embeddings_dict.keys())):
            embed_data = embeddings_dict[movie_id]
            movie_info = movie_metadata_map[movie_id]
            
            embeddings_list.append(embed_data['embedding'])
            
            metadata_list.append({
                'movie_id': movie_id,
                'title': embed_data['title'],
                'embedding_index': embedding_idx,
                'model': f"{EMBEDDING_MODEL}+metadata",
                'dimension': EMBEDDING_DIMENSION
            })
            
            movie_metadata_list.append({
                'movie_id': movie_id,
                'genres': movie_info['genres'],
                'release_date': movie_info['release_date']
            })
        
        # Save embeddings to numpy file
        print("[6/6] Saving embeddings and metadata...")
        data_dir = Path(__file__).parent.parent / 'data'
        data_dir.mkdir(exist_ok=True)
        
        # Save to temporary file first
        embeddings_array = np.array(embeddings_list, dtype=np.float32)
        embeddings_file = data_dir / 'embeddings.npy'
        temp_embeddings_file = data_dir / 'embeddings_temp.npy'
        
        np.save(temp_embeddings_file, embeddings_array)
        print(f"✓ Saved temporary embeddings file\n")
        
        # Save metadata to database
        print("[7/7] Saving metadata to PostgreSQL...")
        
        # Refresh database connection
        try:
            db.session.rollback()
            db.session.execute(db.text('SELECT 1'))
        except:
            db.session.remove()
            db.engine.dispose()
        
        # Clear old metadata
        EmbeddingMetadata.query.delete()
        EmbeddingConfig.query.delete()
        MovieMetadata.query.delete()
        db.session.commit()
        
        # Save MovieMetadata
        for meta in movie_metadata_list:
            movie_meta = MovieMetadata(
                movie_id=meta['movie_id'],
                genres=meta['genres'],
                release_date=meta['release_date']
            )
            db.session.add(movie_meta)
        
        # Save EmbeddingMetadata
        for meta in metadata_list:
            embed_meta = EmbeddingMetadata(
                movie_id=meta['movie_id'],
                title=meta['title'],
                embedding_index=meta['embedding_index'],
                model=meta['model'],
                dimension=meta['dimension']
            )
            db.session.add(embed_meta)
        
        # Save EmbeddingConfig
        config = EmbeddingConfig(
            id=1,
            model=f"{EMBEDDING_MODEL}+metadata",
            dimension=EMBEDDING_DIMENSION,
            total_embeddings=len(embeddings_list),
            embeddings_file='embeddings.npy'
        )
        db.session.add(config)
        
        db.session.commit()
        print(f"✓ Saved metadata for {len(metadata_list)} movies\n")
        
        # Now that database is updated, move temp file to final location
        if temp_embeddings_file.exists():
            temp_embeddings_file.rename(embeddings_file)
            file_size_mb = embeddings_file.stat().st_size / (1024 * 1024)
            print(f"✓ Finalized embeddings.npy ({file_size_mb:.2f} MB)\n")
        
        # Clear checkpoint on success
        clear_checkpoint()
        
        # Verify
        print("[8/8] Verification...")
        movie_meta_count = MovieMetadata.query.count()
        embed_meta_count = EmbeddingMetadata.query.count()
        embed_config_count = EmbeddingConfig.query.count()
        
        print("=" * 80)
        print("EMBEDDING GENERATION COMPLETE!")
        print("=" * 80)
        print(f"✓ Embeddings file: {embeddings_file}")
        print(f"✓ Embeddings shape: {embeddings_array.shape}")
        print(f"✓ MovieMetadata records: {movie_meta_count}")
        print(f"✓ EmbeddingMetadata records: {embed_meta_count}")
        print(f"✓ EmbeddingConfig: {embed_config_count}")
        print(f"\nSuccess Rate: {(success_count/(success_count+failed_count)*100):.1f}%")
        print()
        print("Embedding Components & Weights:")
        print(f"  • Plot (overview): {EMBEDDING_WEIGHTS['plot']*100:.0f}%")
        print(f"  • Genre: {EMBEDDING_WEIGHTS['genre']*100:.0f}%")
        print(f"  • Cast: {EMBEDDING_WEIGHTS['cast']*100:.0f}%")
        print(f"  • Director: {EMBEDDING_WEIGHTS['director']*100:.0f}%")
        print(f"  • Keywords: {EMBEDDING_WEIGHTS['keywords']*100:.0f}%")
        print(f"  • Vote Average (rating): {EMBEDDING_WEIGHTS['vote_average']*100:.0f}%")
        print(f"  • Release Year: {EMBEDDING_WEIGHTS['release_year']*100:.0f}%")
        print()
        print("🎉 Your movie recommendation system is ready!")
        print("   Run: python run_flask.py")
        print("=" * 80)

if __name__ == '__main__':
    main()
