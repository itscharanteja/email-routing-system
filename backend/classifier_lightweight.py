import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from typing import Dict, Any, List, Tuple

# Initial seed training data for the lightweight model
SEED_TRAINING_DATA = [
    # Billing
    ("Need a refund for invoice INV-9021", "billing"),
    ("My credit card was charged twice this morning", "billing"),
    ("Where can I download my monthly VAT receipt?", "billing"),
    ("Please cancel my subscription and stop auto-renewing", "billing"),
    ("Payment failed on our corporate Visa card", "billing"),
    ("Billing address needs to be updated on upcoming invoice", "billing"),
    ("Unexpected overage charges on my account this billing cycle", "billing"),
    ("Can you send the invoice for last month?", "billing"),
    ("How do I change my payment method from credit card to ACH wire?", "billing"),

    # Tech Support
    ("Getting 500 internal server error when calling /api/v1/users", "tech_support"),
    ("Production database connection timeout after update", "tech_support"),
    ("The mobile app crashes every time I open the dashboard", "tech_support"),
    ("OAuth login loop returning 401 unauthorized token expired", "tech_support"),
    ("Webhook deliveries are failing with ECONNREFUSED", "tech_support"),
    ("Memory leak in the worker container causing OOM crash", "tech_support"),
    ("WebSocket disconnects every 30 seconds randomly", "tech_support"),
    ("SSL certificate error handshake failure on domain", "tech_support"),
    ("Bug report: button click does not submit the form in Firefox", "tech_support"),

    # Sales
    ("Interested in Enterprise pricing for 500 team seats", "sales"),
    ("Can we schedule a 30 min product demo for our executive team?", "sales"),
    ("Requesting formal quote and security questionnaire for procurement", "sales"),
    ("We want to upgrade from Pro to Enterprise tier annual plan", "sales"),
    ("Do you offer volume discounts for non-profit organizations?", "sales"),
    ("Looking to discuss custom SLA and dedicated VPC deployment", "sales"),
    ("Inquiry about reseller partnership and affiliate commission", "sales"),

    # General Inquiry
    ("What are your headquarters office hours and visitor guidelines?", "general_inquiry"),
    ("Press and media kit request for tech journalism piece", "general_inquiry"),
    ("Who should I contact regarding speaker invitations for our summit?", "general_inquiry"),
    ("Is your team currently hiring frontend engineers in Austin?", "general_inquiry"),
    ("General feedback about your latest podcast episode and roadmap", "general_inquiry")
]

class LightweightModel:
    def __init__(self, confidence_threshold: float = 0.80):
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.categories = ["billing", "tech_support", "sales", "general_inquiry"]
        self.is_trained = False
        self._train(SEED_TRAINING_DATA)

    def _train(self, data: List[Tuple[str, str]]):
        texts = [item[0] for item in data]
        labels = [item[1] for item in data]
        
        self.model = Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2), min_df=1, stop_words='english')),
            ('clf', MultinomialNB(alpha=0.1))
        ])
        self.model.fit(texts, labels)
        self.is_trained = True

    def retrain(self, additional_data: List[Tuple[str, str]]) -> int:
        all_data = list(SEED_TRAINING_DATA) + additional_data
        self._train(all_data)
        return len(all_data)

    def predict(self, text: str) -> Dict[str, Any]:
        """
        Runs fast classification on input text.
        Returns:
            dict with:
                predicted_team: str
                confidence: float (0.0 to 1.0)
                is_confident: bool (True if confidence >= confidence_threshold)
                class_probabilities: dict
        """
        if not self.is_trained or not text.strip():
            return {
                "predicted_team": "general_inquiry",
                "confidence": 0.25,
                "is_confident": False,
                "reason": "Untrained or empty text",
                "class_probabilities": {c: 0.25 for c in self.categories}
            }

        probs = self.model.predict_proba([text])[0]
        classes = self.model.classes_
        prob_dict = {cls_name: round(float(prob), 4) for cls_name, prob in zip(classes, probs)}
        
        best_idx = np.argmax(probs)
        best_class = str(classes[best_idx])
        confidence = float(probs[best_idx])

        # If text is too short or ambiguous, penalize confidence
        words = len(text.split())
        if words < 4:
            confidence = max(0.2, confidence * 0.7)

        confidence = round(confidence, 3)
        is_confident = confidence >= self.confidence_threshold

        return {
            "predicted_team": best_class,
            "confidence": confidence,
            "threshold": self.confidence_threshold,
            "is_confident": is_confident,
            "class_probabilities": prob_dict,
            "reason": f"Classified with {confidence*100:.1f}% probability (threshold: {self.confidence_threshold*100:.1f}%)"
        }
