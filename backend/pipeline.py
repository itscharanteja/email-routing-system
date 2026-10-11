import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from .models import EmailPayload, ProcessedEmail, StageTrace, TrainingDataEntry
from .classifier_lightweight import LightweightModel
from .classifier_llm import LLMClassifier
from .store import EmailStore

class EmailProcessingService:
    def __init__(self, store: EmailStore, lightweight_model: LightweightModel, llm_classifier: LLMClassifier):
        self.store = store
        self.lightweight_model = lightweight_model
        self.llm_classifier = llm_classifier

    def process_incoming_email(self, payload: EmailPayload) -> ProcessedEmail:
        """
        Executes the exact multi-tier classification flowchart:
        1. Ingestion / Preprocessing
        2. Lightweight Model (Scikit-learn TF-IDF / Naive Bayes)
           - If confident -> Team Queue
           - If uncertain -> LLM API
        3. LLM API (OpenAI)
           - If confident -> Team Queue
           - If uncertain -> Review Queue (Awaiting Human)
        """
        email_id = f"eml_{uuid.uuid4().hex[:8]}"
        now_iso = datetime.now().isoformat()
        clean_subject = payload.subject.strip()
        clean_body = payload.body.strip()
        combined_text = f"{clean_subject}. {clean_body}"

        pipeline_trace = []

        # Trace 1: Webhook Ingest
        pipeline_trace.append(StageTrace(
            stage_name="webhook_ingest",
            status="completed",
            details={
                "sender": payload.sender,
                "recipient": payload.recipient,
                "message_id": payload.message_id or f"msg_{uuid.uuid4().hex[:6]}",
                "content_length": len(clean_body)
            },
            timestamp=datetime.now().isoformat()
        ))

        # Trace 2: Email Processing Service (Preprocessing & normalization)
        pipeline_trace.append(StageTrace(
            stage_name="email_processing_service",
            status="completed",
            details={
                "sanitized_tokens": len(combined_text.split()),
                "subject_tokens": len(clean_subject.split()),
                "status": "Ready for lightweight inference"
            },
            timestamp=datetime.now().isoformat()
        ))

        # Trace 3: Lightweight Model
        lw_res = self.lightweight_model.predict(combined_text)
        
        if lw_res["is_confident"]:
            # CONFIDENT -> Team Queue directly!
            pipeline_trace.append(StageTrace(
                stage_name="lightweight_model",
                status="confident",
                details=lw_res,
                timestamp=datetime.now().isoformat()
            ))

            pipeline_trace.append(StageTrace(
                stage_name="team_queue",
                status="routed",
                details={
                    "routed_by": "Lightweight Model",
                    "destination_queue": lw_res["predicted_team"],
                    "confidence": lw_res["confidence"],
                    "note": f"Fast-path routing without LLM latency or cost"
                },
                timestamp=datetime.now().isoformat()
            ))

            processed = ProcessedEmail(
                id=email_id,
                message_id=payload.message_id or email_id,
                sender=payload.sender,
                subject=clean_subject,
                body=clean_body,
                received_at=now_iso,
                status="ROUTED_LIGHTWEIGHT",
                assigned_team=lw_res["predicted_team"],
                lightweight_result=lw_res,
                llm_result=None,
                human_review=None,
                pipeline_trace=pipeline_trace
            )
            self.store.add_email(processed)
            return processed

        else:
            # UNCERTAIN -> Proceed to LLM API
            pipeline_trace.append(StageTrace(
                stage_name="lightweight_model",
                status="uncertain",
                details=lw_res,
                timestamp=datetime.now().isoformat()
            ))

            # Trace 4: LLM API Evaluation
            llm_res = self.llm_classifier.classify(clean_subject, clean_body)

            if llm_res["is_confident"]:
                # LLM CONFIDENT -> Team Queue
                pipeline_trace.append(StageTrace(
                    stage_name="llm_api",
                    status="confident",
                    details=llm_res,
                    timestamp=datetime.now().isoformat()
                ))

                pipeline_trace.append(StageTrace(
                    stage_name="team_queue",
                    status="routed",
                    details={
                        "routed_by": "LLM API",
                        "model": llm_res.get("model_used", "OpenAI"),
                        "destination_queue": llm_res["predicted_team"],
                        "confidence": llm_res["confidence"],
                        "reasoning": llm_res.get("reasoning", "")
                    },
                    timestamp=datetime.now().isoformat()
                ))

                processed = ProcessedEmail(
                    id=email_id,
                    message_id=payload.message_id or email_id,
                    sender=payload.sender,
                    subject=clean_subject,
                    body=clean_body,
                    received_at=now_iso,
                    status="ROUTED_LLM",
                    assigned_team=llm_res["predicted_team"],
                    lightweight_result=lw_res,
                    llm_result=llm_res,
                    human_review=None,
                    pipeline_trace=pipeline_trace
                )
                self.store.add_email(processed)
                return processed

            else:
                # LLM UNCERTAIN -> Review Queue for Human triage
                pipeline_trace.append(StageTrace(
                    stage_name="llm_api",
                    status="uncertain",
                    details=llm_res,
                    timestamp=datetime.now().isoformat()
                ))

                pipeline_trace.append(StageTrace(
                    stage_name="review_queue",
                    status="pending_review",
                    details={
                        "reason": "Both lightweight and LLM models were uncertain",
                        "lightweight_confidence": lw_res["confidence"],
                        "llm_confidence": llm_res["confidence"],
                        "suggested_team": llm_res["predicted_team"]
                    },
                    timestamp=datetime.now().isoformat()
                ))

                processed = ProcessedEmail(
                    id=email_id,
                    message_id=payload.message_id or email_id,
                    sender=payload.sender,
                    subject=clean_subject,
                    body=clean_body,
                    received_at=now_iso,
                    status="NEEDS_HUMAN_REVIEW",
                    assigned_team=None,
                    lightweight_result=lw_res,
                    llm_result=llm_res,
                    human_review=None,
                    pipeline_trace=pipeline_trace
                )
                self.store.add_email(processed)
                return processed

    def resolve_human_review(self, email_id: str, assigned_team: str, reviewer_notes: str = "", reviewer_id: str = "human_operator_1") -> Optional[ProcessedEmail]:
        """
        Executes Human-in-the-Loop review and feeds into Training Data:
        Review Queue -> Human -> Training Data -> (Enables Retrain)
        """
        email = self.store.get_email(email_id)
        if not email:
            return None

        now_iso = datetime.now().isoformat()

        # Update human review record
        email.human_review = {
            "reviewer_id": reviewer_id,
            "assigned_team": assigned_team,
            "notes": reviewer_notes,
            "reviewed_at": now_iso
        }
        email.assigned_team = assigned_team
        email.status = "HUMAN_RESOLVED"

        # Trace: Human Stage
        email.pipeline_trace.append(StageTrace(
            stage_name="human_triage",
            status="resolved",
            details={
                "assigned_team": assigned_team,
                "notes": reviewer_notes,
                "reviewer_id": reviewer_id
            },
            timestamp=now_iso
        ))

        # Trace: Training Data Stage
        training_entry = TrainingDataEntry(
            id=f"trn_{uuid.uuid4().hex[:8]}",
            email_id=email.id,
            subject=email.subject,
            body=email.body,
            team=assigned_team,
            source="human_review",
            created_at=now_iso,
            notes=reviewer_notes
        )
        self.store.add_training_sample(training_entry)

        email.pipeline_trace.append(StageTrace(
            stage_name="training_data",
            status="added",
            details={
                "training_id": training_entry.id,
                "label": assigned_team,
                "status": "Available for retraining lightweight model"
            },
            timestamp=now_iso
        ))

        # Trace: Finally routed to team queue
        email.pipeline_trace.append(StageTrace(
            stage_name="team_queue",
            status="routed",
            details={
                "routed_by": "Human Reviewer",
                "destination_queue": assigned_team,
                "confidence": 1.0,
                "note": "Gold standard ground truth"
            },
            timestamp=now_iso
        ))

        self.store.save()
        return email

    def retrain_lightweight_model(self) -> Dict[str, Any]:
        """
        Gathers all human-verified training samples from the Training Data Store
        and retrains the Lightweight Model to improve future automated accuracy!
        """
        samples = self.store.get_training_samples()
        additional_pairs = [
            (f"{s.subject}. {s.body}", s.team)
            for s in samples
        ]
        total_samples = self.lightweight_model.retrain(additional_pairs)
        return {
            "status": "success",
            "samples_added": len(additional_pairs),
            "total_training_samples": total_samples,
            "timestamp": datetime.now().isoformat()
        }
