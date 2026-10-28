"""Rebuild the policy search index from data/policies (run after ANY policy change).

    python scripts/rebuild_index.py [--solution]
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "solutions" if "--solution" in sys.argv else ROOT))

from atlas import config, rag  # noqa: E402

index = rag.refresh_index("manual rebuild")
print(f"Indexed {len(index.chunks)} chunks from {len(index.fingerprints)} files in {config.policy_dir()}")
