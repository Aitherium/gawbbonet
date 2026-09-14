"""Notes file management — structured, durable campaign logs."""

from __future__ import annotations

import contextlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class Notes:
    """Structured notes file for a campaign.

    Records all campaign events in a JSON format that can be parsed,
    queried, and replayed. Fails closed: write errors propagate rather
    than silently degrading.
    """

    def __init__(self, path: Path | str):
        """Initialize notes file.

        Args:
            path: where the notes file will be written.
        """
        self.path = Path(path)
        self._events: list[dict[str, Any]] = []

    def record_campaign_start(self, name: str, endpoint: str) -> None:
        """Record campaign start event."""
        self._append_event(
            "campaign_start",
            {
                "name": name,
                "endpoint": endpoint,
            },
        )

    def record_campaign_end(self, success: bool, step_count: int) -> None:
        """Record campaign end event."""
        self._append_event(
            "campaign_end",
            {
                "success": success,
                "step_count": step_count,
            },
        )

    def record_step_start(self, step_name: str) -> None:
        """Record step start event."""
        self._append_event(
            "step_start",
            {
                "step": step_name,
            },
        )

    def record_step_end(
        self, step_name: str, success: bool, error: Optional[str] = None
    ) -> None:
        """Record step end event."""
        event_data: dict[str, Any] = {
            "step": step_name,
            "success": success,
        }
        if error:
            event_data["error"] = error
        self._append_event("step_end", event_data)

    def record_info(self, message: str) -> None:
        """Record an informational message."""
        self._append_event(
            "info",
            {
                "message": message,
            },
        )

    def record_decision(self, decision: str, data: dict) -> None:
        """Record a decision made during the campaign."""
        self._append_event(
            "decision",
            {
                "decision": decision,
                "data": data,
            },
        )

    def _append_event(self, event_type: str, data: dict) -> None:
        """Append an event to the log."""
        timestamp = datetime.utcnow().isoformat() + "Z"
        event = {
            "timestamp": timestamp,
            "type": event_type,
            **data,
        }
        self._events.append(event)

    def save(self) -> None:
        """Write notes to disk.

        Fails closed: raises OSError if write fails.
        """
        try:
            # Ensure parent directory exists
            self.path.parent.mkdir(parents=True, exist_ok=True)

            # Write atomically: write to temp, then rename
            temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
            try:
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(self._events, f, indent=2, ensure_ascii=False)
                temp_path.replace(self.path)
            except (OSError, IOError) as temp_error:
                # Clean up temp file on failure; ignore cleanup errors
                with contextlib.suppress(Exception):
                    temp_path.unlink(missing_ok=True)
                raise temp_error
        except (OSError, IOError) as e:
            raise OSError(f"Cannot save notes to {self.path}: {e}") from e

    def to_dict(self) -> dict:
        """Get notes as a dictionary."""
        return {
            "path": str(self.path),
            "event_count": len(self._events),
            "events": self._events,
        }
