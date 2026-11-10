#!/usr/bin/env bash
#
# Build the Connect IQ application.
#
# The Connect IQ SDK is proprietary, so it cannot be installed from this
# repository.  Download the SDK from
# https://developer.garmin.com/connect-iq/download/ and point MONKEYC at
# the monkeyc executable of the SDK:
#
#     export MONKEYC="$HOME/connectiq/bin/monkeyc"
#     export GARMIN_DEVELOPER_KEY="$HOME/.garmin/developer_key"
#     export GARMIN_DEVELOPER_KEYS="$HOME/.garmin/developer_keys"
#
# A developer key is only needed for the sideload (debug) builds.  The
# release builds are signed by Garmin when the application is submitted.
#
# Usage:
#
#     ./build.sh              build the Venu 4 variant
#     ./build.sh edge         build the Edge 1040 variant
#     ./build.sh both         build both variants
#     ./build.sh all          build both variants and the launcher icons
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONKEYC="${MONKEYC:-monkeyc}"
DEVICE="${DEVICE:-}"

if ! command -v "${MONKEYC}" >/dev/null 2>&1; then
    echo "error: ${MONKEYC} was not found." >&2
    echo "       Install the Connect IQ SDK and set MONKEYC to its monkeyc binary." >&2
    exit 2
fi

build_variant() {
    local name="$1"
    local jungle="$2"
    local output="${HERE}/build/${name}.prg"

    echo "==> building ${name}"
    mkdir -p "${HERE}/build"

    local args=(
        -f "${jungle}"
        -o "${output}"
        -d
    )
    if [[ -n "${GARMIN_DEVELOPER_KEY:-}" ]]; then
        args+=(-k "${GARMIN_DEVELOPER_KEY}")
    elif [[ -n "${GARMIN_DEVELOPER_KEYS:-}" ]]; then
        args+=(-l "${GARMIN_DEVELOPER_KEYS}")
    fi

    "${MONKEYC}" "${args[@]}"
    echo "    wrote ${output}"
}

case "${1:-venu}" in
    venu)
        build_variant "venu" "${HERE}/monkey.jungle"
        ;;
    edge)
        build_variant "edge" "${HERE}/monkey-edge.jungle"
        ;;
    both)
        build_variant "venu" "${HERE}/monkey.jungle"
        build_variant "edge" "${HERE}/monkey-edge.jungle"
        ;;
    all)
        python3 "${HERE}/tools/make_launcher_icon.py"
        build_variant "venu" "${HERE}/monkey.jungle"
        build_variant "edge" "${HERE}/monkey-edge.jungle"
        ;;
    *)
        echo "usage: $0 [venu|edge|both|all]" >&2
        exit 2
        ;;
esac

echo "done"
