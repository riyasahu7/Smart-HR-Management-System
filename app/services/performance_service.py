"""
Performance service — reviews, goals, KPIs.
"""
from datetime import datetime
from bson import ObjectId
from app import mongo
from app.models.performance_model import PerformanceReviewModel, GoalModel
from app.utils.helpers import parse_date


def _reviews():
    return mongo.db[PerformanceReviewModel.COLLECTION]


def _goals():
    return mongo.db[GoalModel.COLLECTION]


# ── Reviews ───────────────────────────────────────────────────────────────────

def create_review(data, reviewer_id):
    employee_id = data.get("employee_id")
    review_type = data.get("review_type", "annual")
    start = parse_date(data.get("review_period_start"))
    end = parse_date(data.get("review_period_end"))
    ratings = data.get("ratings", {})
    comments = data.get("comments", "")

    if not all([employee_id, start, end]):
        return None, "employee_id, review_period_start, review_period_end are required."

    doc = PerformanceReviewModel.new(
        employee_id=employee_id,
        reviewer_id=reviewer_id,
        review_type=review_type,
        review_period_start=start,
        review_period_end=end,
        ratings=ratings,
        comments=comments,
    )
    doc["strengths"] = data.get("strengths", [])
    doc["areas_of_improvement"] = data.get("areas_of_improvement", [])
    doc["goals_for_next_period"] = data.get("goals_for_next_period", [])

    result = _reviews().insert_one(doc)
    doc["_id"] = result.inserted_id
    return PerformanceReviewModel.to_dict(doc), None


def get_review(review_id):
    try:
        doc = _reviews().find_one({"_id": ObjectId(review_id)})
    except Exception:
        doc = None
    return PerformanceReviewModel.to_dict(doc)


def get_employee_reviews(employee_id, review_type=None, status=None):
    query = {"employee_id": employee_id}
    if review_type:
        query["review_type"] = review_type
    if status:
        query["status"] = status
    docs = list(_reviews().find(query).sort("created_at", -1))
    return [PerformanceReviewModel.to_dict(d) for d in docs]


def get_all_reviews(page=1, per_page=20, department=None, status=None,
                    review_type=None, employee_id=None):
    query = {}
    if status:
        query["status"] = status
    if review_type:
        query["review_type"] = review_type
    if employee_id:
        query["employee_id"] = employee_id

    # Join with employees for department filter
    if department:
        from app import mongo as m
        from app.models.employee_model import EmployeeModel
        emp_ids = [
            str(e["_id"])
            for e in m.db[EmployeeModel.COLLECTION].find(
                {"department": department}, {"_id": 1}
            )
        ]
        query["employee_id"] = {"$in": emp_ids}

    total = _reviews().count_documents(query)
    docs = list(
        _reviews()
        .find(query)
        .sort("created_at", -1)
        .skip((page - 1) * per_page)
        .limit(per_page)
    )
    return [PerformanceReviewModel.to_dict(d) for d in docs], {
        "total": total, "page": page, "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }


def update_review(review_id, data):
    allowed = ["ratings", "comments", "strengths", "areas_of_improvement",
               "goals_for_next_period", "status"]
    update_data = {k: v for k, v in data.items() if k in allowed}

    if "ratings" in update_data:
        r = update_data["ratings"]
        filled = [v for v in r.values() if v > 0]
        update_data["average_rating"] = round(sum(filled) / len(filled), 2) if filled else 0

    update_data["updated_at"] = datetime.utcnow()
    result = _reviews().update_one({"_id": ObjectId(review_id)}, {"$set": update_data})
    if result.matched_count == 0:
        return None, "Review not found."
    return get_review(review_id), None


def submit_review(review_id):
    now = datetime.utcnow()
    result = _reviews().update_one(
        {"_id": ObjectId(review_id), "status": "draft"},
        {"$set": {"status": "submitted", "updated_at": now}}
    )
    if result.matched_count == 0:
        return None, "Review not found or already submitted."
    return get_review(review_id), None


def acknowledge_review(review_id, employee_id):
    now = datetime.utcnow()
    review = _reviews().find_one({"_id": ObjectId(review_id)})
    if not review:
        return None, "Review not found."
    if review.get("employee_id") != employee_id:
        return None, "You can only acknowledge your own reviews."
    if review.get("status") != "submitted":
        return None, "Review must be submitted before it can be acknowledged."
    _reviews().update_one(
        {"_id": ObjectId(review_id)},
        {"$set": {
            "acknowledged_by_employee": True,
            "acknowledged_at": now,
            "status": "acknowledged",
            "updated_at": now,
        }}
    )
    return get_review(review_id), None


def get_performance_analytics(employee_id):
    """Return rating trend across all reviews for an employee."""
    docs = list(_reviews().find({"employee_id": employee_id}).sort("created_at", 1))
    trend = []
    for d in docs:
        trend.append({
            "review_type": d.get("review_type"),
            "average_rating": d.get("average_rating", 0),
            "period_start": d["review_period_start"].isoformat() if d.get("review_period_start") else None,
            "status": d.get("status"),
        })
    return {"employee_id": employee_id, "trend": trend, "total_reviews": len(docs)}


# ── Goals ─────────────────────────────────────────────────────────────────────

def create_goal(data, creator_id):
    employee_id = data.get("employee_id", creator_id)
    target_date = parse_date(data.get("target_date"))
    if not data.get("title") or not target_date:
        return None, "title and target_date are required."

    doc = GoalModel.new(
        employee_id=employee_id,
        title=data["title"],
        description=data.get("description", ""),
        target_date=target_date,
        priority=data.get("priority", "medium"),
        kpis=data.get("kpis", []),
    )
    result = _goals().insert_one(doc)
    doc["_id"] = result.inserted_id
    return GoalModel.to_dict(doc), None


def get_employee_goals(employee_id, status=None):
    query = {"employee_id": employee_id}
    if status:
        query["status"] = status
    docs = list(_goals().find(query).sort("target_date", 1))
    return [GoalModel.to_dict(d) for d in docs]


def update_goal(goal_id, data):
    allowed = ["title", "description", "target_date", "priority",
               "kpis", "progress_percentage", "status"]
    update_data = {k: v for k, v in data.items() if k in allowed}
    if "target_date" in update_data:
        update_data["target_date"] = parse_date(update_data["target_date"])
    update_data["updated_at"] = datetime.utcnow()
    result = _goals().update_one({"_id": ObjectId(goal_id)}, {"$set": update_data})
    if result.matched_count == 0:
        return None, "Goal not found."
    doc = _goals().find_one({"_id": ObjectId(goal_id)})
    return GoalModel.to_dict(doc), None


def add_goal_comment(goal_id, author_id, text):
    comment = {"author_id": author_id, "text": text, "timestamp": datetime.utcnow().isoformat()}
    _goals().update_one(
        {"_id": ObjectId(goal_id)},
        {"$push": {"comments": comment}, "$set": {"updated_at": datetime.utcnow()}}
    )
    doc = _goals().find_one({"_id": ObjectId(goal_id)})
    return GoalModel.to_dict(doc)
