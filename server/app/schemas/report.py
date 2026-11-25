from typing import List
from pydantic import BaseModel
from app.schemas.transaction import TransactionResponse
from app.schemas.dashboard import CategoryBreakdownItem, MonthlyTrendItem


class ReportData(BaseModel):
    period: str
    totalIncome: float
    totalExpense: float
    savings: float
    budgetRemaining: float
    categoryBreakdown: List[CategoryBreakdownItem]
    monthlyTrend: List[MonthlyTrendItem]
    transactions: List[TransactionResponse]


class MonthlyReportResponse(BaseModel):
    success: bool = True
    data: ReportData
