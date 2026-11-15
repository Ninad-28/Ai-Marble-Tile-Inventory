"""Auth register / login tests (uses real DB when DATABASE_URL is set)."""
import os
import sys
import uuid
import unittest

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(BACKEND_ROOT, ".env"))


@unittest.skipUnless(os.getenv("DATABASE_URL"), "DATABASE_URL not configured")
class TestAuthAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        # Avoid heavy model warmup during tests
        os.environ["GATEKEEPER_ENABLED"] = "false"
        os.environ["SEARCH_WARMUP_ON_STARTUP"] = "false"
        from app.main import app
        cls.client = TestClient(app)
        cls.app = app

    def _unique_email(self) -> str:
        return f"test_{uuid.uuid4().hex[:10]}@example.com"

    def test_register_and_login(self):
        email = self._unique_email()
        password = "secret12"
        name = "Test User"

        reg = self.client.post(
            "/api/auth/register",
            json={"name": name, "email": email, "password": password},
        )
        self.assertEqual(reg.status_code, 201, reg.text)
        body = reg.json()
        self.assertIn("access_token", body)
        self.assertEqual(body["admin_email"], email.lower())
        self.assertEqual(body["admin_name"], name)

        # Duplicate register should fail
        dup = self.client.post(
            "/api/auth/register",
            json={"name": name, "email": email, "password": password},
        )
        self.assertEqual(dup.status_code, 400)

        # Login with same credentials
        login = self.client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )
        self.assertEqual(login.status_code, 200, login.text)
        self.assertIn("access_token", login.json())

        # /me with token
        token = login.json()["access_token"]
        me = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["email"], email.lower())

    def test_login_invalid_credentials(self):
        res = self.client.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "wrongpass"},
        )
        self.assertEqual(res.status_code, 401)

    def test_register_short_password_rejected(self):
        res = self.client.post(
            "/api/auth/register",
            json={
                "name": "Short",
                "email": self._unique_email(),
                "password": "123",
            },
        )
        self.assertEqual(res.status_code, 422)


class TestPasswordUtils(unittest.TestCase):
    def test_hash_and_verify(self):
        from app.middleware.auth import hash_password, verify_password

        hashed = hash_password("mypassword")
        self.assertTrue(verify_password("mypassword", hashed))
        self.assertFalse(verify_password("other", hashed))


if __name__ == "__main__":
    unittest.main()
