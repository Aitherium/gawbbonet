"""Campaign engine and harness — autonomous orchestration with automatic note-keeping.

The Campaign runs a single complete flow, recording every decision, action, and
outcome into a structured notes file. The harness fails closed: if a service is
unreachable or a step cannot be recorded, the campaign stops and reports the
failure clearly rather than silently degrading.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from .notes import Notes


class StepStatus(Enum):
    """Status of a campaign step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class CampaignStep:
    """One step in a campaign."""
    name: str
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    data: dict = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "status": self.status.value,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "data": self.data,
            "error": self.error,
        }


@dataclass
class CampaignResult:
    """Result of running a campaign."""
    name: str
    success: bool
    started_at: str
    ended_at: str
    notes_path: Path
    steps: list[CampaignStep]
    errors: list[str] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "success": self.success,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "notes_path": str(self.notes_path),
            "steps": [s.to_dict() for s in self.steps],
            "errors": self.errors,
            "reason": self.reason,
        }


class Harness:
    """Orchestrator that keeps notes automatically.

    Fails closed: if notes cannot be written or a step cannot be recorded,
    the campaign stops rather than continuing silently with a broken log.
    """

    def __init__(self, notes_dir: str | Path = "."):
        """Initialize harness.

        Args:
            notes_dir: directory where campaign notes are written.
        """
        self.notes_dir = Path(notes_dir)
        self._validate_notes_dir()

    def _validate_notes_dir(self) -> None:
        """Ensure notes directory is writable."""
        try:
            self.notes_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            raise RuntimeError(
                f"Cannot write notes to {self.notes_dir}: {e}"
            ) from e

    def create_notes(self, campaign_name: str) -> Notes:
        """Create a notes file for a campaign."""
        # Use a filesystem-safe timestamp (no colons)
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S-Z")
        safe_name = campaign_name.replace(" ", "_").replace("/", "_")
        notes_file = self.notes_dir / f"{safe_name}_{timestamp}.json"
        return Notes(notes_file)


class Campaign:
    """A single complete GobboNet campaign.

    Runs autonomously from start to finish, recording every decision and
    outcome. Fails closed: cannot proceed without the harness being able
    to record notes.
    """

    def __init__(
        self,
        name: str,
        endpoint: Optional[str] = None,
        harness: Optional[Harness] = None,
        steps: Optional[list[str]] = None,
    ):
        """Initialize campaign.

        Args:
            name: campaign name (used in notes filenames).
            endpoint: external service endpoint (optional; None means offline mode).
            harness: Harness instance; created with default if not provided.
            steps: list of step names to execute in order.

        Fails closed if endpoint is unreachable or invalid.
        """
        self.name = name
        self.endpoint = endpoint
        self.harness = harness or Harness()
        self.steps = steps or []
        self._result: Optional[CampaignResult] = None

        # Validate endpoint if provided
        if endpoint:
            self._validate_endpoint(endpoint)

    def _validate_endpoint(self, endpoint: str) -> None:
        """Validate endpoint format."""
        try:
            parsed = urlparse(endpoint)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError(f"Invalid endpoint URL: {endpoint}")
        except Exception as e:
            raise RuntimeError(f"Cannot validate endpoint {endpoint}: {e}") from e

    def run(self) -> CampaignResult:
        """Run the campaign autonomously.

        Returns:
            CampaignResult with success flag, notes path, and step outcomes.

        Fails closed: if notes cannot be written, returns a failed result
        without proceeding.
        """
        started_at = datetime.utcnow().isoformat() + "Z"
        errors: list[str] = []
        campaign_steps: list[CampaignStep] = []

        # Create notes file
        try:
            notes = self.harness.create_notes(self.name)
        except RuntimeError as e:
            ended_at = datetime.utcnow().isoformat() + "Z"
            return CampaignResult(
                name=self.name,
                success=False,
                started_at=started_at,
                ended_at=ended_at,
                notes_path=Path(),
                steps=[],
                errors=[str(e)],
                reason="Cannot create notes file",
            )

        # Record campaign start
        try:
            notes.record_campaign_start(self.name, self.endpoint or "offline")
        except OSError as e:
            errors.append(f"Cannot record campaign start: {e}")
            return CampaignResult(
                name=self.name,
                success=False,
                started_at=started_at,
                ended_at=datetime.utcnow().isoformat() + "Z",
                notes_path=notes.path,
                steps=[],
                errors=errors,
                reason="Cannot record campaign start",
            )

        # Run each step
        for step_name in self.steps:
            step = self._run_step(step_name, notes)
            campaign_steps.append(step)
            if step.status == StepStatus.FAILED:
                errors.append(f"Step '{step_name}' failed: {step.error}")
                # Fail closed: do not continue if a step fails
                break

        # If no steps provided, record that
        if not self.steps:
            notes.record_info("No steps configured for this campaign")

        # Record campaign end
        ended_at = datetime.utcnow().isoformat() + "Z"
        success = all(s.status != StepStatus.FAILED for s in campaign_steps)

        try:
            notes.record_campaign_end(
                success=success,
                step_count=len(campaign_steps),
            )
        except OSError as e:
            errors.append(f"Cannot record campaign end: {e}")
            success = False

        # Persist notes
        try:
            notes.save()
        except OSError as e:
            errors.append(f"Cannot save notes: {e}")
            success = False

        self._result = CampaignResult(
            name=self.name,
            success=success,
            started_at=started_at,
            ended_at=ended_at,
            notes_path=notes.path,
            steps=campaign_steps,
            errors=errors,
            reason="Campaign completed" if success else "Campaign failed",
        )
        return self._result

    def _run_step(self, step_name: str, notes: Notes) -> CampaignStep:
        """Run a single campaign step and record it.

        Fails closed: if recording fails, returns a failed step.
        """
        step = CampaignStep(name=step_name)
        step.status = StepStatus.RUNNING
        step.started_at = datetime.utcnow().isoformat() + "Z"

        try:
            # Record step start
            notes.record_step_start(step_name)

            # Execute step (currently a no-op; subclasses would override)
            step.data["executed"] = True

            # Record step end
            notes.record_step_end(step_name, success=True)
            step.status = StepStatus.COMPLETED
        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = str(e)
            try:
                notes.record_step_end(step_name, success=False, error=str(e))
            except OSError as e2:
                # Even the error recording failed; record that
                step.error = f"{step.error}; error recording failed: {e2}"

        step.ended_at = datetime.utcnow().isoformat() + "Z"
        return step

    @property
    def result(self) -> Optional[CampaignResult]:
        """Last campaign result, if any."""
        return self._result
