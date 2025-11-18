# 📱 REST API Documentation

Complete REST API documentation for mobile app integration.

**Base URL:** `http://localhost:5000/api/v1`

---

## 🔐 Authentication

All authenticated endpoints require a JWT token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

### Register New User

**Endpoint:** `POST /api/v1/auth/register`

**Request Body:**
```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepassword123"
}
```

**Response (201):**
```json
{
  "success": true,
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com"
  }
}
```

---

### Login

**Endpoint:** `POST /api/v1/auth/login`

**Request Body:**
```json
{
  "email": "john@example.com",
  "password": "securepassword123"
}
```

**Response (200):**
```json
{
  "success": true,
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com"
  }
}
```

**Token expires in:** 30 days

---

## 🎬 Movie Endpoints

### Get Movies List

**Endpoint:** `GET /api/v1/movies`

**Query Parameters:**
- `page` (int, default: 1) - Page number
- `per_page` (int, default: 20, max: 100) - Items per page
- `genre` (string) - Filter by genre name (e.g., "Action", "Drama")
- `search` (string) - Search in title and overview
- `sort` (string) - Sort by: `popularity`, `rating`, `release_date`
- `year_min` (int) - Minimum release year
- `year_max` (int) - Maximum release year

**Example:** `GET /api/v1/movies?page=1&per_page=20&genre=Action&sort=rating&year_min=2020`

**Response (200):**
```json
{
  "success": true,
  "movies": [
    {
      "id": 550,
      "title": "Fight Club",
      "overview": "A ticking-time-bomb insomniac...",
      "release_date": "1999-10-15",
      "poster_path": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
      "backdrop_path": "/fCayJrkfRaCRCTh8GqN30f8oyQF.jpg",
      "vote_average": 8.4,
      "vote_count": 26280,
      "popularity": 61.416,
      "runtime": 139,
      "content_rating": "R",
      "genres": ["Drama", "Thriller", "Comedy"]
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 5000,
    "pages": 250,
    "has_next": true,
    "has_prev": false
  }
}
```

---

### Get Movie Details

**Endpoint:** `GET /api/v1/movies/<movie_id>`

**Example:** `GET /api/v1/movies/550`

**Response (200):**
```json
{
  "success": true,
  "movie": {
    "id": 550,
    "title": "Fight Club",
    "overview": "A ticking-time-bomb insomniac...",
    "release_date": "1999-10-15",
    "poster_path": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
    "backdrop_path": "/fCayJrkfRaCRCTh8GqN30f8oyQF.jpg",
    "vote_average": 8.4,
    "vote_count": 26280,
    "popularity": 61.416,
    "runtime": 139,
    "content_rating": "R",
    "genres": ["Drama", "Thriller", "Comedy"],
    "budget": 63000000,
    "revenue": 100853753,
    "tagline": "Mischief. Mayhem. Soap.",
    "homepage": "http://www.foxmovies.com/movies/fight-club",
    "status": "Released",
    "original_language": "en",
    "user_interaction": {
      "in_watchlist": false,
      "watched": true,
      "rating": 9,
      "skipped": false
    }
  }
}
```

**Note:** `user_interaction` is only included for authenticated users.

---

### Mark as Watched

**Endpoint:** `POST /api/v1/interactions/watch/<movie_id>` 🔐

**Example:** `POST /api/v1/interactions/watch/550`

**Response (201):**
```json
{
  "success": true,
  "message": "Added \"Fight Club\" to your watch history!",
  "already_watched": false
}
```

---

### Rate Movie

**Endpoint:** `POST /api/v1/interactions/rate/<movie_id>` 🔐

**Request Body:**
```json
{
  "rating": 9
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Rated \"Fight Club\" 9/10",
  "is_update": false
}
```

**Note:** Rating must be an integer between 0-10. Automatically marks movie as watched.

---

### Skip Movie (Not Interested)

**Endpoint:** `POST /api/v1/interactions/skip/<movie_id>` 🔐

**Example:** `POST /api/v1/interactions/skip/550`

**Response (201):**
```json
{
  "success": true,
  "message": "Marked \"Fight Club\" as not interested."
}
```

---

### Get Watchlist

**Endpoint:** `GET /api/v1/watchlist` 🔐

**Query Parameters:**
- `page` (int, default: 1) - Page number
- `per_page` (int, default: 20, max: 100) - Items per page

