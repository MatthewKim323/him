# Deployment Guide - HIM Backend

This guide covers deploying the HIM backend to Railway.

## Prerequisites

1. A Railway account (sign up at [railway.app](https://railway.app))
2. Railway CLI installed (optional, but helpful)
3. PostgreSQL database (Railway provides this)

## Step 1: Prepare Your Code

Make sure all your code is committed to a Git repository (GitHub, GitLab, etc.):

```bash
cd backend
git init  # if not already a git repo
git add .
git commit -m "Initial backend implementation"
git remote add origin <your-repo-url>
git push -u origin main
```

## Step 2: Deploy to Railway

### Option A: Deploy via Railway Dashboard (Recommended)

1. **Go to Railway Dashboard**
   - Visit [railway.app](https://railway.app) and sign in
   - Click "New Project"
   - Select "Deploy from GitHub repo" (or GitLab/Bitbucket)

2. **Connect Your Repository**
   - Select your repository
   - Railway will detect it's a Python project

3. **Configure the Service**
   - Railway should auto-detect the `Procfile`
   - Set the root directory to `backend` (if your repo has both frontend and backend)
   - Or deploy the backend folder as a separate service

4. **Add PostgreSQL Database**
   - In your Railway project, click "New"
   - Select "Database" → "Add PostgreSQL"
   - Railway will create a PostgreSQL instance
   - Copy the connection string (you'll need it for environment variables)

5. **Set Environment Variables**
   - Go to your service → "Variables" tab
   - Add the following variables:

```
DATABASE_URL=<your-postgresql-connection-string>
SECRET_KEY=<generate-a-random-secret-key-min-32-chars>
ACCESS_TOKEN_EXPIRE_MINUTES=30
MAX_UPLOAD_SIZE_MB=100
TEMP_VIDEO_DIR=/tmp/him_videos
MIN_DETECTION_CONFIDENCE=0.5
MIN_TRACKING_CONFIDENCE=0.5
```

   **To generate a secret key:**
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

6. **Deploy**
   - Railway will automatically deploy when you push to your main branch
   - Or click "Deploy" in the dashboard
   - Wait for deployment to complete

### Option B: Deploy via Railway CLI

1. **Install Railway CLI**
   ```bash
   npm i -g @railway/cli
   railway login
   ```

2. **Initialize Railway Project**
   ```bash
   cd backend
   railway init
   ```

3. **Add PostgreSQL**
   ```bash
   railway add postgresql
   ```

4. **Set Environment Variables**
   ```bash
   railway variables set SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
   railway variables set ACCESS_TOKEN_EXPIRE_MINUTES=30
   railway variables set MAX_UPLOAD_SIZE_MB=100
   # DATABASE_URL is automatically set by Railway when you add PostgreSQL
   ```

5. **Deploy**
   ```bash
   railway up
   ```

## Step 3: Verify Deployment

1. **Check Logs**
   - In Railway dashboard, go to "Deployments" → Click on your deployment
   - Check "Logs" tab for any errors

2. **Test the API**
   - Railway provides a public URL (e.g., `https://your-app.railway.app`)
   - Test the health endpoint:
     ```bash
     curl https://your-app.railway.app/health
     ```
   - Should return: `{"status":"healthy"}`

3. **Test API Endpoints**
   ```bash
   # Register a user
   curl -X POST https://your-app.railway.app/api/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"testpass123"}'
   
   # Login
   curl -X POST https://your-app.railway.app/api/auth/login \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=test@example.com&password=testpass123"
   ```

## Step 4: Update Frontend CORS (If Needed)

If your frontend is on a different domain, update CORS settings in `backend/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.com"],  # Update this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Step 5: Database Migrations

The app will automatically create tables on first run. However, for production, consider using Alembic for migrations:

```bash
pip install alembic
alembic init alembic
# Configure alembic.ini and create initial migration
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify `DATABASE_URL` is set correctly
   - Check PostgreSQL service is running in Railway
   - Ensure connection string format: `postgresql://user:pass@host:port/dbname`

2. **Import Errors**
   - Make sure you're running from the `backend` directory
   - Check that all dependencies are in `requirements.txt`

3. **Port Issues**
   - Railway sets `$PORT` automatically
   - The Procfile uses `$PORT` - don't hardcode ports

4. **File Upload Issues**
   - Check `TEMP_VIDEO_DIR` is writable
   - Railway's filesystem is ephemeral - files are deleted on restart
   - Consider using cloud storage (S3) for production

### Viewing Logs

```bash
# Via CLI
railway logs

# Or in Railway dashboard
# Go to your service → Deployments → Click deployment → Logs tab
```

## Production Considerations

1. **Use Environment-Specific Settings**
   - Create separate `.env` files for dev/staging/prod
   - Never commit `.env` files

2. **Database Backups**
   - Railway PostgreSQL includes automatic backups
   - Consider additional backup strategy for production

3. **Video Storage**
   - Current setup processes and deletes videos
   - For production, consider:
     - AWS S3 / Google Cloud Storage
     - Store processed data, delete videos after analysis
     - Implement video compression

4. **Rate Limiting**
   - Add rate limiting to prevent abuse
   - Consider using `slowapi` or similar

5. **Monitoring**
   - Set up error tracking (Sentry, etc.)
   - Monitor API performance
   - Set up alerts for failures

6. **Security**
   - Use strong `SECRET_KEY` (32+ characters)
   - Enable HTTPS (Railway does this automatically)
   - Review CORS settings
   - Consider API key authentication for additional security

## Local Testing Before Deployment

Test locally first:

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up local PostgreSQL or use SQLite for testing
# For PostgreSQL:
export DATABASE_URL="postgresql://user:pass@localhost/him_db"

# 4. Run migrations (tables auto-create, but you can use Alembic)
# Or just run the app - tables will be created automatically

# 5. Run the server
uvicorn main:app --reload

# 6. Test endpoints
curl http://localhost:8000/health
```

## Next Steps

After deployment:
1. Test all API endpoints
2. Update frontend to use production API URL
3. Set up monitoring and alerts
4. Configure custom domain (optional, in Railway settings)
5. Set up CI/CD for automatic deployments

## Support

- Railway Docs: https://docs.railway.app
- FastAPI Docs: https://fastapi.tiangolo.com
- Check Railway logs for detailed error messages
