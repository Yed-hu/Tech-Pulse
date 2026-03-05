# ================================================================
# main.py — Tech Pulse Backend
# ================================================================
# HOW THIS FILE WORKS (simple explanation):
#
# 1. Someone opens the app in their browser
# 2. They click "Fetch Briefing"
# 3. This file does 3 things in order:
#    a) Fetches top stories from Hacker News (free, no key needed)
#    b) Sends those stories to GPT-4o to summarise and categorise
#    c) Returns the result as JSON to the frontend (index.html)
#
# The browser never sees your GitHub token — it stays here safely.
# ================================================================


# ── SECTION 1: IMPORTS ──────────────────────────────────────────
# Imports are like "tools" you borrow from other people's code.
# Instead of writing everything from scratch, we use packages.

import os
# os = operating system tools
# We use it to read your .env file variables like GITHUB_TOKEN
# Example: os.environ.get("GITHUB_TOKEN") reads the token safely

import json
# json = handles JSON data (the format APIs use to send data)
# json.loads("string")  → converts JSON text into a Python dict
# json.dumps(dict)      → converts a Python dict into JSON text

from dotenv import load_dotenv
# dotenv reads your .env file and loads variables into os.environ
# Must be called BEFORE any os.environ.get() calls

from fastapi import FastAPI, HTTPException
# FastAPI  → creates your web server and defines URL routes
# HTTPException → lets you return error responses with status codes
#   e.g. raise HTTPException(status_code=404, detail="Not found")

from fastapi.staticfiles import StaticFiles
# StaticFiles → serves your /public folder to the browser
# So http://localhost:8000/public/index.html works automatically

from fastapi.responses import JSONResponse, FileResponse
# JSONResponse → converts a Python dict into a JSON HTTP response
# FileResponse → sends a file (like index.html) to the browser

from fastapi.middleware.cors import CORSMiddleware
# CORS = Cross-Origin Resource Sharing
# Browsers block requests between different domains/ports by default
# This middleware tells the browser: "it's OK, allow these requests"
# Without this, your frontend can't talk to your backend

from pydantic import BaseModel
# Pydantic → automatic data validation
# You define a class with typed fields
# FastAPI uses it to validate incoming request data automatically
# Wrong data type? FastAPI returns a 422 error automatically

import httpx
# httpx → modern HTTP client (like requests, but supports async)
# We use it to:
#   - Call the Hacker News API to get real stories
#   - Call the GitHub Models API (GPT-4o) to summarise them

from datetime import datetime
# datetime → get current date and time
# Used for logging (print timestamps) and the health check response


# ── SECTION 2: CONFIGURATION ────────────────────────────────────
# Load environment variables from your .env file
# After load_dotenv(), all variables in .env are accessible via os.environ

load_dotenv()
# This reads .env and loads: GITHUB_TOKEN=xxx into os.environ

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
# os.environ.get() safely reads a variable — returns None if missing
# Never use os.environ["KEY"] — that crashes if the key doesn't exist


# ── SECTION 3: CREATE THE FASTAPI APP ───────────────────────────
# app is your web server. Everything connects to this object.
# Routes, middleware, static files — all attached to `app`

app = FastAPI(
    title="Tech Pulse API",
    description="Daily tech briefing — Hacker News + GPT-4o",
    version="2.0.0"
    # These show up at http://localhost:8000/docs
    # FastAPI generates FREE interactive API docs automatically!
)


# ── SECTION 4: MIDDLEWARE ───────────────────────────────────────
# Middleware runs on EVERY request before it reaches your routes
# Think of it as a security checkpoint at the entrance

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # "*" = allow requests from any domain
    # In production you'd restrict this to your GitHub Pages URL
    # e.g. allow_origins=["https://yourusername.github.io"]

    allow_methods=["*"],
    # Allow all HTTP methods: GET, POST, PUT, DELETE, OPTIONS etc.

    allow_headers=["*"],
    # Allow all request headers
)


# ── SECTION 5: SERVE STATIC FILES ──────────────────────────────
# This tells FastAPI to serve files from the /public folder
# So visiting /public/index.html serves your HTML file directly

app.mount("/public", StaticFiles(directory="public"), name="public")


# ── SECTION 6: DATA MODELS (Pydantic) ──────────────────────────
# Pydantic models define the SHAPE of data your API accepts
# FastAPI automatically validates incoming requests against these
#
# Think of it like a form — if someone sends wrong data,
# FastAPI rejects it with a clear error message automatically

