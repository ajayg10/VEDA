from pathlib import Path
from datetime import datetime
import uuid


class WorkspaceManager:

    def __init__(self, root="workspaces"):
        self.root = Path(root)
        self.root.mkdir(exist_ok=True)

    def create(self, user_id="default"):

        workspace = (
            self.root
            / user_id
            / f"{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}"
        )

        workspace.mkdir(parents=True)

        return workspace