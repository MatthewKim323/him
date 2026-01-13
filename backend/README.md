# HIM Backend API

Backend API for mechanical tension analysis from workout videos.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your database URL and secret key
```

3. Initialize database:
```bash
# PostgreSQL should be running
# Tables will be created automatically on first run
```

4. Run the server:
```bash
uvicorn main:app --reload
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get token

### Workouts
- `POST /api/workouts/analyze` - Upload video and analyze
- `GET /api/workouts/{id}` - Get workout analysis
- `GET /api/workouts` - List user workouts
- `DELETE /api/workouts/{id}` - Delete workout

## Deployment

The app is configured for Railway deployment. 

**See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.**

Quick steps:
1. Push code to GitHub/GitLab
2. Create Railway project and connect repository
3. Add PostgreSQL database service
4. Set environment variables (see DEPLOYMENT.md)
5. Deploy!

The app will automatically create database tables on first run.