class BriefingRequest(BaseModel):
    """
    What the frontend sends when clicking 'Fetch Briefing'

    Example request body:
        { "topics": "ai", "date": "Thursday 5 March 2026" }

    FastAPI automatically:
      - Reads the JSON body
      - Checks topics is a string, date is a string
      - Creates this object so you can use request.topics etc.
      - Returns HTTP 422 with clear error if types are wrong
    """
    topics: str = "all"
    # str  = must be a string
    # = "all" means OPTIONAL — defaults to "all" if not sent

    date: str = ""
    # Optional date string from the frontend clock


# ── SECTION 7: HACKER NEWS FETCHER ─────────────────────────────
# This function fetches REAL live stories from Hacker News
# using their free Algolia API — no API key required!
#
# Why Hacker News?
#   - Free, no authentication needed
#   - Updates in real time
#   - Tech community curated — high quality signal
#   - Returns points (upvotes) so we can sort by importance

async def fetch_hn_top_stories(limit: int = 25) -> list:
    """
    Fetches top stories from Hacker News front page.

    Parameters:
        limit (int): how many stories to fetch. Default 25.
                     We fetch more than we need so GPT has
                     enough to filter by topic after.

    Returns:
        list: list of story dicts sorted by popularity (points)

    API used: https://hn.algolia.com/api/v1/search
    This is Algolia's HN search API — completely free, no key needed.
    """

    url = f"https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage={limit}"
    # tags=front_page  → only front page stories (most important)
    # hitsPerPage={limit} → how many results to return
    # f"..." = f-string, embeds the variable {limit} into the URL

    print(f"  [HN] Fetching top {limit} stories from Hacker News...")

    async with httpx.AsyncClient(timeout=20.0) as client:
        # httpx.AsyncClient = async HTTP client (like a browser making requests)
        # timeout=20.0 = give up if no response within 20 seconds
        # 'async with' = ensures connection closes properly when done

        resp = await client.get(url)
        # await = wait for the HTTP response before moving on
        # Without await, Python would move to the next line immediately
        # (before the response even arrives — that would be a bug!)

        resp.raise_for_status()
        # If HTTP status is 4xx or 5xx, this raises an exception
        # Saves you writing: if resp.status_code != 200: raise...
        # Cleaner and catches all error codes automatically

        data = resp.json()
        # Parses the JSON response body into a Python dict
        # HN Algolia returns: { "hits": [...stories...], "nbHits": 500, ... }

    stories = []
    for hit in data.get("hits", []):
        # data.get("hits", []) safely gets the hits list
        # Returns [] (empty list) if "hits" key doesn't exist

        stories.append({
            "title":    hit.get("title", "Untitled"),
            # Story headline

            "url":      hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
            # Some HN stories are "Ask HN" or "Show HN" with no external URL
            # In that case, fall back to the HN discussion page
            # 'or' = if hit.get("url") is None/empty, use the fallback

            "points":   hit.get("points", 0),
            # Upvotes — higher = more important to the community
            # Default 0 if missing

            "comments": hit.get("num_comments", 0),
            # Comment count — signals how much discussion it sparked

            "author":   hit.get("author", "unknown"),
            # Who submitted it

            "time":     hit.get("created_at", ""),
            # When it was posted (ISO timestamp string)
        })

    # Sort by points (upvotes) — most popular first
    # sorted() returns a NEW sorted list (doesn't modify original)
    # key=lambda x: x["points"] → sort by the "points" value
    # reverse=True → descending order (highest first)
    stories_sorted = sorted(stories, key=lambda x: x["points"], reverse=True)

    print(f"  [HN] Got {len(stories_sorted)} stories. Top story: '{stories_sorted[0]['title'] if stories_sorted else 'none'}'")

    return stories_sorted


# ── SECTION 8: PROMPT BUILDER ───────────────────────────────────
# Builds the instructions we send to GPT-4o
# Two parts:
#   system_prompt = GPT's "job description" (what role to play)
#   user_message  = the actual task for this specific request

