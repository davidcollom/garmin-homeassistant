#!/usr/bin/env python3
"""Static checks for the Connect IQ watch application.

The Connect IQ SDK is proprietary and cannot be redistributed, so the watch
application cannot be compiled in an open source CI pipeline.  This script
performs the checks that *can* be done without the compiler:

* the XML resources are well formed and reference each other correctly,
* every ``$.Rez.Strings.*`` and ``$.Rez.Drawables.*`` reference in the
  source exists,
* the Monkey C sources have balanced brackets and no obviously wrong API
  usage,
* the manifest only targets products and permissions that the application
  actually supports.

The build has two variants.  The shared code lives in ``watch/source`` and
every variant adds one presenter in ``watch/variants/<name>``.  The Edge 1040
does not implement ``Toybox.Notifications``, so that module may only be used
by the variant that is built for the Venu.

Usage::

    python3 scripts/check_ciq.py [watch-directory]

The script exits with a non zero status when a problem is found.
"""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

IQ_NS = "{http://www.garmin.com/xml/connectiq}"

#: Products the application is built for.
SUPPORTED_PRODUCTS = {
    "venu441mm",
    "venu445mm",
    "edge1040",
    "edge1040solar",
}

#: Permissions the application asks for.
ALLOWED_PERMISSIONS = {
    "Communications",
    "Background",
    "Notifications",
    "SensorHistory",
    "UserProfile",
    "ActivityMonitor",
    "Positioning",
}

#: API calls that do not exist or that moved between Connect IQ versions.
FORBIDDEN_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\btoLowerCase\s*\(", "Lang.String has toLower(), not toLowerCase()"),
    (r"\btoUpperCase\s*\(", "Lang.String has toUpper(), not toUpperCase()"),
    (r"\bhandleKeyPress\s*\(", "handleKeyPress() was removed in Connect IQ 2"),
    (r"\bAppBase\.onLayout\s*\(", "the application class has no onLayout()"),
    (r"\bAppBase\.onUpdate\s*\(", "the application class has no onUpdate()"),
    (r"\bAppBase\.handleKeyPress\s*\(", "the application class has no handleKeyPress()"),
    (r"\bBackgroundService\b", "the base build does not ship a background service"),
    (r"\bWatchUi\.Text\b", "WatchUi.Text was removed in Connect IQ 2"),
    (r"\bWatchUi\.View\.drawText\s*\(", "use the drawing context instead"),
)

#: Modules the application is allowed to import.
ALLOWED_TOYBOX = {
    "Application",
    "Background",
    "Communications",
    "Graphics",
    "Lang",
    "Math",
    "Notifications",
    "System",
    "Timer",
    "WatchUi",
}

#: The variant that is allowed to use Toybox.Notifications.
NOTIFICATIONS_VARIANT = "notifications"


