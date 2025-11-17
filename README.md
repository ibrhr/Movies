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

### Quick Start (Local Development)

1. **Clone the project and setup**
   ```bash
   git clone <repo-url>
   cd Movies
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Create .env file with your API keys**
   ```bash
   cp .env.example .env
   # Edit .env and add your TMDB_API_KEY and OPENROUTER_API_KEY
   ```

3. **Run the app**
   ```bash
   python run.py
   ```
   - Open http://localhost:5000 in your browser
   - Create an account and start watching!

### Docker Deployment

1. **Build and run with Docker**
   ```bash
   docker-compose up -d
   ```
   - App runs on http://localhost
   - No port number needed!

2. **Check logs**
   ```bash
   docker-compose logs -f
   ```

3. **Stop the app**
   ```bash
   docker-compose down
   ```

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

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with these required variables:

```bash
# TMDB API (get from https://www.themoviedb.org/settings/api)
TMDB_API_KEY=your_key_here
TMDB_BASE_URL=https://api.themoviedb.org/3

# OpenRouter API (get from https://openrouter.ai/)
OPENROUTER_API_KEY=your_key_here

# Database (PostgreSQL URL)
DATABASE_URL=postgresql://user:password@localhost:5432/movies

# Flask settings
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here
FLASK_ENV=production

# Optional: ProtonMail for sending emails
PROTON_SMTP_SERVER=smtp.protonmail.ch
PROTON_SMTP_PORT=587
PROTON_EMAIL=your_email@proton.me
PROTON_PASSWORD=your_password
PROTON_FROM_EMAIL=your_email@proton.me
PROTON_USE_TLS=true
```

## 📊 Data Management

### Adding More Movies

```bash
# Fetch additional movies (respects existing data)
python scripts/fetch_tmdb_data.py --force

# Update embeddings for new movies
python scripts/generate_embeddings_openrouter.py
```

### Database Maintenance

```bash
# Check database integrity
python scripts/cleanup_database.py

# Add content ratings to existing movies
python scripts/update_content_ratings.py

# Fix image paths (if needed)
python scripts/update_image_paths.py
```

### Reset Embeddings

```bash
# Remove all embeddings (forces full regeneration)
python scripts/wipe_embeddings.py

# Regenerate from scratch
python scripts/generate_embeddings_openrouter.py
```

## 🔐 Security Features

- **Password Hashing:** Werkzeug's `generate_password_hash` with salt
- **Session Management:** Flask-Login with secure cookies
- **CSRF Protection:** Flask-WTF form validation
- **Password Reset Tokens:** Timed tokens with URLSafeTimedSerializer (1-hour expiration)
- **Email Enumeration Protection:** Consistent responses whether email exists or not
- **SQL Injection Prevention:** SQLAlchemy ORM parameterized queries
- **Input Validation:** WTForms validators for all user inputs

## 📧 Email Setup

### Using ProtonMail Bridge (Free Account)

1. **Install ProtonMail Bridge**
   - Download from: https://proton.me/mail/bridge
   - Install and sign in with your ProtonMail account

2. **Get Bridge Credentials**
   - Open Bridge → Settings → Account
   - Copy the SMTP password (NOT your ProtonMail password)

3. **Configure .env**
   ```bash
   PROTON_SMTP_SERVER=127.0.0.1
   PROTON_SMTP_PORT=1025
   PROTON_EMAIL=your_email@proton.me
   PROTON_PASSWORD=your_bridge_password
   PROTON_USE_TLS=false
   ```

4. **Test Configuration**
   ```bash
   python test_email.py
   ```

For detailed setup instructions, see [docs/EMAIL_FEATURES.md](docs/EMAIL_FEATURES.md).

## 🐛 Troubleshooting

**App won't start:**
- Check that all required environment variables are set in `.env`
- Make sure PORT 5000 (or your chosen port) is not in use
- Check the logs: `docker-compose logs` (Docker) or console output (local)

**No movie recommendations:**
- Watch and rate at least one movie first
- Recommendations appear after you've built a profile

**Search not working:**
- Verify `OPENROUTER_API_KEY` is set correctly in `.env`
- Check your OpenRouter account at https://openrouter.ai/

**Database connection errors:**
- Make sure PostgreSQL is running
- Check `DATABASE_URL` in `.env` is correct
- Format: `postgresql://username:password@host:port/database`

**Email not sending:**
- Verify ProtonMail credentials in `.env` are correct
- Make sure you're using app password (not account password)
- Check that SMTP settings are configured

## � More Information

- **API Documentation** - See `docs/API_DOCUMENTATION.md` for REST API details
- **Deployment Guide** - See `DEPLOYMENT.md` for production setup
- **Email Setup** - See documentation for ProtonMail configuration

## 🤝 Contributing

Found a bug? Have a feature idea? Contributions are welcome!

## 📝 License

MIT License

## 🛠️ Development

### Running Tests

```bash
# Run test suite (if implemented)
pytest tests/

# Test specific module
pytest tests/test_recommender.py
```

### Code Style

```bash
# Format code
black .

# Lint
flake8 flask_app/ scripts/
```

### Database Migrations

```bash
# Create migration
flask db migrate -m "description"

# Apply migration
flask db upgrade

# Rollback
flask db downgrade
```

## 📈 Performance

- **Recommendation Generation:** ~50-200ms for 20 recommendations
- **Smart Search:** ~500-1000ms (includes OpenRouter API call)
- **Traditional Search:** ~10-50ms with indexes
- **Page Load:** ~100-300ms (cached templates)

**Optimization Tips:**
- Embeddings loaded once at startup (global variables)
- NumPy vectorized operations for similarity calculations
- Database indexes on frequently queried columns
- Pagination prevents large data transfers


## 📝 License

MIT License - See LICENSE file for details.

## 🙏 Attribution

- **Movie Data:** [The Movie Database (TMDB)](https://www.themoviedb.org/) - This product uses the TMDB API but is not endorsed or certified by TMDB.
- **Embeddings:** OpenAI text-embedding-3-small via [OpenRouter](https://openrouter.ai/)
- **UI Framework:** [Bootstrap 5](https://getbootstrap.com/)
- **Icons:** [Bootstrap Icons](https://icons.getbootstrap.com/)

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing documentation in `/docs`
- Review troubleshooting section above

---

**Built with ❤️ using Flask, NumPy, and modern ML embeddings**
