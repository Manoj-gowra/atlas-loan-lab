"""Turn docs/LAB*.md into a structured course model for the lab UI.

The Markdown stays the source of truth. Nothing here is hand-copied: lessons, ideas, checks and exam traps
are parsed out of the lab guides, and files to open are the backticked paths (`atlas/design.py`) and symbols
(`design.needs_coordinator()`) in each lesson.

    python site/labmodel.py            # print the model as JSON
"""
import html
import json
import re
import sys
from pathlib import Path

if sys.version_info < (3, 10):
    sys.exit(f"The Atlas Loan Lab needs Python 3.10 or newer; this is {sys.version.split()[0]} ({sys.executable}).\n"
             "Activate the project venv first: source .venv/bin/activate")

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

PEOPLE = [
    ("Daniel Reyes", "Head of Commercial Lending"),
    ("Sam Ortiz", "Senior Loan Officer"),
    ("Raj Patel", "Chief Compliance Officer"),
    ("Lena Brooks", "Head of Cloud Platform"),
    ("Priya Shah", "Finance business partner"),
    ("Grace Okonkwo", "Credit Committee chair"),
]

LABELS = {"the idea": "idea", "practical": "practical", "check": "check", "exam trap": "trap"}
LABEL_RE = re.compile(r"^\*\*(The idea|Practical|Check|Exam trap)\*\*:?\s*(.*)$|^\*\*(Practical|Check|Exam trap):\*\*\s*(.*)$")
HEADING_RE = re.compile(r"^## (Lesson|Exercise|Case) ([\w.]+):\s*(.+)$|^## Lesson 0:\s*(.+)$")
FILE_RE = re.compile(r"^[\w./-]+\.(py|md|json|txt|yaml|yml)$")
SYMBOL_RE = re.compile(r"^([a-z_]\w*)\.([A-Za-z_]\w*)(?:\(\))?$")


# ---------------------------------------------------------------- code references

def resolve(token: str) -> tuple[str, int] | None:
    """Map a backticked token to (path, line): `atlas/design.py`, `design.py`, `design.needs_coordinator()`."""
    token = token.split("::")[0]
    if FILE_RE.match(token) and (ROOT / token).is_file():
        return token, 0
    if FILE_RE.match(token) and (ROOT / "atlas" / token).is_file():
        return f"atlas/{token}", 0
    m = SYMBOL_RE.match(token)
    if m and (ROOT / "atlas" / f"{m.group(1)}.py").is_file():
        path = f"atlas/{m.group(1)}.py"
        return path, line_of(path, m.group(2))
    return None


def line_of(path: str, symbol: str) -> int:
    """1-based line where `symbol` is defined in `path`, or 0 if it is not found."""
    pattern = re.compile(rf"^\s*(?:async\s+def|def|class)\s+{re.escape(symbol)}\b|^{re.escape(symbol)}\s*[:=]")
    for i, line in enumerate((ROOT / path).read_text().splitlines(), 1):
        if pattern.match(line):
            return i
    return 0


def code_span(m: re.Match) -> str:
    """A backticked token; one that names a repo file or atlas symbol becomes a button that opens it."""
    token = m.group(1)
    target = resolve(html.unescape(token))
    if not target:
        return f"<code>{token}</code>"
    path, line = target
    where = f"{path}:{line}" if line else path
    return (f'<button class="codelink" data-act="open" data-file="{path}" data-line="{line}" title="Open {where}">'
            f"<code>{token}</code></button>")


# ---------------------------------------------------------------- markdown -> html

def inline(text: str) -> str:
    out = html.escape(text, quote=False)
    out = re.sub(r"`([^`]+)`", code_span, out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<![\w*])\*([^*\s][^*]*)\*(?![\w*])", r"<em>\1</em>", out)
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<span class="link">\1</span>', out)


def md_to_html(md: str) -> str:
    """Small converter for the subset the lab guides use: paragraphs, lists, fences, tables."""
    lines = md.splitlines()
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif line.startswith("```"):
            i += 1
            code = []
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            out.append(f'<pre class="code"><code>{html.escape(chr(10).join(code))}</code></pre>')
        elif re.match(r"^\s*([-*]|\d+\.)\s+", line):
            ordered = bool(re.match(r"^\s*\d+\.", line))
            items = []
            while i < len(lines) and (re.match(r"^\s*([-*]|\d+\.)\s+", lines[i]) or (lines[i].startswith("  ") and items)):
                m = re.match(r"^\s*([-*]|\d+\.)\s+(.*)", lines[i])
                if m:
                    items.append(m.group(2))
                else:
                    items[-1] += " " + lines[i].strip()
                i += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{inline(t)}</li>" for t in items) + f"</{tag}>")
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            head, body = rows[0], rows[1:]
            out.append("<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body) + "</tbody></table>")
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(("```", "|")) \
                    and not re.match(r"^\s*([-*]|\d+\.)\s+", lines[i]):
                para.append(lines[i].strip())
                i += 1
            out.append(f"<p>{inline(' '.join(para))}</p>")
    return "\n".join(out)


# ---------------------------------------------------------------- lab guide parsing

def split_sections(body: list[str]) -> dict[str, str]:
    sections: dict[str, list[str]] = {"lead": []}
    current = "lead"
    for line in body:
        if line.strip() == "---":
            continue
        m = LABEL_RE.match(line.strip())
        if m:
            label = (m.group(1) or m.group(3)).lower()
            current = LABELS[label]
            sections.setdefault(current, [])
            rest = m.group(2) if m.group(1) else m.group(4)
            if rest:
                sections[current].append(rest)
        else:
            sections[current].append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items() if "\n".join(v).strip()}


