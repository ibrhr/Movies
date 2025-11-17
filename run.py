"""
Run the Flask application.
"""
import os
from dotenv import load_dotenv
from app import create_app

# Load environment variables from .env file
load_dotenv()

# Verify critical environment variables
print("=" * 60)
print("🔍 Environment Check")
print("=" * 60)
api_key = os.getenv('OPENROUTER_API_KEY')
if api_key:
    print(f"✅ OPENROUTER_API_KEY is set (length: {len(api_key)})")
else:
    print("❌ OPENROUTER_API_KEY is NOT set")
print("=" * 60)

app = create_app(os.getenv('FLASK_CONFIG') or 'development')

if __name__ == '__main__':
    # Run with reloader enabled to pick up template changes
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
