# Email LLM Web App

A full-stack starter project that lets you:
- paste raw notes or message content
- generate a polished email draft with OpenAI
- review and edit the subject/body in a browser
- send the email through SMTP
- deploy the frontend and backend online with a clean split

## Recommended production architecture

- **Frontend:** Next.js on **Vercel**
- **Backend:** FastAPI on **Render**
- **LLM:** OpenAI Responses API
- **Email delivery:** SMTP

This split keeps your browser UI fast and simple while protecting your OpenAI and SMTP secrets on the backend.

## Project structure

```text
email-llm-webapp/
├── backend/
│   ├── app/
│   ├── .env.example
│   ├── .python-version
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── .env.example
│   ├── package.json
│   └── tsconfig.json
├── docker-compose.yml
├── render.yaml
└── README.md
```

## Local development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Backend URLs:
- API: `http://127.0.0.1:8000`
- Docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`

### Frontend

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Frontend URL:
- `http://127.0.0.1:3000`

## Deploy backend on Render

### Option A: use the included Blueprint file

This repo includes a root `render.yaml` so you can create the backend as a Render Blueprint.

```bash
git init
git add .
git commit -m "Initial commit"
# push to GitHub/GitLab/Bitbucket
```

Then in Render:
1. Create **New > Blueprint**
2. Connect your repo
3. Render will detect `render.yaml`
4. Provide secret values when prompted
5. Deploy

### Option B: create the service manually

In Render, create a new **Web Service** and use:

- **Root Directory:** `backend`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path:** `/health`

Set these environment variables:

```env
APP_ENV=production
PYTHON_VERSION=3.13.7
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-5.4-mini
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_smtp_username
SMTP_PASSWORD=your_smtp_password
SMTP_USE_TLS=true
SMTP_FROM_EMAIL=your_email@example.com
SMTP_FROM_NAME=Your Name
ALLOW_ORIGINS=https://your-frontend-domain.vercel.app
```

After deploy, copy your live backend URL, for example:

```text
https://email-llm-api.onrender.com
```

## Deploy frontend on Vercel

Push the repo to GitHub first, then in Vercel:

1. Create a new project from the repo
2. Set **Root Directory** to `frontend`
3. Keep the detected **Next.js** framework preset
4. Add this environment variable:

```env
NEXT_PUBLIC_API_BASE_URL=https://your-backend-domain.onrender.com
```

5. Deploy

Your frontend will get a URL like:

```text
https://your-project.vercel.app
```

## Final production wiring

After the frontend is live:

1. Copy the Vercel frontend URL
2. Go back to Render
3. Update:

```env
ALLOW_ORIGINS=https://your-project.vercel.app
```

4. Redeploy the backend if needed

This allows the browser app to call your API without CORS errors.

## Common deployment issues

### Frontend shows “Backend not reachable”

Check:
- `NEXT_PUBLIC_API_BASE_URL` in Vercel
- backend is healthy at `/health`
- backend URL starts with `https://`

### CORS errors in the browser

Check `ALLOW_ORIGINS` on Render. It must match your deployed frontend URL exactly.

Examples:

```env
ALLOW_ORIGINS=https://your-project.vercel.app
```

or for multiple origins:

```env
ALLOW_ORIGINS=https://your-project.vercel.app,https://www.yourdomain.com
```

### SMTP authentication fails

Use valid SMTP credentials for your provider. For Gmail, this usually means using an app password with 2-step verification enabled.

### Cold starts on free backend hosting

If you use a free backend plan, the first request after inactivity can be slow.

## Docker setup

If you prefer local Docker:

```bash
cp backend/.env.example backend/.env
# edit backend/.env first

docker compose up --build
```

Then open:
- Frontend: `http://127.0.0.1:3000`
- Backend docs: `http://127.0.0.1:8000/docs`

## API endpoints

- `GET /`
- `GET /health`
- `POST /draft-email`
- `POST /send-email`
- `POST /generate-and-send`

## Recommended next upgrades

- login/auth for protected sending
- sent email history in a database
- reusable templates
- Gmail OAuth instead of SMTP credentials
- rate limiting and backend API auth
- domain setup for branded frontend URLs
- provider-based email sending such as Resend or SendGrid
