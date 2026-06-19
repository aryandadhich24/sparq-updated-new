# ROI Decision Intelligence

## Getting Started

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ (for local frontend dev)
- Python 3.11+ (for local backend dev)

### Running with Docker (Recommended)
```bash
docker-compose up --build
```
- Backend API Docs: http://localhost:8000/docs
- Frontend: http://localhost:3000

### Local Development

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Project Structure
- `backend/`: FastAPI application
- `frontend/`: Next.js application
- `docker-compose.yml`: Infrastructure orchestration
