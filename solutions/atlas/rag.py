"""LAB 3 - Exercise 3.3: chunking, indexing and retrieval for the policy manual (a RAG pipeline).

Course lesson 3.3. A RAG pipeline is several independent decisions, each able to fail SILENTLY:
  chunk  - follow the SOURCE STRUCTURE (one numbered rule per chunk), not a fixed token size
  index  - store metadata (loan type, jurisdiction, effective dates) on every chunk
  retrieve - FILTER on exact metadata first, THEN rank; exact thresholds favour keyword ranking (BM25)
  keep fresh - a STALE INDEX (source updated, index not rebuilt) or MISMATCHED RANKER/EMBEDDINGS
             (query side upgraded, index built by the old one) both return confident wrong answers
             with no error anywhere. PolicyIndex records fingerprints and the ranker version so
             staleness is DETECTABLE.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

from . import config

RANKER_VERSION = "bm25-v1"  # change this and every existing index is stale (like a new embedding model)


@dataclass
class Chunk:
    id: str                    # "POL-EQUIP-v3-1.2" = policy_id-v<version>-<section>
    policy_id: str
    version: int
    section: str
    heading_path: str          # "Equipment Financing Policy (v3) > 1. Eligibility > 1.2 Debt service coverage ratio"
    text: str
    loan_type: str             # product or "all"
    jurisdictions: list[str] = field(default_factory=list)
    effective_from: date = date(1900, 1, 1)
    effective_to: date | None = None


# ------------------------------------------------------------------ given helpers


def read_front_matter(path: Path) -> tuple[dict, str]:
    """Split a policy file into (metadata, body). Tiny YAML subset: scalars, [a, b] lists, null, dates, ints."""
    _, meta_text, body = path.read_text().split("---", 2)
    meta: dict = {}
    for line in meta_text.strip().splitlines():
        key, value = (part.strip() for part in line.split(":", 1))
        if value.startswith("[") and value.endswith("]"):
            meta[key] = [v.strip() for v in value[1:-1].split(",") if v.strip()]
        elif value == "null":
            meta[key] = None
        elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            meta[key] = date.fromisoformat(value)
        elif value.isdigit():
            meta[key] = int(value)
        else:
            meta[key] = value
    return meta, body.strip()


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def bm25_scores(query: str, docs: list[str], k1: float = 1.5, b: float = 0.75) -> list[float]:
    """Keyword relevance. Good at exact terms and thresholds ("DSCR", "1.25"); blind to paraphrase."""
    tokenized = [tokenize(d) for d in docs]
    if not tokenized:
        return []
    avg = sum(len(t) for t in tokenized) / len(tokenized) or 1.0
    df = Counter(term for toks in tokenized for term in set(toks))
    n = len(tokenized)
    scores = []
    for toks in tokenized:
        tf = Counter(toks)
        s = 0.0
        for term in set(tokenize(query)):
            if term in tf:
                idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
                s += idf * tf[term] * (k1 + 1) / (tf[term] + k1 * (1 - b + b * len(toks) / avg))
        scores.append(s)
    return scores


def format_chunks(chunks: list[Chunk]) -> str:
    """How chunks are shown to Claude: tagged, with an id it can cite."""
    return "\n\n".join(f'<policy_chunk id="{c.id}" source="{c.heading_path}">\n{c.text}\n</policy_chunk>' for c in chunks)


def file_fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


# ------------------------------------------------------------------ LAB 3 TODOs: chunking + filtering


def chunk_policy(path: Path) -> list[Chunk]:
    """One Chunk per '### ' subsection.
    heading_path = "<title> (v<version>) > <current ## heading> > <### heading>" (headings without #'s)
    section = first word of the ### heading ("1.2"); text = ### heading line (no #'s) + "\\n" + body, stripped
    id = f"{policy_id}-v{version}-{section}"; metadata from read_front_matter."""
    meta, body = read_front_matter(path)
    title = f"{meta['title']} (v{meta['version']})"
    chunks: list[Chunk] = []
    h2, h3, lines = "", None, []

    def flush() -> None:
        if h3 is None:
            return
        section = h3.split()[0]
        chunks.append(Chunk(id=f"{meta['policy_id']}-v{meta['version']}-{section}", policy_id=meta["policy_id"],
                            version=meta["version"], section=section, heading_path=f"{title} > {h2} > {h3}",
                            text=(h3 + "\n" + "\n".join(lines)).strip(), loan_type=meta["loan_type"],
                            jurisdictions=list(meta.get("jurisdictions") or []), effective_from=meta["effective_from"],
                            effective_to=meta.get("effective_to")))

    for line in body.splitlines():
        if line.startswith("### "):
            flush()
            h3, lines = line[4:].strip(), []
        elif line.startswith("## "):
            flush()
            h2, h3, lines = line[3:].strip(), None, []
        elif h3 is not None:
            lines.append(line)
    flush()
    return chunks


def is_applicable(chunk: Chunk, loan_type: str, jurisdiction: str, as_of: date) -> bool:
    """Metadata filter: product matches (or "all"), jurisdiction listed, in force on as_of
    (effective_from <= as_of, and effective_to is None or as_of <= effective_to)."""
    return (chunk.loan_type in (loan_type, "all") and jurisdiction in chunk.jurisdictions
            and chunk.effective_from <= as_of and (chunk.effective_to is None or as_of <= chunk.effective_to))


# ------------------------------------------------------------------ LAB 3 TODOs: the index and its freshness


@dataclass
class PolicyIndex:
    chunks: list[Chunk]
    fingerprints: dict[str, str]     # file name -> file_fingerprint
    ranker_version: str
    built_at: str

    @classmethod
    def build(cls, folder: Path) -> "PolicyIndex":
        """Chunk every *.md in folder (sorted), fingerprint each file, stamp RANKER_VERSION and the
        current UTC time (isoformat)."""
        chunks, prints = [], {}
        for path in sorted(Path(folder).glob("*.md")):
            chunks.extend(chunk_policy(path))
            prints[path.name] = file_fingerprint(path)
        return cls(chunks, prints, RANKER_VERSION, datetime.now(timezone.utc).isoformat())

    def is_stale(self, folder: Path, ranker_version: str = RANKER_VERSION) -> bool:
        """True when the index no longer matches its sources: any file added, removed or changed
        (compare fingerprints), OR the ranker version differs (the 'mismatched embeddings' failure)."""
        current = {p.name: file_fingerprint(p) for p in sorted(Path(folder).glob("*.md"))}
        return current != self.fingerprints or ranker_version != self.ranker_version

    # -- given: persistence
    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"fingerprints": self.fingerprints, "ranker_version": self.ranker_version,
                                    "built_at": self.built_at, "chunks": [asdict(c) for c in self.chunks]}, default=str))

    @classmethod
    def load(cls, path: Path) -> "PolicyIndex":
        raw = json.loads(path.read_text())
        chunks = []
        for c in raw["chunks"]:
            c["effective_from"] = date.fromisoformat(c["effective_from"])
            c["effective_to"] = date.fromisoformat(c["effective_to"]) if c["effective_to"] else None
            chunks.append(Chunk(**c))
        return cls(chunks, raw["fingerprints"], raw["ranker_version"], raw["built_at"])


def index_path() -> Path:
    return config.RUNS / "policy_index.json"


def log_index_build(folder: Path, reason: str) -> None:
    log = config.RUNS / "index_build.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} built index from {folder} ({reason})\n")


def get_index() -> PolicyIndex:
    """Given. Load the persisted index, or build it the first time. NOTE: it does not check
    staleness on load - rebuilding is a deployment step (refresh_index). Lab 8 is about what happens
    when that step is skipped."""
    path = index_path()
    if path.exists():
        return PolicyIndex.load(path)
    return refresh_index("first build")


def refresh_index(reason: str = "manual refresh") -> PolicyIndex:
    """Given. Rebuild from config.policy_dir(), persist it, and log the build."""
    folder = config.policy_dir()
    index = PolicyIndex.build(folder)
    index.save(index_path())
    log_index_build(folder, reason)
    return index


def retrieve(query: str, loan_type: str, jurisdiction: str, as_of: date, k: int = 4,
             index: PolicyIndex | None = None) -> list[Chunk]:
    """FILTER with is_applicable, THEN rank survivors with bm25_scores over heading_path + " " + text;
    drop zero scores; highest first; at most k. Use get_index() when no index is passed."""
    index = index or get_index()
    candidates = [c for c in index.chunks if is_applicable(c, loan_type, jurisdiction, as_of)]
    scores = bm25_scores(query, [f"{c.heading_path} {c.text}" for c in candidates])
    ranked = sorted(zip(scores, candidates), key=lambda pair: pair[0], reverse=True)
    return [c for s, c in ranked if s > 0][:k]
