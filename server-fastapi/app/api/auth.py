from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.models.user import User
from app.models.transaction import Transaction
from app.models.budget import Budget
from app.schemas.user import (
    UserSignup,
    UserLogin,
    UserProfileUpdate,
    UserPasswordChange,
    UserResponse,
    AuthResponse,
    GenericResponse
)
from app.api.deps import get_current_user
from app.services.ai_service import clear_ai_cache
from app.core.cache import invalidate_all_user_caches, invalidate_user_cache

router = APIRouter(prefix="/auth", tags=["auth"])


def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    is_production = settings.ENVIRONMENT.lower() == "production"
    samesite_policy = "none" if is_production else "lax"
    secure_cookie = True if is_production else False

    # Access token cookie (7 days)
    response.set_cookie(
        key="token",
        value=access_token,
        httponly=True,
        secure=secure_cookie,
        samesite=samesite_policy,
        max_age=7 * 24 * 60 * 60
    )

    # Refresh token cookie (30 days)
    response.set_cookie(
        key="refreshToken",
        value=refresh_token,
        httponly=True,
        secure=secure_cookie,
        samesite=samesite_policy,
        max_age=30 * 24 * 60 * 60
    )


def clear_auth_cookies(response: Response):
    is_production = settings.ENVIRONMENT.lower() == "production"
    samesite_policy = "none" if is_production else "lax"
    secure_cookie = True if is_production else False
    response.delete_cookie(key="token", samesite=samesite_policy, secure=secure_cookie)
    response.delete_cookie(key="refreshToken", samesite=samesite_policy, secure=secure_cookie)


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: UserSignup, response: Response, db: AsyncSession = Depends(get_db)):
    clean_name = payload.name.strip()
    clean_email = payload.email.lower().strip()

    if not clean_name or not clean_email or not payload.password:
        raise HTTPException(status_code=400, detail="Name, email, and password are required")

    # Check if user already exists
    existing_query = await db.execute(select(User).where(User.email == clean_email))
    if existing_query.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    new_user = User(
        name=clean_name,
        email=clean_email,
        hashed_password=hash_password(payload.password)
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    access_token = create_access_token(new_user.id)
    refresh_token = create_refresh_token(new_user.id)
    set_auth_cookies(response, access_token, refresh_token)

    return AuthResponse(
        success=True,
        message="Account created",
        token=access_token,
        user=UserResponse.from_model(new_user)
    )


@router.post("/login", response_model=AuthResponse)
async def login(payload: UserLogin, response: Response, db: AsyncSession = Depends(get_db)):
    clean_email = payload.email.lower().strip()

    result = await db.execute(select(User).where(User.email == clean_email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    set_auth_cookies(response, access_token, refresh_token)

    return AuthResponse(
        success=True,
        message="Login successful",
        token=access_token,
        user=UserResponse.from_model(user)
    )


@router.post("/refresh")
async def refresh_access_token(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    refresh_token = request.cookies.get("refreshToken") or request.headers.get("x-refresh-token")
    if not refresh_token:
        try:
            body = await request.json()
            refresh_token = body.get("refreshToken")
        except Exception:
            pass

    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    try:
        decoded = decode_token(refresh_token)
        if decoded.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = decoded.get("id")
    except Exception:
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    try:
        numeric_user_id = int(user_id)
    except (ValueError, TypeError):
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Invalid session token")

    result = await db.execute(select(User).where(User.id == numeric_user_id))
    user = result.scalar_one_or_none()
    if not user:
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="User account no longer exists")

    new_access_token = create_access_token(user.id)
    new_refresh_token = create_refresh_token(user.id)
    set_auth_cookies(response, new_access_token, new_refresh_token)

    return {
        "success": True,
        "token": new_access_token,
        "user": UserResponse.from_model(user)
    }


@router.post("/logout", response_model=GenericResponse)
async def logout(response: Response):
    clear_auth_cookies(response)
    return GenericResponse(success=True, message="Logged out successfully")


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "success": True,
        "user": UserResponse.from_model(current_user)
    }


@router.put("/profile")
async def update_profile(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    clean_name = payload.name.strip()
    clean_email = payload.email.lower().strip()

    if not clean_name or not clean_email:
        raise HTTPException(status_code=400, detail="Name and email are required")

    # Fetch live attached user record from the database session
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # If changing email, ensure it's not already taken by another account
    if clean_email != user.email:
        existing = await db.execute(select(User).where(User.email == clean_email, User.id != user.id))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="An account with this email already exists")
        user.email = clean_email

    user.name = clean_name
    await db.commit()
    await db.refresh(user)
    invalidate_user_cache(user.id)

    return {
        "success": True,
        "message": "Profile updated",
        "user": UserResponse.from_model(user)
    }


@router.put("/password", response_model=GenericResponse)
async def change_password(
    payload: UserPasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not payload.currentPassword or not payload.newPassword:
        raise HTTPException(status_code=400, detail="Current and new password are required")

    if len(payload.newPassword) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    # Fetch live attached user record from the database session
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(payload.currentPassword, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    user.hashed_password = hash_password(payload.newPassword)
    await db.commit()
    invalidate_user_cache(user.id)

    return GenericResponse(success=True, message="Password updated successfully")


@router.get("/stats")
async def get_account_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Total count of transactions
    count_query = select(func.count(Transaction.id)).where(Transaction.user_id == current_user.id)
    tx_count_result = await db.execute(count_query)
    tx_count = tx_count_result.scalar_one() or 0

    # Calculate overall income and expense
    totals_query = (
        select(Transaction.type, func.sum(Transaction.amount))
        .where(Transaction.user_id == current_user.id)
        .group_by(Transaction.type)
    )
    totals_res = await db.execute(totals_query)
    total_income = 0.0
    total_expense = 0.0
    for row in totals_res.all():
        t_type, amount = row[0], float(row[1] or 0)
        if t_type == "income":
            total_income = amount
        elif t_type == "expense":
            total_expense = amount

    savings = total_income - total_expense

    # Get budget setting
    budget_query = select(Budget).where(Budget.user_id == current_user.id)
    budget_res = await db.execute(budget_query)
    budget = budget_res.scalar_one_or_none()
    monthly_budget = float(budget.monthly_budget) if budget else 0.0
    budget_remaining = (monthly_budget - total_expense) if monthly_budget > 0 else savings

    stats_data = {
        "transactionCount": tx_count,
        "totalIncome": total_income,
        "totalExpense": total_expense,
        "savings": savings,
        "budgetRemaining": budget_remaining,
        "joinedDate": current_user.created_at
    }

    return {
        "success": True,
        "data": stats_data,
        "stats": stats_data
    }


@router.delete("/account", response_model=GenericResponse)
async def delete_account(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user_id = current_user.id
    clear_ai_cache(user_id)
    invalidate_all_user_caches(user_id)

    # Fetch live attached user record to delete
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        await db.delete(user)
        await db.commit()

    clear_auth_cookies(response)
    return GenericResponse(success=True, message="Account and all associated records deleted permanently")
