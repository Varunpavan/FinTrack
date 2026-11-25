import time
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import User
from app.models.transaction import Transaction
from app.models.budget import Budget
from app.schemas.ai import (
    AIInsightsResponse,
    AIInsightsData,
    AIPredictResponse,
    AIPredictData
)
from app.api.deps import get_current_user
from app.services.ai_service import (
    generate_ai_insights,
    predict_expense,
    _insights_cache,
    _prediction_cache,
    CACHE_TTL_SECONDS
)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/insights", response_model=AIInsightsResponse)
async def get_insights(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    cache_key = str(current_user.id)
    cached = _insights_cache.get(cache_key)

    # Return cached insights if fresh (within 15 minutes)
    if cached and (time.time() - cached["timestamp"] < CACHE_TTL_SECONDS):
        data = cached["data"]
        return AIInsightsResponse(
            success=True,
            data=AIInsightsData(**data),
            insights=data["insights"]
        )

    # Fetch user transactions and budget
    tx_query = select(Transaction).where(Transaction.user_id == current_user.id)
    tx_res = await db.execute(tx_query)
    transactions = tx_res.scalars().all()

    budget_query = select(Budget).where(Budget.user_id == current_user.id)
    budget_res = await db.execute(budget_query)
    budget = budget_res.scalar_one_or_none()

    result = await generate_ai_insights(transactions, budget)

    # Store in cache
    _insights_cache[cache_key] = {
        "timestamp": time.time(),
        "data": result
    }

    return AIInsightsResponse(
        success=True,
        data=AIInsightsData(**result),
        insights=result["insights"]
    )


@router.post("/predict", response_model=AIPredictResponse)
async def get_prediction(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    cache_key = str(current_user.id)
    cached = _prediction_cache.get(cache_key)

    # Return cached prediction if fresh
    if cached and (time.time() - cached["timestamp"] < CACHE_TTL_SECONDS):
        data = cached["data"]
        predict_obj = AIPredictData(**data)
        return AIPredictResponse(
            success=True,
            data=predict_obj,
            prediction=predict_obj
        )

    tx_query = select(Transaction).where(Transaction.user_id == current_user.id)
    tx_res = await db.execute(tx_query)
    transactions = tx_res.scalars().all()

    budget_query = select(Budget).where(Budget.user_id == current_user.id)
    budget_res = await db.execute(budget_query)
    budget = budget_res.scalar_one_or_none()

    prediction_result = await predict_expense(transactions, budget)

    _prediction_cache[cache_key] = {
        "timestamp": time.time(),
        "data": prediction_result
    }

    predict_obj = AIPredictData(**prediction_result)
    return AIPredictResponse(
        success=True,
        data=predict_obj,
        prediction=predict_obj
    )
