#!/bin/bash

# Run Chatter Server
# This script starts the FastAPI server for local development

echo "🚀 Starting Chatter Server..."
echo ""

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Virtual environment not activated. Activating..."
    source .venv/bin/activate
fi

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt -q
fi

echo "✅ Environment ready"
echo ""
echo "📍 Server will be available at:"
echo "   - API: http://127.0.0.1:8000"
echo "   - Docs: http://127.0.0.1:8000/docs"
echo "   - ReDoc: http://127.0.0.1:8000/redoc"
echo ""
echo "🔗 Available endpoints:"
echo "   - POST /accounts/register - Register new account"
echo "   - POST /auth/login - Login"
echo "   - GET /accounts/me - Get account info (requires auth)"
echo "   - PATCH /accounts/me - Update account (requires auth)"
echo "   - POST /accounts/reset-password - Reset password (requires auth)"
echo "   - DELETE /accounts/me - Delete account (requires auth)"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run the server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
