import asyncio
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# To setup data we need the DB directly, but we can do that in a separate sync wrapper.
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.core.database import sessionmanager
from src.modules.users.models import User
from src.modules.branches.models import Branch
from src.modules.modules.models import Module
from src.modules.classes.models import Class
from src.modules.groups.models import Group
from src.core.security import hash_password, create_access_token

BASE_URL = "http://127.0.0.1:8000"

async def setup_test_data():
    async with sessionmanager.session() as db:
        admin = await db.scalar(select(User).where(User.email == "admin@test.com"))
        if not admin:
            admin = User(
                first_name="Admin", last_name="Test", email="admin@test.com", phone="123",
                password_hash=hash_password("admin"), role="admin", status="active",
                permissions={"manageEnrollments": True, "manageUsers": True}
            )
            db.add(admin)
            await db.flush()
        
        branch = await db.scalar(select(Branch).limit(1))
        if not branch:
            branch = Branch(name="Test Branch")
            db.add(branch)
            await db.flush()
            
        mod = await db.scalar(select(Module).limit(1))
        if not mod:
            mod = Module(name="Test Module", category="general")
            db.add(mod)
            await db.flush()
            
        cls = await db.scalar(select(Class).limit(1))
        if not cls:
            cls = Class(name="Test Class", module_id=mod.id, branch_id=branch.id, teacher_id=admin.id)
            db.add(cls)
            await db.flush()
            
        group = await db.scalar(select(Group).limit(1))
        if not group:
            group = Group(
                name="Test Group", class_id=cls.id, teacher_id=admin.id,
                room="Room 1", subscription_type="monthly", max_students=1, price=100.0, status="active"
            )
            db.add(group)
            
        await db.commit()
        return admin.id, group.id

def test_api():
    loop = asyncio.get_event_loop()
    admin_id, group_id = loop.run_until_complete(setup_test_data())
    
    admin_token = create_access_token({"sub": str(admin_id)}) 
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    client = httpx.Client(base_url=BASE_URL, timeout=30.0)
    
    print("--- Starting Sprint 5 Enrollment Tests (HTTP) ---")
    print(f"Using Group ID: {group_id}")
    
    # 1. Test Visitor Reservation
    print("\n[TEST] Submitting visitor reservation 1...")
    visitor_payload = {
        "groupId": group_id,
        "firstName": "Test",
        "lastName": "Visitor",
        "dateOfBirth": "2010-01-01",
        "gender": "male",
        "contactPhone": "1234567890",
        "contactEmail": "visitor@test.com",
        "guardianName": "Test Guardian",
        "guardianPhone": "0987654321",
        "notes": "Testing reservation"
    }
    res = client.post("/api/visitor-enrollments", json=visitor_payload)
    if res.status_code == 201:
        req_data = res.json()["data"]
        print("✅ Visitor 1 created:", req_data["status"], "ID:", req_data["visitorRequestId"])
        request_id_1 = req_data["visitorRequestId"]
    else:
        print("❌ Failed:", res.text)
        return

    # 2. Test Waitlist Capacity
    print("\n[TEST] Submitting visitor reservation 2 (waitlist)...")
    visitor_payload["contactEmail"] = "visitor2@test.com"
    res2 = client.post("/api/visitor-enrollments", json=visitor_payload)
    if res2.status_code == 201:
        req_data2 = res2.json()["data"]
        print("✅ Visitor 2 created:", req_data2["status"], "ID:", req_data2["visitorRequestId"])
        if req_data2["status"] == "waitlisted":
            print("   ✅ CORRECTLY Waitlisted due to capacity!")
        else:
            print("   ❌ Expected waitlisted, got:", req_data2["status"])
        request_id_2 = req_data2["visitorRequestId"]
    else:
        print("❌ Failed:", res2.text)

    # 3. Test Admin Listing Visitor Requests
    print("\n[TEST] Admin Listing pending visitors...")
    res = client.get("/api/visitor-enrollments?status=pending", headers=admin_headers)
    if res.status_code == 200:
        print("✅ Success! Returned items:", len(res.json()["data"]["items"]))
    else:
        print("❌ Failed:", res.text)

    # 4. Test Conversion
    print(f"\n[TEST] Converting visitor {request_id_1} to student...")
    convert_payload = {
        "parentAction": "none",
        "student": {
            "firstName": "Test",
            "lastName": "Visitor",
            "gender": "male",
            "dateOfBirth": "2010-01-01"
        }
    }
    res = client.post(f"/api/visitor-enrollments/{request_id_1}/convert", json=convert_payload, headers=admin_headers)
    if res.status_code == 200:
        data = res.json()["data"]
        print("✅ Converted successfully! Student ID:", data["student"]["id"])
        enrollment_id = data["enrollment"]["id"]
    else:
        print("❌ Failed:", res.text)
        return

    # 5. Test Cancellation & Auto-Promotion
    print(f"\n[TEST] Cancelling enrollment {enrollment_id} to trigger waitlist promotion...")
    cancel_payload = {"reason": "Test Promotion"}
    res = client.post(f"/api/enrollments/{enrollment_id}/cancel", json=cancel_payload, headers=admin_headers)
    if res.status_code == 200:
        print("✅ Cancelled successfully!")
        
        # Check if visitor 2 is now pending
        res_list = client.get(f"/api/visitor-enrollments?status=pending", headers=admin_headers)
        items = res_list.json()["data"]["items"]
        if any(r["id"] == request_id_2 for r in items):
            print(f"   ✅ Visitor {request_id_2} was automatically promoted to pending!")
        else:
            print(f"   ❌ Visitor {request_id_2} was NOT promoted.")
    else:
        print("❌ Failed:", res.text)
        
    print("\n--- Testing Completed ---")

if __name__ == "__main__":
    test_api()
