import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


class ReviewHistoryAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._mock_db = AsyncMock()
        cls._mock_db.commit = AsyncMock()
        cls._mock_db.add = MagicMock()

        # ------------------------------------------------------------------
        # Patch "source" dependencies BEFORE any endpoint module is imported.
        # Patching inside the endpoint modules is too late: the
        # patch.start() call itself triggers the import, which causes
        # Depends(...) in the function signatures to capture the real
        # (unpatched) function reference.
        # ------------------------------------------------------------------
        cls._jwt_patch = patch(
            "app.core.security.require_jwt_user", lambda: 1
        )
        cls._jwt_patch.start()

        cls._rate_patch = patch(
            "app.core.rate_limit.require_rate_limit", lambda: None
        )
        cls._rate_patch.start()

        # Prevent startup from trying to connect to a real Redis server.
        cls._redis_patch = patch(
            "app.core.redis.get_redis", AsyncMock(return_value=MagicMock())
        )
        cls._redis_patch.start()

        # Patch get_db at its source so that Depends(get_db) in endpoint
        # signatures picks up the mock session provider.
        cls._get_db_patch = patch(
            "app.core.db.get_db", lambda: cls._mock_db
        )
        cls._get_db_patch.start()

        cls._history_patch = patch(
            "app.api.v1.endpoints.review.find_cached_record",
            AsyncMock(return_value=None),
        )
        cls._history_patch.start()

        cls._create_patch = patch(
            "app.api.v1.endpoints.review.create_pending_record",
            AsyncMock(return_value=1),
        )
        cls._create_patch.start()

        cls._save_patch = patch(
            "app.api.v1.endpoints.review.save_completed_record",
            AsyncMock(),
        )
        cls._save_patch.start()

        cls._save_failed_patch = patch(
            "app.api.v1.endpoints.review.save_failed_record",
            AsyncMock(),
        )
        cls._save_failed_patch.start()

        from app.main import app

        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls._jwt_patch.stop()
        cls._rate_patch.stop()
        cls._redis_patch.stop()
        cls._get_db_patch.stop()
        cls._history_patch.stop()
        cls._create_patch.stop()
        cls._save_patch.stop()
        cls._save_failed_patch.stop()

    def setUp(self):
        self._mock_db.execute = AsyncMock()
        self._mock_db.refresh = AsyncMock()
        self._mock_db.commit = AsyncMock()
        self._mock_db.delete = AsyncMock()

    def test_list_records_returns_200(self):
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_result.scalars.return_value.all.return_value = []
        self._mock_db.execute = AsyncMock(return_value=mock_result)

        response = self.client.get("/api/v1/review/records")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("items", body)
        self.assertIn("total", body)
        self.assertEqual(body["total"], 0)

    def test_list_records_with_filters(self):
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_result.scalars.return_value.all.return_value = []
        self._mock_db.execute = AsyncMock(return_value=mock_result)

        response = self.client.get(
            "/api/v1/review/records?status=completed&owner=microsoft&repo=vscode"
        )
        self.assertEqual(response.status_code, 200)

    def test_list_records_page_size_capped(self):
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_result.scalars.return_value.all.return_value = []
        self._mock_db.execute = AsyncMock(return_value=mock_result)

        response = self.client.get("/api/v1/review/records?page=1&page_size=500")
        self.assertEqual(response.status_code, 200)

    def test_get_record_not_found_returns_404(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self._mock_db.execute = AsyncMock(return_value=mock_result)

        response = self.client.get("/api/v1/review/records/999")
        self.assertEqual(response.status_code, 404)

    def test_delete_record_not_found_returns_404(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self._mock_db.execute = AsyncMock(return_value=mock_result)

        response = self.client.delete("/api/v1/review/records/999")
        self.assertEqual(response.status_code, 404)

    def test_submit_feedback_returns_201(self):
        from app.models.feedback import Feedback

        record_mock = MagicMock()
        record_mock.scalar_one_or_none.return_value = MagicMock()

        feedback_obj = Feedback(
            id=1, record_id=1, risk_index=0,
            rating="helpful", comment="good",
            created_at=datetime.now(timezone.utc),
        )

        self._mock_db.execute = AsyncMock(return_value=record_mock)
        self._mock_db.refresh = AsyncMock(
            side_effect=lambda obj: (
                setattr(obj, "id", 1),
                setattr(obj, "created_at", datetime.now(timezone.utc)),
            )
        )

        response = self.client.post(
            "/api/v1/review/records/1/feedback",
            json={"risk_index": 0, "rating": "helpful", "comment": "good"},
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["risk_index"], 0)
        self.assertEqual(body["rating"], "helpful")

    def test_submit_feedback_record_not_found_returns_404(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self._mock_db.execute = AsyncMock(return_value=mock_result)

        response = self.client.post(
            "/api/v1/review/records/999/feedback",
            json={"risk_index": 0, "rating": "helpful"},
        )
        self.assertEqual(response.status_code, 404)

    def test_submit_feedback_invalid_rating_returns_422(self):
        response = self.client.post(
            "/api/v1/review/records/1/feedback",
            json={"risk_index": 0, "rating": "invalid_rating"},
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
