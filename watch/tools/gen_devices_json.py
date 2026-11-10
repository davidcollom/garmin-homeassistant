#!/usr/bin/env python3
"""Generate the Connect IQ "Devices package" JSON for a device from the SDK's
legacy ``dev_<deviceId>.xml`` device description.

The Connect IQ SDK (monkeyc) resolves ``-d <deviceId>`` through the *Devices
package* that the Garmin SDK Manager installs into::

    <user.home>/.Garmin/ConnectIQ/Devices/<deviceId>/compiler.json
    <user.home>/.Garmin/ConnectIQ/Devices/<deviceId>/simulator.json      (optional)
    <user.home>/.Garmin/ConnectIQ/Devices/<deviceId>/<deviceId>.api.debug.xml (optional)

If the SDK Manager has never been run, ``monkeyc -d venu441mm`` fails with
``ERROR: Invalid device id specified: 'venu441mm'``.  This script recreates
the ``compiler.json`` half of that package straight from the ``dev_*.xml``
files that ship inside the SDK zip (``<sdk>/dev_*.xml``), so a device can be
targeted with nothing but the plain SDK.

Usage::

    python3 tools/gen_devices_json.py --sdk /path/to/connectiq-sdk-9.3.0 \
        --devices-root ~/.Garmin/ConnectIQ/Devices \
        --device venu441mm --device edge1040

The generated ``compiler.json`` is a faithful translation of the XML device
description; field names come from
``com.garmin.connectiq.common.devices.DevicesJsonReader``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

ORIENTATION = {
    "GFX_ORNTN_0": 0,
    "GFX_ORNTN_90": 90,
    "GFX_ORNTN_180": 180,
    "GFX_ORNTN_270": 270,
}

# App type identifiers understood by DevicesJsonReader /
# com.garmin.connectiq.common.apps.AppTypeManager.  The device XML uses the
# *xml* type name, the devices package JSON uses the *json* type name.
APP_TYPES = {
    "watch-app": "watchApp",
    "watchface": "watchFace",
    "datafield": "datafield",
    "widget": "widget",
    "background": "background",
    "glance": "glance",
    "audio-content-provider-app": "audioContentProvider",
    "barrel": "barrel",
}

TRUTHY = {"TRUE", "true", "1", "YES", "yes"}


def _text(node, tag, default=None):
    child = node.find(tag)
    if child is None or child.text is None:
        return default
    return child.text.strip()


def _bool(node, tag, default=False):
    value = _text(node, tag)
    if value is None:
        return default
    return value in TRUTHY


def _resolution(node, tag):
    child = node.find(tag)
    if child is None:
        return None
    width = child.get("width")
    height = child.get("height")
    if width is None or height is None:
        return None
    return {"width": int(width), "height": int(height)}


def build_compiler_json(device_xml: str) -> dict:
    root = ET.parse(device_xml).getroot()
    device = root if root.tag == "device" else root.find("device")
    if device is None:
        raise SystemExit("no <device> element in %s" % device_xml)

    device_id = device.get("id")
    part_numbers = []

    for part in device.findall("./part_numbers/part_number"):
        languages = []
        for lang in part.findall("./languages/language"):
            languages.append(
                {
                    "code": (lang.text or "").strip(),
                    "fontSet": lang.get("font_set", "ww"),
                }
            )
        entry = {
            "number": part.get("number"),
            "connectIQVersion": part.get("connectIQVersion"),
            "languages": languages,
        }
        if part.get("firmwareVersion"):
            entry["firmwareVersion"] = int(part.get("firmwareVersion"))
        annotations = [
            (a.text or "").strip()
            for a in part.findall("./supported_api_annotations/annotation")
        ]
        if annotations:
            entry["supportedAPIAnnotations"] = annotations
        part_numbers.append(entry)

    app_types = []
    for app in device.findall("./app_types/app"):
        app_type = app.get("id")
        if app_type not in APP_TYPES:
            continue
        entry = {"type": APP_TYPES[app_type]}
        if app.get("memory_limit"):
            entry["memoryLimit"] = int(app.get("memory_limit"))
        if app.get("prg_limit"):
            entry["prgLimit"] = int(app.get("prg_limit"))
        app_types.append(entry)

    palette = None
    palette_node = device.find("palette")
    if palette_node is not None:
        colors = [
            (c.text or "").strip()
            for c in palette_node.findall("color")
            if (c.text or "").strip()
        ]
        if colors:
            palette = {"colors": colors}

    image_formats = [
        f.get("name")
        for f in device.findall("./imageFormats/format")
        if f.get("name")
    ]

    compiler = {
        "deviceId": device_id,
        "displayName": device.get("name"),
        "deviceFamily": device.get("family"),
        "worldWidePartNumber": device.get("part_number"),
        "partNumbers": part_numbers,
        "orientation": ORIENTATION.get(_text(device, "orientation", "GFX_ORNTN_0"), 0),
        "bitsPerPixel": int(_text(device, "bpp", "16")),
        "resolution": _resolution(device, "resolution"),
        "appTypes": app_types,
        "launcherIcon": _resolution(device, "launcher_icon"),
        "pixelFormat": _text(device, "pixel_format", ""),
        "menuBar": {"location": {"height": 0}},
        "antiAliasedFontSupport": _bool(device, "anti_aliased_font_support", True),
        "screenRotationSupport": _bool(device, "screen_rotation_support", False),
        "alphaBlendingSupport": _bool(device, "alpha_blending_support", True),
        "imageFormats": image_formats,
        "gpuSupport": _bool(device, "gpu_support", False),
        "enhancedGraphicSupport": _bool(device, "enhanced_graphics_support", False),
        "exportSupport": _bool(device, "export_support", True),
        "controlBarSupport": _bool(device, "control_bar_support", False),
        "codePageSize": int(_text(device, "code_page_size", "0")),
    }

    complication = _resolution(device, "complication_icon")
    if complication:
        compiler["complicationIcon"] = complication
    if palette:
        compiler["palette"] = palette
    if compiler["resolution"] is None:
        del compiler["resolution"]
    if compiler["launcherIcon"] is None:
        del compiler["launcherIcon"]

    return compiler


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", required=True, help="Connect IQ SDK directory")
    parser.add_argument(
        "--devices-root",
        default=os.path.expanduser("~/.Garmin/ConnectIQ/Devices"),
        help="devices root folder used by monkeyc",
    )
    parser.add_argument(
        "--device",
        action="append",
        required=True,
        help="device id (repeatable), e.g. venu441mm",
    )
    args = parser.parse_args(argv)

    for device_id in args.device:
        xml_path = os.path.join(args.sdk, "dev_%s.xml" % device_id)
        if not os.path.exists(xml_path):
            print("skip %s: %s not found" % (device_id, xml_path), file=sys.stderr)
            continue
        compiler = build_compiler_json(xml_path)
        out_dir = os.path.join(args.devices_root, device_id)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "compiler.json")
        with open(out_path, "w", encoding="utf-8") as handle:
            json.dump(compiler, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        print("wrote %s" % out_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
