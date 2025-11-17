# 🎬 Movie Recommender

A web application that learns what movies you like and recommends new ones tailored to your taste. Watch movies, rate them, and get personalized suggestions powered by machine learning.

**What it does:**
- Recommends movies based on your watch history and ratings
- Search by movie title, actor, director, or even describe the vibe you want
- Track your watch history and see stats about your viewing habits
- Web interface for browsing and discovering new films
- REST API for developers and mobile apps

## Features

### Smart Recommendations
- Gets smarter as you watch and rate more movies
- Shows you why each movie is recommended
- Adjustable diversity slider (find similar movies or discover something completely new)
- Learns what you skip to avoid bad suggestions

### Smart Search
- Search by movie title, actor, or director
- Describe what you want: "dark sci-fi thriller" or "feel-good comedy"
- Filter by content rating and release year

### Your Profile
- Track what you've watched and when
- Rate movies to help the algorithm learn your taste
- View your watch history and viewing stats
- Mark movies as "not interested" to improve suggestions

### Secure & Private
- Password-protected accounts
- Secure login with session management
- Password reset via email if you forget
- Delete your data anytime

## 🏗️ Tech Stack

- **Backend:** Flask (Python web framework)
- **Database:** PostgreSQL 
- **AI/ML:** OpenAI embeddings via OpenRouter API
- **Movie Data:** The Movie Database (TMDB)
- **Frontend:** HTML, CSS, JavaScript with Tailwind CSS
- **Deployment:** Docker, Gunicorn

## 🚀 Getting Started

### Requirements
- Python 3.8 or higher
- Docker and Docker Compose (optional, for easy deployment)
- API keys (free):
  - [TMDB API](https://www.themoviedb.org/settings/api) - Movie database
  - [OpenRouter API](https://openrouter.ai/) - AI embeddings


## 📖 How It Works

### The Recommendation Algorithm

The app learns from your behavior:

1. **Watches & Ratings** - What you watch and how you rate it
2. **Similarity Matching** - Finds movies similar to ones you liked
3. **Diversity** - Avoids recommending the same type of movie over and over
4. **Learning** - Gets better as you watch more

The algorithm balances:
- **Relevance:** Movies similar to what you like
- **Discovery:** New and different recommendations
- **Popularity:** Highly-rated movies from the community

### Smart Search

Natural language search powered by AI:
- Search: "dark sci-fi thriller" → gets sci-fi thrillers
- Search: "feel-good animated movie" → gets uplifting animated films
- Traditional search also available (search by title, actor, director)


## 🤝 Contributing

Found a bug? Have a feature idea? Contributions are welcome!

## 📝 License

MIT License

## 🙏 Attribution

- **Movie Data:** [The Movie Database (TMDB)](https://www.themoviedb.org/) - This product uses the TMDB API but is not endorsed or certified by TMDB.
- **Embeddings:** OpenAI text-embedding-3-small via [OpenRouter](https://openrouter.ai/)