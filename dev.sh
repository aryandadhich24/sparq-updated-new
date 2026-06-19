#!/bin/bash
# Kill port 8000 and 3000 if occupied
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:3000 | xargs kill -9 2>/dev/null

# Start Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

# Start Frontend
cd frontend
npm run dev &
FRONTEND_PID=$!

echo "Servers started. Backend: $BACKEND_PID, Frontend: $FRONTEND_PID"
echo "Press CTRL+C to stop both."

trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
