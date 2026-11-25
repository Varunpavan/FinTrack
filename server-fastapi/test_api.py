import asyncio
import httpx
from datetime import datetime, timezone

BASE_URL = "http://127.0.0.1:5055/api"

async def run_tests():
    from app.main import app
    transport = httpx.ASGITransport(app=app)
    
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver/api") as client:
        print("\n--- 1. Testing Health Check ---")
        health = await client.get("http://testserver/health")
        assert health.status_code == 200, f"Health check failed: {health.text}"
        print(" Health OK:", health.json())

        test_email = f"test_{int(datetime.now().timestamp())}@example.com"
        print(f"\n--- 2. Testing Signup with {test_email} ---")
        signup_res = await client.post("/auth/signup", json={
            "name": "Varun Test",
            "email": test_email,
            "password": "password123"
        })
        assert signup_res.status_code == 201, f"Signup failed: {signup_res.text}"
        auth_data = signup_res.json()
        token = auth_data["token"]
        user = auth_data["user"]
        print(" Signup OK: User ID =", user["id"])

        headers = {"Authorization": f"Bearer {token}"}

        print("\n--- 3. Testing Get Me ---")
        me_res = await client.get("/auth/me", headers=headers)
        assert me_res.status_code == 200, f"Get me failed: {me_res.text}"
        print(" Get Me OK:", me_res.json()["user"]["email"])

        print("\n--- 4. Testing Budget Creation ---")
        budget_res = await client.post("/budget", headers=headers, json={
            "monthlyBudget": 50000,
            "categoryBudgets": [
                {"category": "Food", "limit": 15000},
                {"category": "Rent", "limit": 20000}
            ]
        })
        assert budget_res.status_code == 200, f"Set budget failed: {budget_res.text}"
        print(" Budget Set OK: Monthly Budget =", budget_res.json()["data"]["monthlyBudget"])

        print("\n--- 5. Testing Create Transactions ---")
        tx1 = await client.post("/transactions", headers=headers, json={
            "type": "income",
            "title": "Monthly Salary",
            "amount": 75000,
            "category": "Salary",
            "paymentMethod": "bank_transfer"
        })
        assert tx1.status_code == 201, f"Create income failed: {tx1.text}"

        tx2 = await client.post("/transactions", headers=headers, json={
            "type": "expense",
            "title": "Grocery Shopping",
            "amount": 4500,
            "category": "Food",
            "paymentMethod": "upi"
        })
        assert tx2.status_code == 201, f"Create expense failed: {tx2.text}"

        tx3 = await client.post("/transactions", headers=headers, json={
            "type": "expense",
            "title": "House Rent",
            "amount": 18000,
            "category": "Rent",
            "paymentMethod": "bank_transfer"
        })
        assert tx3.status_code == 201, f"Create expense failed: {tx3.text}"
        print(" Transactions Created OK (1 income, 2 expenses)")

        print("\n--- 6. Testing List Transactions ---")
        tx_list = await client.get("/transactions?page=1&limit=10", headers=headers)
        assert tx_list.status_code == 200, f"List transactions failed: {tx_list.text}"
        tx_data = tx_list.json()
        assert tx_data["pagination"]["total"] == 3
        print(f" List OK: Found {tx_data['pagination']['total']} transactions")

        print("\n--- 7. Testing Dashboard Summary ---")
        dash_res = await client.get("/dashboard/summary", headers=headers)
        assert dash_res.status_code == 200, f"Dashboard summary failed: {dash_res.text}"
        dash = dash_res.json()["data"]
        print(f" Dashboard OK: Income = ₹{dash['totalIncome']}, Expense = ₹{dash['totalExpense']}, Savings = ₹{dash['savings']}")
        assert dash["totalIncome"] == 75000
        assert dash["totalExpense"] == 22500
        assert dash["savings"] == 52500

        print("\n--- 8. Testing AI Insights ---")
        ai_res = await client.post("/ai/insights", headers=headers)
        assert ai_res.status_code == 200, f"AI insights failed: {ai_res.text}"
        insights = ai_res.json()["insights"]
        print(f" AI Insights OK ({len(insights)} insights generated):")
        for i, ins in enumerate(insights[:2], 1):
            print(f"   {i}. {ins}")

        print("\n--- 9. Testing Monthly Report & PDF Export ---")
        report_json = await client.get("/reports/monthly", headers=headers)
        assert report_json.status_code == 200, f"Report JSON failed: {report_json.text}"
        print(" Report JSON OK: Period =", report_json.json()["data"]["period"])

        report_pdf = await client.get("/reports/monthly?format=pdf", headers=headers)
        assert report_pdf.status_code == 200, f"Report PDF failed: {report_pdf.text}"
        assert report_pdf.headers["content-type"] == "application/pdf"
        print(f" Report PDF OK: Received {len(report_pdf.content)} bytes of PDF")

        print("\n--- 10. Testing Account Deletion (Cascading) ---")
        del_res = await client.delete("/auth/account", headers=headers)
        assert del_res.status_code == 200, f"Account deletion failed: {del_res.text}"
        print(" Account Deletion OK:", del_res.json()["message"])

        # Verify login now fails
        login_again = await client.post("/auth/login", json={"email": test_email, "password": "password123"})
        assert login_again.status_code == 401
        print(" Verification OK: Account deleted cleanly and cannot log in.")

        print("\n ALL BACKEND TESTS PASSED SUCCESSFULLY! ")

if __name__ == "__main__":
    asyncio.run(run_tests())
