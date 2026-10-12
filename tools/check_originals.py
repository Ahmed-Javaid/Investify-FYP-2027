"""Check the protected source snapshot without changing any original file."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / "evidence/original_files.sha256.json").read_text())
changed = []
for entry in manifest["files"]:
    path = Path(manifest["roots"][entry["origin"]]) / entry["path"]
    if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
        changed.append(str(path))
result = {
    "checked_utc": datetime.now(timezone.utc).isoformat(),
    "files_checked": len(manifest["files"]), "changed_originals": changed, "passed": not changed,
}
(ROOT / "evidence/originals_preservation_check.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(f"Checked {len(manifest['files'])} original files; changes: {len(changed)}")
raise SystemExit(1 if changed else 0)
