from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import threading
from typing import Any, Mapping, TextIO


class JsonlCheckpoint:
    """Append run-bound events durably without entering the public output pair."""

    def __init__(self, path: Path, run_fingerprint: str) -> None:
        self.path = path
        self.run_fingerprint = run_fingerprint
        self._handle: TextIO | None = None
        self._local = threading.local()
        self._write_lock = threading.Lock()

    def __enter__(self) -> JsonlCheckpoint:
        parent_created = not self.path.parent.exists()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self.path.parent, 0o700)
        created = not self.path.exists()
        self._handle = self.path.open("a", encoding="utf-8")
        os.chmod(self.path, 0o600)
        try:
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._validate_existing()
        except Exception:
            self._handle.close()
            self._handle = None
            raise
        if parent_created:
            self._fsync_directory(self.path.parent.parent)
        if created:
            self._fsync_directory(self.path.parent)
        return self

    def __exit__(self, *_args: object) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None

    def __call__(self, event: Mapping[str, Any]) -> None:
        if self._handle is None:
            raise RuntimeError("checkpoint writer is not open")
        payload = {
            **dict(event),
            "run_fingerprint": self.run_fingerprint,
            "attempt": getattr(self._local, "attempt", None),
        }
        try:
            with self._write_lock:
                self._handle.write(
                    json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
                    + "\n"
                )
                self._handle.flush()
                os.fsync(self._handle.fileno())
        except OSError as exc:
            raise CheckpointWriteError(f"failed to persist checkpoint: {self.path}") from exc

    def set_attempt(self, attempt: int | None) -> None:
        self._local.attempt = attempt

    def _validate_existing(self) -> None:
        if not self.path.exists():
            return
        raw = self.path.read_bytes()
        lines = raw.splitlines(keepends=True)
        consumed = 0
        for line_number, encoded in enumerate(lines, start=1):
            complete = encoded.endswith((b"\n", b"\r"))
            try:
                line = encoded.decode("utf-8")
                event = json.loads(line) if line.strip() else None
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                if line_number == len(lines) and not complete:
                    with self.path.open("r+b") as handle:
                        handle.truncate(consumed)
                        handle.flush()
                        os.fsync(handle.fileno())
                    return
                raise ValueError(
                    f"invalid checkpoint JSON at line {line_number}: {self.path}"
                ) from exc
            consumed += len(encoded)
            if event is None:
                continue
            if not isinstance(event, Mapping):
                raise ValueError(
                    f"checkpoint event at line {line_number} is not an object: {self.path}"
                )
            if event.get("run_fingerprint") != self.run_fingerprint:
                raise ValueError("checkpoint belongs to a different run manifest")
        if lines and not lines[-1].endswith((b"\n", b"\r")):
            if self._handle is None:
                raise RuntimeError("checkpoint writer is not open")
            self._handle.write("\n")
            self._handle.flush()
            os.fsync(self._handle.fileno())

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        directory = os.open(path, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)


class CheckpointWriteError(RuntimeError):
    pass
