"""Edge repository - graph data access for pathfinding and connectivity."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.digital_twin.models.edge import Edge, EdgeType
from app.shared.result import Result, Success


class EdgeRepository:
    """Handles all database operations for the Edge (graph) model.

    Supports neighbor lookups, adjacency list construction,
    and graph connectivity analysis.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, edge_id: uuid.UUID) -> Result[Edge | None]:
        """Fetch an edge by ID, excluding soft-deleted."""
        stmt = select(Edge).where(Edge.id == edge_id, Edge.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return Success(result.scalar_one_or_none())

    async def create(self, edge: Edge) -> Result[Edge]:
        """Persist a new edge."""
        self._session.add(edge)
        await self._session.flush()
        return Success(edge)

    async def create_many(self, edges: list[Edge]) -> Result[Sequence[Edge]]:
        """Batch-insert multiple edges."""
        self._session.add_all(edges)
        await self._session.flush()
        return Success(edges)

    async def delete(self, edge_id: uuid.UUID) -> Result[None]:
        """Soft-delete an edge."""
        stmt = update(Edge).where(Edge.id == edge_id).values(deleted_at=func.now())
        await self._session.execute(stmt)
        return Success(None)

    async def get_neighbors(
        self, entity_id: uuid.UUID, edge_type: EdgeType | None = None,
    ) -> Result[list[Edge]]:
        """Fetch all outgoing edges from an entity (directed graph traversal)."""
        conditions = [
            Edge.from_entity_id == entity_id,
            Edge.deleted_at.is_(None),
        ]
        if edge_type is not None:
            conditions.append(Edge.edge_type == edge_type)

        stmt = select(Edge).where(and_(*conditions))
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))

    async def get_all_bidirectional(
        self, entity_id: uuid.UUID, edge_type: EdgeType | None = None,
    ) -> Result[list[Edge]]:
        """Fetch all edges connected to an entity in both directions.

        For bidirectional edges, returns the edge if entity is either source or target.
        """
        conditions = [
            ((Edge.from_entity_id == entity_id) | (Edge.to_entity_id == entity_id)),
            Edge.is_bidirectional.is_(True),
            Edge.deleted_at.is_(None),
        ]
        if edge_type is not None:
            conditions.append(Edge.edge_type == edge_type)

        stmt = select(Edge).where(and_(*conditions))
        result = await self._session.execute(stmt)
        return Success(list(result.scalars().all()))

    async def get_by_venue(self, venue_id: uuid.UUID) -> Result[Sequence[Edge]]:
        """Fetch all edges for a venue (for in-memory graph construction)."""
        stmt = select(Edge).where(Edge.venue_id == venue_id, Edge.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return Success(result.scalars().all())

    async def exists_between(
        self, from_id: uuid.UUID, to_id: uuid.UUID,
    ) -> Result[bool]:
        """Check if a direct edge exists between two entities."""
        stmt = select(func.count()).where(
            Edge.from_entity_id == from_id,
            Edge.to_entity_id == to_id,
            Edge.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return Success(result.scalar_one() > 0)

    async def count_by_venue(self, venue_id: uuid.UUID) -> Result[int]:
        """Count all non-deleted edges for a venue."""
        stmt = select(func.count()).where(
            Edge.venue_id == venue_id, Edge.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return Success(result.scalar_one())
