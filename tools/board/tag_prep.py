#!/usr/bin/env python3
"""PD-REMAIN-TAG-APPLY-01 / PD-TAG-PREP-01 — SemVer tag prep.

BDD-PD-REMAIN-TAG-APPLY-01:
  - ``tag_prep --apply`` only when **both** ``--apply`` and owner gate
    ``--owner-approved`` are present.
  - Default mode is **dry-run** (no git tag).
  - Dry-run output must never claim the release was published / tagged.
  - No default ``git push`` (push not implemented).

BDD-PD-TAG-PREP-01 (predecessor):
  - Rerunnable plan + CHANGELOG cross-check; stub apply → NOT RUN.

Usage::

    python tools/board/tag_prep.py
    python tools/board/tag_prep.py --version 0.1.0
    python tools/board/tag_prep.py --apply              # GATE_BLOCKED
    python tools/board/tag_prep.py --apply --owner-approved  # stub → NOT RUN
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

BOARD_DIR = Path(__file__).resolve().parent
REPO = BOARD_DIR.parents[1]

CARD_ID = "PD-REMAIN-TAG-APPLY-01"
BDD_ID = "BDD-PD-REMAIN-TAG-APPLY-01"
DEFAULT_VERSION = "0.1.0"
DEFAULT_CHANGELOG = REPO / "CHANGELOG.md"

# Modes
MODE_DRY_RUN = "dry-run"
MODE_APPLY = "apply"

# Apply / tag outcome vocabulary aligned with Build Result
STATUS_PLANNED = "PLANNED"  # dry-run only — not a release claim
STATUS_NOT_RUN = "NOT RUN"
STATUS_GATE_BLOCKED = "GATE_BLOCKED"  # --apply without owner gate
STATUS_TAGGED = "TAGGED"  # reserved; not produced by default stub

# Owner gate vocabulary
GATE_N_A = "N/A"  # dry-run — gate not applicable
GATE_BLOCKED = "BLOCKED"
GATE_OPEN = "OPEN"


@dataclass(frozen=True)
class ChangelogCheck:
    path: str
    present: bool
    has_version_section: bool
    has_release_id: bool
    excerpt: str


@dataclass(frozen=True)
class TagPlan:
    card: str
    bdd: str
    mode: str
    version: str
    planned_tag: str
    changelog: ChangelogCheck
    tag_status: str
    published: bool
    message: str
    owner_approved: bool
    gate_status: str
    push: bool  # always False in this tool (no default push)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["changelog"] = asdict(self.changelog)
        return d


def normalize_version(raw: str) -> str:
    """Strip optional leading ``v``; require SemVer X.Y.Z (+ optional pre/build)."""
    s = (raw or "").strip()
    if s.lower().startswith("v") and len(s) > 1 and s[1].isdigit():
        s = s[1:]
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", s):
        raise ValueError("version must be SemVer X.Y.Z (got %r)" % raw)
    return s


def planned_tag_name(version: str) -> str:
    return "v" + normalize_version(version)


def check_changelog(
    changelog_path: Path,
    version: str,
) -> ChangelogCheck:
    """Read CHANGELOG and report presence + version / release-id cross-check."""
    ver = normalize_version(version)
    release_id = "v" + ver
    path_s = str(changelog_path.as_posix())
    if not changelog_path.is_file():
        return ChangelogCheck(
            path=path_s,
            present=False,
            has_version_section=False,
            has_release_id=False,
            excerpt="",
        )
    try:
        text = changelog_path.read_text(encoding="utf-8")
    except OSError:
        return ChangelogCheck(
            path=path_s,
            present=False,
            has_version_section=False,
            has_release_id=False,
            excerpt="",
        )
    # Keep a Changelog style: ## [0.1.0] — …
    section_re = re.compile(
        r"^##\s*\[%s\]" % re.escape(ver),
        re.MULTILINE,
    )
    has_section = bool(section_re.search(text))
    has_rid = release_id in text or ("`%s`" % release_id) in text
    # Short excerpt around the version heading if present
    excerpt = ""
    m = section_re.search(text)
    if m:
        start = m.start()
        excerpt = text[start : start + 160].replace("\r\n", "\n").strip()
        if len(text) > start + 160:
            excerpt += "…"
    return ChangelogCheck(
        path=path_s,
        present=True,
        has_version_section=has_section,
        has_release_id=has_rid,
        excerpt=excerpt,
    )


# Optional real tagger for future use; default stub never tags.
Tagger = Callable[[str, Path], str]


def stub_tagger(_tag: str, _repo: Path) -> str:
    """Default ``--apply`` backend: do not run git; report NOT RUN."""
    return STATUS_NOT_RUN


def plan_tag(
    *,
    version: str = DEFAULT_VERSION,
    changelog_path: Path | None = None,
    repo: Path | None = None,
    apply: bool = False,
    owner_approved: bool = False,
    tagger: Tagger | None = None,
) -> TagPlan:
    """Build a tag plan. Default ``apply=False`` never creates a git tag.

    ``apply=True`` requires ``owner_approved=True`` (owner gate) before the
    tagger is invoked. Push is never performed by this tool.
    """
    ver = normalize_version(version)
    tag = planned_tag_name(ver)
    clog = check_changelog(
        changelog_path if changelog_path is not None else DEFAULT_CHANGELOG,
        ver,
    )
    root = repo if repo is not None else REPO

    if not apply:
        msg = (
            "dry-run: would create git tag %s (CHANGELOG present=%s, "
            "section=%s). Not published; no git tag executed."
            % (tag, clog.present, clog.has_version_section)
        )
        return TagPlan(
            card=CARD_ID,
            bdd=BDD_ID,
            mode=MODE_DRY_RUN,
            version=ver,
            planned_tag=tag,
            changelog=clog,
            tag_status=STATUS_PLANNED,
            published=False,
            message=msg,
            owner_approved=False,
            gate_status=GATE_N_A,
            push=False,
        )

    # Explicit --apply without owner gate → blocked; never call tagger.
    if not owner_approved:
        msg = (
            "apply blocked: --owner-approved required (owner gate); "
            "no git tag created (not published). No push."
        )
        return TagPlan(
            card=CARD_ID,
            bdd=BDD_ID,
            mode=MODE_APPLY,
            version=ver,
            planned_tag=tag,
            changelog=clog,
            tag_status=STATUS_GATE_BLOCKED,
            published=False,
            message=msg,
            owner_approved=False,
            gate_status=GATE_BLOCKED,
            push=False,
        )

    fn = tagger if tagger is not None else stub_tagger
    status = fn(tag, root)
    if status == STATUS_TAGGED:
        # Real tagging path (not used by default stub / unit tests).
        msg = (
            "apply: git tag %s created (owner gate open). "
            "Push not performed by this tool."
            % tag
        )
        published = True
    else:
        # Explicit apply + gate, but backend did not tag → NOT RUN
        msg = (
            "apply: tag backend returned %s for %s - no git tag created "
            "(not published). Owner gate was open; push not performed."
            % (status, tag)
        )
        published = False
        status = STATUS_NOT_RUN
    return TagPlan(
        card=CARD_ID,
        bdd=BDD_ID,
        mode=MODE_APPLY,
        version=ver,
        planned_tag=tag,
        changelog=clog,
        tag_status=status,
        published=published,
        message=msg,
        owner_approved=True,
        gate_status=GATE_OPEN,
        push=False,
    )


def format_plan(plan: TagPlan) -> str:
    """Human-readable, rerunnable report. Never labels dry-run as published."""
    c = plan.changelog
    lines = [
        "%s / %s" % (plan.card, plan.bdd),
        "mode=%s" % plan.mode,
        "version=%s" % plan.version,
        "planned_tag=%s" % plan.planned_tag,
        "changelog.path=%s" % c.path,
        "changelog.present=%s" % ("yes" if c.present else "no"),
        "changelog.has_version_section=%s"
        % ("yes" if c.has_version_section else "no"),
        "changelog.has_release_id=%s" % ("yes" if c.has_release_id else "no"),
        "owner_approved=%s" % ("yes" if plan.owner_approved else "no"),
        "gate_status=%s" % plan.gate_status,
        "tag_status=%s" % plan.tag_status,
        "published=%s" % ("yes" if plan.published else "no"),
        "push=%s" % ("yes" if plan.push else "no"),
        "message=%s" % plan.message,
    ]
    if c.excerpt:
        lines.append("changelog.excerpt=")
        lines.append(c.excerpt)
    if plan.mode == MODE_DRY_RUN:
        lines.append(
            "NOTE: dry-run is a plan only - not a publish claim; no tag created."
        )
    if plan.tag_status == STATUS_GATE_BLOCKED:
        lines.append(
            "NOTE: --apply requires --owner-approved; gate blocked; not published."
        )
    return "\n".join(lines) + "\n"


def plan_from_argv(
    argv: list[str] | None = None,
    *,
    tagger: Tagger | None = None,
) -> TagPlan:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--version",
        default=DEFAULT_VERSION,
        help="SemVer without required v-prefix (default: %s)" % DEFAULT_VERSION,
    )
    ap.add_argument(
        "--changelog",
        type=Path,
        default=DEFAULT_CHANGELOG,
        help="Path to CHANGELOG.md",
    )
    ap.add_argument(
        "--repo",
        type=Path,
        default=REPO,
        help="Repo root (unused by dry-run / stub apply)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan only (default when --apply is omitted; no git tag)",
    )
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Request real tag; requires --owner-approved (owner gate)",
    )
    ap.add_argument(
        "--owner-approved",
        action="store_true",
        help="Owner gate: required with --apply; without it apply is GATE_BLOCKED",
    )
    ap.add_argument(
        "--push",
        action="store_true",
        help="Rejected: push is not implemented (no default push)",
    )
    args = ap.parse_args(argv)
    if args.dry_run and args.apply:
        raise ValueError("pass only one of --dry-run / --apply")
    if args.push:
        raise ValueError(
            "push is not implemented; tag_prep never default-pushes "
            "(BDD-PD-REMAIN-TAG-APPLY-01)"
        )
    if args.owner_approved and not args.apply:
        raise ValueError("--owner-approved only valid with --apply")
    return plan_tag(
        version=args.version,
        changelog_path=args.changelog,
        repo=args.repo,
        apply=bool(args.apply),
        owner_approved=bool(args.owner_approved),
        tagger=tagger,
    )


def main(argv: list[str] | None = None) -> int:
    try:
        plan = plan_from_argv(argv)
    except ValueError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    sys.stdout.write(format_plan(plan))
    # GATE_BLOCKED → non-zero so callers do not treat it as success.
    if plan.tag_status == STATUS_GATE_BLOCKED:
        return 3
    # Exit 0 for dry-run / NOT RUN stub; never claim publish success by exit alone.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
