"""Deterministic test doubles for the artifacts domain (no DB, no network).

Fake repositories mimic the exact method signatures of the typed repos so the
services under test exercise their real logic (pycrdt merges run for real —
the library is pure-local). ``FakeObjectStorage`` implements the S3 port with
an in-memory dict.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError


class FakeUniqueViolationError(Exception):
    """Mimics asyncpg's UniqueViolationError shape (sqlstate 23505)."""

    sqlstate = "23505"


class FakeCheckViolationError(Exception):
    """Mimics asyncpg's CheckViolationError shape (sqlstate 23514)."""

    sqlstate = "23514"


def integrity_error(constraint: str = "artifact_versions_num_uniq") -> IntegrityError:
    """A realistic unique-violation IntegrityError for race simulations."""
    return IntegrityError(
        "INSERT INTO ...",
        {},
        FakeUniqueViolationError(f'duplicate key value violates unique constraint "{constraint}"'),
    )


def check_violation_error() -> IntegrityError:
    """A non-retryable IntegrityError (CHECK violation, not a version race)."""
    return IntegrityError(
        "INSERT INTO ...",
        {},
        FakeCheckViolationError(
            'new row for relation "artifact_versions" violates check constraint '
            '"artifact_versions_storage_xor"'
        ),
    )


