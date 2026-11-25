import calendar
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import User
from app.models.transaction import Transaction
from app.models.budget import Budget
from app.schemas.report import MonthlyReportResponse, ReportData
from app.schemas.transaction import TransactionResponse
from app.schemas.dashboard import CategoryBreakdownItem, MonthlyTrendItem
from app.api.deps import get_current_user
from app.services.finance_analyzer import summarize_transactions
from app.services.pdf_service import generate_monthly_pdf

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/monthly")
async def get_monthly_report(
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    format: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    now = datetime.now(timezone.utc)
    target_year = year if (year and 1970 <= year <= 2100) else now.year
    target_month = max(1, min(12, month)) if month else now.month

    # Calculate month date range
    _, last_day = calendar.monthrange(target_year, target_month)
    start_date = datetime(target_year, target_month, 1, 0, 0, 0, tzinfo=timezone.utc)
    end_date = datetime(target_year, target_month, last_day, 23, 59, 59, 999999, tzinfo=timezone.utc)

    # Fetch transactions in this period
    tx_stmt = (
        select(Transaction)
        .where(
            Transaction.user_id == current_user.id,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date
        )
        .order_by(Transaction.transaction_date.desc())
    )
    tx_res = await db.execute(tx_stmt)
    transactions = tx_res.scalars().all()

    # Fetch budget
    budget_stmt = select(Budget).where(Budget.user_id == current_user.id)
    budget_res = await db.execute(budget_stmt)
    budget = budget_res.scalar_one_or_none()

    summary = summarize_transactions(transactions, budget)
    period_str = f"{calendar.month_name[target_month]} {target_year}"

    tx_responses = [TransactionResponse.from_model(t) for t in transactions]

    report_payload = {
        "period": period_str,
        "totalIncome": summary["totalIncome"],
        "totalExpense": summary["totalExpense"],
        "savings": summary["savings"],
        "budgetRemaining": summary["budgetRemaining"],
        "categoryBreakdown": summary["categoryBreakdown"],
        "monthlyTrend": summary["monthlyTrend"],
        "transactions": [t.model_dump() for t in tx_responses]
    }

    # If PDF format requested, build and return the PDF file
    if format == "pdf":
        pdf_bytes = generate_monthly_pdf(report_payload)
        filename = f"finance-report-{target_year}-{target_month:02d}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    return MonthlyReportResponse(
        success=True,
        data=ReportData(
            period=period_str,
            totalIncome=summary["totalIncome"],
            totalExpense=summary["totalExpense"],
            savings=summary["savings"],
            budgetRemaining=summary["budgetRemaining"],
            categoryBreakdown=[CategoryBreakdownItem(**c) for c in summary["categoryBreakdown"]],
            monthlyTrend=[MonthlyTrendItem(**m) for m in summary["monthlyTrend"]],
            transactions=tx_responses
        )
    )
