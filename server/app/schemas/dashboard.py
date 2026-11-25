from typing import List
from pydantic import BaseModel
from app.schemas.transaction import TransactionResponse


class CategoryBreakdownItem(BaseModel):
    category: str
    amount: float


class MonthlyTrendItem(BaseModel):
    month: str
    income: float
    expense: float


class DashboardData(BaseModel):
    totalIncome: float
    totalExpense: float
    savings: float
    monthlyBudget: float
    budgetRemaining: float
    categoryBreakdown: List[CategoryBreakdownItem]
    monthlyTrend: List[MonthlyTrendItem]
    recentTransactions: List[TransactionResponse]


class DashboardSummaryResponse(BaseModel):
    success: bool = True
    data: DashboardData
