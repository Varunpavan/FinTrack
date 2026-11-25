import json
import time
from typing import Dict, Any, List
from google import genai
from google.genai import types
from openai import AsyncOpenAI
from app.core.config import settings
from app.services.finance_analyzer import analyze_finance

# In-memory cache to store insights and predictions per user (15 min TTL)
_insights_cache: Dict[str, Dict[str, Any]] = {}
_prediction_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 15 * 60


def clear_ai_cache(user_id: Any) -> None:
    if user_id:
        key = str(user_id)
        _insights_cache.pop(key, None)
        _prediction_cache.pop(key, None)


def sanitize_insights(insights: List[str]) -> List[str]:
    # Ensure all currency symbols are consistently Indian Rupees (₹)
    return [item.replace("$", "₹") if isinstance(item, str) else str(item) for item in insights]


def has_gemini_key() -> bool:
    key = settings.GEMINI_API_KEY
    if not key or not key.strip() or "your_" in key:
        return False
    return True


def has_openai_key() -> bool:
    key = settings.OPENAI_API_KEY
    if not key or not key.strip() or "your_" in key:
        return False
    return True


async def generate_ai_insights(transactions: List[Any], budget: Any) -> Dict[str, Any]:
    analysis = analyze_finance(transactions, budget)

    def fallback():
        combined = analysis["insights"] + analysis["recommendations"]
        return {
            "provider": "heuristic",
            "insights": combined[:8]
        }

    summary_payload = {
        "totalIncome": analysis["totalIncome"],
        "totalExpense": analysis["totalExpense"],
        "savings": analysis["savings"],
        "monthlyBudget": analysis["monthlyBudget"],
        "budgetRemaining": analysis["budgetRemaining"],
        "categoryBreakdown": analysis["categoryBreakdown"]
    }

    prompt = (
        "You are a friendly personal finance assistant. Based on this user's spending summary, "
        "provide 5 to 8 short, clear, and actionable financial insights as a JSON array of strings.\n"
        "CRITICAL CURRENCY INSTRUCTION:\n"
        "- The user's currency is Indian Rupees (INR). Always format every amount using the Indian Rupee symbol '₹' (e.g. ₹50,000, ₹30,000, ₹80,000).\n"
        "- NEVER use the dollar sign ('$') or any other currency symbol under any circumstance.\n"
        "- Return ONLY the JSON array of strings without any markdown formatting or extra text.\n\n"
        f"Spending Summary (in INR): {json.dumps(summary_payload)}"
    )

    # 1. Primary AI Provider: Google Gemini
    if has_gemini_key():
        candidate_models = [settings.GEMINI_MODEL]
        if "lite" in settings.GEMINI_MODEL:
            candidate_models.append("gemini-3.5-flash-lite")
        else:
            candidate_models.append("gemini-2.5-flash-lite")

        client = genai.Client(api_key=settings.GEMINI_API_KEY, http_options={"api_version": "v1beta"})
        for model_name in candidate_models:
            try:
                response = await client.aio.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )

                raw_text = response.text or ""
                cleaned = raw_text.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(cleaned)

                if isinstance(parsed, list) and len(parsed) > 0:
                    return {
                        "provider": "gemini",
                        "insights": sanitize_insights(parsed)
                    }
            except Exception as e:
                print(f"[AI Service] Gemini ({model_name}) call failed, trying next option: {e}")

    # 2. Secondary AI Provider: OpenAI (if configured and Gemini is not used)
    if has_openai_key():
        try:
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4
            )

            raw_content = response.choices[0].message.content or ""
            cleaned = raw_content.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(cleaned)

            if isinstance(parsed, list) and len(parsed) > 0:
                return {
                    "provider": "openai",
                    "insights": sanitize_insights(parsed)
                }
        except Exception as e:
            print(f"[AI Service] OpenAI call failed: {e}")

    # 3. Final Fallback: Deterministic Heuristic Engine
    return {
        "provider": "heuristic",
        "insights": sanitize_insights(fallback()["insights"])
    }


async def predict_expense(transactions: List[Any], budget: Any) -> Dict[str, Any]:
    analysis = analyze_finance(transactions, budget)
    monthly_budget = analysis["monthlyBudget"]
    predicted = analysis["predictedExpense"]

    budget_risk = bool(monthly_budget > 0 and predicted > monthly_budget)

    return {
        "predictedExpense": predicted,
        "confidence": analysis["confidence"],
        "budgetRisk": budget_risk,
        "recommendations": analysis["recommendations"]
    }
