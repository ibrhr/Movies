"""
Fresh start: Fetch top-rated and popular movies from TMDB and populate PostgreSQL.
This script will:
1. Fetch 10000 top-rated movies
2. Fetch 10000 popular movies
3. Store them directly in PostgreSQL with parallel processing
4. Get full details including genres, keywords, credits
5. Checkpoint progress to resume on failure
"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
import time
import json
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
from models import db, Movie, Genre, Keyword, Credit

# TMDB API configuration
TMDB_API_KEY = os.environ.get('TMDB_API_KEY')
TMDB_BASE_URL = os.environ.get('TMDB_BASE_URL', 'https://api.themoviedb.org/3')

# Batch configuration
BATCH_SIZE = 2000
TARGET_TOTAL_MOVIES = 20000
MOVIES_PER_PAGE = 20

if not TMDB_API_KEY:
    print("❌ TMDB_API_KEY not found in environment!")
    sys.exit(1)

print("=" * 80)
print("FRESH DATA FETCH FROM TMDB (PARALLEL)")
print("=" * 80)
print(f"API Key: {TMDB_API_KEY[:10]}...")
print()

app = create_app('development')
db_lock = Lock()  # Thread-safe database operations

# Checkpoint file for resuming
CHECKPOINT_FILE = Path(__file__).parent.parent / 'data' / 'fetch_checkpoint.json'

def load_checkpoint():
    """Load checkpoint if exists."""
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, 'r') as f:
                return json.load(f)
        except:
            return {'processed_ids': [], 'current_batch': 0}
    return {'processed_ids': [], 'current_batch': 0}

def save_checkpoint(processed_ids, current_batch):
    """Save checkpoint with list of processed movie IDs and current batch."""
    CHECKPOINT_FILE.parent.mkdir(exist_ok=True)
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump({
            'processed_ids': processed_ids,
            'current_batch': current_batch
        }, f)

def clear_checkpoint():
    """Clear checkpoint file."""
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()

def fetch_batch_pages(start_page, num_pages):
    """Fetch a specific range of pages for a batch."""
    movies = []
    
    print(f"  Fetching pages {start_page} to {start_page + num_pages - 1}...")
    
    for page_offset in range(num_pages):
        current_page = start_page + page_offset
        
        for attempt in range(3):
            try:
                url = f"{TMDB_BASE_URL}/movie/popular"
                params = {
                    'api_key': TMDB_API_KEY,
                    'page': current_page,
                    'language': 'en-US'
                }
                
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                results = data.get('results', [])
                if not results:
                    return movies
                
                movies.extend(results)
                print(f"  Page {current_page}: {len(results)} movies (batch total: {len(movies)})")
                
                time.sleep(0.3)  # Rate limiting
                break
                
            except requests.exceptions.Timeout:
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
                    continue
                print(f"  ⚠️ Timeout on page {current_page} after 3 attempts")
                break
            except Exception as e:
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
                    continue
                print(f"  ⚠️ Error on page {current_page}: {e}")
                break
        
        # Stop if we've reached batch size
        if len(movies) >= BATCH_SIZE:
            return movies[:BATCH_SIZE]
    
    return movies

def fetch_movie_details(movie_id, retries=3):
    """Fetch detailed information for a specific movie with retry logic."""
    for attempt in range(retries):
        try:
            url = f"{TMDB_BASE_URL}/movie/{movie_id}"
            params = {
                'api_key': TMDB_API_KEY,
                'append_to_response': 'credits,keywords',
                'language': 'en-US'
            }
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                time.sleep(1 * (attempt + 1))  # Exponential backoff
                continue
            print(f"    ❌ Timeout fetching movie {movie_id} after {retries} attempts")
            return None
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                time.sleep(1 * (attempt + 1))
                continue
            print(f"    ❌ Error fetching details for movie {movie_id}: {e}")
            return None
        except Exception as e:
            print(f"    ❌ Unexpected error for movie {movie_id}: {e}")
            return None
    
    return None

def save_movie_to_db(movie_data):
    """Save movie and related data to PostgreSQL (thread-safe)."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with db_lock:
                with app.app_context():
                    # Refresh connection if needed
                    if attempt > 0:
                        db.session.rollback()

                    # Check if movie already exists
                    existing = Movie.query.filter_by(title=movie_data['title']).first()
                    if existing:
                        return existing

                    # Create movie
                    movie = Movie(
                        title=movie_data.get('title'),
                        overview=movie_data.get('overview'),
                        release_date=movie_data.get('release_date'),
                        vote_average=movie_data.get('vote_average'),
                        vote_count=movie_data.get('vote_count'),
                        popularity=movie_data.get('popularity'),
                        poster_path=movie_data.get('poster_path'),
                        backdrop_path=movie_data.get('backdrop_path'),
                        content_rating=None
                    )
                    db.session.add(movie)
                    db.session.flush()  # Get the ID

                    # Add genres
                    for genre_data in movie_data.get('genres', []):
                        genre = Genre(
                            movie_id=movie.id,
                            genre_id=genre_data['id'],
                            genre_name=genre_data['name']
                        )
                        db.session.add(genre)

                    # Add keywords
                    keywords_data = movie_data.get('keywords', {}).get('keywords', [])
                    for keyword_data in keywords_data:
                        keyword = Keyword(
                            movie_id=movie.id,
                            keyword_id=keyword_data['id'],
                            keyword=keyword_data['name']
                        )
                        db.session.add(keyword)

                    # Add credits (cast and crew)
                    credits = movie_data.get('credits', {})

                    # Directors
                    crew = credits.get('crew', [])
                    directors = [c for c in crew if c.get('job') == 'Director']
                    for idx, director in enumerate(directors[:5]):  # Top 5 directors
                        credit = Credit(
                            movie_id=movie.id,
                            person_id=director['id'],
                            role='director',
                            person_name=director['name'],
                            character_name=None,
                            credit_order=idx
                        )
                        db.session.add(credit)

                    # Cast
                    cast = credits.get('cast', [])
                    for actor in cast[:10]:  # Top 10 actors
                        credit = Credit(
                            movie_id=movie.id,
                            person_id=actor['id'],
                            role='actor',
                            person_name=actor['name'],
                            character_name=actor.get('character'),
                            credit_order=actor.get('order', 999)
                        )
                        db.session.add(credit)

                    # Commit everything and return
                    db.session.commit()
                    return movie
        
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"    ⚠️  Attempt {attempt + 1}/{max_retries} failed, retrying...")
                time.sleep(1)
                continue
            print(f"    ❌ Error saving movie after {max_retries} attempts: {e}")
            return None
    
    return None

