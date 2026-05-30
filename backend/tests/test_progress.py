import unittest
from unittest.mock import AsyncMock, MagicMock


class ProgressPublishTests(unittest.IsolatedAsyncioTestCase):
    async def test_publish_progress_calls_redis_publish(self):
        from app.services.review.progress import publish_progress

        mock_redis = MagicMock()
        mock_redis.publish = AsyncMock()

        await publish_progress(mock_redis, 1, "agent_done", agent="[安全]", risks=3, high=1, percent=40)

        mock_redis.publish.assert_called_once()
        args = mock_redis.publish.call_args[0]
        self.assertEqual(args[0], "progress:1")
        self.assertIn("agent_done", args[1])

    async def test_publish_progress_survives_redis_error(self):
        from app.services.review.progress import publish_progress

        mock_redis = MagicMock()
        mock_redis.publish = AsyncMock(side_effect=Exception("boom"))

        await publish_progress(mock_redis, 1, "phase_start", phase="phase1", message="ok", percent=5)


if __name__ == "__main__":
    unittest.main()
