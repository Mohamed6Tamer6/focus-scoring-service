import unittest
from fastapi.testclient import TestClient
from main import app
from app.database import SessionLocal, Base, engine
from app.models.user import User
from app.models.rbac import Role, UserRole
from app.repositories import create_user
from app.schemas.user import UserCreate
import uuid

class TestFocusAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        
    def tearDown(self):
        self.db.close()

    def test_registration_defaults_to_user(self):
        email = f"test_{uuid.uuid4()}@example.com"
        response = self.client.post("/auth/register", json={
            "name": "Test User",
            "email": email,
            "password": "password123"
        })
        self.assertEqual(response.status_code, 201)
        user_id = response.json()["id"]
        
        # Verify role in DB
        db_user = self.db.query(User).filter(User.id == user_id).first()
        roles = [ur.role.name for ur in db_user.user_roles]
        self.assertIn("user", roles)
        self.assertNotIn("admin", roles)

    def test_user_cannot_download_pdf(self):
        # 1. Login to get token
        email = "test_user_download@example.com"
        # Create user if it doesn't exist
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            from app.services.auth import register_user
            user = register_user(self.db, UserCreate(name="U", email=email, password="p"))
            
        response = self.client.post("/auth/login", json={"email": email, "password": "p"})
        token = response.json()["access_token"]
        
        # 2. Try to download a PDF (session ID doesn't matter much for 403)
        session_id = str(uuid.uuid4())
        response = self.client.get(f"/focus/sessions/{session_id}/pdf", headers={"Authorization": f"Bearer {token}"})
        # Note: If PDF route is limited by get_current_admin dependency
        self.assertEqual(response.status_code, 403)

    def test_login_success(self):
        email = f"login_test_{uuid.uuid4()}@example.com"
        # 1. Register
        self.client.post("/auth/register", json={
            "name": "Login User",
            "email": email,
            "password": "password123",
            "role": "user"
        })
        
        # 2. Login
        response = self.client.post("/auth/login", json={
            "email": email,
            "password": "password123"
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.json())

if __name__ == "__main__":
    unittest.main()