@dataclass
class Report:
    """Collects the problems found while checking the sources."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, message: str) -> None:
        """Record a problem that makes the check fail."""
        self.errors.append(message)

    def warn(self, message: str) -> None:
        """Record a problem that does not make the check fail."""
        self.warnings.append(message)

    @property
    def ok(self) -> bool:
        """Return True when no error was found."""
        return not self.errors


def strip_comments(text: str) -> str:
    """Remove the comments from a Monkey C source.

    The comments are replaced by spaces so that the line numbers of the
    remaining code stay the same.
    """
    out: list[str] = []
    index = 0
    length = len(text)
    in_string: str | None = None
    while index < length:
        char = text[index]
        if in_string:
            out.append(char)
            if char == "\\" and index + 1 < length:
                out.append(text[index + 1])
                index += 2
                continue
            if char == in_string:
                in_string = None
            index += 1
            continue
        if char in {'"', "'"}:
            in_string = char
            out.append(char)
            index += 1
            continue
        if char == "/" and index + 1 < length and text[index + 1] == "/":
            end = text.find("\n", index)
            end = length if end == -1 else end
            out.append(" " * (end - index))
            index = end
            continue
        if char == "/" and index + 1 < length and text[index + 1] == "*":
            end = text.find("*/", index + 2)
            end = length if end == -1 else end + 2
            out.append("".join("\n" if c == "\n" else " " for c in text[index:end]))
            index = end
            continue
        out.append(char)
        index += 1
    return "".join(out)


def _read_xml(path: Path, report: Report) -> ET.Element | None:
    """Parse an XML file and report problems instead of raising."""
    try:
        return ET.parse(path).getroot()
    except ET.ParseError as err:
        report.error(f"{path}: invalid XML: {err}")
        return None


def check_manifest(path: Path, watch: Path, report: Report) -> None:
    """Check one application manifest."""
    if not path.is_file():
        report.error(f"{path}: manifest is missing")
        return
    root = _read_xml(path, report)
    if root is None:
        return

    application = root.find(f"{IQ_NS}application")
    if application is None:
        report.error(f"{path}: no <iq:application> element")
        return

    for attribute in ("id", "type", "name", "entry", "launcherIcon", "minApiLevel"):
        if not application.get(attribute):
            report.error(f"{path}: <iq:application> is missing the {attribute} attribute")

    app_id = application.get("id", "")
    uuid = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    if app_id and not re.fullmatch(uuid, app_id):
        report.error(f"{path}: the application id {app_id!r} is not a UUID")

    products = application.find(f"{IQ_NS}products")
    if products is None:
        report.error(f"{path}: no <iq:products> element")
    else:
        found = [node.get("id", "") for node in products.findall(f"{IQ_NS}product")]
        if not found:
            report.error(f"{path}: no products are declared")
        for product in found:
            if product not in SUPPORTED_PRODUCTS:
                report.error(
                    f"{path}: product {product!r} is not one of the supported products "
                    f"({', '.join(sorted(SUPPORTED_PRODUCTS))})"
                )

    permissions = application.find(f"{IQ_NS}permissions")
    if permissions is None:
        report.error(f"{path}: no <iq:permissions> element")
    else:
        for node in permissions.findall(f"{IQ_NS}uses-permission"):
            permission = node.get("id", "")
            if permission not in ALLOWED_PERMISSIONS:
                report.error(f"{path}: unexpected permission {permission!r}")

    launcher_icon = application.get("launcherIcon", "")
    if launcher_icon.startswith("@Drawables."):
        name = launcher_icon.split(".", 1)[1]
        if not (watch / "resources" / "drawables" / f"{name}.png").is_file():
            report.error(f"{path}: the launcher icon {launcher_icon} does not exist")


def check_resources(watch: Path, report: Report) -> tuple[set[str], set[str]]:
    """Check the strings, properties and settings resources."""
    strings: set[str] = set()

    strings_path = watch / "resources" / "strings.xml"
    if strings_path.is_file():
        root = _read_xml(strings_path, report)
        if root is not None:
            for node in root.findall("string"):
                identifier = node.get("id", "")
                if not identifier:
                    report.error(f"{strings_path}: a <string> element has no id")
                    continue
                if identifier in strings:
                    report.error(f"{strings_path}: duplicate string id {identifier!r}")
                strings.add(identifier)
    else:
        report.error(f"{strings_path}: the strings resource is missing")

    properties: set[str] = set()
    properties_path = watch / "resources" / "settings" / "properties.xml"
    if properties_path.is_file():
        root = _read_xml(properties_path, report)
        if root is not None:
            for node in root.findall("property"):
                identifier = node.get("id", "")
                if not identifier:
                    report.error(f"{properties_path}: a <property> element has no id")
                    continue
                if identifier in properties:
                    report.error(f"{properties_path}: duplicate property id {identifier!r}")
                properties.add(identifier)
    else:
        report.error(f"{properties_path}: the properties resource is missing")

    settings_path = watch / "resources" / "settings" / "settings.xml"
    if settings_path.is_file():
        root = _read_xml(settings_path, report)
        if root is not None:
            for node in root.findall("setting"):
                key = node.get("propertyKey", "")
                if key.startswith("@Properties."):
                    name = key.split(".", 1)[1]
                    if name not in properties:
                        report.error(f"{settings_path}: unknown property {key!r}")
                elif key:
                    report.error(f"{settings_path}: malformed propertyKey {key!r}")
                title = node.get("title", "")
                if title.startswith("@Strings."):
                    name = title.split(".", 1)[1]
                    if name not in strings:
                        report.error(f"{settings_path}: unknown string {title!r}")
                elif title:
                    report.error(f"{settings_path}: malformed title {title!r}")
    else:
        report.error(f"{settings_path}: the settings resource is missing")

    drawables_dir = watch / "resources" / "drawables"
    if not drawables_dir.is_dir():
        report.warn(f"{drawables_dir}: the drawables directory is missing")

    return strings, properties


def _collect_classes(paths: list[Path]) -> set[str]:
    """Return the names of the classes and modules that are defined."""
    classes: set[str] = set()
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"^\s*class\s+(\w+)", text, re.MULTILINE):
            classes.add(match.group(1))
        for match in re.finditer(r"^\s*module\s+(\w+)", text, re.MULTILINE):
            classes.add(match.group(1))
    return classes


def check_source_file(
    path: Path,
    relative: Path,
    report: Report,
    classes: set[str],
    strings: set[str],
    drawables: set[str],
    allow_notifications: bool,
) -> None:
    """Check a single Monkey C source file."""
    raw = path.read_text(encoding="utf-8")
    text = strip_comments(raw)

    _check_brackets(relative, text, report)

    patterns = list(FORBIDDEN_PATTERNS)
    if not allow_notifications:
        patterns.append(
            (
                r"\bToybox\.Notifications\b",
                "Toybox.Notifications is not available on the Edge 1040",
            )
        )

    for pattern, message in patterns:
        for match in re.finditer(pattern, text):
            line = text.count("\n", 0, match.start()) + 1
            report.error(f"{relative}:{line}: {message}")

    for match in re.finditer(r"using\s+Toybox\.(\w+)\s+as\s+(\w+)\s*;", text):
        module, alias = match.groups()
        if module not in ALLOWED_TOYBOX:
            report.error(f"{relative}: Toybox.{module} is not used by this application")
        uses = len(re.findall(rf"\b{re.escape(alias)}\.", text))
        if uses == 0:
            report.warn(f"{relative}: the alias {alias} is imported but never used")

    for match in re.finditer(r"\$\.Rez\.Strings\.(\w+)", text):
        name = match.group(1)
        if strings and name not in strings:
            line = text.count("\n", 0, match.start()) + 1
            report.error(f"{relative}:{line}: unknown string resource {name!r}")

    for match in re.finditer(r"\$\.Rez\.Drawables\.(\w+)", text):
        name = match.group(1)
        if drawables and name.lower() not in {item.lower() for item in drawables}:
            line = text.count("\n", 0, match.start()) + 1
            report.error(f"{relative}:{line}: unknown drawable resource {name!r}")

    for match in re.finditer(r"\bnew\s+(\w+)\s*\(", text):
        name = match.group(1)
        if name in {"Lang", "Dictionary", "Array", "String", "Number", "Boolean"}:
            continue
        if name not in classes and name[0].isupper():
            line = text.count("\n", 0, match.start()) + 1
            report.error(f"{relative}:{line}: unknown class {name!r}")


def check_sources(watch: Path, report: Report) -> None:
    """Check the Monkey C sources of the base build and of the variants."""
    source_dir = watch / "source"
    if not source_dir.is_dir():
        report.error(f"{source_dir}: the source directory is missing")
        return

    base_sources = sorted(source_dir.glob("*.mc"))
    if not base_sources:
        report.error(f"{source_dir}: no Monkey C sources were found")

    variants_dir = watch / "variants"
    variant_sources: dict[str, list[Path]] = {}
    if variants_dir.is_dir():
        for variant_dir in sorted(variants_dir.iterdir()):
            if not variant_dir.is_dir():
                continue
            variant_sources[variant_dir.name] = sorted(variant_dir.glob("*.mc"))
    if not variant_sources:
        report.error(f"{variants_dir}: no variants were found")

    all_sources = list(base_sources)
    for sources in variant_sources.values():
        all_sources.extend(sources)

    classes = _collect_classes(all_sources)

    strings, _properties = check_resources(watch, report)

    drawables_dir = watch / "resources" / "drawables"
    drawables = (
        {path.stem for path in drawables_dir.glob("*.png")} if drawables_dir.is_dir() else set()
    )

    for path in base_sources:
        check_source_file(
            path,
            path.relative_to(watch.parent),
            report,
            classes,
            strings,
            drawables,
            allow_notifications=False,
        )

    for name, sources in variant_sources.items():
        for path in sources:
            check_source_file(
                path,
                path.relative_to(watch.parent),
                report,
                classes,
                strings,
                drawables,
                allow_notifications=name == NOTIFICATIONS_VARIANT,
            )

    for manifest in sorted(watch.glob("manifest*.xml")):
        check_manifest(manifest, watch, report)

    # The entry class of every manifest has to exist.
    for manifest in sorted(watch.glob("manifest*.xml")):
        root = _read_xml(manifest, report)
        if root is None:
            continue
        application = root.find(f"{IQ_NS}application")
        entry = application.get("entry") if application is not None else None
        if entry and entry not in classes:
            report.error(f"{manifest}: the entry class {entry!r} does not exist")


def _check_brackets(relative: Path, text: str, report: Report) -> None:
    """Make sure the brackets in a source file are balanced."""
    pairs = {")": "(", "]": "[", "}": "{"}
    stack: list[tuple[str, int]] = []
    in_string: str | None = None
    index = 0
    line = 1
    while index < len(text):
        char = text[index]
        if char == "\n":
            line += 1
            index += 1
            continue
        if in_string:
            if char == "\\":
                index += 2
                continue
            if char == in_string:
                in_string = None
            index += 1
            continue
        if char in {'"', "'"}:
            in_string = char
            index += 1
            continue
        if char in "([{":
            stack.append((char, line))
        elif char in ")]}":
            if not stack:
                report.error(f"{relative}:{line}: unexpected {char!r}")
                return
            opener, opener_line = stack.pop()
            if opener != pairs[char]:
                report.error(
                    f"{relative}:{line}: {char!r} closes {opener!r} opened on line {opener_line}"
                )
                return
        index += 1

    if stack:
        opener, opener_line = stack[-1]
        report.error(f"{relative}:{opener_line}: {opener!r} is never closed")


def main(argv: list[str]) -> int:
    """Run the checks."""
    root = Path(__file__).resolve().parents[1]
    watch = Path(argv[1]) if len(argv) > 1 else root / "watch"

    if not watch.is_dir():
        print(f"error: {watch} is not a directory", file=sys.stderr)
        return 2

    report = Report()
    check_sources(watch, report)

    for warning in report.warnings:
        print(f"warning: {warning}")
    for error in report.errors:
        print(f"error: {error}", file=sys.stderr)

    if report.errors:
        print(f"\n{len(report.errors)} problem(s) found", file=sys.stderr)
        return 1

    print(f"Connect IQ sources in {watch} look consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
