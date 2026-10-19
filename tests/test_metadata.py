"""Pure metadata tests: no Home Assistant required.

Guards the "keep in sync" footgun called out in const.py: the version must
be identical in manifest.json, const.py and, where they exist, a bundled
card's ``CARD_VERSION`` and the root package.json. Also asserts the manifest and
hacs.json carry what hassfest / HACS expect, and that the zip release asset
is wired end to end. Runs in milliseconds, stdlib only.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPONENT = ROOT / "custom_components" / "bora_dryer"


def _manifest() -> dict:
    return json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))


def _const_version() -> str:
    text = (COMPONENT / "const.py").read_text(encoding="utf-8")
    match = re.search(r'^VERSION\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert match, "VERSION not found in const.py"
    return match.group(1)


def _version_sources() -> dict[str, str]:
    """Every place that declares the version, keyed by where it was found."""
    found = {
        "manifest.json version": _manifest()["version"],
        "const.py VERSION": _const_version(),
    }
    # A card shipped inside the integration (frontend/*.js) and the
    # package.json that exists only for its tests carry the version too.
    for card in sorted((COMPONENT / "frontend").glob("*.js")):
        text = card.read_text(encoding="utf-8")
        match = re.search(r"CARD_VERSION\s*=\s*['\"]([^'\"]+)['\"]", text)
        if match:
            found[f"frontend/{card.name} CARD_VERSION"] = match.group(1)
    package = ROOT / "package.json"
    if package.is_file():
        found["package.json version"] = json.loads(package.read_text(encoding="utf-8"))[
            "version"
        ]
    return found


def test_versions_are_in_sync() -> None:
    """Every file that carries the version moves together, or it drifts."""
    sources = _version_sources()
    assert len(set(sources.values())) == 1, f"versions out of sync: {sources}"


def test_manifest_has_required_keys() -> None:
    manifest = _manifest()
    for key in (
        "domain",
        "name",
        "codeowners",
        "documentation",
        "issue_tracker",
        "version",
        "config_flow",
        "iot_class",
    ):
        assert key in manifest, f"manifest.json missing '{key}'"
    assert manifest["domain"] == "bora_dryer"
    assert manifest["config_flow"] is True


def test_strings_and_translation_agree() -> None:
    """strings.json is the source; translations/en.json must be identical."""
    strings = json.loads((COMPONENT / "strings.json").read_text(encoding="utf-8"))
    english = json.loads(
        (COMPONENT / "translations" / "en.json").read_text(encoding="utf-8")
    )
    assert strings == english


def _leaf_keys(obj: object, prefix: str = "") -> set[str]:
    """Recursively collect dotted paths to every leaf value in a nested dict."""
    if not isinstance(obj, dict):
        return {prefix}
    keys: set[str] = set()
    for k, v in obj.items():
        child = f"{prefix}.{k}" if prefix else k
        keys |= _leaf_keys(v, child)
    return keys


def test_translation_key_parity() -> None:
    """Every translation file must carry exactly the key set of en.json.

    Catches drift when new strings are added to en.json but the other
    languages are not updated, and vice-versa (extra keys in a translation
    that were removed from en.json).
    """
    translations_dir = COMPONENT / "translations"
    english = json.loads((translations_dir / "en.json").read_text(encoding="utf-8"))
    en_keys = _leaf_keys(english)

    for path in sorted(translations_dir.glob("*.json")):
        if path.name == "en.json":
            continue
        lang = path.stem
        other = json.loads(path.read_text(encoding="utf-8"))
        other_keys = _leaf_keys(other)
        missing = en_keys - other_keys
        extra = other_keys - en_keys
        assert not missing, f"{lang}.json is missing keys: {sorted(missing)}"
        assert not extra, f"{lang}.json has extra keys not in en.json: {sorted(extra)}"


def test_hacs_json_is_valid() -> None:
    hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))
    assert hacs["name"]
    # Minimum HA version must look like a real release string. Raise it in
    # the same PR that starts relying on a newer HA API.
    assert re.fullmatch(r"\d{4}\.\d+\.\d+", hacs["homeassistant"])
    # HACS renders the README as the store page.
    assert hacs.get("render_readme") is True


def test_zip_release_asset_is_wired_end_to_end() -> None:
    """The zip must be requested, named, and actually built.

    HACS only increments a release's download counter when it fetches a
    release asset, and it only does that when zip_release is set with a
    .zip filename. Three files have to agree; if any drifts, installs
    either stop counting or break outright, and nothing else notices.
    """
    hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))
    domain = _manifest()["domain"]

    assert hacs.get("zip_release") is True
    expected = f"{domain}.zip"
    assert hacs.get("filename") == expected, (
        f"hacs.json filename must be {expected!r} to match the manifest domain"
    )

    release_workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )
    assert expected in release_workflow, (
        f"release.yml must build and attach {expected}; hacs.json points HACS "
        "at an asset that would not exist"
    )
    # The zip holds the *contents* of the integration directory. A wrapper
    # folder lands as custom_components/<domain>/<domain>/ and nothing loads.
    assert f"cd custom_components/{domain}" in release_workflow, (
        "release.yml must zip from inside the integration directory"
    )
