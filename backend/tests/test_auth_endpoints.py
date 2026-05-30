import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


class AuthEndpointsIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._mock_db = AsyncMock()
        cls._mock_db.commit = AsyncMock()
        cls._mock_db.refresh = AsyncMock()

        async def _refresh_side_effect(user):
            user.id = 1
            user.created_at = datetime.utcnow()

        cls._mock_db.refresh.side_effect = _refresh_side_effect

        cls._mock_redis = MagicMock()
        cls._mock_redis.setex = AsyncMock()
        cls._mock_redis.exists = AsyncMock(return_value=True)
        cls._mock_redis.delete = AsyncMock()

        # Patch at source module level BEFORE the app is imported.
        # FastAPI's Depends() stores the function reference at decorator time,
        # so we must patch the original modules before the auth endpoint module
        # is imported by app.main.
        cls._db_patch = patch(
            "app.core.db.get_db",
            lambda: cls._mock_db,
        )
        cls._db_patch.start()

        cls._redis_patch = patch(
            "app.core.redis.get_redis",
            lambda: cls._mock_redis,
        )
        cls._redis_patch.start()

        cls._jwt_patch = patch(
            "app.core.security.require_jwt_user",
            lambda: 1,
        )
        cls._jwt_patch.start()

        from app.main import app

        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls._jwt_patch.stop()
        cls._db_patch.stop()
        cls._redis_patch.stop()

    def test_register_valid_request_returns_201(self):
        response = self.client.post(
            "/api/v1/auth/register",
            json={"email": "new@example.com", "password": "Abc12345"},
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertIn("access_token", body)
        self.assertIn("refresh_token", body)
        self.assertEqual(body["token_type"], "bearer")
        self.assertEqual(body["user"]["email"], "new@example.com")

    def test_register_short_password_returns_422(self):
        response = self.client.post(
            "/api/v1/auth/register",
            json={"email": "new@example.com", "password": "Ab1"},
        )
        self.assertEqual(response.status_code, 422)

    def test_register_invalid_email_returns_422(self):
        response = self.client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "Abc12345"},
        )
        self.assertEqual(response.status_code, 422)

    def test_login_valid_credentials_returns_200(self):
        import bcrypt
        from app.models.user import User

        password_hash = bcrypt.hashpw(b"Abc12345", bcrypt.gensalt(4)).decode("utf-8")
        mock_user = User(
            id=1,
            email="test@example.com",
            password_hash=password_hash,
            created_at=datetime.utcnow(),
        )

        self._mock_db.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        self._mock_db.execute.return_value = mock_result

        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "Abc12345"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("access_token", body)

    def test_refresh_valid_token_returns_200(self):
        from app.services.auth.jwt import create_refresh_token

        refresh_token = create_refresh_token(1)
        response = self.client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("access_token", body)

    def test_logout_returns_204(self):
        response = self.client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": "eyJ.dummy.token"},
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")


if __name__ == "__main__":
    unittest.main()
