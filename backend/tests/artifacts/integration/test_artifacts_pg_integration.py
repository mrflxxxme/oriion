"""Integration: artifacts domain on real Postgres via testcontainers.

Exercises migrations + repositories + services end-to-end under RLS as the
non-superuser ``oriion_app`` role (superusers bypass even FORCE RLS):

* AC-01.5.1 — cross-cell isolation on ALL 7 artifacts tables;
* AC-01.5.2 — version race-retry (UNIQUE violation → re-read → next num) and
  DB-grant immutability (UPDATE/DELETE on versions rejected by Postgres);
* AC-01.5.3 — Yjs read-your-writes + explicit commit + compaction pruning
  the log (never snapshots) on the real bytea round-trip;
* AC-01.5.5 — resolver head / vN / cell-mismatch-404 on real rows;
* AC-01.5.6 — tasks.task_artifacts s3_key / yjs_document_id resolve against
  artifacts tables (tasks context untouched);
* AC-01.5.7 — cell_storage_usage stays transactionally consistent.

Setup rows (workspaces / cells / cross-cell fixtures) are created as the
superuser test role BEFORE dropping to ``oriion_app``.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from pycrdt import Doc, Text
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession
from src._shared.db.rls import set_tenant_context
from src.artifacts.exceptions import ArtifactNotFound, MalformedArtifactUrl
from src.artifacts.repositories.artifact_repository import ArtifactRepository, UsageRepository
from src.artifacts.repositories.s3_repository import S3ObjectRepository
from src.artifacts.repositories.yjs_repository import YjsRepository
from src.artifacts.services.artifacts import ArtifactService, _canonical_json
from src.artifacts.services.resolver import ArtifactResolver
from src.artifacts.services.s3 import S3AssetService
from src.artifacts.services.yjs import YjsService

from tests.artifacts._fakes import FakeObjectStorage

pytestmark = pytest.mark.integration

_ALL_TABLES = (
    "artifacts.artifacts",
    "artifacts.artifact_versions",
    "artifacts.yjs_documents",
    "artifacts.yjs_updates",
    "artifacts.yjs_snapshots",
    "artifacts.s3_objects",
    "artifacts.cell_storage_usage",
)


async def _make_workspace_cell(session: AsyncSession) -> tuple[UUID, UUID]:
    ws_id, cell_id = uuid4(), uuid4()
    await session.execute(
        text(
            "INSERT INTO multitenancy.workspaces (id, slug, display_name) "
            "VALUES (:id, :slug, :name)"
        ),
        {"id": str(ws_id), "slug": f"ws-{ws_id}", "name": "WS"},
    )
    await session.execute(
        text(
            "INSERT INTO multitenancy.cells (id, workspace_id, slug, display_name) "
            "VALUES (:id, :ws, 'default', 'C')"
        ),
        {"id": str(cell_id), "ws": str(ws_id)},
    )
    return ws_id, cell_id


async def _seed_full_artifact_graph(session: AsyncSession, cell_id: UUID) -> UUID:
    """Superuser setup: one row in EVERY artifacts table for the cell."""
    artifact_id, doc_id, snap_id, obj_id = uuid4(), uuid4(), uuid4(), uuid4()
    await session.execute(
        text(
            "INSERT INTO artifacts.artifacts (id, cell_id, artifact_type, title, "
            "current_version_num) VALUES (:id, :cell, 'document', 'seed', 1)"
        ),
        {"id": str(artifact_id), "cell": str(cell_id)},
    )
    await session.execute(
        text(
            "INSERT INTO artifacts.yjs_documents (id, cell_id, artifact_id, state, "
            "state_vector) VALUES (:id, :cell, :art, '\\x0000'::bytea, '\\x00'::bytea)"
        ),
        {"id": str(doc_id), "cell": str(cell_id), "art": str(artifact_id)},
    )
    await session.execute(
        text(
            "INSERT INTO artifacts.yjs_updates (cell_id, yjs_document_id, update_data) "
            "VALUES (:cell, :doc, '\\x00'::bytea)"
        ),
        {"cell": str(cell_id), "doc": str(doc_id)},
    )
    await session.execute(
        text(
            "INSERT INTO artifacts.yjs_snapshots (id, cell_id, yjs_document_id, state, "
            "state_vector) VALUES (:id, :cell, :doc, '\\x0000'::bytea, '\\x00'::bytea)"
        ),
        {"id": str(snap_id), "cell": str(cell_id), "doc": str(doc_id)},
    )
    await session.execute(
        text(
            "INSERT INTO artifacts.s3_objects (id, cell_id, artifact_id, bucket, s3_key, "
            "status) VALUES (:id, :cell, :art, 'b', :key, 'stored')"
        ),
        {
            "id": str(obj_id),
            "cell": str(cell_id),
            "art": str(artifact_id),
            "key": f"seed/{cell_id}/{artifact_id}/1/f.bin",
        },
    )
    await session.execute(
        text(
            "INSERT INTO artifacts.artifact_versions (cell_id, artifact_id, version_num, "
            "storage_kind, content_inline) VALUES (:cell, :art, 1, 'inline', '{}'::jsonb)"
        ),
        {"cell": str(cell_id), "art": str(artifact_id)},
    )
    await session.execute(
        text(
            "INSERT INTO artifacts.cell_storage_usage (cell_id, bytes_total) " "VALUES (:cell, 42)"
        ),
        {"cell": str(cell_id)},
    )
    return artifact_id


def _services(
    session: AsyncSession,
) -> tuple[ArtifactService, YjsService, ArtifactResolver]:
    artifact_repo = ArtifactRepository(session)
    usage_repo = UsageRepository(session)
    s3_repo = S3ObjectRepository(session)
    yjs_repo = YjsRepository(session)
    art_svc = ArtifactService(artifact_repo, usage_repo, s3_repo)
    yjs_svc = YjsService(yjs_repo, artifact_repo, usage_repo)
    s3_svc = S3AssetService(
        s3_repo,
        artifact_repo,
        usage_repo,
        FakeObjectStorage(),
        bucket="b",
        env_prefix="it",
        max_upload_bytes=1024,
    )
    resolver = ArtifactResolver(artifact_repo, yjs_repo, s3_svc)
    return art_svc, yjs_svc, resolver


def _client_update(word: str) -> bytes:
    doc = Doc()
    body = doc.get("body", type=Text)
    body += word
    return doc.get_update()


def _state_text(state: bytes) -> str:
    doc = Doc()
    doc.apply_update(state)
    return str(doc.get("body", type=Text))


# ── AC-01.5.1: RLS isolation on all 7 tables ────────────────────────────── #


async def test_rls_cross_cell_isolation_all_seven_tables(db_session: AsyncSession) -> None:
    ws_a, cell_a = await _make_workspace_cell(db_session)
    _, cell_b = await _make_workspace_cell(db_session)
    await _seed_full_artifact_graph(db_session, cell_a)
    await _seed_full_artifact_graph(db_session, cell_b)

    async with set_tenant_context(db_session, workspace_id=ws_a, cell_id=cell_a, user_id=uuid4()):
        await db_session.execute(text("SET LOCAL ROLE oriion_app"))
        for table in _ALL_TABLES:
            rows = (await db_session.execute(text(f"SELECT cell_id FROM {table}"))).all()
            cells = {str(r[0]) for r in rows}
            assert cells == {str(cell_a)}, f"RLS leak on {table}: {cells}"


async def test_rls_default_deny_without_context(db_session: AsyncSession) -> None:
    _, cell_a = await _make_workspace_cell(db_session)
    await _seed_full_artifact_graph(db_session, cell_a)

    # No tenant GUC at all → current_cell_id() IS NULL → zero rows visible.
    async with db_session.begin_nested():
        await db_session.execute(text("SET LOCAL ROLE oriion_app"))
        for table in _ALL_TABLES:
            count = (await db_session.execute(text(f"SELECT count(*) FROM {table}"))).scalar_one()
            assert count == 0, f"default-deny broken on {table}"


# ── AC-01.5.2: race-retry + DB-grant immutability ───────────────────────── #


async def test_version_race_retry_lands_on_next_free_num(db_session: AsyncSession) -> None:
    ws_id, cell_id = await _make_workspace_cell(db_session)
    art_svc, _, _ = _services(db_session)

    async with set_tenant_context(db_session, workspace_id=ws_id, cell_id=cell_id, user_id=uuid4()):
        await db_session.execute(text("SET LOCAL ROLE oriion_app"))
        artifact = await art_svc.create(cell_id=cell_id, artifact_type="document", title="race")
        # A "racer" inserts v1 directly, bypassing the head bump.
        await db_session.execute(
            text(
                "INSERT INTO artifacts.artifact_versions (cell_id, artifact_id, "
                "version_num, storage_kind, content_inline) "
                "VALUES (:cell, :art, 1, 'inline', '{}'::jsonb)"
            ),
            {"cell": str(cell_id), "art": str(artifact.id)},
        )
        version = await art_svc.create_inline_version(
            cell_id=cell_id, artifact_id=artifact.id, content={"text": "mine"}
        )
        # First attempt (v1) collides → re-read max → v2. Head follows.
        assert version.version_num == 2
        head = (
            await db_session.execute(
                text("SELECT current_version_num FROM artifacts.artifacts WHERE id = :id"),
                {"id": str(artifact.id)},
            )
        ).scalar_one()
        assert head == 2


async def test_versions_and_snapshots_immutable_at_db_level(db_session: AsyncSession) -> None:
    ws_id, cell_id = await _make_workspace_cell(db_session)
    artifact_id = await _seed_full_artifact_graph(db_session, cell_id)

    async with set_tenant_context(db_session, workspace_id=ws_id, cell_id=cell_id, user_id=uuid4()):
        await db_session.execute(text("SET LOCAL ROLE oriion_app"))
        statements = (
            "UPDATE artifacts.artifact_versions SET byte_size = 999 WHERE artifact_id = :art",
            "DELETE FROM artifacts.artifact_versions WHERE artifact_id = :art",
            "UPDATE artifacts.yjs_snapshots SET state = '\\x99'::bytea",
            "DELETE FROM artifacts.yjs_snapshots",
        )
        for stmt in statements:
            with pytest.raises(ProgrammingError, match="permission denied"):
                async with db_session.begin_nested():
                    await db_session.execute(text(stmt), {"art": str(artifact_id)})


# ── AC-01.5.3: Yjs read-your-writes / commit / compaction on real PG ────── #


async def test_yjs_read_your_writes_commit_and_compaction(db_session: AsyncSession) -> None:
    ws_id, cell_id = await _make_workspace_cell(db_session)
    artifact_repo = ArtifactRepository(db_session)
    usage_repo = UsageRepository(db_session)
    yjs_repo = YjsRepository(db_session)
    art_svc, _, resolver = _services(db_session)
    yjs_svc = YjsService(yjs_repo, artifact_repo, usage_repo, compact_update_count=1000)

    async with set_tenant_context(db_session, workspace_id=ws_id, cell_id=cell_id, user_id=uuid4()):
        await db_session.execute(text("SET LOCAL ROLE oriion_app"))
        artifact = await art_svc.create(cell_id=cell_id, artifact_type="document", title="doc")
        await yjs_svc.create_document(cell_id=cell_id, artifact_id=artifact.id)

        await yjs_svc.apply_update(
            cell_id=cell_id, artifact_id=artifact.id, update_data=_client_update("hello ")
        )
        await yjs_svc.apply_update(
            cell_id=cell_id, artifact_id=artifact.id, update_data=_client_update("world")
        )
        # Read-your-writes: a fresh SELECT sees the merged state (POST → GET).
        state = (
            await db_session.execute(
                text("SELECT state FROM artifacts.yjs_documents WHERE artifact_id = :art"),
                {"art": str(artifact.id)},
            )
        ).scalar_one()
        merged = _state_text(bytes(state))
        assert "hello " in merged and "world" in merged

        # Explicit commit → immutable snapshot + version row + resolvable /v1.
        version, snapshot = await yjs_svc.commit_version(cell_id=cell_id, artifact_id=artifact.id)
        assert version.version_num == 1 and version.storage_kind == "yjs_snapshot"
        resolved = await resolver.resolve(
            f"artifact://{cell_id}/{artifact.id}/v1", current_cell_id=cell_id
        )
        assert resolved.yjs_state_base64 is not None

        # Compaction: threshold 0 → the NEXT update EXCEEDS it (strict `>`,
        # ADR-038), prunes the log, keeps every snapshot, resets the counter.
        compacting = YjsService(yjs_repo, artifact_repo, usage_repo, compact_update_count=0)
        await compacting.apply_update(
            cell_id=cell_id, artifact_id=artifact.id, update_data=_client_update("!")
        )
        updates_left = (
            await db_session.execute(
                text(
                    "SELECT count(*) FROM artifacts.yjs_updates u "
                    "JOIN artifacts.yjs_documents d ON d.id = u.yjs_document_id "
                    "WHERE d.artifact_id = :art"
                ),
                {"art": str(artifact.id)},
            )
        ).scalar_one()
        snapshots = (
            await db_session.execute(
                text("SELECT count(*) FROM artifacts.yjs_snapshots WHERE yjs_document_id = :doc"),
                {"doc": str(snapshot.yjs_document_id)},
            )
        ).scalar_one()
        assert updates_left == 0  # log pruned
        assert snapshots == 2  # commit snapshot + compaction snapshot — none deleted


# ── AC-01.5.5: resolver on real rows ────────────────────────────────────── #


async def test_resolver_head_vn_and_404_semantics(db_session: AsyncSession) -> None:
    ws_id, cell_id = await _make_workspace_cell(db_session)
    _, cell_b = await _make_workspace_cell(db_session)
    art_svc, _, resolver = _services(db_session)

    async with set_tenant_context(db_session, workspace_id=ws_id, cell_id=cell_id, user_id=uuid4()):
        await db_session.execute(text("SET LOCAL ROLE oriion_app"))
        artifact = await art_svc.create(cell_id=cell_id, artifact_type="document", title="r")
        await art_svc.create_inline_version(
            cell_id=cell_id, artifact_id=artifact.id, content={"text": "old"}
        )
        await art_svc.create_inline_version(
            cell_id=cell_id, artifact_id=artifact.id, content={"text": "new"}
        )

        head = await resolver.resolve(
            f"artifact://{cell_id}/{artifact.id}", current_cell_id=cell_id
        )
        assert head.version_num == 2 and head.content_inline == {"text": "new"}
        v1 = await resolver.resolve(
            f"artifact://{cell_id}/{artifact.id}/v1", current_cell_id=cell_id
        )
        assert v1.content_inline == {"text": "old"}

        with pytest.raises(ArtifactNotFound):  # cell mismatch → plain 404
            await resolver.resolve(f"artifact://{cell_b}/{artifact.id}", current_cell_id=cell_id)
        with pytest.raises(MalformedArtifactUrl):  # malformed → 422
            await resolver.resolve("artifact://oops", current_cell_id=cell_id)


# ── AC-01.5.6: tasks.task_artifacts refs resolve (tasks untouched) ──────── #


async def test_task_artifacts_refs_resolve_against_artifacts_tables(
    db_session: AsyncSession,
) -> None:
    ws_id, cell_id = await _make_workspace_cell(db_session)
    artifact_id = await _seed_full_artifact_graph(db_session, cell_id)
    seeded_key = f"seed/{cell_id}/{artifact_id}/1/f.bin"

    # A task + its artifacts rows (superuser setup, no FK to artifacts schema).
    task_id = uuid4()
    await db_session.execute(
        text(
            "INSERT INTO tasks.tasks (id, cell_id, initiated_by_user_id, title) "
            "VALUES (:id, :cell, :user, 'produce artifacts')"
        ),
        {"id": str(task_id), "cell": str(cell_id), "user": str(uuid4())},
    )
    doc_id = (
        await db_session.execute(
            text("SELECT id FROM artifacts.yjs_documents WHERE artifact_id = :art"),
            {"art": str(artifact_id)},
        )
    ).scalar_one()
    await db_session.execute(
        text(
            "INSERT INTO tasks.task_artifacts (task_id, artifact_type, storage_kind, s3_key) "
            "VALUES (:task, 'file', 's3', :key)"
        ),
        {"task": str(task_id), "key": seeded_key},
    )
    await db_session.execute(
        text(
            "INSERT INTO tasks.task_artifacts (task_id, artifact_type, storage_kind, "
            "yjs_document_id) VALUES (:task, 'text', 'yjs_document', :doc)"
        ),
        {"task": str(task_id), "doc": str(doc_id)},
    )

    async with set_tenant_context(db_session, workspace_id=ws_id, cell_id=cell_id, user_id=uuid4()):
        await db_session.execute(text("SET LOCAL ROLE oriion_app"))
        # s3_key → artifacts.s3_objects (queryable target, AC-01.5.6).
        resolved_s3 = (
            await db_session.execute(
                text(
                    "SELECT o.status, o.artifact_id FROM tasks.task_artifacts ta "
                    "JOIN artifacts.s3_objects o ON o.s3_key = ta.s3_key "
                    "WHERE ta.task_id = :task AND ta.storage_kind = 's3'"
                ),
                {"task": str(task_id)},
            )
        ).one()
        assert resolved_s3[0] == "stored"
        assert str(resolved_s3[1]) == str(artifact_id)

        # yjs_document_id → artifacts.yjs_documents.
        resolved_doc = (
            await db_session.execute(
                text(
                    "SELECT d.artifact_id FROM tasks.task_artifacts ta "
                    "JOIN artifacts.yjs_documents d ON d.id = ta.yjs_document_id "
                    "WHERE ta.task_id = :task AND ta.storage_kind = 'yjs_document'"
                ),
                {"task": str(task_id)},
            )
        ).one()
        assert str(resolved_doc[0]) == str(artifact_id)

        # Repository-level resolution (service path) matches.
        s3_row = await S3ObjectRepository(db_session).find_stored_by_key(
            seeded_key, cell_id=cell_id
        )
        assert s3_row is not None and s3_row.artifact_id == artifact_id
        doc_row = await YjsRepository(db_session).get_by_id(doc_id, cell_id=cell_id)
        assert doc_row is not None and doc_row.artifact_id == artifact_id


# ── AC-01.5.7: usage accounting consistency ─────────────────────────────── #


async def test_cell_storage_usage_consistent_across_lifecycle(
    db_session: AsyncSession,
) -> None:
    ws_id, cell_id = await _make_workspace_cell(db_session)
    art_svc, yjs_svc, _ = _services(db_session)

    async def usage() -> int:
        value = (
            await db_session.execute(
                text("SELECT bytes_total FROM artifacts.cell_storage_usage WHERE cell_id = :c"),
                {"c": str(cell_id)},
            )
        ).scalar_one_or_none()
        return int(value) if value is not None else 0

    async with set_tenant_context(db_session, workspace_id=ws_id, cell_id=cell_id, user_id=uuid4()):
        await db_session.execute(text("SET LOCAL ROLE oriion_app"))
        artifact = await art_svc.create(cell_id=cell_id, artifact_type="document", title="u")
        assert await usage() == 0

        inline_bytes = len(_canonical_json({"text": "usage-data"}))
        await art_svc.create_inline_version(
            cell_id=cell_id, artifact_id=artifact.id, content={"text": "usage-data"}
        )
        assert await usage() == inline_bytes

        await yjs_svc.create_document(cell_id=cell_id, artifact_id=artifact.id)
        version, _ = await yjs_svc.commit_version(cell_id=cell_id, artifact_id=artifact.id)
        assert await usage() == inline_bytes + version.byte_size

        # Soft-delete frees the logical bytes transactionally.
        await art_svc.soft_delete(cell_id=cell_id, artifact_id=artifact.id)
        assert await usage() == 0
