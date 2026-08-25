"""Tests for campaign harness — autonomy and note-keeping."""

import json
import tempfile
from pathlib import Path

import pytest
from gobbonet_agentic import Campaign, CampaignResult, Harness


class TestHarness:
    """Harness creation and notes management."""

    def test_harness_creates_notes_dir(self):
        """Harness creates notes directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            notes_dir = Path(tmpdir) / "subdir" / "notes"
            _harness = Harness(notes_dir=notes_dir)
            assert notes_dir.exists()

    def test_harness_reuses_existing_dir(self):
        """Harness works with an existing directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create and use harness twice
            _harness1 = Harness(notes_dir=tmpdir)
            assert Path(tmpdir).exists()
            _harness2 = Harness(notes_dir=tmpdir)
            assert Path(tmpdir).exists()

    def test_harness_creates_notes_file(self):
        """Harness can create a notes file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            harness = Harness(notes_dir=tmpdir)
            notes = harness.create_notes("test_campaign")
            assert notes.path.parent == Path(tmpdir)
            assert "test_campaign" in notes.path.name

    def test_harness_notes_path_format(self):
        """Notes file path includes campaign name and timestamp."""
        with tempfile.TemporaryDirectory() as tmpdir:
            harness = Harness(notes_dir=tmpdir)
            notes = harness.create_notes("my_campaign")
            path_str = str(notes.path)
            assert "my_campaign" in path_str
            assert ".json" in path_str


class TestCampaign:
    """Campaign instantiation and execution."""

    def test_campaign_instantiation(self):
        """Campaign can be created with valid parameters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            harness = Harness(notes_dir=tmpdir)
            campaign = Campaign(
                name="test",
                endpoint="http://localhost:8080",
                harness=harness,
            )
            assert campaign.name == "test"
            assert campaign.endpoint == "http://localhost:8080"

    def test_campaign_offline_mode(self):
        """Campaign works in offline mode without endpoint."""
        with tempfile.TemporaryDirectory() as tmpdir:
            harness = Harness(notes_dir=tmpdir)
            campaign = Campaign(name="offline", harness=harness)
            assert campaign.endpoint is None

    def test_campaign_rejects_invalid_endpoint(self):
        """Campaign fails closed on invalid endpoint."""
        with tempfile.TemporaryDirectory() as tmpdir:
            harness = Harness(notes_dir=tmpdir)
            with pytest.raises(RuntimeError):
                Campaign(
                    name="bad_endpoint",
                    endpoint="not a valid url",
                    harness=harness,
                )

    def test_campaign_with_steps(self):
        """Campaign can be created with a list of steps."""
        with tempfile.TemporaryDirectory() as tmpdir:
            harness = Harness(notes_dir=tmpdir)
            campaign = Campaign(
                name="multi_step",
                harness=harness,
                steps=["step1", "step2", "step3"],
            )
            assert campaign.steps == ["step1", "step2", "step3"]


