import asyncio
import os
import sys

# Ensure project root is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from sqlalchemy import text
from src.app import create_app
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from src.modules.users.models import User
from src.modules.branches.models import Branch
from src.modules.modules.models import Module
from src.modules.classes.models import Class
from src.modules.groups.models import Group
from src.core.database import sessionmanager
from src.core.security import hash_password, create_access_token

app = create_app()
client = TestClient(app)

async def setup_test_data():
    async with sessionmanager.session() as db:
        # Create user
        admin = await db.scalar(select(User).where(User.email == "admin@test.com"))
        if not admin:
            admin = User(
                first_name="Admin", last_name="Test", email="admin@test.com", phone="123",
                password_hash=hash_password("admin"), role="admin", status="active",
                permissions={"manageEnrollments": True, "manageUsers": True}
            )
            db.add(admin)
            await db.flush()
        
        # Create branch
        branch = await db.scalar(select(Branch).limit(1))
        if not branch:
            branch = Branch(name="Test Branch")
            db.add(branch)
            await db.flush()
            
        # Create module
        mod = await db.scalar(select(Module).limit(1))
        if not mod:
            mod = Module(name="Test Module", category="general")
            db.add(mod)
            await db.flush()
            
        # Create class
        cls = await db.scalar(select(Class).limit(1))
        if not cls:
            cls = Class(name="Test Class", module_id=mod.id, branch_id=branch.id, teacher_id=admin.id)
            db.add(cls)
            await db.flush()
            
        # Create group
        group = await db.scalar(select(Group).limit(1))
        if not group:
            group = Group(
                name="Test Group", class_id=cls.id, teacher_id=admin.id,
                room="Room 1",
                subscription_type="monthly",
                max_students=1, # Set to 1 to easily test waitlist!
                price=100.0,
                status="active"
            )
            db.add(group)
            
        await db.commit()
        return admin.id, group.id

def run_tests():
    print("--- Starting Sprint 5 Enrollment Tests ---")

    loop = asyncio.get_event_loop()
    admin_id, group_id = loop.run_until_complete(setup_test_data())

    # 1. Setup Admin Token
    admin_token = create_access_token({"sub": str(admin_id)}) 
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    print(f"Testing with Group ID: {group_id} (Max Students: 1)")
    
    # 2. Test Visitor Reservation
    print("\n[TEST] Submitting visitor reservation...")
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
    res = client.post("/api/visitor-reservations", json=visitor_payload)
    if res.status_code == 201:
        req_data = res.json()["data"]
        print("✅ Visitor reservation created successfully!")
        print("   Status:", req_data["status"], "ID:", req_data["id"])
    else:
        print("❌ Failed to create visitor reservation:", res.json())
        return
        
    request_id = req_data["id"]
    
    # 2.5 Test Waitlist Capacity
    print("\n[TEST] Submitting second visitor (should waitlist)...")
    visitor_payload["contactEmail"] = "visitor2@test.com"
    res2 = client.post("/api/visitor-reservations", json=visitor_payload)
    if res2.status_code == 201:
        req_data2 = res2.json()["data"]
        print("✅ Second visitor handled.")
        if req_data2["status"] == "waitlisted":
            print("   ✅ CORRECTLY Waitlisted due to capacity!")
        else:
            print("   ❌ Expected waitlisted, got:", req_data2["status"])
    else:
        print("❌ Failed to create second visitor:", res2.json())
        
    request_id_2 = req_data2["id"]
    
    # 3. Test Admin Listing Visitor Requests
    print("\n[TEST] Listing visitor requests (Admin)...")
    res = client.get("/api/enrollments/visitors?status=pending", headers=admin_headers)
    if res.status_code == 200:
        print("✅ Admin can list visitor requests.")
    else:
        print("❌ Admin listing failed:", res.json())
        
    # 4. Test Convert Visitor to Student
    print("\n[TEST] Converting visitor to student...")
    convert_payload = {
        "parentAction": "none",
        "student": {
            "firstName": "Test",
            "lastName": "Visitor",
            "gender": "male",
            "dateOfBirth": "2010-01-01"
        }
    }
    res = client.post(f"/api/enrollments/visitors/{request_id}/convert", json=convert_payload, headers=admin_headers)
    if res.status_code == 200:
        print("✅ Visitor converted successfully!")
        enrollment = res.json()["data"]["enrollment"]
        print("   New Student ID:", res.json()["data"]["student"]["id"])
        print("   Enrollment Status:", enrollment["status"])
        enrollment_id = enrollment["id"]
    else:
        print("❌ Conversion failed:", res.json())

    # 4.5 Test Admin Cancellation and Waitlist Promotion
    print(f"\n[TEST] Cancelling active enrollment ID {enrollment_id} to trigger promotion...")
    cancel_payload = {"reason": "Testing promotion"}
    res = client.post(f"/api/enrollments/{enrollment_id}/cancel", json=cancel_payload, headers=admin_headers)
    if res.status_code == 200:
        print("✅ Cancelled successfully!")
        
        print("   Checking if second visitor (waitlisted) was promoted...")
        res_list = client.get(f"/api/enrollments/visitors?status=pending", headers=admin_headers)
        requests = res_list.json()["data"]["items"]
        promoted = any(r["id"] == request_id_2 for r in requests)
        if promoted:
            print("   ✅ Visitor 2 successfully auto-promoted to pending!")
        else:
            print("   ❌ Visitor 2 was NOT promoted.")
    else:
        print("❌ Cancellation failed:", res.json())

    # 5. Test Group Stats Update
    print("\n[TEST] Checking Group Stats Update...")
    res = client.get(f"/api/groups/{group_id}", headers=admin_headers)
    if res.status_code == 200:
        group_info = res.json()["data"]
        print(f"✅ Group activeEnrollments: {group_info.get('activeEnrollments')}")
        print(f"   Group availableSeats: {group_info.get('availableSeats')}")
    else:
        print("❌ Failed to get group details:", res.json())
        
    print("\n--- All tests completed! ---")

if __name__ == "__main__":
    run_tests()
