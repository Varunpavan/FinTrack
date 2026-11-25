from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified
from app.core.database import get_db
from app.core.cache import (
    get_cached_budget,
    set_cached_budget,
    invalidate_budget_cache,
    invalidate_dashboard_cache
)
from app.models.user import User
from app.models.budget import Budget
from app.schemas.budget import BudgetSet, BudgetResponse, BudgetDataResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/budget", tags=["budget"])


@router.post("", response_model=BudgetResponse)
async def set_budget(
    payload: BudgetSet,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if payload.monthlyBudget is None or payload.monthlyBudget < 0:
        raise HTTPException(status_code=400, detail="A valid monthly budget is required")

    categories_list = [c.model_dump() for c in (payload.categoryBudgets or [])]

    # Check for existing budget (upsert)
    stmt = select(Budget).where(Budget.user_id == current_user.id)
    result = await db.execute(stmt)
    budget = result.scalar_one_or_none()

    if budget:
        budget.monthly_budget = float(payload.monthlyBudget)
        budget.category_budgets = categories_list
        flag_modified(budget, "category_budgets")
        budget.updated_at = datetime.now(timezone.utc)
    else:
        budget = Budget(
            user_id=current_user.id,
            monthly_budget=float(payload.monthlyBudget),
            category_budgets=categories_list
        )
        db.add(budget)

    await db.commit()
    await db.refresh(budget)

    # Invalidate and cache fresh budget data
    budget_data = BudgetDataResponse.from_model(budget)
    set_cached_budget(current_user.id, budget_data)
    invalidate_dashboard_cache(current_user.id)

    return BudgetResponse(
        success=True,
        message="Budget saved",
        data=budget_data
    )


@router.get("", response_model=BudgetResponse)
async def get_budget(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    cached = get_cached_budget(current_user.id)
    if cached is not None:
        return BudgetResponse(success=True, data=cached)

    stmt = select(Budget).where(Budget.user_id == current_user.id)
    result = await db.execute(stmt)
    budget = result.scalar_one_or_none()

    if not budget:
        empty_data = BudgetDataResponse(monthlyBudget=0.0, categoryBudgets=[])
        set_cached_budget(current_user.id, empty_data)
        return BudgetResponse(success=True, data=empty_data)

    budget_data = BudgetDataResponse.from_model(budget)
    set_cached_budget(current_user.id, budget_data)
    return BudgetResponse(
        success=True,
        data=budget_data
    )


@router.put("", response_model=BudgetResponse)
async def update_budget(
    payload: BudgetSet,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await set_budget(payload, current_user, db)
