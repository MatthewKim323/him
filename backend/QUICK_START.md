# Quick Start - Railway Deployment

## Fastest Way to Deploy

### 1. Push to GitHub
```bash
cd backend
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-github-repo-url>
git push -u origin main
```

### 2. Deploy on Railway
1. Go to [railway.app](https://railway.app) and sign in
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Railway will auto-detect Python and use the `Procfile`

### 3. Add Database
1. In Railway project, click "New" → "Database" → "Add PostgreSQL"
2. Railway creates the database automatically

### 4. Set Environment Variables
In your Railway service → "Variables" tab, add:

```
SECRET_KEY=<generate-random-key>
```

Generate secret key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Note:** `DATABASE_URL` is automatically set by Railway when you add PostgreSQL.

### 5. Deploy!
Railway will automatically deploy. Check the "Deployments" tab for status.

### 6. Test
Your API will be available at: `https://your-app.railway.app`

Test it:
```bash
curl https://your-app.railway.app/health
```

## That's It! 🚀

For detailed instructions, troubleshooting, and production tips, see [DEPLOYMENT.md](DEPLOYMENT.md).