def process_movie(movie_id, basic_movie, idx, total):
    """Process a single movie (fetch details and save to DB)."""
    try:
        # Fetch full details
        full_movie = fetch_movie_details(movie_id)
        if not full_movie:
            return None, f"[{idx}/{total}] ❌ Failed to fetch: {basic_movie.get('title', 'Unknown')}"
        
        # Save to database
        movie = save_movie_to_db(full_movie)
        if movie:
            return movie, f"[{idx}/{total}] ✓ {basic_movie.get('title', 'Unknown')}"
        else:
            return None, f"[{idx}/{total}] ⚠️ Skipped: {basic_movie.get('title', 'Unknown')}"
    except Exception as e:
        return None, f"[{idx}/{total}] ❌ Error: {basic_movie.get('title', 'Unknown')} - {e}"

def main():
    """Main execution function with batch processing."""
    print("=" * 70)
    print("TMDB Movie Fetcher - BATCH MODE")
    print("=" * 70)
    print(f"Target: {TARGET_TOTAL_MOVIES:,} movies")
    print(f"Batch size: {BATCH_SIZE:,} movies")
    print(f"Total batches: {TARGET_TOTAL_MOVIES // BATCH_SIZE}")
    print("=" * 70)
    
    # Load checkpoint
    checkpoint = load_checkpoint()
    processed_ids = set(checkpoint.get('processed_ids', []))
    start_batch = checkpoint.get('current_batch', 0)
    
    if processed_ids:
        print(f"\n📋 Resuming from checkpoint:")
        print(f"   Already processed: {len(processed_ids)} movies")
        print(f"   Starting from batch: {start_batch + 1}\n")
    
    num_batches = TARGET_TOTAL_MOVIES // BATCH_SIZE
    pages_per_batch = BATCH_SIZE // MOVIES_PER_PAGE
    
    total_saved = len([mid for mid in processed_ids if mid > 0])  # Count actual saves (not skips)
    
    for batch_num in range(start_batch, num_batches):
        print(f"\n{'=' * 70}")
        print(f"📦 BATCH {batch_num + 1}/{num_batches}")
        print(f"   Target movies: {batch_num * BATCH_SIZE + 1} - {(batch_num + 1) * BATCH_SIZE}")
        print(f"{'=' * 70}\n")
        
        # Calculate page range for this batch
        start_page = batch_num * pages_per_batch + 1
        
        print(f"[1/3] Fetching movie IDs for batch {batch_num + 1}...")
        batch_movies = fetch_batch_pages(start_page, pages_per_batch)
        print(f"✓ Fetched {len(batch_movies)} movies for this batch\n")
        
        if not batch_movies:
            print(f"⚠️ No movies found for batch {batch_num + 1}, skipping...\n")
            continue
        
        # Filter already processed
        remaining_movies = {m['id']: m for m in batch_movies if m['id'] not in processed_ids}
        
        if not remaining_movies:
            print(f"✅ All movies in batch {batch_num + 1} already processed!\n")
            save_checkpoint(list(processed_ids), batch_num + 1)
            continue
        
        print(f"[2/3] Processing {len(remaining_movies)} movies (20 parallel workers)...\n")
        
        batch_saved = 0
        batch_skipped = 0
        checkpoint_interval = 50
        
        # Process movies in parallel
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {
                executor.submit(process_movie, movie_id, basic_movie, idx, len(remaining_movies)): movie_id
                for idx, (movie_id, basic_movie) in enumerate(remaining_movies.items(), 1)
            }
            
            for future in as_completed(futures):
                movie_id = futures[future]
                movie, message = future.result()
                print(message)
                
                if movie:
                    batch_saved += 1
                    processed_ids.add(movie_id)
                    
                    # Checkpoint every N movies
                    if (batch_saved + batch_skipped) % checkpoint_interval == 0:
                        save_checkpoint(list(processed_ids), batch_num)
                        print(f"\n💾 Checkpoint: {len(processed_ids)} total processed\n")
                else:
                    batch_skipped += 1
                    processed_ids.add(movie_id)
        
        total_saved += batch_saved
        
        # Save checkpoint after batch
        save_checkpoint(list(processed_ids), batch_num + 1)
        
        print(f"\n[3/3] Batch {batch_num + 1} complete!")
        print(f"   Batch: {batch_saved} saved, {batch_skipped} skipped")
        print(f"   Overall: {len(processed_ids)}/{TARGET_TOTAL_MOVIES} movies processed\n")
    
    print(f"\n{'=' * 70}")
    print(f"✅ ALL BATCHES COMPLETED!")
    print(f"{'=' * 70}")
    print(f"Total processed: {len(processed_ids)}")
    print(f"{'=' * 70}\n")
    
    # Verification
    print("Verification...")
    with app.app_context():
        movie_count = Movie.query.count()
        genre_count = Genre.query.count()
        keyword_count = Keyword.query.count()
        credit_count = Credit.query.count()
        
        print(f"✓ Movies in database: {movie_count}")
        print(f"✓ Genres: {genre_count}")
        print(f"✓ Keywords: {keyword_count}")
        print(f"✓ Credits: {credit_count}\n")
    
    # Clear checkpoint on success
    clear_checkpoint()
    
    print("=" * 80)
    print("DATABASE POPULATION COMPLETE!")
    print("=" * 80)
    print(f"✓ Movies: {movie_count:,}")
    print(f"✓ Genres: {genre_count:,}")
    print(f"✓ Keywords: {keyword_count:,}")
    print(f"✓ Credits: {credit_count:,}")
    print(f"\nSaved: {saved_count}, Skipped: {skipped_count}")
    print(f"Success Rate: {(saved_count/(saved_count+skipped_count)*100):.1f}%")
    print()
    print("Next step: Run the embedding generation script")
    print("=" * 80)

if __name__ == '__main__':
    main()
