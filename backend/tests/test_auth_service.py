import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.auth import AuthResponse


class AuthServiceRegisterTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._settings_patch = patch(
            "app.services.auth.jwt.settings",
            MagicMock(
                jwt_secret="test-secret-key-that-is-at-least-32-chars!!",
                jwt_access_token_expire_minutes=15,
                jwt_refresh_token_expire_days=30,
            ),
        )
        self._settings_patch.start()

    def tearDown(self):
        self._settings_patch.stop()

    async def test_register_creates_user_and_returns_tokens(self):
        from datetime import datetime, timezone

        from app.services.auth.service import register

        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_redis = MagicMock()
        mock_redis.setex = AsyncMock()

        def _fake_refresh(user):
            user.id = 1
            user.created_at = datetime.now(timezone.utc)

        mock_db.refresh.side_effect = _fake_refresh

        result = await register(mock_db, mock_redis, "test@example.com", "Abc12345")

        self.assertIsInstance(result, AuthResponse)
        self.assertEqual(result.user.email, "test@example.com")
        self.assertTrue(len(result.access_token) > 0)
        self.assertTrue(len(result.refresh_token) > 0)

    async def test_register_rejects_weak_password_no_digit(self):
        from app.services.auth.service import register
        from fastapi import HTTPException

        mock_db = AsyncMock()
        mock_redis = MagicMock()

        with self.assertRaises(HTTPException) as ctx:
            await register(mock_db, mock_redis, "test@example.com", "abcdefgh")
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_register_rejects_weak_password_no_letter(self):
        from app.services.auth.service import register
        from fastapi import HTTPException

        mock_db = AsyncMock()
        mock_redis = MagicMock()

        with self.assertRaises(HTTPException) as ctx:
            await register(mock_db, mock_redis, "test@example.com", "12345678")
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_login_with_valid_credentials_returns_tokens(self):
        import bcrypt
        from datetime import datetime, timezone

        from app.models.user import User
        from app.services.auth.service import login

        password_hash = bcrypt.hashpw(b"Abc12345", bcrypt.gensalt(4)).decode("utf-8")
        mock_user = User(
            id=1, email="test@example.com", password_hash=password_hash,
            created_at=datetime.now(timezone.utc),
        )

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        mock_redis = MagicMock()
        mock_redis.setex = AsyncMock()

        result = await login(mock_db, mock_redis, "test@example.com", "Abc12345")
        self.assertIsInstance(result, AuthResponse)

    async def test_login_wrong_password_raises_401(self):
        import bcrypt
        from app.models.user import User
        from app.services.auth.service import login
        from fastapi import HTTPException

        password_hash = bcrypt.hashpw(b"Abc12345", bcrypt.gensalt(4)).decode("utf-8")
        mock_user = User(
            id=1, email="test@example.com", password_hash=password_hash
        )

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        mock_redis = MagicMock()

        with self.assertRaises(HTTPException) as ctx:
            await login(mock_db, mock_redis, "test@example.com", "WrongPassword1")
        self.assertEqual(ctx.exception.status_code, 401)

    async def test_login_unknown_email_raises_401(self):
        from app.services.auth.service import login
        from fastapi import HTTPException

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        mock_redis = MagicMock()

        with self.assertRaises(HTTPException) as ctx:
            await login(mock_db, mock_redis, "nobody@example.com", "Abc12345")
        self.assertEqual(ctx.exception.status_code, 401)

    async def test_rotate_tokens_revokes_old_and_issues_new(self):
        from app.services.auth.jwt import (
            ACCESS_TYPE,
            REFRESH_TYPE,
            create_refresh_token,
            decode_token,
        )
        from app.services.auth.service import rotate_tokens

        old_refresh = create_refresh_token(42)
        mock_redis = MagicMock()
        mock_redis.exists = AsyncMock(return_value=True)
        mock_redis.delete = AsyncMock()
        mock_redis.setex = AsyncMock()

        result = await rotate_tokens(mock_redis, old_refresh)

        self.assertIsInstance(result, AuthResponse)
        self.assertEqual(result.user.id, 42)
        mock_redis.delete.assert_called_once()
        mock_redis.setex.assert_called_once()

    async def test_rotate_tokens_revoked_token_raises_401(self):
        from app.services.auth.jwt import create_refresh_token
        from app.services.auth.service import rotate_tokens
        from fastapi import HTTPException

        old_refresh = create_refresh_token(42)
        mock_redis = MagicMock()
        mock_redis.exists = AsyncMock(return_value=False)

        with self.assertRaises(HTTPException) as ctx:
            await rotate_tokens(mock_redis, old_refresh)
        self.assertEqual(ctx.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
