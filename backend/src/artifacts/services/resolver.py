"""``artifact://`` resolver — strict grammar, no cross-cell existence oracle.

Grammar (ADR-012 / ADR-038):

    artifact://<cell_id>/<artifact_id>[/v<N>]

- canonical lowercase UUIDs, ``N`` >= 1 without leading zeros;
- malformed URL → 422 (``MalformedArtifactUrl``);
- cell mismatch → the SAME 404 as a missing artifact (ADR-038 graft G2 —
  a foreign cell learns nothing about existence);
- no version segment → head via ``current_version_num`` (0 → 404);
- ``/vN`` → the immutable ``artifact_versions`` row;
- dispatch on ``storage_kind``: inline content / signed S3 GET URL /
  yjs snapshot state (base64).
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from uuid import UUID

from src.artifacts.exceptions import (
    ArtifactNotFound,
    ArtifactVersionNotFound,
    MalformedArtifactUrl,
)
from src.artifacts.repositories.artifact_repository import ArtifactRepository
from src.artifacts.repositories.yjs_repository import YjsRepository
from src.artifacts.services.s3 import S3AssetService

_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
# \Z (not $): `$` would also match before a trailing newline — reject it.
_ARTIFACT_URL_RE = re.compile(rf"\Aartifact://({_UUID})/({_UUID})(?:/v([1-9][0-9]{{0,8}}))?\Z")


@dataclass(frozen=True)
class ParsedArtifactUrl:
    cell_id: UUID
    artifact_id: UUID
    version_num: int | None  # None = head


@dataclass(frozen=True)
class ResolvedArtifact:
    """Resolution result — exactly one of the three payload fields is set."""

    artifact_id: UUID
    cell_id: UUID
    artifact_type: str
    title: str
    version_num: int
    storage_kind: str
    byte_size: int
    content_hash_sha256: str
    content_inline: dict[str, object] | None = None
    download_url: str | None = None
    yjs_state_base64: str | None = None


def parse_artifact_url(url: str) -> ParsedArtifactUrl:
    """Strict parse; raises ``MalformedArtifactUrl`` (422) on any deviation."""
    match = _ARTIFACT_URL_RE.match(url)
    if match is None:
        raise MalformedArtifactUrl(url)
    cell_raw, artifact_raw, version_raw = match.groups()
    return ParsedArtifactUrl(
        cell_id=UUID(cell_raw),
        artifact_id=UUID(artifact_raw),
        version_num=int(version_raw) if version_raw is not None else None,
    )


class ArtifactResolver:
    """Resolve citeable URLs inside the caller's tenant cell."""

    def __init__(
        self,
        artifact_repo: ArtifactRepository,
        yjs_repo: YjsRepository,
        s3_service: S3AssetService,
    ) -> None:
        self._artifact_repo = artifact_repo
        self._yjs_repo = yjs_repo
        self._s3_service = s3_service

    async def resolve(self, url: str, *, current_cell_id: UUID) -> ResolvedArtifact:
        parsed = parse_artifact_url(url)

        # Cell mismatch is indistinguishable from not-found — 404, no oracle.
        if parsed.cell_id != current_cell_id:
            raise ArtifactNotFound(url)

        artifact = await self._artifact_repo.get(parsed.artifact_id, cell_id=current_cell_id)
        if artifact is None:
            raise ArtifactNotFound(url)

        version_num = parsed.version_num
        if version_num is None:
            if artifact.current_version_num < 1:
                raise ArtifactVersionNotFound(url)  # head with zero commits
            version_num = artifact.current_version_num

        version = await self._artifact_repo.get_version(
            parsed.artifact_id, version_num, cell_id=current_cell_id
        )
        if version is None:
            raise ArtifactVersionNotFound(url, version_num)

        content_inline: dict[str, object] | None = None
        download_url: str | None = None
        yjs_state_base64: str | None = None

        if version.storage_kind == "inline":
            content_inline = version.content_inline
        elif version.storage_kind == "s3":
            assert version.s3_object_id is not None  # XOR CHECK guarantees it
            download_url = await self._s3_service.download_url(
                cell_id=current_cell_id, s3_object_id=version.s3_object_id
            )
        else:  # yjs_snapshot — the XOR CHECK admits no other kind
            assert version.yjs_snapshot_id is not None
            snapshot = await self._yjs_repo.get_snapshot(
                version.yjs_snapshot_id, cell_id=current_cell_id
            )
            if snapshot is None:  # defensive: FK makes this unreachable
                raise ArtifactVersionNotFound(url, version_num)
            yjs_state_base64 = base64.b64encode(snapshot.state).decode("ascii")

        return ResolvedArtifact(
            artifact_id=artifact.id,
            cell_id=artifact.cell_id,
            artifact_type=artifact.artifact_type,
            title=artifact.title,
            version_num=version_num,
            storage_kind=version.storage_kind,
            byte_size=version.byte_size,
            content_hash_sha256=version.content_hash_sha256,
            content_inline=content_inline,
            download_url=download_url,
            yjs_state_base64=yjs_state_base64,
        )
