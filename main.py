# ================================================================
# main.py — Tech Pulse Backend v3
# Changes from v2:
#   - Fetches 30 HN stories (was 25)
#   - Longer digest (4-5 sentences)
#   - Longer per-article summaries (3-4 sentences)
#   - CORS now accepts your GitHub Pages URL specifically
# ================================================================

import os
import json
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from datetime import datetime

load_dotenv()
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# ── Your GitHub Pages URL ────────────────────────────────────────
# Format: https://YOUR-USERNAME.github.io
# Replace with your actual GitHub username below
FRONTEND_URL = os.environ.get("FRONTEND_URL", "*")
# We read this from .env so you never hardcode your URL in code
# .env:  FRONTEND_URL=https://yourusername.github.io
# If not set, defaults to "*" (allow all) — fine for development

app = FastAPI(
    title="Tech Pulse API",
    description="Daily tech briefing — Hacker News + GPT-4o",
    version="3.0.0"
)

# ── CORS ─────────────────────────────────────────────────────────
# Allow requests from your GitHub Pages frontend
# and from localhost for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL,
        # Your deployed GitHub Pages URL
        # e.g. https://yourusername.github.io

        "http://localhost:8000",
        "http://localhost:3000",
        # Local development URLs

        "https://*.app.github.dev",
        # Codespaces URLs (wildcard)
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/public", StaticFiles(directory="public"), name="public")


# ── DATA MODELS ──────────────────────────────────────────────────
class BriefingRequest(BaseModel):
    topics: str = "all"
    date:   str = ""


# ── HACKER NEWS FETCHER ──────────────────────────────────────────
# Fetches 30 real stories from HN front page
# Sorted by points (upvotes) so GPT gets the best stories first

async def fetch_hn_top_stories(limit: int = 30) -> list:
    """
    Fetches top stories from Hacker News via Algolia API.
    Free, no API key needed, updates in real time.
    
    We fetch 30 so GPT has enough to filter by topic.
    After GPT filters for relevance, you'll get 8-12 articles.
    """
    url = f"https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage={limit}"

    print(f"  [HN] Fetching top {limit} stories...")

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    stories = []
    for hit in data.get("hits", []):
        stories.append({
            "title":    hit.get("title", "Untitled"),
            "url":      hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
            "points":   hit.get("points", 0),
            "comments": hit.get("num_comments", 0),
            "author":   hit.get("author", "unknown"),
        })

    # Sort by points — most upvoted = most important
    stories_sorted = sorted(stories, key=lambda x: x["points"], reverse=True)

    print(f"  [HN] Got {len(stories_sorted)} stories. Top: '{stories_sorted[0]['title'] if stories_sorted else 'none'}'")

    return stories_sorted


# ── PROMPT BUILDER ───────────────────────────────────────────────
# Key changes from v2:
#   - Digest is now 4-5 sentences (was 2-3)
#   - Each article summary is now 3-4 sentences (was 2-3)

def build_prompt(topics: str, date: str, hn_stories: list) -> tuple[str, str]:
    """
    Builds the GPT system prompt and user message.
    
    The longer digest and summary instructions are in the
    system prompt — GPT will follow these constraints.
    """

    topic_map = {
        "all":      "AI & Machine Learning, Data Engineering & Analytics, Cloud & DevOps, and Tech Startups",
        "ai":       "Artificial Intelligence and Machine Learning",
        "data":     "Data Engineering, Analytics, and Business Intelligence",
        "cloud":    "Cloud Computing and DevOps",
        "startups": "Tech Startups and Venture Capital"
    }
    topic_label = topic_map.get(topics, topic_map["all"])

    system_prompt = f"""You are a senior tech news analyst and briefing assistant for Yedhu Prasad,
a Data Analytics professional in the UK skilled in Python, SQL, Power BI, and Machine Learning.

You will receive a list of real Hacker News front page stories ranked by upvotes.
Your job: produce a detailed, insightful daily tech briefing from these stories.

FOCUS TOPICS: {topic_label}

STRICT OUTPUT RULES:
1. Return ONLY valid JSON — absolutely no markdown, no backticks, no explanation text
2. Only include stories relevant to the focus topics
3. Use the EXACT field names shown in the structure below
4. Do not rename, add, or remove any fields

CONTENT QUALITY RULES:
- digest: Write 4 to 5 sentences. Cover the biggest themes of the day, 
  mention specific companies or technologies, and explain what this means 
  for data and AI professionals specifically.
  
- summary (per article): Write 3 to 4 sentences minimum.
  Sentence 1: What happened and who is involved.
  Sentence 2: The technical details or context behind it.
  Sentence 3: Why this matters specifically to a data analyst or ML engineer.
  Sentence 4 (optional): What to watch for next or how to take action.

Return EXACTLY this JSON structure:
{{
  "digest": "4-5 sentence big-picture overview...",
  "articles": [
    {{
      "title":    "original story title",
      "summary":  "3-4 sentence detailed summary as described above",
      "category": "ai OR data OR cloud OR startups",
      "source":   "domain name or Hacker News",
      "url":      "original story url"
    }}
  ]
}}

Stories to process (sorted by upvotes, most popular first):
{json.dumps(hn_stories, indent=2)}

Return 8 to 12 of the most relevant articles. JSON only. No other text."""

    user_message = f"Generate today's tech briefing for {date or 'today'}. JSON only."

    return system_prompt, user_message


