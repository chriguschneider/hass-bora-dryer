"""Guard CHANGELOG.md format and coverage.

Verifies that CHANGELOG.md exists and contains a section header for the
version currently declared in manifest.json, so a version bump without a
matching changelog section fails on every push, not only on tag push.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = ROOT / "CHANGELOG.md"
MANIFEST = ROOT / "custom_components" / "bora_dryer" / "manifest.json"

# Versions released before the changelog moved out of the README that were
# never tagged (checked with `git tag` on 2026-10-19). Their sections stay for
# the history but have no tag to link to. Frozen: every version from v0.8.2 on
# is released from a tag and needs its link definition.
UNTAGGED_LEGACY = frozenset(
    {"v0.1.0", "v0.2.0", "v0.3.2", "v0.4.0", "v0.5.0", "v0.5.1"}
)


def _current_version() -> str:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))["version"]


def test_changelog_exists() -> None:
    assert CHANGELOG.exists(), "CHANGELOG.md is missing"


def test_changelog_has_section_for_current_version() -> None:
    version = _current_version()
    text = CHANGELOG.read_text(encoding="utf-8")
    pattern = rf"^## \[v{re.escape(version)}\]"
    assert re.search(pattern, text, re.MULTILINE), (
        f"CHANGELOG.md has no section for version {version!r}. "
        f"Add a '## [v{version}]' entry before bumping the version."
    )


def test_changelog_has_unreleased_section() -> None:
    text = CHANGELOG.read_text(encoding="utf-8")
    assert re.search(r"^## \[Unreleased\]", text, re.MULTILINE), (
        "CHANGELOG.md must have an '[Unreleased]' section at the top "
        "(Keep a Changelog convention)"
    )


def _headers(text: str) -> list[str]:
    return re.findall(r"^## \[(v\d+\.\d+\.\d+)\]", text, re.MULTILINE)


def test_changelog_link_definitions_present() -> None:
    """Every tagged version header has a link definition.

    Only the frozen pre-standard versions in UNTAGGED_LEGACY may lack one.
    """
    text = CHANGELOG.read_text(encoding="utf-8")
    headers = _headers(text)
    assert headers, "CHANGELOG.md has no version sections"
    for version in headers:
        if version in UNTAGGED_LEGACY:
            continue
        assert f"[{version}]:" in text, (
            f"CHANGELOG.md is missing the link definition for [{version}]"
        )


def test_untagged_legacy_versions_have_no_link() -> None:
    """A link to a tag that does not exist would 404; keep the list honest."""
    text = CHANGELOG.read_text(encoding="utf-8")
    headers = set(_headers(text))
    assert UNTAGGED_LEGACY <= headers, (
        f"stale UNTAGGED_LEGACY entries: {sorted(UNTAGGED_LEGACY - headers)}"
    )
    for version in UNTAGGED_LEGACY:
        assert f"[{version}]:" not in text, (
            f"[{version}] was never tagged; drop its link definition or, if the "
            "tag now exists, remove it from UNTAGGED_LEGACY"
        )
