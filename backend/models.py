from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class EmailPayload(BaseModel):
    message_id: Optional[str] = None
    sender: str
    recipient: Optional[str] = "support@company.com"
    subject: str
    body: str
    timestamp: Optional[str] = None

class StageTrace(BaseModel):
    stage_name: str  # "webhook_ingest", "lightweight_model", "llm_api", "team_queue", "review_queue", "human_triage", "training_data"
    status: str      # "confident", "uncertain", "routed", "pending_review", "resolved"
    details: Dict[str, Any]
    timestamp: str

class ProcessedEmail(BaseModel):
    id: str
    message_id: str
    sender: str
    subject: str
    body: str
    received_at: str
    
    # Final or current routing state
    status: str  # "ROUTED_LIGHTWEIGHT", "ROUTED_LLM", "NEEDS_HUMAN_REVIEW", "HUMAN_RESOLVED"
    assigned_team: Optional[str] = None # "billing", "tech_support", "sales", "general_inquiry"
    
    # Decisions at stages
    lightweight_result: Optional[Dict[str, Any]] = None
    llm_result: Optional[Dict[str, Any]] = None
    human_review: Optional[Dict[str, Any]] = None
    
    # Full audit trail of the flowchart
    pipeline_trace: List[StageTrace] = []

class HumanReviewSubmission(BaseModel):
    email_id: str
    assigned_team: str
    reviewer_notes: Optional[str] = ""
    reviewer_id: Optional[str] = "agent_human_1"

class TrainingDataEntry(BaseModel):
    id: str
    email_id: str
    subject: str
    body: str
    team: str
    source: str # "human_review" or "seed"
    created_at: str
    notes: Optional[str] = ""

class SettingsPayload(BaseModel):
    openai_api_key: Optional[str] = None
    model_name: Optional[str] = "gpt-4o-mini"
    lightweight_threshold: Optional[float] = 0.80
    llm_threshold: Optional[float] = 0.75
    mock_mode: Optional[bool] = False
