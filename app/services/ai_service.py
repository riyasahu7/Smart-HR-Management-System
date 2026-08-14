"""
AI HR Assistant service — OpenAI-powered chatbot with HR context.
Falls back to rule-based responses if OpenAI key is not configured.
"""
import os
from datetime import datetime
from flask import current_app


HR_KNOWLEDGE_BASE = {
    "leave policy": (
        "Our leave policy: Casual Leave – 12 days/year, Sick Leave – 10 days/year, "
        "Earned Leave – 15 days/year, Maternity – 90 days, Paternity – 15 days, "
        "Bereavement – 5 days. Apply via the Leave section in the portal."
    ),
    "payroll": (
        "Salaries are processed on the last working day of every month. "
        "Payslips are available in the Payroll section. "
        "PF is deducted at 12% of basic salary. For queries contact HR."
    ),
    "attendance": (
        "Mark attendance by clicking Check-In when you start work and Check-Out when done. "
        "Work-from-home must be pre-approved. Missed punches can be regularized within 3 days."
    ),
    "performance review": (
        "Performance reviews are conducted annually and mid-year. "
        "You will receive a notification when your review is ready for acknowledgement. "
        "Ratings are on a scale of 1 (Poor) to 5 (Excellent)."
    ),
    "holidays": (
        "The holiday calendar is published at the start of each year. "
        "There are approximately 10 national holidays and 2 optional holidays per year."
    ),
    "probation": (
        "The probation period is 3–6 months depending on your role. "
        "A probation review will be conducted before confirmation."
    ),
    "resignation": (
        "To resign, submit a resignation letter to your manager and HR. "
        "Notice period is typically 30–90 days depending on your employment agreement."
    ),
    "reimbursement": (
        "Submit expense claims through the Finance team with original receipts. "
        "Travel and medical reimbursements are processed within 15 working days."
    ),
}

SYSTEM_PROMPT = """You are an intelligent HR Assistant for a Smart HR Management System.
You help employees with questions about HR policies, leave, payroll, attendance, performance reviews, and general workplace matters.
Be concise, friendly, and professional. If you don't know something, direct the user to contact HR directly.
Always stay within HR-related topics."""


def _rule_based_response(message: str) -> str:
    """Fallback rule-based responses when OpenAI is not configured."""
    msg_lower = message.lower()
    for keyword, response in HR_KNOWLEDGE_BASE.items():
        if keyword in msg_lower:
            return response

    if any(w in msg_lower for w in ["hi", "hello", "hey", "good morning", "good afternoon"]):
        return "Hello! I'm your HR Assistant. How can I help you today? You can ask me about leave policies, payroll, attendance, performance reviews, or any other HR-related queries."

    if any(w in msg_lower for w in ["thank", "thanks"]):
        return "You're welcome! Feel free to ask if you have any other HR questions."

    if "salary" in msg_lower or "ctc" in msg_lower:
        return HR_KNOWLEDGE_BASE["payroll"]

    if "wfh" in msg_lower or "work from home" in msg_lower:
        return "Work from home requests must be approved by your manager in advance. Mark your attendance as WFH on the day. For extended WFH, consult HR."

    return (
        "I understand you have a query. For this specific topic, please contact your HR team directly at hr@company.com "
        "or raise a ticket through the HR portal. I'm here to help with general policy questions!"
    )


def chat_with_ai(message: str, conversation_history: list = None) -> dict:
    """
    Process an HR chat message.
    Uses OpenAI GPT if API key is available, otherwise falls back to rule-based responses.
    """
    api_key = current_app.config.get("OPENAI_API_KEY", "")
    conversation_history = conversation_history or []

    if api_key and api_key != "your-openai-api-key":
        try:
            import openai
            openai.api_key = api_key

            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            # Include last 10 messages for context
            for entry in conversation_history[-10:]:
                messages.append({"role": entry["role"], "content": entry["content"]})
            messages.append({"role": "user", "content": message})

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=500,
                temperature=0.7,
            )
            reply = response.choices[0].message["content"].strip()
            source = "openai"
        except Exception as e:
            reply = _rule_based_response(message)
            source = "fallback"
    else:
        reply = _rule_based_response(message)
        source = "rule_based"

    return {
        "reply": reply,
        "source": source,
        "timestamp": datetime.utcnow().isoformat(),
    }


def get_hr_insights(data_type: str, context: dict = None) -> str:
    """
    Generate AI-driven HR insights (headcount trends, attrition risk, etc.).
    Returns a text summary.
    """
    context = context or {}
    insights = {
        "attrition": (
            f"Based on current data, departments with high overtime and low performance scores "
            f"are at elevated attrition risk. Consider scheduling 1:1 check-ins and reviewing "
            f"compensation benchmarks."
        ),
        "attendance": (
            f"Attendance patterns show peak absences on Mondays and Fridays. "
            f"Consider flexible scheduling to improve overall attendance rates."
        ),
        "performance": (
            f"Team performance averages {context.get('avg_rating', 'N/A')}/5. "
            f"Focus areas: technical skills training and cross-functional collaboration."
        ),
        "leave": (
            f"Leave utilization is currently at {context.get('utilization', 'N/A')}%. "
            f"Encourage employees to plan and use earned leaves to avoid burnout."
        ),
    }
    return insights.get(data_type, "Insufficient data to generate insights at this time.")
