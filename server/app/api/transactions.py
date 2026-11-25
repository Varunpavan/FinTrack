import math
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from app.core.database import get_db
from app.models.user import User
from app.models.transaction import Transaction
from app.schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionListResponse,
    PaginationMeta
)
from app.api.deps import get_current_user
from app.services.ai_service import clear_ai_cache
from app.core.cache import invalidate_dashboard_cache

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_transaction(
    payload: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not payload.type or not payload.title or not payload.category or payload.amount is None or payload.amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Type, title, category, and a valid positive amount are required"
        )

    tx_date = payload.transactionDate or datetime.now(timezone.utc)

    new_tx = Transaction(
        user_id=current_user.id,
        type=payload.type,
        title=payload.title.strip(),
        amount=float(payload.amount),
        category=payload.category.strip(),
        payment_method=payload.paymentMethod or "card",
        description=payload.description.strip() if payload.description else "",
        transaction_date=tx_date
    )

    db.add(new_tx)
    await db.commit()
    await db.refresh(new_tx)

    # Invalidate AI insight and dashboard cache so fresh metrics will be served
    clear_ai_cache(current_user.id)
    invalidate_dashboard_cache(current_user.id)

    return {
        "success": True,
        "message": "Transaction added",
        "data": TransactionResponse.from_model(new_tx)
    }


@router.get("", response_model=TransactionListResponse)
async def get_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    category: Optional[str] = None,
    type: Optional[str] = None,
    search: Optional[str] = None,
    sort: str = Query("latest"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Base query filtered by logged-in user
    conditions = [Transaction.user_id == current_user.id]

    if category:
        conditions.append(Transaction.category == category)
    if type:
        conditions.append(Transaction.type == type)
    if search and search.strip():
        term = f"%{search.strip()}%"
        conditions.append(
            or_(
                Transaction.title.ilike(term),
                Transaction.category.ilike(term),
                Transaction.description.ilike(term)
            )
        )

    # Data query with sorting and pagination
    data_stmt = select(Transaction).where(*conditions)

    if sort == "oldest":
        data_stmt = data_stmt.order_by(Transaction.transaction_date.asc())
    elif sort == "amount_desc":
        data_stmt = data_stmt.order_by(Transaction.amount.desc())
    elif sort == "amount_asc":
        data_stmt = data_stmt.order_by(Transaction.amount.asc())
    else:  # default 'latest'
        data_stmt = data_stmt.order_by(Transaction.transaction_date.desc())

    offset = (page - 1) * limit
    data_stmt = data_stmt.offset(offset).limit(limit)

    results = await db.execute(data_stmt)
    records = results.scalars().all()

    # Fast-path: if page 1 has fewer records than limit, total is already known without an extra round-trip
    if page == 1 and len(records) < limit:
        total = len(records)
    else:
        count_stmt = select(func.count(Transaction.id)).where(*conditions)
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one() or 0

    total_pages = max(1, math.ceil(total / limit)) if total > 0 else 1

    return TransactionListResponse(
        success=True,
        data=[TransactionResponse.from_model(t) for t in records],
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            pages=total_pages
        )
    )


@router.put("/{tx_id}")
async def update_transaction(
    tx_id: str,
    payload: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        numeric_id = int(tx_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid transaction ID")

    stmt = select(Transaction).where(Transaction.id == numeric_id, Transaction.user_id == current_user.id)
    result = await db.execute(stmt)
    tx = result.scalar_one_or_none()

    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if payload.type is not None:
        tx.type = payload.type
    if payload.title is not None:
        tx.title = payload.title.strip()
    if payload.amount is not None:
        if payload.amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be positive")
        tx.amount = float(payload.amount)
    if payload.category is not None:
        tx.category = payload.category.strip()
    if payload.paymentMethod is not None:
        tx.payment_method = payload.paymentMethod
    if payload.description is not None:
        tx.description = payload.description.strip()
    if payload.transactionDate is not None:
        tx.transaction_date = payload.transactionDate

    await db.commit()
    await db.refresh(tx)

    clear_ai_cache(current_user.id)
    invalidate_dashboard_cache(current_user.id)

    return {
        "success": True,
        "message": "Transaction updated",
        "data": TransactionResponse.from_model(tx)
    }


@router.delete("/{tx_id}")
async def delete_transaction(
    tx_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        numeric_id = int(tx_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid transaction ID")

    stmt = select(Transaction).where(Transaction.id == numeric_id, Transaction.user_id == current_user.id)
    result = await db.execute(stmt)
    tx = result.scalar_one_or_none()

    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    await db.delete(tx)
    await db.commit()

    clear_ai_cache(current_user.id)
    invalidate_dashboard_cache(current_user.id)

    return {
        "success": True,
        "message": "Transaction deleted"
    }
