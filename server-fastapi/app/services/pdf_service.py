import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from app.services.finance_analyzer import format_inr


def generate_monthly_pdf(report: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=14
    )
    section_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=12,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#334155")
    )

    elements = []

    # Title & Period
    elements.append(Paragraph("Finance Report", title_style))
    elements.append(Paragraph(report.get("period", ""), subtitle_style))
    elements.append(Spacer(1, 8))

    # Summary Section
    elements.append(Paragraph("Summary", section_style))
    summary_data = [
        ["Total Income", format_inr(report.get("totalIncome", 0))],
        ["Total Expense", format_inr(report.get("totalExpense", 0))],
        ["Savings", format_inr(report.get("savings", 0))],
        ["Budget Remaining", format_inr(report.get("budgetRemaining", 0))]
    ]
    summary_table = Table(summary_data, colWidths=[200, 200])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1e293b")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 12))

    # Category Breakdown Section
    elements.append(Paragraph("Category Breakdown", section_style))
    categories = report.get("categoryBreakdown", [])
    if categories:
        cat_data = [["Category", "Amount"]]
        for item in categories:
            cat_data.append([item.get("category", ""), format_inr(item.get("amount", 0))])
        cat_table = Table(cat_data, colWidths=[200, 200])
        cat_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ]))
        elements.append(cat_table)
    else:
        elements.append(Paragraph("No expenses recorded this period.", body_style))
    elements.append(Spacer(1, 12))

    # Transactions List
    elements.append(Paragraph("Transactions", section_style))
    transactions = report.get("transactions", [])
    if transactions:
        tx_data = [["Date", "Title", "Category", "Amount"]]
        max_items = 35
        for t in transactions[:max_items]:
            t_date = t.get("transactionDate")
            if isinstance(t_date, str):
                try:
                    dt = datetime.fromisoformat(t_date.replace("Z", "+00:00"))
                    date_str = dt.strftime("%d/%m/%Y")
                except Exception:
                    date_str = t_date[:10]
            elif isinstance(t_date, datetime):
                date_str = t_date.strftime("%d/%m/%Y")
            else:
                date_str = "-"

            sign = "+" if t.get("type") == "income" else "-"
            amt_str = f"{sign}{format_inr(t.get('amount', 0))}"
            tx_data.append([
                date_str,
                t.get("title", "")[:28],
                t.get("category", "")[:18],
                amt_str
            ])

        tx_table = Table(tx_data, colWidths=[75, 175, 120, 100])
        tx_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ]))
        elements.append(tx_table)

        if len(transactions) > max_items:
            extra = len(transactions) - max_items
            elements.append(Spacer(1, 4))
            elements.append(Paragraph(f"<i>...and {extra} more transactions (view full list in dashboard)</i>", body_style))
    else:
        elements.append(Paragraph("No transactions recorded this period.", body_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