def practical_files(text: str) -> list[str]:
    seen = []
    for token in re.findall(r"`([^`\s]+)`", text):
        target = resolve(token)
        if target and target[0] not in seen:
            seen.append(target[0])
    return seen


def first_command(text: str) -> str:
    m = re.search(r"`(pytest [^`]+)`", text)
    return m.group(1) if m else ""


def parse_lab(n: int) -> dict:
    lines = (DOCS / f"LAB{n}.md").read_text().splitlines()
    title = re.sub(r"^# Lab \d+:\s*", "", lines[0])
    idx = [i for i, l in enumerate(lines) if l.startswith("## ")]
    head_end = idx[0] if idx else len(lines)

    head = "\n".join(lines[1:head_end])
    meta_para = re.search(r"Course:.*?(?:\n\n|\n```)", head, re.S)
    meta = " ".join(meta_para.group(0).split()) if meta_para else ""
    time = (re.search(r"Time: about ([^·]+?)(?:\s*·|$)", meta) or [None, ""])[1].strip()
    tests = int((re.search(r"Tests: (\d+)", meta) or [0, 0])[1])
    needs = (re.search(r"Needs: (.+)$", meta) or [None, ""])[1].strip()
    chapter = (re.search(r"Chapter (\d+)", meta) or [None, str(n)])[1]
    intro_md = head.replace(meta_para.group(0), "") if meta_para else head
    intro_md = re.sub(r"```.*?```", "", intro_md, flags=re.S).strip()

    lesson_list, tail = [], {}
    for k, start in enumerate(idx):
        end = idx[k + 1] if k + 1 < len(idx) else len(lines)
        heading = lines[start]
        body = lines[start + 1:end]
        m = HEADING_RE.match(heading)
        if m and m.group(1) is None:
            kind, lid, ltitle = "Lesson", "0", m.group(4)
        elif m:
            kind, lid, ltitle = m.group(1), m.group(2), m.group(3)
        else:
            name = heading[3:].strip()
            tail[name.lower()] = "\n".join(body).strip()
            continue
        sec = split_sections(body)
        practical = sec.get("practical", "")
        case = n == 8 and kind == "Case"
        lesson_list.append({
            "id": f"c{lid}" if case else lid,
            "kind": kind,
            "title": ltitle,
            "html": {key: md_to_html(val) for key, val in sec.items()},
            "files": practical_files("\n".join(sec.values())),
            "check": first_command(sec.get("check", "")),
        })

    say_md = next((v for key, v in tail.items() if key.startswith("say it out loud")), "")
    see_md = next((v for key, v in tail.items() if key.startswith("see it work")), "")
    return {
        "n": n, "title": title, "chapter": chapter, "time": time, "tests": tests, "needs": needs,
        "intro": md_to_html(intro_md),
        "lessons": lesson_list,
        "see": md_to_html(see_md),
        "say": [re.sub(r"^\s*[-*]\s+|^\s*\d+\.\s+", "", l) for l in say_md.splitlines() if re.match(r"^\s*([-*]|\d+\.)\s+", l)],
    }


def lesson_for_test(lab: int, name: str, lesson_ids: list[str]) -> str | None:
    """Map a test name to its lesson id (test_3_2_... -> 3.2; test_0_... -> 0; lab 8 by case)."""
    if lab == 8:
        return "c1" if "renewals" in name else "c2"
    m = re.match(r"test_(\d+)_(\d+)_", name)
    if m:
        lid = f"{m.group(1)}.{m.group(2)}"
        if lid in lesson_ids:
            return lid
    m = re.match(r"test_0_", name)
    if m and "0" in lesson_ids:
        return "0"
    return lesson_ids[-1] if lesson_ids else None  # e.g. test_3_end belongs to the lab's last lesson


def build_model() -> dict:
    labs = [parse_lab(n) for n in range(1, 9) if (DOCS / f"LAB{n}.md").exists()]
    return {
        "title": "Atlas Loan Lab",
        "labs": labs,
        "people": [{"name": n, "role": r} for n, r in PEOPLE],
    }


if __name__ == "__main__":
    print(json.dumps(build_model(), indent=2))