def make_artifact(**over: Any) -> SimpleNamespace:
    base: dict[str, Any] = {
        "id": uuid4(),
        "cell_id": uuid4(),
        "artifact_type": "document",
        "title": "Doc",
        "tags": [],
        "owner_user_id": None,
        "created_by_agent_id": None,
        "current_version_num": 0,
        "deleted_at": None,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    base.update(over)
    return SimpleNamespace(**base)


class FakeArtifactRepo:
    """Envelope + versions in dicts; UNIQUE(artifact_id, version_num) enforced."""

    def __init__(self) -> None:
        self.artifacts: dict[UUID, SimpleNamespace] = {}
        self.versions: list[SimpleNamespace] = []
        self.fail_next_inserts = 0  # simulate UNIQUE races
        self.raise_on_insert: Exception | None = None  # one-shot arbitrary error
        self.insert_version_calls = 0

    def add(self, artifact: SimpleNamespace) -> SimpleNamespace:
        self.artifacts[artifact.id] = artifact
        return artifact

    async def insert(self, **kw: Any) -> SimpleNamespace:
        row = make_artifact(**kw)
        return self.add(row)

    async def get(
        self, artifact_id: UUID, *, cell_id: UUID, include_deleted: bool = False
    ) -> SimpleNamespace | None:
        row = self.artifacts.get(artifact_id)
        if row is None or row.cell_id != cell_id:
            return None
        if row.deleted_at is not None and not include_deleted:
            return None
        return row

    async def get_for_update(self, artifact_id: UUID, *, cell_id: UUID) -> SimpleNamespace | None:
        return await self.get(artifact_id, cell_id=cell_id)

    async def list_recent(
        self,
        cell_id: UUID,
        *,
        artifact_type: str | None = None,
        limit: int,
        offset: int = 0,
    ) -> list[SimpleNamespace]:
        rows = [
            a
            for a in self.artifacts.values()
            if a.cell_id == cell_id
            and a.deleted_at is None
            and (artifact_type is None or a.artifact_type == artifact_type)
        ]
        rows.sort(key=lambda a: a.created_at, reverse=True)
        return rows[offset : offset + limit]

    async def soft_delete(self, artifact_id: UUID, *, cell_id: UUID) -> bool:
        row = await self.get(artifact_id, cell_id=cell_id)
        if row is None:
            return False
        row.deleted_at = datetime.now(UTC)
        return True

    async def set_current_version(self, artifact_id: UUID, *, version_num: int) -> None:
        self.artifacts[artifact_id].current_version_num = version_num

    async def insert_version(self, **fields: Any) -> SimpleNamespace:
        self.insert_version_calls += 1
        if self.raise_on_insert is not None:
            exc, self.raise_on_insert = self.raise_on_insert, None
            raise exc
        if self.fail_next_inserts > 0:
            self.fail_next_inserts -= 1
            raise integrity_error()
        if any(
            v.artifact_id == fields["artifact_id"] and v.version_num == fields["version_num"]
            for v in self.versions
        ):
            raise integrity_error()
        row = SimpleNamespace(id=uuid4(), created_at=datetime.now(UTC), **fields)
        self.versions.append(row)
        return row

    async def get_version(
        self, artifact_id: UUID, version_num: int, *, cell_id: UUID
    ) -> SimpleNamespace | None:
        for v in self.versions:
            if (
                v.artifact_id == artifact_id
                and v.version_num == version_num
                and v.cell_id == cell_id
            ):
                return v
        return None

    async def list_versions(self, artifact_id: UUID, *, cell_id: UUID) -> list[SimpleNamespace]:
        return sorted(
            (v for v in self.versions if v.artifact_id == artifact_id and v.cell_id == cell_id),
            key=lambda v: v.version_num,
        )

    async def max_version_num(self, artifact_id: UUID) -> int:
        nums = [v.version_num for v in self.versions if v.artifact_id == artifact_id]
        return max(nums, default=0)

    async def sum_version_bytes(self, artifact_id: UUID) -> int:
        return sum(v.byte_size for v in self.versions if v.artifact_id == artifact_id)


class FakeUsageRepo:
    def __init__(self) -> None:
        self.by_cell: dict[UUID, int] = {}
        self.calls: list[tuple[UUID, int]] = []

    async def add_bytes(self, cell_id: UUID, delta: int) -> None:
        self.calls.append((cell_id, delta))
        self.by_cell[cell_id] = max(self.by_cell.get(cell_id, 0) + delta, 0)

    async def get_bytes(self, cell_id: UUID) -> int:
        return self.by_cell.get(cell_id, 0)


class FakeYjsRepo:
    def __init__(self) -> None:
        self.documents: dict[UUID, SimpleNamespace] = {}  # by artifact_id
        self.updates: list[SimpleNamespace] = []
        self.snapshots: list[SimpleNamespace] = []
        self._seq = 0

    async def insert_document(
        self, *, cell_id: UUID, artifact_id: UUID, state: bytes, state_vector: bytes
    ) -> SimpleNamespace:
        if artifact_id in self.documents:  # UNIQUE(artifact_id), like the real DDL
            raise integrity_error("yjs_documents_artifact_uniq")
        row = SimpleNamespace(
            id=uuid4(),
            cell_id=cell_id,
            artifact_id=artifact_id,
            state=state,
            state_vector=state_vector,
            update_count=0,
            last_compacted_at=None,
        )
        self.documents[artifact_id] = row
        return row

    async def get_by_artifact(self, artifact_id: UUID, *, cell_id: UUID) -> SimpleNamespace | None:
        row = self.documents.get(artifact_id)
        return row if row is not None and row.cell_id == cell_id else None

    async def get_by_id(self, document_id: UUID, *, cell_id: UUID) -> SimpleNamespace | None:
        for row in self.documents.values():
            if row.id == document_id and row.cell_id == cell_id:
                return row
        return None

    async def get_by_artifact_for_update(
        self, artifact_id: UUID, *, cell_id: UUID
    ) -> SimpleNamespace | None:
        return await self.get_by_artifact(artifact_id, cell_id=cell_id)

    async def save_head(
        self, row: SimpleNamespace, *, state: bytes, state_vector: bytes, update_count: int
    ) -> None:
        row.state = state
        row.state_vector = state_vector
        row.update_count = update_count

    async def mark_compacted(self, row: SimpleNamespace) -> None:
        row.update_count = 0
        row.last_compacted_at = datetime.now(UTC)

    async def append_update(
        self, *, document_id: UUID, cell_id: UUID, update_data: bytes
    ) -> SimpleNamespace:
        self._seq += 1
        row = SimpleNamespace(
            seq=self._seq,
            cell_id=cell_id,
            yjs_document_id=document_id,
            update_data=update_data,
        )
        self.updates.append(row)
        return row

    async def count_updates(self, document_id: UUID) -> int:
        return sum(1 for u in self.updates if u.yjs_document_id == document_id)

    async def max_update_seq(self, document_id: UUID) -> int | None:
        seqs = [u.seq for u in self.updates if u.yjs_document_id == document_id]
        return max(seqs, default=None)

    async def prune_updates(self, document_id: UUID, *, up_to_seq: int) -> int:
        before = len(self.updates)
        self.updates = [
            u for u in self.updates if not (u.yjs_document_id == document_id and u.seq <= up_to_seq)
        ]
        return before - len(self.updates)

    async def insert_snapshot(
        self, *, document_id: UUID, cell_id: UUID, state: bytes, state_vector: bytes
    ) -> SimpleNamespace:
        row = SimpleNamespace(
            id=uuid4(),
            cell_id=cell_id,
            yjs_document_id=document_id,
            state=state,
            state_vector=state_vector,
            created_at=datetime.now(UTC),
        )
        self.snapshots.append(row)
        return row

    async def get_snapshot(self, snapshot_id: UUID, *, cell_id: UUID) -> SimpleNamespace | None:
        for s in self.snapshots:
            if s.id == snapshot_id and s.cell_id == cell_id:
                return s
        return None

    async def list_snapshots(self, document_id: UUID, *, cell_id: UUID) -> list[SimpleNamespace]:
        return [
            s for s in self.snapshots if s.yjs_document_id == document_id and s.cell_id == cell_id
        ]


class FakeS3Repo:
    """s3_objects lifecycle rows in memory; UNIQUE(bucket, s3_key) enforced."""

    def __init__(self) -> None:
        self.rows: dict[UUID, SimpleNamespace] = {}

    async def insert_pending(
        self,
        *,
        cell_id: UUID,
        artifact_id: UUID,
        bucket: str,
        s3_key: str,
        mime_type: str | None = None,
    ) -> SimpleNamespace:
        if any(r.bucket == bucket and r.s3_key == s3_key for r in self.rows.values()):
            raise integrity_error("s3_objects_bucket_key_uniq")
        row = SimpleNamespace(
            id=uuid4(),
            cell_id=cell_id,
            artifact_id=artifact_id,
            bucket=bucket,
            s3_key=s3_key,
            mime_type=mime_type,
            byte_size=None,
            content_hash_sha256=None,
            status="pending",
            created_at=datetime.now(UTC),
        )
        self.rows[row.id] = row
        return row

    async def get(self, s3_object_id: UUID, *, cell_id: UUID) -> SimpleNamespace | None:
        row = self.rows.get(s3_object_id)
        return row if row is not None and row.cell_id == cell_id else None

    async def find_stored_by_key(self, s3_key: str, *, cell_id: UUID) -> SimpleNamespace | None:
        for row in self.rows.values():
            if row.s3_key == s3_key and row.cell_id == cell_id and row.status == "stored":
                return row
        return None

    async def mark_stored(
        self, s3_object_id: UUID, *, byte_size: int, content_hash_sha256: str
    ) -> bool:
        row = self.rows[s3_object_id]
        if row.status != "pending":  # conditional transition, like the real repo
            return False
        row.status = "stored"
        row.byte_size = byte_size
        row.content_hash_sha256 = content_hash_sha256
        return True

    async def mark_deleted(self, s3_object_id: UUID) -> None:
        self.rows[s3_object_id].status = "deleted"

    async def mark_all_deleted_for_artifact(self, artifact_id: UUID, *, cell_id: UUID) -> int:
        flipped = 0
        for row in self.rows.values():
            if (
                row.artifact_id == artifact_id
                and row.cell_id == cell_id
                and row.status != "deleted"
            ):
                row.status = "deleted"
                flipped += 1
        return flipped

    async def delete_stale_pending(self, *, cell_id: UUID, older_than: datetime) -> int:
        stale = [
            rid
            for rid, r in self.rows.items()
            if r.cell_id == cell_id and r.status == "pending" and r.created_at < older_than
        ]
        for rid in stale:
            del self.rows[rid]
        return len(stale)


class FakeObjectStorage:
    """In-memory S3 port double — presign/head/get/delete with no network."""

    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}
        self.deleted: list[tuple[str, str]] = []

    def put(self, bucket: str, key: str, body: bytes) -> None:
        """Test helper: simulate the client-side upload."""
        self.objects[(bucket, key)] = body

    async def presign_post(
        self, *, bucket: str, key: str, expires_in: int, max_bytes: int
    ) -> dict[str, object]:
        return {
            "url": f"https://fake-s3.local/{bucket}",
            "fields": {"key": key, "policy": "fake-policy"},
        }

    async def head_object(self, *, bucket: str, key: str) -> int | None:
        body = self.objects.get((bucket, key))
        return len(body) if body is not None else None

    async def get_object(self, *, bucket: str, key: str) -> bytes | None:
        return self.objects.get((bucket, key))

    async def presign_get(self, *, bucket: str, key: str, expires_in: int) -> str:
        return f"https://fake-s3.local/{bucket}/{key}?signed=1&ttl={expires_in}"

    async def delete_object(self, *, bucket: str, key: str) -> None:
        self.objects.pop((bucket, key), None)
        self.deleted.append((bucket, key))


def sha256_hex(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()