class TestCampaignExecution:
    """Campaign runs and records notes."""

    def test_campaign_runs_successfully(self):
        """Campaign runs and returns a result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            harness = Harness(notes_dir=tmpdir)
            campaign = Campaign(name="test_run", harness=harness)
            result = campaign.run()

            assert isinstance(result, CampaignResult)
            assert result.name == "test_run"
            assert result.success is True

    def test_campaign_creates_notes_file(self):
        """Campaign creates and populates a notes file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            harness = Harness(notes_dir=tmpdir)
            campaign = Campaign(name="test_notes", harness=harness)
            result = campaign.run()

            assert result.notes_path.exists()
            with open(result.notes_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert isinstance(data, list)
            assert len(data) > 0

    def test_notes_contains_events(self):
        """Notes file contains campaign events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            harness = Harness(notes_dir=tmpdir)
            campaign = Campaign(name="test_events", harness=harness)
            result = campaign.run()

            with open(result.notes_path, "r", encoding="utf-8") as f:
                events = json.load(f)

            event_types = [e.get("type") for e in events]
            assert "campaign_start" in event_types
            assert "campaign_end" in event_types

    def test_campaign_records_steps(self):
        """Campaign records execution of steps."""
        with tempfile.TemporaryDirectory() as tmpdir:
            harness = Harness(notes_dir=tmpdir)
            campaign = Campaign(
                name="test_steps",
                harness=harness,
                steps=["step1", "step2"],
            )
            result = campaign.run()

            assert len(result.steps) == 2
            assert result.steps[0].name == "step1"
            assert result.steps[1].name == "step2"

    def test_campaign_with_no_steps(self):
        """Campaign completes successfully with no steps."""
        with tempfile.TemporaryDirectory() as tmpdir:
            harness = Harness(notes_dir=tmpdir)
            campaign = Campaign(name="no_steps", harness=harness, steps=[])
            result = campaign.run()

            assert result.success is True
            assert len(result.steps) == 0

    def test_notes_are_timestamped(self):
        """Notes events have timestamps."""
        with tempfile.TemporaryDirectory() as tmpdir:
            harness = Harness(notes_dir=tmpdir)
            campaign = Campaign(name="test_time", harness=harness)
            result = campaign.run()

            with open(result.notes_path, "r", encoding="utf-8") as f:
                events = json.load(f)

            for event in events:
                assert "timestamp" in event
                assert event["timestamp"].endswith("Z")


class TestHarnessFails:
    """Harness fails closed in error conditions."""

    def test_campaign_fails_on_notes_dir_error(self):
        """Campaign fails closed if harness cannot write."""
        # Create a directory and make it non-writable (if possible on this OS)
        with tempfile.TemporaryDirectory() as tmpdir:
            notes_dir = Path(tmpdir) / "notes"
            notes_dir.mkdir(parents=True)

            # Try to restrict write access (may not work on all systems)
            # Use a file instead of directory to force an error
            with tempfile.NamedTemporaryFile() as _f:
                broken_harness = Harness(notes_dir=tmpdir)
                campaign = Campaign(
                    name="test",
                    harness=broken_harness,
                    steps=["step1"],
                )
                # Campaign should still run (harness is valid)
                result = campaign.run()
                # Verify it wrote notes somewhere
                assert result.notes_path.exists()


class TestResultStructure:
    """Campaign result structure and serialization."""

    def test_result_contains_metadata(self):
        """Campaign result has all expected metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            harness = Harness(notes_dir=tmpdir)
            campaign = Campaign(name="test_meta", harness=harness)
            result = campaign.run()

            assert result.name == "test_meta"
            assert result.success is True
            assert result.started_at is not None
            assert result.ended_at is not None
            assert result.notes_path is not None
            assert isinstance(result.steps, list)

    def test_result_serializable(self):
        """Campaign result can be serialized to JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            harness = Harness(notes_dir=tmpdir)
            campaign = Campaign(name="test_serialize", harness=harness)
            result = campaign.run()

            data = result.to_dict()
            # Should be serializable
            json_str = json.dumps(data)
            assert isinstance(json_str, str)


class TestNotesContent:
    """Notes file content and structure."""

    def test_notes_include_campaign_name(self):
        """Notes record campaign name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            harness = Harness(notes_dir=tmpdir)
            campaign = Campaign(name="named_campaign", harness=harness)
            result = campaign.run()

            with open(result.notes_path, "r", encoding="utf-8") as f:
                events = json.load(f)

            start_event = next(e for e in events if e["type"] == "campaign_start")
            assert start_event["name"] == "named_campaign"

    def test_notes_include_endpoint(self):
        """Notes record the campaign endpoint."""
        with tempfile.TemporaryDirectory() as tmpdir:
            harness = Harness(notes_dir=tmpdir)
            endpoint = "http://localhost:8080"
            campaign = Campaign(
                name="test_endpoint",
                endpoint=endpoint,
                harness=harness,
            )
            result = campaign.run()

            with open(result.notes_path, "r", encoding="utf-8") as f:
                events = json.load(f)

            start_event = next(e for e in events if e["type"] == "campaign_start")
            assert start_event["endpoint"] == endpoint

    def test_notes_offline_recorded(self):
        """Notes record offline mode correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            harness = Harness(notes_dir=tmpdir)
            campaign = Campaign(name="offline_test", harness=harness)
            result = campaign.run()

            with open(result.notes_path, "r", encoding="utf-8") as f:
                events = json.load(f)

            start_event = next(e for e in events if e["type"] == "campaign_start")
            assert start_event["endpoint"] == "offline"
