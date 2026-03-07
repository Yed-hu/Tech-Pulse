---
title: Tech Pulse
emoji: 📰
colorFrom: gray
colorTo: purple
sdk: docker
app_file: main.py
pinned: false
---

# Tech Pulse

> Daily AI-powered tech briefing — Hacker News + GPT-4o

[![Live App](https://img.shields.io/badge/Live%20App-GitHub%20Pages-00e5ff?style=flat-square&logo=github)](https://yed-hu.github.io/Tech-Pulse/)
[![Backend](https://img.shields.io/badge/Backend-Hugging%20Face-ff6b6b?style=flat-square&logo=huggingface)](https://ydhu-tech-pulse.hf.space)
[![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)

---

## What Is This?

Tech Pulse is a personal daily briefing app that automatically:

1. Fetches the **top 40 stories** from Hacker News in real time
2. Sends them to **GPT-4o** for summarisation and categorisation
3. Presents a clean, **AI-written briefing** tailored for data and tech professionals

---

## Features

- **Real-time news** — 40 Hacker News front page stories per fetch
- **AI digest** — 4-5 sentence big-picture overview of the day's themes
- **Detailed summaries** — 3-4 sentences per article, written for data professionals
- **Topic filters** — All Topics / AI & ML / Data & Analytics / Cloud & DevOps / Startups
- **Server health check** — automatic backend status on page load
- **Live clock** — real-time date and time display
- **Dark theme** — clean, minimal UI with cyan/purple accents
- **Responsive** — works on desktop and mobile

---

## Architecture

```
Browser (GitHub Pages)
        │
        │  POST /api/briefing
        ▼
Python FastAPI (Hugging Face Spaces)
        │
        ├── GET hn.algolia.com  ──→  40 real HN stories
        │
        └── POST GitHub Models  ──→  GPT-4o summarises
                                         │
                                         ▼
                              JSON { digest, articles[] }
                                         │
                                         ▼
                              Frontend renders briefing
```

---

## Tech Stack

| Layer | Technology | Hosting |
|---|---|---|
| Frontend | HTML / CSS / JavaScript | GitHub Pages |
| Backend | Python FastAPI | Hugging Face Spaces |
| AI Model | GPT-4o via GitHub Models | Azure (free tier) |
| News Data | Hacker News Algolia API | Free, no key needed |
| Container | Docker | Hugging Face |

**Total cost: $0/month** — everything runs on free tiers.

---

## Project Structure

```
Tech-Pulse/
├── main.py              # FastAPI backend — all server logic
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container config for Hugging Face
├── render.yaml          # Render.com config (legacy)
├── runtime.txt          # Python version pin
├── .env                 # Local secrets — never committed
├── .gitignore           # Protects secrets from Git
├── README.md            # This file
├── index.html           # Frontend — served by GitHub Pages
└── public/
    └── index.html       # Frontend — served by FastAPI locally
```

---

## Running Locally

### Prerequisites
- Python 3.11+
- A GitHub Personal Access Token (for GPT-4o access)

### Setup

```bash
# Clone the repo
git clone https://github.com/Yed-hu/Tech-Pulse.git
cd Tech-Pulse

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo "GITHUB_TOKEN=your_token_here" > .env
echo "PORT=8000" >> .env

# Start the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

### Getting a GitHub Token
1. GitHub → Profile → Settings → Developer Settings
2. Personal access tokens → Tokens (classic) → Generate new token
3. No special scopes needed — just generate and copy

---

## Deployment

### Backend — Hugging Face Spaces

```bash
# Add Hugging Face as a remote
git remote add huggingface https://huggingface.co/spaces/Ydhu/tech-pulse

# Deploy
git push huggingface main
```

Set these secrets in your Hugging Face Space settings:
- `GITHUB_TOKEN` — your GitHub personal access token
- `FRONTEND_URL` — your GitHub Pages URL

### Frontend — GitHub Pages

Push to `origin main` — GitHub Pages auto-deploys within 1-2 minutes.

```bash
# After any frontend change
cp index.html public/index.html
git add index.html public/index.html
git commit -m "description"
git push origin main
git push huggingface main
```

---

## API Endpoints

### `GET /health`
Returns server status and token configuration.

```json
{
  "status": "ok",
  "message": "Tech Pulse v3 is running!",
  "token_configured": true,
  "timestamp": "2026-03-07T10:00:00"
}
```

### `POST /api/briefing`
Returns AI-generated briefing from today's HN stories.

**Request:**
```json
{ "topics": "all", "date": "Saturday, 7 March 2026" }
```

**topics options:** `all` | `ai` | `data` | `cloud` | `startups`

**Response:**
```json
{
  "digest": "4-5 sentence overview of today...",
  "articles": [
    {
      "title": "Story title",
      "summary": "3-4 sentence summary...",
      "category": "ai",
      "source": "openai.com",
      "url": "https://..."
    }
  ],
  "fetched_at": "2026-03-07T10:00:00",
  "model": "gpt-4o via GitHub Models",
  "hn_stories_fetched": 40
}
```

---

## Security

- `GITHUB_TOKEN` lives only on the server — never exposed to the browser
- `.env` is excluded from Git via `.gitignore`
- Production secrets stored as encrypted Hugging Face Secrets
- CORS uses `allow_origins=["*"]` — safe as there are no user sessions

---

## What I Learned Building This

| Concept | Where Applied |
|---|---|
| Python FastAPI | REST API backend |
| Pydantic validation | Request body parsing |
| async/await + httpx | Non-blocking API calls |
| CORS middleware | Cross-domain browser requests |
| Docker | Hugging Face containerisation |
| Git multi-remote | Deploy to GitHub + HF simultaneously |
| GPT prompt engineering | Structured JSON output from LLMs |
| CSS custom properties | Design tokens and theming |
| JavaScript fetch() | Frontend API communication |

---

## icense

MIT — free to use and adapt.

---

*Built by [Yedhu Prasad](https://github.com/Yed-hu) — March 2026*