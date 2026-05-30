import time
import unittest
from unittest.mock import patch

from app.core.config import Settings
from app.services.auth.jwt import (
    ACCESS_TYPE,
    REFRESH_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
    extract_jti_payload,
)


class JWTTokenCreationTests(unittest.TestCase):
    def setUp(self):
        self._settings_patch = patch(
            "app.services.auth.jwt.settings",
            Settings(
                JWT_SECRET="test-secret-key-that-is-at-least-32-chars!!",
                JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15,
                JWT_REFRESH_TOKEN_EXPIRE_DAYS=30,
            ),
        )
        self._settings_patch.start()

    def tearDown(self):
        self._settings_patch.stop()

    def test_access_token_contains_expected_payload(self):
        token = create_access_token(42, "user@example.com")
        payload = decode_token(token, ACCESS_TYPE)

        self.assertEqual(payload["sub"], "42")
        self.assertEqual(payload["email"], "user@example.com")
        self.assertEqual(payload["type"], ACCESS_TYPE)
        self.assertIn("jti", payload)
        self.assertIn("iat", payload)
        self.assertIn("exp", payload)

    def test_refresh_token_contains_expected_payload(self):
        token = create_refresh_token(42)
        payload = decode_token(token, REFRESH_TYPE)

        self.assertEqual(payload["sub"], "42")
        self.assertEqual(payload["type"], REFRESH_TYPE)

    def test_decode_rejects_wrong_type(self):
        token = create_access_token(1, "a@b.com")
        from jwt import InvalidTokenError

        with self.assertRaises(InvalidTokenError):
            decode_token(token, REFRESH_TYPE)

    def test_decode_rejects_tampered_token(self):
        token = create_access_token(1, "a@b.com")
        tampered = token[:-5] + ("A" if token[-5] != "A" else "B") + token[-4:]
        from jwt import InvalidTokenError

        with self.assertRaises(InvalidTokenError):
            decode_token(tampered, ACCESS_TYPE)

    def test_extract_jti_payload_bypasses_expiry(self):
        token = create_access_token(1, "a@b.com")
        jti, payload = extract_jti_payload(token)

        self.assertIsNotNone(jti)
        self.assertEqual(payload["sub"], "1")

    def test_access_token_expires_in_15_minutes(self):
        token = create_access_token(1, "a@b.com")
        payload = decode_token(token, ACCESS_TYPE)

        lifetime = payload["exp"] - payload["iat"]
        self.assertEqual(lifetime, 900)  # 15 * 60


if __name__ == "__main__":
    unittest.main()
