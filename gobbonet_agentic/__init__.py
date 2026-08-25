"""gobbonet-agentic — run one GobboNet campaign where the harness keeps the notes.

    from gobbonet_agentic import Campaign, Harness

    campaign = Campaign(
        name="my_campaign",
        endpoint="http://localhost:8080",
        harness=Harness(notes_dir="/tmp/notes")
    )
    result = campaign.run()
    print(result.notes_path)    # path to the notes file

Part of the `aw` family. A standalone harness that orchestrates a single campaign
autonomously, recording all decisions and outcomes without manual intervention.
"""

from .engine import Campaign, CampaignResult, Harness
from .notes import Notes

__version__ = "0.1.0"
__all__ = ["Campaign", "Harness", "CampaignResult", "Notes"]
