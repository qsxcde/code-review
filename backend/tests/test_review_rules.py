"""Tests for review rule CRUD service."""

import asyncio
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException

from app.schemas.review_rule import (
    ReviewRuleCreate,
    ReviewRuleUpdate,
    RuleFileFilters,
)
from app.services.review.rule_service import (
    create_rule,
    delete_rule,
    get_enabled_rules,
    get_rule,
    list_rules,
    update_rule,
    _to_out,
)

NOW = datetime.now(timezone.utc)


def _make_orm_rule(**overrides) -> MagicMock:
    r = MagicMock()
    r.id = overrides.get("id", 1)
    r.user_id = overrides.get("user_id", 1)
    r.name = overrides.get("name", "Test Rule")
    r.description = overrides.get("description", "A test rule")
    r.category = overrides.get("category", "security")
    r.prompt_content = overrides.get("prompt_content", "Check for issues.")
    r.file_filters = overrides.get("file_filters", None)
    r.is_enabled = overrides.get("is_enabled", True)
    r.priority = overrides.get("priority", 5)
    r.created_at = overrides.get("created_at", NOW)
    r.updated_at = overrides.get("updated_at", NOW)
    return r


def _r(*, scalar=None, scalars_all=None):
    """Build a Result mock supporting .scalar() / .scalar_one_or_none() / .scalars().all()."""
    m = MagicMock()
    if scalar is not None:
        m.scalar.return_value = scalar
        m.scalar_one_or_none.return_value = scalar
    if scalars_all is not None:
        m.scalars.return_value.all.return_value = scalars_all
    return m


def _exec_returns(results):
    """Return an AsyncMock whose side_effect yields coroutines returning the next result."""
    if not isinstance(results, list):
        results = [results]
    async def _side_effect(*args, **kwargs):
        return results.pop(0)
    return AsyncMock(side_effect=_side_effect)


class ToOutTests(unittest.TestCase):
    def test_converts(self) -> None:
        r = _make_orm_rule(id=7, name="Check Auth")
        out = _to_out(r)
        self.assertEqual(out.id, 7)
        self.assertEqual(out.name, "Check Auth")


class CreateRuleTests(unittest.TestCase):
    def test_creates_and_returns(self) -> None:
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=lambda r: (
            setattr(r, "id", 99),
            setattr(r, "is_enabled", True),
            setattr(r, "created_at", NOW),
            setattr(r, "updated_at", NOW),
        ))

        payload = ReviewRuleCreate(name="SQL Check", category="security",
                                   prompt_content="Use params.", priority=10)
        result = asyncio.run(create_rule(db, 1, payload))
        self.assertEqual(result.name, "SQL Check")

    def test_file_filters_serialized_to_dict(self) -> None:
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=lambda r: (
            setattr(r, "id", 1),
            setattr(r, "is_enabled", True),
            setattr(r, "created_at", NOW),
            setattr(r, "updated_at", NOW),
        ))

        payload = ReviewRuleCreate(name="X", category="custom", prompt_content="Y")
        payload.file_filters = RuleFileFilters(include=["*.ts"], exclude=["dist/"])
        asyncio.run(create_rule(db, 1, payload))
        self.assertEqual(db.add.call_args[0][0].file_filters,
                         {"include": ["*.ts"], "exclude": ["dist/"]})


class ListRulesTests(unittest.TestCase):
    def test_empty(self) -> None:
        results = [_r(scalar=0), _r(scalars_all=[])]
        db = AsyncMock()
        db.execute = _exec_returns(results)
        res = asyncio.run(list_rules(db, user_id=1))
        self.assertEqual(res.total, 0)

    def test_with_items(self) -> None:
        rules = [_make_orm_rule(id=i) for i in range(3)]
        results = [_r(scalar=3), _r(scalars_all=rules)]
        db = AsyncMock()
        db.execute = _exec_returns(results)
        res = asyncio.run(list_rules(db, user_id=1))
        self.assertEqual(res.total, 3)
        self.assertEqual(len(res.items), 3)


class GetRuleTests(unittest.TestCase):
    def test_found(self) -> None:
        db = AsyncMock()
        db.execute = _exec_returns(_r(scalar=_make_orm_rule(id=5)))
        res = asyncio.run(get_rule(db, 5, 1))
        self.assertEqual(res.id, 5)

    def test_not_found(self) -> None:
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        db = AsyncMock()
        db.execute = AsyncMock(return_value=result)
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(get_rule(db, 999, 1))
        self.assertEqual(ctx.exception.status_code, 404)


class UpdateRuleTests(unittest.TestCase):
    def test_updates_name(self) -> None:
        rule = _make_orm_rule(name="Old")
        db = AsyncMock()
        db.execute = _exec_returns(_r(scalar=rule))
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        asyncio.run(update_rule(db, 1, 1, ReviewRuleUpdate(name="New")))
        self.assertEqual(rule.name, "New")

    def test_partial_preserves_unchanged(self) -> None:
        rule = _make_orm_rule(name="Keep", priority=3)
        db = AsyncMock()
        db.execute = _exec_returns(_r(scalar=rule))
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        asyncio.run(update_rule(db, 1, 1, ReviewRuleUpdate(priority=99)))
        self.assertEqual(rule.priority, 99)
        self.assertEqual(rule.name, "Keep")

    def test_not_found(self) -> None:
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        db = AsyncMock()
        db.execute = AsyncMock(return_value=result)
        with self.assertRaises(HTTPException):
            asyncio.run(update_rule(db, 999, 1, ReviewRuleUpdate(name="X")))

    def test_file_filters_update(self) -> None:
        rule = _make_orm_rule()
        db = AsyncMock()
        db.execute = _exec_returns(_r(scalar=rule))
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        asyncio.run(update_rule(db, 1, 1,
                                ReviewRuleUpdate(file_filters=RuleFileFilters(include=["*.java"]))))
        self.assertEqual(rule.file_filters, {"include": ["*.java"]})


class DeleteRuleTests(unittest.TestCase):
    def test_deletes(self) -> None:
        rule = _make_orm_rule()
        db = AsyncMock()
        db.execute = _exec_returns(_r(scalar=rule))
        db.delete = AsyncMock()
        db.commit = AsyncMock()
        asyncio.run(delete_rule(db, 1, 1))
        db.delete.assert_awaited_once_with(rule)

    def test_not_found(self) -> None:
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        db = AsyncMock()
        db.execute = AsyncMock(return_value=result)
        with self.assertRaises(HTTPException):
            asyncio.run(delete_rule(db, 999, 1))


class GetEnabledRulesTests(unittest.TestCase):
    def test_returns_rules(self) -> None:
        rules = [_make_orm_rule(id=i) for i in range(3)]
        db = AsyncMock()
        db.execute = _exec_returns(_r(scalars_all=rules))
        res = asyncio.run(get_enabled_rules(db, 1))
        self.assertEqual(len(res), 3)

    def test_empty(self) -> None:
        db = AsyncMock()
        db.execute = _exec_returns(_r(scalars_all=[]))
        res = asyncio.run(get_enabled_rules(db, 1))
        self.assertEqual(len(res), 0)


if __name__ == "__main__":
    unittest.main()
