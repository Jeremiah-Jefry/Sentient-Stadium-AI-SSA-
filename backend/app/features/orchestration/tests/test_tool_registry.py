"""Tests for ToolRegistry — tool registration, retrieval, default tools, and access validation."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.features.orchestration.dto.tool import ToolMetadata
from app.features.orchestration.registry.tool_registry import ToolRegistry
from app.shared.result import Failure, Success


@pytest.fixture
def registry() -> ToolRegistry:
    return ToolRegistry()


def _make_tool(
    tool_id: UUID | None = None,
    name: str = "Test Tool",
    permissions: list[str] | None = None,
    requires_authorization: bool = True,
) -> ToolMetadata:
    return ToolMetadata(
        tool_id=tool_id or uuid4(),
        name=name,
        description="Test tool",
        schema={"type": "object", "properties": {}, "required": []},
        version="1.0.0",
        timeout_seconds=5.0,
        cache_ttl_seconds=0.0,
        max_retries=1,
        requires_authorization=requires_authorization,
        permissions=permissions or ["read:test"],
    )


class TestToolRegistry:

    @pytest.mark.asyncio
    async def test_default_tools_registered(self, registry: ToolRegistry) -> None:
        tools = await registry.get_all_tools()
        assert len(tools) == 10
        names = {t.name for t in tools}
        assert "Digital Twin Query" in names
        assert "Routing Engine" in names
        assert "Prediction Engine" in names
        assert "Knowledge Search" in names
        assert "Memory Search" in names

    @pytest.mark.asyncio
    async def test_register_tool(self, registry: ToolRegistry) -> None:
        tool = _make_tool(name="Custom Tool")
        result = await registry.register_tool(tool)
        assert isinstance(result, Success)
        assert result.value.name == "Custom Tool"

    @pytest.mark.asyncio
    async def test_register_duplicate_tool(self, registry: ToolRegistry) -> None:
        tool = _make_tool(name="Dup Tool")
        result1 = await registry.register_tool(tool)
        assert isinstance(result1, Success)
        result2 = await registry.register_tool(tool)
        assert isinstance(result2, Failure)
        assert result2.error_code == "TOOL_ALREADY_REGISTERED"

    @pytest.mark.asyncio
    async def test_get_tool(self, registry: ToolRegistry) -> None:
        tool = _make_tool(name="Fetchable Tool")
        await registry.register_tool(tool)
        result = await registry.get_tool(tool.tool_id)
        assert result is not None
        assert result.name == "Fetchable Tool"

    @pytest.mark.asyncio
    async def test_get_tool_not_found(self, registry: ToolRegistry) -> None:
        result = await registry.get_tool(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_unregister_tool(self, registry: ToolRegistry) -> None:
        tool = _make_tool(name="Remove Me")
        await registry.register_tool(tool)
        result = await registry.unregister_tool(tool.tool_id)
        assert isinstance(result, Success)
        assert await registry.get_tool(tool.tool_id) is None

    @pytest.mark.asyncio
    async def test_unregister_not_found(self, registry: ToolRegistry) -> None:
        result = await registry.unregister_tool(uuid4())
        assert isinstance(result, Failure)
        assert result.error_code == "TOOL_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_validate_tool_access_authorized(self, registry: ToolRegistry) -> None:
        tool = _make_tool(permissions=["read:venue", "read:crowd"], requires_authorization=True)
        await registry.register_tool(tool)
        access = await registry.validate_tool_access(tool.tool_id, ["read:venue", "read:crowd", "write:alerts"])
        assert access is True

    @pytest.mark.asyncio
    async def test_validate_tool_access_unauthorized(self, registry: ToolRegistry) -> None:
        tool = _make_tool(permissions=["read:secret"], requires_authorization=True)
        await registry.register_tool(tool)
        access = await registry.validate_tool_access(tool.tool_id, ["read:public"])
        assert access is False

    @pytest.mark.asyncio
    async def test_validate_tool_access_no_auth_required(self, registry: ToolRegistry) -> None:
        tool = _make_tool(permissions=["read:internal"], requires_authorization=False)
        await registry.register_tool(tool)
        access = await registry.validate_tool_access(tool.tool_id, [])
        assert access is True

    @pytest.mark.asyncio
    async def test_validate_tool_access_nonexistent(self, registry: ToolRegistry) -> None:
        access = await registry.validate_tool_access(uuid4(), ["read:anything"])
        assert access is False

    @pytest.mark.asyncio
    async def test_find_tools_by_permission(self, registry: ToolRegistry) -> None:
        tools = await registry.find_tools_by_permission("read:weather")
        assert len(tools) >= 1
        assert all("read:weather" in t.permissions for t in tools)

    @pytest.mark.asyncio
    async def test_stats(self, registry: ToolRegistry) -> None:
        stats = await registry.stats()
        assert stats["total_tools"] == 10
        assert len(stats["tool_names"]) == 10
        assert isinstance(stats["authorized_tools"], int)
        assert isinstance(stats["unauthenticated_tools"], int)