**Response (200):**
```json
{
  "success": true,
  "movies": [
    {
      "id": 550,
      "title": "Fight Club",
      "overview": "A ticking-time-bomb insomniac...",
      "release_date": "1999-10-15",
      "poster_path": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
      "vote_average": 8.4,
      "runtime": 139,
      "content_rating": "R",
      "genres": ["Drama", "Thriller", "Comedy"]
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 15,
    "pages": 1
  }
}
```

---

### Add to Watchlist

**Endpoint:** `POST /api/v1/watchlist/<movie_id>` 🔐

**Example:** `POST /api/v1/watchlist/550`

**Response (201):**
```json
{
  "success": true,
  "message": "Added \"Fight Club\" to your watchlist!"
}
```

---

### Remove from Watchlist

**Endpoint:** `DELETE /api/v1/watchlist/<movie_id>` 🔐

**Example:** `DELETE /api/v1/watchlist/550`

**Response (200):**
```json
{
  "success": true,
  "message": "Removed \"Fight Club\" from your watchlist."
}
```

---

### Get Watched Movies

**Endpoint:** `GET /api/v1/watched` 🔐

**Query Parameters:**
- `page` (int, default: 1) - Page number
- `per_page` (int, default: 20, max: 100) - Items per page

**Response (200):**
```json
{
  "success": true,
  "movies": [
    {
      "id": 550,
      "title": "Fight Club",
      "overview": "A ticking-time-bomb insomniac...",
      "release_date": "1999-10-15",
      "poster_path": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
      "vote_average": 8.4,
      "runtime": 139,
      "content_rating": "R",
      "genres": ["Drama", "Thriller", "Comedy"],
      "watched_at": "2024-11-10T15:30:00",
      "user_rating": 9
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 42,
    "pages": 3
  }
}
```

---

### Get User Profile

**Endpoint:** `GET /api/v1/profile` 🔐

**Response (200):**
```json
{
  "success": true,
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com",
    "created_at": "2024-01-15T10:30:00"
  },
  "statistics": {
    "watchlist_count": 15,
    "watched_count": 42,
    "ratings_count": 38,
    "average_rating": 7.8
  }
}
```

---

## ❌ Error Responses

All endpoints return consistent error responses:

**400 Bad Request:**
```json
{
  "success": false,
  "message": "Rating must be between 0 and 10"
}
```

**401 Unauthorized:**
```json
{
  "msg": "Missing Authorization Header"
}
```

**404 Not Found:**
```json
{
  "success": false,
  "message": "Movie not found"
}
```

**500 Internal Server Error:**
```json
{
  "success": false,
  "message": "Failed to generate recommendations: <error_details>"
}
```

---

## 🔧 Development Testing

### Using cURL

**Login:**
```bash
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'
```

**Get Movies (with token):**
```bash
curl -X GET http://localhost:5000/api/v1/movies?page=1&per_page=10 \
  -H "Authorization: Bearer <your_jwt_token>"
```

**Rate a Movie:**
```bash
curl -X POST http://localhost:5000/api/v1/interactions/rate/550 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -d '{"rating":9}'
```

### Using Python Requests

```python
import requests

BASE_URL = "http://localhost:5000/api/v1"

# Login
response = requests.post(f"{BASE_URL}/auth/login", json={
    "email": "user@example.com",
    "password": "password123"
})
token = response.json()["access_token"]

# Get recommendations
headers = {"Authorization": f"Bearer {token}"}
recommendations = requests.get(
    f"{BASE_URL}/recommendations?limit=10",
    headers=headers
)
print(recommendations.json())
```

---

## 🚀 Production Considerations

1. **JWT Secret:** Set `JWT_SECRET_KEY` environment variable
2. **CORS Origins:** Configure allowed origins in `flask_app/__init__.py`
3. **Rate Limiting:** Consider adding Flask-Limiter
4. **HTTPS:** Use HTTPS in production (tokens in plain HTTP are insecure)
5. **Token Refresh:** Implement token refresh endpoint for better UX
6. **API Versioning:** Current version is v1, plan for v2 migrations

---

## 📖 Additional Resources

- **Web UI:** `http://localhost:5000` (Flask templates)
- **API Base:** `http://localhost:5000/api/v1` (JSON responses)
- **Database:** SQLite at `data/movies.db`
- **Embeddings:** NumPy array at `data/embeddings.npy`
