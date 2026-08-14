"""
Performance model — goals, reviews, and KPIs.
Stored in MongoDB collections: performance_reviews, goals
"""
from datetime import datetime


class PerformanceReviewModel:
    COLLECTION = "performance_reviews"

    REVIEW_TYPES = ["annual", "mid_year", "quarterly", "probation", "360_degree"]
    RATING_SCALE = [1, 2, 3, 4, 5]  # 1=Poor, 2=Below Average, 3=Average, 4=Good, 5=Excellent

    @staticmethod
    def new(employee_id, reviewer_id, review_type, review_period_start,
            review_period_end, ratings=None, comments=""):
        now = datetime.utcnow()
        ratings = ratings or {
            "technical_skills": 0,
            "communication": 0,
            "teamwork": 0,
            "leadership": 0,
            "punctuality": 0,
            "problem_solving": 0,
            "initiative": 0,
            "overall": 0,
        }
        avg = round(
            sum(v for v in ratings.values() if v > 0) /
            max(len([v for v in ratings.values() if v > 0]), 1),
            2,
        )
        return {
            "employee_id": employee_id,
            "reviewer_id": reviewer_id,
            "review_type": review_type,
            "review_period_start": review_period_start,
            "review_period_end": review_period_end,
            "ratings": ratings,
            "average_rating": avg,
            "comments": comments,
            "strengths": [],
            "areas_of_improvement": [],
            "goals_for_next_period": [],
            "status": "draft",         # draft | submitted | acknowledged
            "acknowledged_by_employee": False,
            "acknowledged_at": None,
            "created_at": now,
            "updated_at": now,
        }

    @staticmethod
    def to_dict(doc):
        if not doc:
            return None
        d = dict(doc)
        d["id"] = str(doc["_id"])
        d.pop("_id", None)
        for field in ("review_period_start", "review_period_end",
                      "acknowledged_at", "created_at", "updated_at"):
            if d.get(field) and isinstance(d[field], datetime):
                d[field] = d[field].isoformat()
        return d


class GoalModel:
    COLLECTION = "goals"

    STATUS = ["not_started", "in_progress", "completed", "cancelled"]
    PRIORITY = ["low", "medium", "high"]

    @staticmethod
    def new(employee_id, title, description, target_date,
            priority="medium", kpis=None):
        now = datetime.utcnow()
        return {
            "employee_id": employee_id,
            "title": title,
            "description": description,
            "target_date": target_date,
            "priority": priority,
            "kpis": kpis or [],        # list of {metric, target_value, current_value}
            "progress_percentage": 0,
            "status": "not_started",
            "comments": [],            # list of {author_id, text, timestamp}
            "created_at": now,
            "updated_at": now,
        }

    @staticmethod
    def to_dict(doc):
        if not doc:
            return None
        d = dict(doc)
        d["id"] = str(doc["_id"])
        d.pop("_id", None)
        for field in ("target_date", "created_at", "updated_at"):
            if d.get(field) and isinstance(d[field], datetime):
                d[field] = d[field].isoformat()
        return d
