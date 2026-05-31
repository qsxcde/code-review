import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.core.db import get_db as _orig_get_db
from app.core.redis import get_redis as _orig_get_redis
from app.core.security import require_jwt_user as _orig_require_jwt_user


class AuthEndpointsIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._mock_db = AsyncMock()
        cls._mock_db.commit = AsyncMock()
        cls._mock_db.refresh = AsyncMock()

        async def _refresh_side_effect(user):
            user.id = 1
            user.created_at = datetime.now(timezone.utc)

        cls._mock_db.refresh.side_effect = _refresh_side_effect

        cls._mock_redis = MagicMock()
        cls._mock_redis.setex = AsyncMock()
        cls._mock_redis.exists = AsyncMock(return_value=True)
        cls._mock_redis.delete = AsyncMock()

        from app.main import app

        # Use FastAPI dependency_overrides — works regardless of
        # which test class imported the app first.
        app.dependency_overrides[_orig_get_db] = lambda: cls._mock_db
        app.dependency_overrides[_orig_get_redis] = lambda: cls._mock_redis
        app.dependency_overrides[_orig_require_jwt_user] = lambda: 1

        cls._app = app
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app = cls._app
        app.dependency_overrides.pop(_orig_get_db, None)
        app.dependency_overrides.pop(_orig_get_redis, None)
        app.dependency_overrides.pop(_orig_require_jwt_user, None)

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
            created_at=datetime.now(timezone.utc),
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
        from app.core.jwt import create_refresh_token

        refresh_token = create_refresh_token(1, "test@example.com")
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
