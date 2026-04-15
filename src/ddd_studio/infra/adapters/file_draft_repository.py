"""FileDraftRepository — file-based implementation of DraftRepositoryPort.

Stores each draft as an individual JSON file in a drafts/ directory,
with a lightweight manifest.json index for fast sidebar rendering.
Uses atomic writes (temp file + os.replace) to prevent partial state.
"""

from __future__ import annotations

import json
import os
import tempfile

from domain.models.draft import (
    Draft,
    DraftManifest,
    DraftManifestEntry,
)


class FileDraftRepository:
    """File-based adapter for DraftRepositoryPort."""

    def __init__(self, drafts_dir: str = "drafts") -> None:
        self._dir = drafts_dir
        os.makedirs(self._dir, exist_ok=True)
        self._manifest_path = os.path.join(self._dir, "manifest.json")
        self._ensure_manifest()

    # ── Public API ────────────────────────────────────────────────────

    def save(self, draft: Draft) -> None:
        """Persist a draft record (create or update)."""
        # Write draft file atomically
        draft_path = self._draft_path(draft.id)
        self._atomic_write(draft_path, draft.model_dump_json(indent=2))

        # Update manifest
        manifest = self._load_manifest()
        # Remove existing entry if updating
        manifest.entries = [e for e in manifest.entries if e.id != draft.id]
        manifest.entries.append(self._entry_from_draft(draft))
        self._save_manifest(manifest)

    def load(self, draft_id: str) -> Draft | None:
        """Load a full draft by ID."""
        draft_path = self._draft_path(draft_id)
        if not os.path.exists(draft_path):
            return None
        with open(draft_path, encoding="utf-8") as f:
            return Draft.model_validate_json(f.read())

    def delete(self, draft_id: str) -> bool:
        """Delete a draft permanently."""
        draft_path = self._draft_path(draft_id)
        if not os.path.exists(draft_path):
            return False
        os.remove(draft_path)
        manifest = self._load_manifest()
        manifest.entries = [e for e in manifest.entries if e.id != draft_id]
        self._save_manifest(manifest)
        return True

    def list_entries(self, project_name: str | None = None) -> list[DraftManifestEntry]:
        """List draft entries, optionally filtered by project. Sorted by created_at desc."""
        manifest = self._load_manifest()
        entries = manifest.entries
        if project_name:
            entries = [e for e in entries if e.project_name == project_name]
        entries.sort(key=lambda e: e.created_at, reverse=True)
        return entries

    def find_by_generation_id(self, generation_id: str) -> Draft | None:
        """Find a draft by its generation_id."""
        manifest = self._load_manifest()
        for entry in manifest.entries:
            if entry.generation_id == generation_id:
                return self.load(entry.id)
        return None

    # ── Private helpers ───────────────────────────────────────────────

    def _draft_path(self, draft_id: str) -> str:
        return os.path.join(self._dir, f"{draft_id}.json")

    def _ensure_manifest(self) -> None:
        """Ensure manifest exists; rebuild from draft files if corrupted/missing."""
        if os.path.exists(self._manifest_path):
            try:
                self._load_manifest()
                self._reconcile()
                return
            except (json.JSONDecodeError, Exception):
                pass  # Fall through to rebuild

        # Rebuild from individual draft files
        self._rebuild_manifest()

    def _reconcile(self) -> None:
        """Reconcile manifest with actual files on disk."""
        manifest = self._load_manifest()
        manifest_ids = {e.id for e in manifest.entries}
        disk_ids = self._scan_draft_ids()

        changed = False

        # Remove orphan manifest entries (no file on disk)
        orphans = manifest_ids - disk_ids
        if orphans:
            manifest.entries = [e for e in manifest.entries if e.id not in orphans]
            changed = True

        # Add missing entries (file on disk, not in manifest)
        missing = disk_ids - manifest_ids
        for draft_id in missing:
            draft = self.load(draft_id)
            if draft:
                manifest.entries.append(self._entry_from_draft(draft))
                changed = True

        if changed:
            self._save_manifest(manifest)

    def _rebuild_manifest(self) -> None:
        """Rebuild manifest from scratch by reading all draft files."""
        entries: list[DraftManifestEntry] = []
        for draft_id in self._scan_draft_ids():
            draft_path = self._draft_path(draft_id)
            try:
                with open(draft_path, encoding="utf-8") as f:
                    draft = Draft.model_validate_json(f.read())
                entries.append(self._entry_from_draft(draft))
            except Exception:
                continue  # Skip corrupted files
        manifest = DraftManifest(entries=entries)
        self._save_manifest(manifest)

    def _scan_draft_ids(self) -> set[str]:
        """Scan the drafts directory for draft JSON files (excluding manifest)."""
        ids = set()
        for fname in os.listdir(self._dir):
            if fname.endswith(".json") and fname != "manifest.json":
                ids.add(fname[:-5])  # Strip .json
        return ids

    def _load_manifest(self) -> DraftManifest:
        with open(self._manifest_path, encoding="utf-8") as f:
            return DraftManifest.model_validate_json(f.read())

    def _save_manifest(self, manifest: DraftManifest) -> None:
        self._atomic_write(self._manifest_path, manifest.model_dump_json(indent=2))

    def _atomic_write(self, path: str, content: str) -> None:
        """Write content atomically using temp file + os.replace."""
        dir_name = os.path.dirname(path)
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, path)
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    @staticmethod
    def _entry_from_draft(draft: Draft) -> DraftManifestEntry:
        return DraftManifestEntry(
            id=draft.id,
            project_name=draft.project_name,
            generation_id=draft.generation_id,
            created_at=draft.created_at.isoformat(),
            updated_at=draft.updated_at.isoformat(),
            summary=draft.summary,
        )
