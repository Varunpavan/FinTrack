from typing import List, Optional
from pydantic import BaseModel


class AIInsightsData(BaseModel):
    provider: str
    insights: List[str]


class AIInsightsResponse(BaseModel):
    success: bool = True
    data: AIInsightsData
    insights: List[str]


class AIPredictData(BaseModel):
    predictedExpense: float
    confidence: float
    budgetRisk: bool
    recommendations: List[str]


class AIPredictResponse(BaseModel):
    success: bool = True
    data: AIPredictData
    prediction: AIPredictData
