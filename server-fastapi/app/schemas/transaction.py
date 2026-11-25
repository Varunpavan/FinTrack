from typing import Optional, List, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict, field_validator


def normalize_transaction_date(v: Any) -> Optional[datetime]:
    if not v:
        return None
    if isinstance(v, str):
        v = v.strip()
        if not v:
            return None
        # Handle simple date strings like "2026-11-01"
        if len(v) == 10 and v[4] == "-" and v[7] == "-":
            try:
                dt = datetime.strptime(v, "%Y-%m-%d")
                # Fix at 12:00:00 UTC to ensure immunity against any timezone shift (+-12h)
                return dt.replace(hour=12, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
            except Exception:
                pass
        try:
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None
    elif isinstance(v, datetime):
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v
    return v


class TransactionCreate(BaseModel):
    type: str  # 'income' or 'expense'
    title: str
    amount: float
    category: str
    paymentMethod: Optional[str] = "card"
    description: Optional[str] = ""
    transactionDate: Optional[datetime] = None

    @field_validator("transactionDate", mode="before")
    @classmethod
    def validate_date(cls, v):
        return normalize_transaction_date(v)


class TransactionUpdate(BaseModel):
    type: Optional[str] = None
    title: Optional[str] = None
    amount: Optional[float] = None
    category: Optional[str] = None
    paymentMethod: Optional[str] = None
    description: Optional[str] = None
    transactionDate: Optional[datetime] = None

    @field_validator("transactionDate", mode="before")
    @classmethod
    def validate_date(cls, v):
        return normalize_transaction_date(v)


class TransactionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    mongo_id: str = Field(serialization_alias="_id")
    userId: str
    type: str
    title: str
    amount: float
    category: str
    paymentMethod: str
    description: str
    transactionDate: datetime
    createdAt: datetime

    @classmethod
    def from_model(cls, t):
        t_id_str = str(t.id)
        return cls(
            id=t_id_str,
            mongo_id=t_id_str,
            userId=str(t.user_id),
            type=t.type,
            title=t.title,
            amount=t.amount,
            category=t.category,
            paymentMethod=t.payment_method or "card",
            description=t.description or "",
            transactionDate=t.transaction_date,
            createdAt=t.created_at
        )


class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int
    pages: int


class TransactionListResponse(BaseModel):
    success: bool = True
    data: List[TransactionResponse]
    pagination: PaginationMeta
