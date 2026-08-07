from typing import List, Optional

from src.feedback.models import Feedback
from src.feedback.store import FeedbackStore, feedback_store


class FeedbackService:
    def __init__(self, store: Optional[FeedbackStore] = None):
        self.store = store or feedback_store

    def submit(self, run_id: str, helpful: Optional[bool], rating: Optional[int], comment: Optional[str]) -> Feedback:
        feedback = Feedback(run_id=run_id, helpful=helpful, rating=rating, comment=comment)
        return self.store.save(feedback)

    def list_for_run(self, run_id: str) -> List[Feedback]:
        return self.store.list_by_run(run_id)


feedback_service = FeedbackService()
