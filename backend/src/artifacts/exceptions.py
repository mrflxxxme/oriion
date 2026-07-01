"""Artifacts bounded-context exceptions.

Carry ``code`` / ``status_code`` / ``title`` mirroring ``memory.exceptions`` so
the RFC-7807 handler in ``src.main`` and generic failure handlers
(``getattr(exc, "code", ...)``) treat them uniformly.

Resolver semantics per ADR-038: cell-mismatch and any not-found are the SAME
404 (no existence oracle across cells); a malformed ``artifact://`` URL is 422.
"""

from __future__ import annotations


class ArtifactsError(Exception):
    """Base for all artifacts-domain errors."""

    code: str = "artifacts.error"
    status_code: int = 500
    title: str = "Artifacts error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail
        super().__init__(detail or self.title)


class ArtifactNotFound(ArtifactsError):
    """Envelope id absent, soft-deleted, or belongs to another cell (404)."""

    code = "artifacts.not_found"
    status_code = 404
    title = "Artifact not found"

    def __init__(self, artifact_ref: str) -> None:
        super().__init__(f"artifact not found: {artifact_ref}")


class ArtifactVersionNotFound(ArtifactsError):
    """Requested version_num absent for the artifact — or head with 0 versions (404)."""

    code = "artifacts.version_not_found"
    status_code = 404
    title = "Artifact version not found"

    def __init__(self, artifact_ref: str, version_num: int | None = None) -> None:
        suffix = f"/v{version_num}" if version_num is not None else " (no committed versions)"
        super().__init__(f"artifact version not found: {artifact_ref}{suffix}")


class MalformedArtifactUrl(ArtifactsError):
    """The artifact:// URL does not match the strict grammar (422)."""

    code = "artifacts.malformed_url"
    status_code = 422
    title = "Malformed artifact URL"

    def __init__(self, url: str) -> None:
        # Do not echo arbitrarily long garbage back — truncate defensively.
        super().__init__(f"malformed artifact url: {url[:200]}")


class YjsDocumentNotFound(ArtifactsError):
    """No live Yjs document for the artifact (404)."""

    code = "artifacts.yjs_document_not_found"
    status_code = 404
    title = "Yjs document not found"

    def __init__(self, ref: str) -> None:
        super().__init__(f"yjs document not found: {ref}")


class InvalidYjsUpdate(ArtifactsError):
    """The submitted bytes are not a valid Yjs update / base64 payload (422)."""

    code = "artifacts.invalid_yjs_update"
    status_code = 422
    title = "Invalid Yjs update"


class YjsDocumentAlreadyExists(ArtifactsError):
    """The artifact already has a live Yjs document (409)."""

    code = "artifacts.yjs_document_exists"
    status_code = 409
    title = "Yjs document already exists"

    def __init__(self, artifact_ref: str) -> None:
        super().__init__(f"yjs document already exists for artifact: {artifact_ref}")


class S3ObjectNotFound(ArtifactsError):
    """No s3_objects row for the given id/key in this cell (404)."""

    code = "artifacts.s3_object_not_found"
    status_code = 404
    title = "S3 object not found"

    def __init__(self, ref: str) -> None:
        super().__init__(f"s3 object not found: {ref}")


class S3KeyAlreadyReserved(ArtifactsError):
    """UNIQUE(bucket, s3_key) rejected the presign reservation (409)."""

    code = "artifacts.s3_key_reserved"
    status_code = 409
    title = "S3 key already reserved"

    def __init__(self, s3_key: str) -> None:
        super().__init__(f"s3 key already reserved: {s3_key}")


class UploadNotVerified(ArtifactsError):
    """`complete` could not verify the uploaded object (409).

    Either the object is missing in the bucket, or the s3_objects row is not
    in ``pending`` state anymore (double-complete).
    """

    code = "artifacts.upload_not_verified"
    status_code = 409
    title = "Upload not verified"


class ArtifactTypeMismatch(ArtifactsError):
    """Operation not valid for this artifact_type (409) — e.g. Yjs on 'asset'."""

    code = "artifacts.type_mismatch"
    status_code = 409
    title = "Operation not valid for artifact type"


class VersionConflict(ArtifactsError):
    """UNIQUE(artifact_id, version_num) still violated after retries (409)."""

    code = "artifacts.version_conflict"
    status_code = 409
    title = "Version number conflict"

    def __init__(self, artifact_ref: str) -> None:
        super().__init__(f"version conflict persisted after retries: {artifact_ref}")
