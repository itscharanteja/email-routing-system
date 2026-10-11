import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from .models import ProcessedEmail, TrainingDataEntry

class EmailStore:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.emails: Dict[str, ProcessedEmail] = {}
        self.training_data: List[TrainingDataEntry] = []
        self.storage_file = os.path.join(self.data_dir, "emails.json")
        self.training_file = os.path.join(self.data_dir, "training_data.jsonl")
        self._load()

    def _load(self):
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, "r") as f:
                    raw = json.load(f)
                    for item in raw:
                        email_obj = ProcessedEmail(**item)
                        self.emails[email_obj.id] = email_obj
            except Exception as e:
                print(f"Error loading emails: {e}")

        if os.path.exists(self.training_file):
            try:
                with open(self.training_file, "r") as f:
                    for line in f:
                        if line.strip():
                            item = json.loads(line)
                            self.training_data.append(TrainingDataEntry(**item))
            except Exception as e:
                print(f"Error loading training data: {e}")

    def save(self):
        try:
            with open(self.storage_file, "w") as f:
                json.dump([e.model_dump() for e in self.emails.values()], f, indent=2)
        except Exception as e:
            print(f"Error persisting emails: {e}")

    def add_email(self, email: ProcessedEmail):
        self.emails[email.id] = email
        self.save()

    def get_email(self, email_id: str) -> Optional[ProcessedEmail]:
        return self.emails.get(email_id)

    def get_all_emails(self) -> List[ProcessedEmail]:
        # Return sorted by newest first
        return sorted(list(self.emails.values()), key=lambda e: e.received_at, reverse=True)

    def get_team_queue(self, team: Optional[str] = None) -> List[ProcessedEmail]:
        emails = [e for e in self.emails.values() if e.status in ["ROUTED_LIGHTWEIGHT", "ROUTED_LLM", "HUMAN_RESOLVED"]]
        if team:
            emails = [e for e in emails if e.assigned_team == team]
        return sorted(emails, key=lambda e: e.received_at, reverse=True)

    def get_review_queue(self) -> List[ProcessedEmail]:
        emails = [e for e in self.emails.values() if e.status == "NEEDS_HUMAN_REVIEW"]
        return sorted(emails, key=lambda e: e.received_at, reverse=True)

    def add_training_sample(self, entry: TrainingDataEntry):
        self.training_data.append(entry)
        try:
            with open(self.training_file, "a") as f:
                f.write(json.dumps(entry.model_dump()) + "\n")
        except Exception as e:
            print(f"Error saving training data: {e}")

    def get_training_samples(self) -> List[TrainingDataEntry]:
        return list(self.training_data)

    def get_stats(self) -> Dict[str, Any]:
        all_emails = list(self.emails.values())
        total = len(all_emails)
        lightweight_routed = len([e for e in all_emails if e.status == "ROUTED_LIGHTWEIGHT"])
        llm_routed = len([e for e in all_emails if e.status == "ROUTED_LLM"])
        needs_review = len([e for e in all_emails if e.status == "NEEDS_HUMAN_REVIEW"])
        human_resolved = len([e for e in all_emails if e.status == "HUMAN_RESOLVED"])
        
        team_counts = {
            "billing": len([e for e in all_emails if e.assigned_team == "billing"]),
            "tech_support": len([e for e in all_emails if e.assigned_team == "tech_support"]),
            "sales": len([e for e in all_emails if e.assigned_team == "sales"]),
            "general_inquiry": len([e for e in all_emails if e.assigned_team == "general_inquiry"])
        }

        # Cost & Latency estimations for architecture analysis
        # Lightweight is near zero cost (<0.1ms), LLM is ~0.002$ and ~500ms, Human is ~2$ and minutes
        llm_calls_saved_percent = round((lightweight_routed / max(1, total)) * 100, 1)

        return {
            "total_emails": total,
            "lightweight_routed": lightweight_routed,
            "llm_routed": llm_routed,
            "needs_review": needs_review,
            "human_resolved": human_resolved,
            "training_samples_collected": len(self.training_data),
            "team_counts": team_counts,
            "llm_calls_saved_percent": llm_calls_saved_percent
        }