def build_prompt(topics: str, date: str, hn_stories: list) -> tuple[str, str]:
    """
    Builds the system prompt and user message for GPT-4o.

    Parameters:
        topics     (str):  selected category tab e.g. "ai", "all"
        date       (str):  today's date from the frontend
        hn_stories (list): the real stories fetched from HN

    Returns:
        tuple: (system_prompt, user_message)
        Python can return multiple values — caller unpacks like:
            system, user = build_prompt(topics, date, stories)
    """

    # Map tab values to readable topic descriptions
    # dict = key:value pairs, accessed with dict.get(key, default)
    topic_map = {
        "all":      "AI & Machine Learning, Data Engineering & Analytics, Cloud & DevOps, and Tech Startups",
        "ai":       "Artificial Intelligence and Machine Learning",
        "data":     "Data Engineering, Analytics, and Business Intelligence",
        "cloud":    "Cloud Computing and DevOps",
        "startups": "Tech Startups and Venture Capital"
    }
    topic_label = topic_map.get(topics, topic_map["all"])

    # Build the system prompt
    # Triple-quoted f-string = multiline string with embedded variables
    # {{ }} inside f-strings = escaped braces → literal { } in output
    system_prompt = f"""You are a tech news briefing assistant for Yedhu Prasad,
a Data Analytics professional in the UK skilled in Python, SQL, Power BI, and Machine Learning.

You will receive a list of real Hacker News front page stories.
Your job is to categorise and summarise them as a professional daily tech briefing.

FOCUS TOPICS: {topic_label}

STRICT RULES:
1. Return ONLY valid JSON — no markdown fences, no backticks, no explanation text whatsoever
2. Only include stories relevant to the focus topics above
3. Each summary must explain WHAT happened AND WHY it matters to a data/ML professional
4. Use the exact field names shown below — do not rename them

Return EXACTLY this JSON structure:
{{
  "digest": "2-3 sentence big-picture overview of today's key tech themes",
  "articles": [
    {{
      "title":    "story title from the list",
      "summary":  "2-3 sentences: what it is and why a data professional should care",
      "category": "ai OR data OR cloud OR startups",
      "source":   "domain name or Hacker News",
      "url":      "original url from the story"
    }}
  ]
}}

Stories to process:
{json.dumps(hn_stories, indent=2)}

Return 8 to 12 of the most relevant articles. JSON only. No other text."""

    user_message = f"Generate today's tech briefing for {date or 'today'}. Return JSON only, no other text."

    return system_prompt, user_message


# ── SECTION 9: JSON PARSER ──────────────────────────────────────
# GPT sometimes adds extra text around the JSON even when told not to
# This function defensively finds and extracts just the JSON part

def parse_ai_response(content: str) -> dict:
    """
    Extracts and parses JSON from GPT's response text.

    Even with strict instructions, GPT occasionally adds:
    - Markdown fences: ```json ... ```
    - Sentences before/after the JSON
    This function handles all of those cases safely.

    Parameters:
        content (str): raw text from GPT

    Returns:
        dict: parsed Python dictionary
    """

    # Step 1: Remove markdown fences if present
    clean = content.strip()
    clean = clean.replace("```json", "").replace("```", "").strip()
    # str.replace(old, new) replaces ALL occurrences
    # .strip() removes whitespace from start and end

    # Step 2: Find the boundaries of the JSON object
    start = clean.find("{")
    # str.find("{") → index of FIRST { character, or -1 if not found

    end = clean.rfind("}") + 1
    # str.rfind("}") → index of LAST } character (r = reverse search)
    # +1 because Python slicing is exclusive at end: string[start:end]
    # We want to include the } so we add 1

    # Step 3: Guard against no JSON found
    if start == -1 or end == 0:
        raise ValueError(f"No JSON object found in GPT response. First 200 chars: {clean[:200]}")

    # Step 4: Extract just the JSON substring
    json_string = clean[start:end]
    # string[start:end] = Python slicing, extracts a substring

    # Step 5: Parse JSON string → Python dictionary
    return json.loads(json_string)
    # json.loads() raises json.JSONDecodeError if invalid JSON


# ── SECTION 10: ROUTES ──────────────────────────────────────────
# Routes define what happens at each URL
# @app.get("/path")  → handles GET requests  (browser visiting a URL)
# @app.post("/path") → handles POST requests (frontend sending data)
#
# async def = asynchronous function
# FastAPI is async — it handles many requests at once without blocking
# Use 'await' inside async functions when calling other async functions


# ROUTE 1 ── Serve the frontend HTML ─────────────────────────────
@app.get("/")
async def serve_frontend():
    """
    What happens: User visits http://localhost:8000
    What returns: The public/index.html file (your frontend UI)

    FileResponse reads the file from disk and sends it to the browser.
    The browser then renders it as your web app.
    """
    return FileResponse("public/index.html")


