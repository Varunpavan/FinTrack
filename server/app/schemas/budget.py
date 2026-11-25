from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class CategoryBudgetItem(BaseModel):
    category: str
    limit: float


class BudgetSet(BaseModel):
    monthlyBudget: float
    categoryBudgets: Optional[List[CategoryBudgetItem]] = []


class BudgetDataResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: Optional[str] = None
    mongo_id: Optional[str] = Field(default=None, serialization_alias="_id")
    userId: Optional[str] = None
    monthlyBudget: float
    categoryBudgets: List[CategoryBudgetItem]
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

    @classmethod
    def from_model(cls, b):
        if not b:
            return cls(monthlyBudget=0.0, categoryBudgets=[])
        b_id_str = str(b.id)
        raw_categories = b.category_budgets if isinstance(b.category_budgets, list) else []
        categories = [
            CategoryBudgetItem(category=c.get("category", ""), limit=float(c.get("limit", 0)))
            for c in raw_categories if isinstance(c, dict)
        ]
        return cls(
            id=b_id_str,
            mongo_id=b_id_str,
            userId=str(b.user_id),
            monthlyBudget=float(b.monthly_budget),
            categoryBudgets=categories,
            createdAt=b.created_at,
            updatedAt=b.updated_at
        )


class BudgetResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
    data: BudgetDataResponse
