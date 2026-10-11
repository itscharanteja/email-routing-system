import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from openai import OpenAI

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for the basic system
team_queue = []       # Confident emails routed to teams
review_queue = []     # Uncertain emails awaiting human review
training_data = []    # Human-labeled emails for future training

class Email(BaseModel):
    sender: str
    subject: str
    body: str

class ReviewAction(BaseModel):
    email_index: int
    team: str

# 1. LIGHTWEIGHT MODEL (Fast rule check for high-confidence simple cases)
def lightweight_model(text: str):
    text = text.lower()
    has_billing = any(w in text for w in ["refund", "invoice", "receipt"])
    has_tech = any(w in text for w in ["error 500", "stack trace", "broken api"])
    
    # Confident only if exactly one simple match
    if has_billing and not has_tech:
        return {"team": "Billing", "confidence": 0.9, "is_confident": True}
    if has_tech and not has_billing:
        return {"team": "Tech Support", "confidence": 0.9, "is_confident": True}
    return {"team": "Uncertain", "confidence": 0.3, "is_confident": False}

# 2. LLM API (OpenAI API classifier)
def llm_classifier(subject: str, body: str):
    api_key = os.getenv("OPENAI_API_KEY")
    prompt = f"Classify this email into 'Billing', 'Tech Support', or 'Sales'. Give your answer as: TEAM | CONFIDENCE (0.0 to 1.0).\n\nSubject: {subject}\nBody: {body}"
    
    if api_key and api_key.startswith("sk-"):
        try:
            client = OpenAI(api_key=api_key)
            res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=20
            )
            answer = res.choices[0].message.content.strip()
            team, conf = answer.split("|")
            conf = float(conf.strip())
            return {"team": team.strip(), "confidence": conf, "is_confident": conf >= 0.75}
        except Exception:
            pass

    # Built-in fallback if no API key is set
    text = f"{subject} {body}".lower()
    if "pricing" in text or "demo" in text or "enterprise" in text:
        return {"team": "Sales", "confidence": 0.9, "is_confident": True}
    return {"team": "Uncertain", "confidence": 0.4, "is_confident": False}

# 3. PIPELINE ENDPOINT: Webhook / Email ingestion
@app.post("/api/ingest")
def ingest_email(email: Email):
    text = f"{email.subject} {email.body}"
    
    # Step A: Lightweight Model
    lw = lightweight_model(text)
    if lw["is_confident"]:
        entry = {**email.model_dump(), "team": lw["team"], "routed_by": "Lightweight Model"}
        team_queue.insert(0, entry)
        return {"path": "Lightweight Model -> Team Queue", "email": entry}

    # Step B: LLM API
    llm = llm_classifier(email.subject, email.body)
    if llm["is_confident"]:
        entry = {**email.model_dump(), "team": llm["team"], "routed_by": "LLM API"}
        team_queue.insert(0, entry)
        return {"path": "LLM API -> Team Queue", "email": entry}

    # Step C: Review Queue
    entry = {**email.model_dump(), "suggested_team": llm["team"], "routed_by": "Review Queue (Uncertain)"}
    review_queue.insert(0, entry)
    return {"path": "LLM API -> Review Queue", "email": entry}

# 4. HUMAN REVIEW: Assigns team & pushes to Training Data
@app.post("/api/human-review")
def review_email(action: ReviewAction):
    if 0 <= action.email_index < len(review_queue):
        email = review_queue.pop(action.email_index)
        email["team"] = action.team
        email["routed_by"] = "Human Review"
        
        # Add to Team Queue
        team_queue.insert(0, email)
        
        # Add to Training Data
        training_data.insert(0, {
            "subject": email["subject"],
            "body": email["body"],
            "team": action.team
        })
        return {"status": "success", "email": email}
    return {"status": "error", "message": "Invalid index"}

@app.get("/api/data")
def get_data():
    return {
        "team_queue": team_queue,
        "review_queue": review_queue,
        "training_data": training_data
    }
