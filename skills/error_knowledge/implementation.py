import json
import uuid
from pathlib import Path
from datetime import datetime

class SkillHandler:
    def __init__(self):
        self.errors_dir = Path("data/errors")
        self.errors_dir.mkdir(parents=True, exist_ok=True)

    def store_error(self, error: str) -> dict:
        error_id = str(uuid.uuid4())[:8]
        record = {
            "id": error_id,
            "error": error,
            "timestamp": datetime.now().isoformat(),
            "classified": self.classify_error(error)
        }
        with open(self.errors_dir / f"{error_id}.json", "w") as f:
            json.dump(record, f)
        return {"success": True, "error_id": error_id}

    def classify_error(self, error: str) -> dict:
        error_lower = error.lower()
        if "syntax" in error_lower:
            category = "syntax_error"
        elif "timeout" in error_lower:
            category = "timeout"
        else:
            category = "unknown"
        return {"category": category, "confidence": 0.7}
