from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.cache import get_cached_dashboard, set_cached_dashboard
from app.models.user import User
from app.models.transaction import Transaction
from app.models.budget import Budget
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    DashboardData,
    CategoryBreakdownItem,
    MonthlyTrendItem
)
from app.schemas.transaction import TransactionResponse
from app.api.deps import get_current_user
from app.services.finance_analyzer import summarize_transactions

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Return in-memory cached dashboard if available (sub-millisecond speed)
    cached = get_cached_dashboard(current_user.id)
    if cached is not None:
        return DashboardSummaryResponse(success=True, data=cached)

    # 2. Fetch transactions and budget in 2 fast queries
    tx_query = (
        select(Transaction)
        .where(Transaction.user_id == current_user.id)
        .order_by(Transaction.transaction_date.desc())
    )
    tx_res = await db.execute(tx_query)
    all_transactions = tx_res.scalars().all()

    budget_query = select(Budget).where(Budget.user_id == current_user.id)
    budget_res = await db.execute(budget_query)
    budget = budget_res.scalar_one_or_none()

    # 3. Compute metrics in memory (instantaneous in Python)
    summary = summarize_transactions(all_transactions, budget)
    recent_transactions = [TransactionResponse.from_model(t) for t in all_transactions[:5]]

    data = DashboardData(
        totalIncome=summary["totalIncome"],
        totalExpense=summary["totalExpense"],
        savings=summary["savings"],
        monthlyBudget=summary["monthlyBudget"],
        budgetRemaining=summary["budgetRemaining"],
        categoryBreakdown=[CategoryBreakdownItem(**c) for c in summary["categoryBreakdown"]],
        monthlyTrend=[MonthlyTrendItem(**m) for m in summary["monthlyTrend"]],
        recentTransactions=recent_transactions
    )

    # Cache for 60 seconds (invalidated on any transaction or budget mutation)
    set_cached_dashboard(current_user.id, data)

    return DashboardSummaryResponse(success=True, data=data)