# ── JSON PARSER ──────────────────────────────────────────────────
def parse_ai_response(content: str) -> dict:
    """Defensively extracts and parses JSON from GPT's response."""
    clean = content.strip().replace("```json", "").replace("```", "").strip()
    start = clean.find("{")
    end   = clean.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON found in GPT response: {clean[:200]}")
    return json.loads(clean[start:end])


# ── ROUTES ───────────────────────────────────────────────────────

@app.get("/")
async def serve_frontend():
    return FileResponse("public/index.html")


@app.get("/health")
async def health_check():
    return JSONResponse({
        "status":           "ok",
        "message":          "Tech Pulse v3 is running!",
        "token_configured": bool(GITHUB_TOKEN and GITHUB_TOKEN != "your_github_token_here"),
        "timestamp":        datetime.now().isoformat()
    })


@app.post("/api/briefing")
async def get_briefing(request: BriefingRequest):
    """
    Main endpoint. Full flow:
      1. Fetch 30 real stories from Hacker News
      2. Send to GPT-4o with detailed summarisation instructions
      3. Parse, validate, and return clean JSON to frontend
    """

    if not GITHUB_TOKEN or GITHUB_TOKEN == "your_github_token_here":
        raise HTTPException(500, detail="GITHUB_TOKEN not set in .env")

    print(f"\n{'='*55}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Briefing requested")
    print(f"  Topics: {request.topics} | Date: {request.date or 'today'}")
    print(f"{'='*55}")

    # Step 1: Fetch HN stories
    try:
        hn_stories = await fetch_hn_top_stories(limit=30)
    except Exception as e:
        raise HTTPException(503, detail=f"Failed to fetch Hacker News: {str(e)}")

    # Step 2 & 3: Build prompt and call GPT-4o
    system_prompt, user_message = build_prompt(request.topics, request.date, hn_stories)

    try:
        print("  Calling GPT-4o via GitHub Models...")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://models.inference.ai.azure.com/chat/completions",
                headers={
                    "Content-Type":  "application/json",
                    "Authorization": f"Bearer {GITHUB_TOKEN}"
                },
                json={
                    "model":       "gpt-4o",
                    "max_tokens":  4000,
                    "temperature": 0.3,
                    # 0.3 = factual and consistent, good for summarisation
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_message}
                    ]
                }
            )

        if response.status_code != 200:
            err = response.json().get("error", {}).get("message", "Unknown")
            print(f"  GPT error: {response.status_code} — {err}")
            raise HTTPException(502, detail=f"GitHub Models API error: {err}")

        ai_text = response.json()["choices"][0]["message"]["content"]
        print(f"  GPT responded ({len(ai_text)} chars)")

        # Step 4: Parse and validate
        data = parse_ai_response(ai_text)

        valid_cats = {"ai", "data", "cloud", "startups"}
        articles   = []

        for a in data.get("articles", []):
            cat = a.get("category", "ai").lower()
            if cat not in valid_cats:
                cat = "ai"
            articles.append({
                "title":    a.get("title",   "Untitled"),
                "summary":  a.get("summary", ""),
                "category": cat,
                "source":   a.get("source",  "Hacker News"),
                "url":      a.get("url",     "")
            })

        print(f"  Done — {len(articles)} articles returned")

        return JSONResponse({
            "digest":             data.get("digest", "Today's tech landscape is evolving."),
            "articles":           articles,
            "fetched_at":         datetime.now().isoformat(),
            "topic_filter":       request.topics,
            "model":              "gpt-4o via GitHub Models",
            "hn_stories_fetched": len(hn_stories)
        })

    except json.JSONDecodeError as e:
        raise HTTPException(500, detail=f"GPT returned invalid JSON: {str(e)}")
    except httpx.TimeoutException:
        raise HTTPException(504, detail="GPT request timed out. Try again.")
    except httpx.ConnectError:
        raise HTTPException(503, detail="Could not connect to GitHub Models API.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=f"Unexpected error: {type(e).__name__}: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 7860)), reload=True)