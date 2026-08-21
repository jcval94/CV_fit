from __future__ import annotations

import argparse
import json
from pathlib import Path

from rag.evidence import retrieve_evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="Retrieve public-safe professional evidence chunks.")
    parser.add_argument("query")
    parser.add_argument("--state-dir", default="rag_state")
    parser.add_argument("--top-k", type=int, default=8)
    args = parser.parse_args()
    index_path = Path(args.state_dir) / "lexical_index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    hits = retrieve_evidence(index, args.query, top_k=args.top_k)
    print(json.dumps(hits, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