# ROUTE 2 ── Health Check ────────────────────────────────────────
@app.get("/health")
async def health_check():
    """
    What happens: Anyone calls GET /health
    What returns: JSON confirming server is alive + token status

    Used by:
      - The frontend "Ping" button to check server is running
      - Render.com to monitor if the deployed app is healthy
    """
    return JSONResponse({
        "status":           "ok",
        "message":          "Tech Pulse is running!",
        "token_configured": bool(GITHUB_TOKEN and GITHUB_TOKEN != "your_github_token_here"),
        # bool() converts to True/False
        # True only if token exists AND isn't the placeholder text
        "timestamp":        datetime.now().isoformat()
        # isoformat() → "2026-03-05T08:30:00.123456"
    })


# ROUTE 3 ── Main Briefing Endpoint ──────────────────────────────
@app.post("/api/briefing")
async def get_briefing(request: BriefingRequest):
    """
    THE MAIN ENDPOINT — called when user clicks 'Fetch Briefing'

    Full flow:
      Step 1: Validate GitHub token exists
      Step 2: Fetch top 25 stories from Hacker News (free API)
      Step 3: Build GPT prompt with those real stories
      Step 4: Call GPT-4o via GitHub Models API
      Step 5: Parse and validate the JSON response
      Step 6: Return clean data to the frontend

    request: BriefingRequest → FastAPI auto-validates and injects this
    The frontend sends: { "topics": "ai", "date": "Thursday 5 March 2026" }
    """

    # ── Guard: check token ───────────────────────────────────────
    if not GITHUB_TOKEN or GITHUB_TOKEN == "your_github_token_here":
        raise HTTPException(
            status_code=500,
            detail="GITHUB_TOKEN not set. Add it to your .env file and restart the server."
        )
    # HTTPException immediately stops execution and returns an error response
    # Frontend receives: { "detail": "GITHUB_TOKEN not set..." }

    # ── Log the incoming request ─────────────────────────────────
    # These print statements show in your terminal (Codespace console)
    # Very helpful for debugging — you see exactly what's happening
    print(f"\n{'='*55}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] New briefing request")
    print(f"  Topics : {request.topics}")
    print(f"  Date   : {request.date or 'today'}")
    print(f"{'='*55}")
    # strftime('%H:%M:%S') formats current time as "08:30:00"


    # ── STEP 2: Fetch Hacker News stories ────────────────────────
    try:
        hn_stories = await fetch_hn_top_stories(limit=25)
        # await = wait for the async function to complete
        # hn_stories is now a list of dicts with title, url, points etc.
    except Exception as e:
        # If HN API is down or unreachable, return a clear error
        raise HTTPException(
            status_code=503,
            detail=f"Failed to fetch Hacker News stories: {str(e)}"
        )


    # ── STEP 3 & 4: Build prompt and call GPT-4o ─────────────────
    system_prompt, user_message = build_prompt(request.topics, request.date, hn_stories)
    # Unpacking a tuple: first value → system_prompt, second → user_message

    try:
        print(f"  Calling GPT-4o via GitHub Models API...")

        async with httpx.AsyncClient(timeout=60.0) as client:
            # timeout=60.0 → wait up to 60 seconds (GPT can be slow)

            response = await client.post(
                "https://models.inference.ai.azure.com/chat/completions",
                # GitHub Models API endpoint (powered by Azure OpenAI)
                # This is the same as OpenAI's API but authenticated
                # with your GitHub token instead of an OpenAI key

                headers={
                    "Content-Type":  "application/json",
                    "Authorization": f"Bearer {GITHUB_TOKEN}",
                    # Bearer token auth — standard for REST APIs
                    # f"Bearer {GITHUB_TOKEN}" → "Bearer ghp_xxxx..."
                },

                json={
                    "model": "gpt-4o",
                    # GPT-4o = OpenAI's fast, capable model
                    # Free via GitHub Marketplace for personal use

                    "max_tokens": 4000,
                    # Max length of GPT's response
                    # 4000 tokens ≈ 3000 words — enough for 10+ articles

                    "temperature": 0.3,
                    # Controls randomness (0.0 to 2.0)
                    # 0.3 = mostly factual, low creativity
                    # Good for summarisation — we want accuracy not creativity
                    # (Changed from 0.7 — lower is better for structured JSON)

                    "messages": [
                        {"role": "system", "content": system_prompt},
                        # system = GPT's instructions and persona

                        {"role": "user",   "content": user_message}
                        # user = the actual request
                    ]
                }
            )

        # ── Check for API errors ──────────────────────────────────
        if response.status_code != 200:
            err_body = response.json()
            err_msg  = err_body.get("error", {}).get("message", "Unknown error")
            # .get() safely navigates nested dicts — no KeyError if missing
            print(f"  GPT API error: {response.status_code} — {err_msg}")
            raise HTTPException(
                status_code=502,
                # 502 = Bad Gateway (our server got bad response upstream)
                detail=f"GitHub Models API error: {err_msg}"
            )

        # ── Extract GPT's text response ───────────────────────────
        result  = response.json()
        ai_text = result["choices"][0]["message"]["content"]
        # OpenAI response structure:
        # { "choices": [{ "message": { "role": "assistant", "content": "..." } }] }
        # [0] = first choice (usually only one)

        print(f"  GPT responded ({len(ai_text)} characters)")


        # ── STEP 5: Parse the JSON ────────────────────────────────
        data = parse_ai_response(ai_text)


        # ── STEP 5b: Validate and clean each article ──────────────
        valid_categories = {"ai", "data", "cloud", "startups"}
        articles = []

        for article in data.get("articles", []):
            # dict.get("articles", []) → returns [] if key missing (safe)

            category = article.get("category", "ai").lower()
            # .lower() = "AI" → "ai", handles GPT capitalising inconsistently

            if category not in valid_categories:
                category = "ai"
                # Fallback — if GPT returns "machine-learning" etc.

            articles.append({
                "title":    article.get("title",   "Untitled"),
                "summary":  article.get("summary", ""),
                "category": category,
                "source":   article.get("source",  "Hacker News"),
                "url":      article.get("url",      "")
            })
            # .append() adds an item to the end of a list

        print(f"  Parsed {len(articles)} articles successfully")


        # ── STEP 6: Return the final response ─────────────────────
        return JSONResponse({
            "digest":       data.get("digest", "Today's tech landscape is evolving rapidly."),
            "articles":     articles,
            "fetched_at":   datetime.now().isoformat(),
            "topic_filter": request.topics,
            "model":        "gpt-4o via GitHub Models",
            "hn_stories_fetched": len(hn_stories)
            # Extra field so you can see in the UI how many HN stories were fetched
        })
        # JSONResponse converts this Python dict → JSON HTTP response
        # The frontend's fetch() call receives this and parses it


    # ── SPECIFIC ERROR HANDLERS ───────────────────────────────────
    # Specific handlers give the frontend (and you!) clear error messages
    # instead of one generic "something went wrong"

    except json.JSONDecodeError as e:
        # GPT returned something that isn't valid JSON
        print(f"  JSON parse error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"GPT returned invalid JSON. Try again. Error: {str(e)}"
        )

    except httpx.TimeoutException:
        # GPT took longer than 60 seconds
        print("  Request timed out after 60s")
        raise HTTPException(
            status_code=504,
            # 504 = Gateway Timeout
            detail="GPT request timed out. Please try again."
        )

    except httpx.ConnectError:
        # Can't reach the GitHub Models API (no internet, DNS issue etc.)
        print("  Connection error — can't reach GitHub Models API")
        raise HTTPException(
            status_code=503,
            detail="Could not connect to GitHub Models API. Check your internet connection."
        )

    except HTTPException:
        # Re-raise any HTTPExceptions we deliberately raised above
        # Without this line, they'd get caught by the generic Exception below
        raise

    except Exception as e:
        # Catch-all for anything unexpected
        # Always put this LAST — it catches everything
        print(f"  Unexpected error: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected server error: {type(e).__name__}: {str(e)}"
        )


# ── SECTION 11: RUN THE SERVER ──────────────────────────────────
# This block only runs when you execute: python main.py directly
# It does NOT run when uvicorn imports this file normally
# Best practice: use the command: uvicorn main:app --reload

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        # "filename:variable" — tells uvicorn where to find the FastAPI app

        host="0.0.0.0",
        # 0.0.0.0 = listen on all network interfaces
        # Required in GitHub Codespaces so the forwarded port works
        # 127.0.0.1 would only work locally and block Codespace access

        port=int(os.environ.get("PORT", 8000)),
        # Read PORT from .env, default to 8000 if not set
        # int() converts the string "8000" → integer 8000

        reload=True
        # Auto-restart when you save changes to any .py file
        # Great for development — only use in dev, not production
    )