# gobbonet-agentic

Run one GobboNet campaign where the harness, not the human, keeps the notes.

```bash
pip install gobbonet-agentic
```

```python
from gobbonet_agentic import Campaign, Harness

# Create a harness that keeps notes automatically
harness = Harness(notes_dir="/tmp/campaign_notes")

# Define and run a campaign
campaign = Campaign(
    name="my_campaign",
    endpoint="http://localhost:8080",  # optional
    harness=harness,
    steps=["discover", "analyze", "decide"],
)

result = campaign.run()
print(f"Campaign: {result.name}")
print(f"Success: {result.success}")
print(f"Notes: {result.notes_path}")
```

```bash
# Run a campaign from the command line
gobbonet-agentic \
  --name my_campaign \
  --endpoint http://localhost:8080 \
  --notes-dir ./notes \
  --steps step1 step2 step3

# Offline mode (no endpoint)
gobbonet-agentic \
  --name offline_campaign \
  --notes-dir ./notes

# Output as JSON
gobbonet-agentic \
  --name my_campaign \
  --json

# Self-test
gobbonet-agentic --self-test
```

## The harness

The harness orchestrates a campaign autonomously from start to finish, recording:
- Campaign start/end with timestamps
- Each step's execution and outcome
- Errors and decisions made
- All events into a structured JSON notes file

Fails closed: if notes cannot be written or a step fails, the campaign stops
rather than continuing silently with a broken log.

## Design

This brick answers one question: **Run one complete campaign where every decision
and outcome is recorded automatically.** It works standalone — install, run, get
notes. No manual intervention needed.

- **Autonomous** — no human note-taking, the harness records everything
- **Offline capable** — works without an external service
- **Structured notes** — timestamped JSON events, not prose logs
- **Fail-closed** — cannot proceed if recording fails

## Offline mode

If no endpoint is provided, the campaign runs in offline mode. The harness still
keeps notes but doesn't attempt external service calls:

```python
campaign = Campaign(
    name="standalone_campaign",
    harness=harness,
    # no endpoint, offline mode
)
result = campaign.run()
```

## Tests

```bash
pip install -e ".[dev]" && pytest
```

Tests verify:
- Harness creates and manages notes directories
- Campaign records all events
- Notes files contain valid JSON
- Offline mode works
- Fail-closed behavior on errors

## Exit codes

From the CLI:

- `0` — campaign completed successfully
- `1` — campaign failed during execution
- `2` — could not initialize or malformed arguments

## Where it sits

Part of the `aw` family — standalone tools that replace something you would
otherwise have to trust with something you can check.

| package | question |
|---|---|
| `gobbonet-agentic` | **how do we know what the harness did?** |
| [`awm`](https://github.com/Aitherium/awm) | what does the agent remember? |
| [`awgit`](https://github.com/Aitherium/awgit) | who else is editing this right now? |

Apache-2.0.
