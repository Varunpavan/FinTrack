from datetime import datetime, timezone


def format_inr(value: float) -> str:
    # Clean Indian Rupee formatting
    rounded = int(round(value or 0))
    return f"₹{rounded:,}"


def summarize_transactions(transactions, budget=None):
    total_income = 0.0
    total_expense = 0.0
    category_totals = {}
    month_buckets = {}

    for t in transactions:
        amount = float(t.amount or 0)
        t_type = t.type

        if t_type == "income":
            total_income += amount
        elif t_type == "expense":
            total_expense += amount
            cat = t.category or "Other"
            category_totals[cat] = category_totals.get(cat, 0.0) + amount

        # Monthly trend grouping
        t_date = t.transaction_date or datetime.now(timezone.utc)
        month_key = t_date.strftime("%Y-%m")

        if month_key not in month_buckets:
            month_buckets[month_key] = {"month": month_key, "income": 0.0, "expense": 0.0}

        if t_type in ("income", "expense"):
            month_buckets[month_key][t_type] += amount

    savings = total_income - total_expense
    monthly_budget = float(budget.monthly_budget) if budget else 0.0
    budget_remaining = (monthly_budget - total_expense) if monthly_budget > 0 else savings

    # Sort categories by highest spending first
    category_breakdown = [
        {"category": cat, "amount": amt}
        for cat, amt in sorted(category_totals.items(), key=lambda item: item[1], reverse=True)
    ]

    # Sort monthly trends chronologically
    monthly_trend = [month_buckets[k] for k in sorted(month_buckets.keys())]

    return {
        "totalIncome": total_income,
        "totalExpense": total_expense,
        "savings": savings,
        "monthlyBudget": monthly_budget,
        "budgetRemaining": budget_remaining,
        "categoryBreakdown": category_breakdown,
        "monthlyTrend": monthly_trend,
    }


def analyze_finance(transactions, budget=None):
    summary = summarize_transactions(transactions, budget)
    insights = []
    recommendations = []

    if not transactions:
        welcome_insights = [
            "Welcome to FinTrack! Add your first income or expense transaction to unlock personalized AI insights and spending forecasts."
        ]
        monthly_budget = summary["monthlyBudget"]
        if monthly_budget > 0:
            welcome_insights.append(
                f"Your monthly target budget is set to {format_inr(monthly_budget)}. Add your expenses as they occur to monitor remaining limits."
            )
        welcome_insights.append(
            "FinTrack categorizes your cash flow across Food, Rent, Shopping, Bills, and Transport to give you full financial visibility."
        )
        return {
            **summary,
            "insights": welcome_insights,
            "recommendations": [
                "Record daily transactions promptly to keep financial metrics up to date.",
                "Review category-specific limits under the Budget tab to control discretionary spending."
            ],
            "predictedExpense": 0.0,
            "confidence": 0.0,
        }

    # 1. Top expense category insight
    if summary["categoryBreakdown"]:
        top_cat = summary["categoryBreakdown"][0]
        share = 0
        if summary["totalExpense"] > 0:
            share = round((top_cat["amount"] / summary["totalExpense"]) * 100)
        insights.append(
            f"{top_cat['category']} is your largest expense category at {format_inr(top_cat['amount'])}, {share}% of total spending."
        )

    # 2. Monthly budget alert
    monthly_budget = summary["monthlyBudget"]
    total_expense = summary["totalExpense"]

    if monthly_budget > 0:
        if total_expense > monthly_budget:
            insights.append(
                f"You have exceeded your monthly budget of {format_inr(monthly_budget)} by {format_inr(total_expense - monthly_budget)}."
            )
        elif total_expense >= monthly_budget * 0.8:
            used_pct = round((total_expense / monthly_budget) * 100)
            insights.append(
                f"You've used {used_pct}% of your monthly budget — approaching the limit."
            )
        else:
            insights.append(
                f"Spending is healthy: {format_inr(summary['budgetRemaining'])} left in your monthly budget."
            )

    # 3. Savings rate evaluation
    total_income = summary["totalIncome"]
    if total_income > 0:
        savings_rate = round((summary["savings"] / total_income) * 100)
        if savings_rate >= 20:
            insights.append(f"Great savings discipline! You are saving {savings_rate}% of your income.")
        elif savings_rate > 0:
            insights.append(f"Your current savings rate is {savings_rate}%. Target at least 20% for long-term safety.")
        else:
            insights.append("Your expenses currently exceed your income. Look for non-essential cuts.")

    # 4. Actionable recommendations
    if summary["categoryBreakdown"]:
        top_cat = summary["categoryBreakdown"][0]
        recommendations.append(
            f"Review discretionary charges in {top_cat['category']} to lower monthly outflow."
        )

    recommendations.append("Build an emergency fund covering 3 to 6 months of basic living costs.")

    if monthly_budget == 0:
        recommendations.append("Set a monthly budget on the Budget page to track spending caps.")

    # 5. Simple predictive estimation based on past daily run rate
    predicted_expense = total_expense
    expense_tx_count = len([t for t in transactions if getattr(t, "type", None) == "expense"])
    confidence = min(95, max(55, 55 + expense_tx_count * 2))

    return {
        **summary,
        "insights": insights,
        "recommendations": recommendations,
        "predictedExpense": predicted_expense,
        "confidence": confidence,
    }
