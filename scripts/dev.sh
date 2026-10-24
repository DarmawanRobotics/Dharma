#!/usr/bin/env bash
# Dev container helper (Linux / macOS): one container per ROS distro, see compose.yaml.
#
#   scripts/dev.sh [--distro foxy|humble|jazzy] <command> [args]
#
#   up             import the stack if missing, build the image if needed, start the container
#   shell          interactive shell inside (ROS and the workspace sourced)
#   build [args]   colcon build inside (args go to colcon, e.g. --packages-up-to robot_bringup)
#   test [args]    colcon test + colcon test-result inside
#   vnc            print the VNC / noVNC addresses (opens Screen Sharing on macOS)
#   down           stop and remove the container (build/install/log volumes are kept)
#   clean          down, then delete this distro's build/install/log volumes
#   import [--update]  vcs import dharma.repos and external.repos into src/ (--update: move
#                  existing checkouts to the listed versions too)
#
# Env: DHARMA_DISTRO (default distro, humble), VNC_PASSWORD (dharma), VNC=0 (no desktop),
#      USER_UID / USER_GID (container user, default 1000)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

usage() {
    sed -n '2,/^set -/p' "$0" | sed -e '$d' -e 's/^# \{0,1\}//'
}

DISTRO="${DHARMA_DISTRO:-humble}"
ARGS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --distro) DISTRO="${2:-}"; shift 2 || { usage; exit 1; } ;;
        --distro=*) DISTRO="${1#*=}"; shift ;;
        -h | --help) usage; exit 0 ;;
        *) ARGS+=("$1"); shift ;;
    esac
done
set -- "${ARGS[@]+"${ARGS[@]}"}"
case "$DISTRO" in
    foxy) VNC_PORT=5903 NOVNC_PORT=6082 ;;
    humble) VNC_PORT=5901 NOVNC_PORT=6080 ;;
    jazzy) VNC_PORT=5902 NOVNC_PORT=6081 ;;
    *) echo "unknown distro '$DISTRO': foxy, humble or jazzy" >&2; exit 1 ;;
esac
SERVICE="dev-$DISTRO"
compose() { docker compose --profile "$DISTRO" "$@"; }

# Run a command in the container with ROS and the workspace sourced (arguments stay quoted).
in_container() {
    local tty=() quoted
    [[ -t 0 && -t 1 ]] || tty=(-T)
    printf -v quoted ' %q' "$@"
    compose exec "${tty[@]}" "$SERVICE" bash -c \
        "source /opt/ros/$DISTRO/setup.bash && cd \"\$WS\" \
&& { [ ! -f install/setup.bash ] || source install/setup.bash; } &&$quoted"
}

import_repos() {
    local flags=(--recursive --skip-existing)
    [[ "${1:-}" == "--update" ]] && flags=(--recursive)
    if ! command -v vcs > /dev/null; then
        echo "vcs not found: pip install vcstool (or apt install python3-vcstool)" >&2
        return 1
    fi
    vcs import "${flags[@]}" src < dharma.repos
    vcs import "${flags[@]}" src < external.repos
}

project_name() {
    echo "${COMPOSE_PROJECT_NAME:-$(sed -n 's/^name: *//p' compose.yaml)}"
}

case "${1:-}" in
    up)
        if [[ ! -d src/dharma ]]; then
            import_repos || echo "warning: the stack is not imported (scripts/dev.sh import)" >&2
        fi
        compose up -d --build "$SERVICE"
        echo "$SERVICE up: VNC localhost:$VNC_PORT, noVNC http://localhost:$NOVNC_PORT/vnc.html"
        echo "password: ${VNC_PASSWORD:-dharma}"
        ;;
    shell) compose exec "$SERVICE" bash ;;
    build) shift; in_container colcon build "$@" ;;
    test)
        shift
        in_container colcon test "$@"
        in_container colcon test-result --verbose
        ;;
    vnc)
        echo "VNC   vnc://localhost:$VNC_PORT  (password: ${VNC_PASSWORD:-dharma})"
        echo "noVNC http://localhost:$NOVNC_PORT/vnc.html?resize=remote&autoconnect=true"
        if [[ "$(uname -s)" == Darwin ]]; then open "vnc://localhost:$VNC_PORT"; fi
        ;;
    down) compose stop "$SERVICE" && compose rm -f "$SERVICE" ;;
    clean)
        compose stop "$SERVICE" && compose rm -f "$SERVICE"
        project="$(project_name)"
        for volume in build install log; do
            docker volume rm "${project}_${volume}-$DISTRO" 2> /dev/null || true
        done
        echo "removed the $DISTRO build/install/log volumes"
        ;;
    import) shift; import_repos "$@" ;;
    *) usage; exit 1 ;;
esac
