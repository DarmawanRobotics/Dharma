#!/usr/bin/env bash
# Check or install what the stack needs on a robot computer, a dev machine or in the dev image.
#
#   scripts/setup.sh                       # same as: check
#   scripts/setup.sh check                 # status of every component
#   scripts/setup.sh install               # install the default components that are missing
#   scripts/setup.sh install livox build   # only these
#   scripts/setup.sh install all           # every component, service included
#
# Components: ros tools repos livox rosdep build service
#   ros      ROS 2 $ROS_DISTRO from packages.ros.org (ros-base)
#   tools    colcon, rosdep, vcstool, git, cmake, tmux, the Python packages of the stack
#   repos    the stack (dharma.repos) and the external packages (external.repos) under src/
#   livox    Livox-SDK2 (for livox_ros_driver2)
#   rosdep   the system dependencies of every package under src/
#   build    colcon build of the workspace
#   service  a systemd unit running `ros2 launch robot_bringup robot.launch.py` at boot
# Env: ROS_DISTRO (humble), LIVOX_SDK_REF (master), BUILD_WORKERS / BUILD_JOBS (lower them when
#      the build runs out of memory), SERVICE_NAME (robot_bringup), FORCE=1 (reinstall anyway)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROS_DISTRO="${ROS_DISTRO:-humble}"
LIVOX_SDK_REPO="${LIVOX_SDK_REPO:-https://github.com/Livox-SDK/Livox-SDK2.git}"
LIVOX_SDK_REF="${LIVOX_SDK_REF:-master}"
BUILD_WORKERS="${BUILD_WORKERS:-}"
BUILD_JOBS="${BUILD_JOBS:-}"
BRINGUP_PACKAGE=robot_bringup
SERVICE_NAME="${SERVICE_NAME:-$BRINGUP_PACKAGE}"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"
ENV_FILE="/etc/$SERVICE_NAME/robot.env"
BUILD_STAMP="$ROOT/install/.build_commit"

ALL=(ros tools repos livox rosdep build service)
DEFAULT_INSTALL=(tools repos livox rosdep build)

SUDO=$([[ "$(id -u)" -eq 0 ]] && echo "" || echo "sudo")
IN_DOCKER=$([[ -f /.dockerenv ]] && echo 1 || echo 0)
if [[ -t 1 ]]; then
    GREEN=$'\e[32m' RED=$'\e[31m' YELLOW=$'\e[33m' BOLD=$'\e[1m' RESET=$'\e[0m'
else
    GREEN="" RED="" YELLOW="" BOLD="" RESET=""
fi

log() { echo "${BOLD}==>${RESET} $*"; }
usage() { sed -n '2,/^set -/p' "$0" | sed -e '$d' -e 's/^# \{0,1\}//'; }
apt_install() {
    $SUDO apt-get update -qq || log "${YELLOW}apt-get update had errors (check the mirrors)${RESET}"
    $SUDO apt-get -o DPkg::Lock::Timeout=180 install -y --no-install-recommends "$@"
}
source_ros() {
    set +u
    # shellcheck disable=SC1090
    source "/opt/ros/$ROS_DISTRO/setup.bash"
    set -u
}

# ---------------------------------------------------------------- components
# Each component has check_<name> (exit 0 = ok, prints one detail line) and install_<name>.

check_ros() {
    [[ -f "/opt/ros/$ROS_DISTRO/setup.bash" ]] && echo "/opt/ros/$ROS_DISTRO" && return 0
    echo "ROS 2 $ROS_DISTRO not found"
    return 1
}
install_ros() {
    apt_install software-properties-common curl gnupg lsb-release locales
    $SUDO add-apt-repository -y universe
    $SUDO curl -fsSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
        -o /usr/share/keyrings/ros-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo "$UBUNTU_CODENAME") main" \
        | $SUDO tee /etc/apt/sources.list.d/ros2.list > /dev/null
    apt_install "ros-$ROS_DISTRO-ros-base"
}

TOOLS=(colcon rosdep vcs git cmake g++ tmux curl)
check_tools() {
    local missing=() cmd
    for cmd in "${TOOLS[@]}"; do
        command -v "$cmd" > /dev/null || missing+=("$cmd")
    done
    python3 -c 'import loguru, scipy, yaml' 2> /dev/null || missing+=("python3-loguru/scipy/yaml")
    [[ ${#missing[@]} -eq 0 ]] && echo "${TOOLS[*]}" && return 0
    echo "missing: ${missing[*]}"
    return 1
}
install_tools() {
    apt_install python3-colcon-common-extensions python3-rosdep python3-vcstool python3-pip \
        python3-loguru python3-scipy python3-yaml git cmake build-essential tmux curl \
        ca-certificates
}

repo_paths() { # the checkout paths of a .repos file
    sed -nE 's/^  ([A-Za-z0-9_./-]+):[[:space:]]*$/\1/p' "$1"
}
check_repos() {
    local missing=() path
    for path in $(repo_paths "$ROOT/dharma.repos") $(repo_paths "$ROOT/external.repos"); do
        [[ -d "$ROOT/src/$path/.git" ]] || missing+=("$path")
    done
    [[ ${#missing[@]} -eq 0 ]] && echo "src/: every repository of dharma.repos, external.repos" \
        && return 0
    echo "not checked out: ${missing[*]}"
    return 1
}
install_repos() {
    command -v vcs > /dev/null || apt_install python3-vcstool
    vcs import --recursive --skip-existing "$ROOT/src" < "$ROOT/dharma.repos"
    vcs import --recursive --skip-existing "$ROOT/src" < "$ROOT/external.repos"
}

check_livox() {
    [[ -f /usr/local/lib/liblivox_lidar_sdk_shared.so ]] \
        && echo "/usr/local/lib/liblivox_lidar_sdk_shared.so" && return 0
    echo "Livox-SDK2 not installed"
    return 1
}
install_livox() {
    local tmp
    tmp=$(mktemp -d)
    git clone --depth 1 --branch "$LIVOX_SDK_REF" "$LIVOX_SDK_REPO" "$tmp"
    # GCC 13 (Ubuntu 24.04) no longer includes <cstdint> transitively; the SDK relies on it
    cmake -S "$tmp" -B "$tmp/build" -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_CXX_FLAGS="-include cstdint"
    cmake --build "$tmp/build" -j"$(nproc)"
    $SUDO cmake --install "$tmp/build"
    $SUDO ldconfig
    rm -rf "$tmp"
}

check_rosdep() {
    check_ros > /dev/null || { echo "needs ROS"; return 1; }
    [[ -d /etc/ros/rosdep/sources.list.d ]] || { echo "rosdep not initialised"; return 1; }
    source_ros
    local report=/tmp/dharma_rosdep.log
    rosdep check --from-paths "$ROOT/src" --ignore-src --rosdistro "$ROS_DISTRO" \
        > "$report" 2>&1 && echo "all system dependencies installed" && return 0
    echo "missing keys, see $report"
    return 1
}
install_rosdep() {
    [[ -d /etc/ros/rosdep/sources.list.d ]] || $SUDO rosdep init
    source_ros
    rosdep update --rosdistro "$ROS_DISTRO"
    rosdep install --from-paths "$ROOT/src" --ignore-src -r -y --rosdistro "$ROS_DISTRO"
}

check_build() {
    [[ -f "$ROOT/install/setup.bash" ]] || { echo "workspace not built"; return 1; }
    local n built head
    n=$(find "$ROOT/install" -mindepth 1 -maxdepth 1 -type d | wc -l)
    head=$(git -C "$ROOT" rev-parse --short HEAD 2> /dev/null || echo unknown)
    built=$(cat "$BUILD_STAMP" 2> /dev/null || echo unknown)
    [[ "$built" == "$head" ]] || { echo "built from $built, source is $head: rebuild"; return 1; }
    echo "$n packages in install/, built from $head"
}
install_build() {
    source_ros
    local args=(--cmake-args -DCMAKE_BUILD_TYPE=Release)
    [[ -n "$BUILD_WORKERS" ]] && args=(--parallel-workers "$BUILD_WORKERS" "${args[@]}")
    [[ -n "$BUILD_JOBS" ]] && export MAKEFLAGS="-j$BUILD_JOBS"
    (cd "$ROOT" && colcon build "${args[@]}")
    git -C "$ROOT" rev-parse --short HEAD > "$BUILD_STAMP" 2> /dev/null || echo unknown > "$BUILD_STAMP"
}

# The launch arguments robot_ns, robot_driver, odometry, site and sites_dir default to these.
env_template() {
    printf '%s\n' \
        "# $SERVICE_NAME.service environment (also read by bash): no comments after values" \
        "ROS_DISTRO=$ROS_DISTRO" 'ROS_DOMAIN_ID=0' 'RMW_IMPLEMENTATION=rmw_fastrtps_cpp' \
        'ROBOT_NS=robot' 'ROBOT_DRIVER=' 'ODOMETRY=fast_lio' 'SITE=' "SITES_DIR=$HOME/sites" \
        'OPENBLAS_NUM_THREADS=1' 'OMP_NUM_THREADS=1'
}
service_unit() {
    cat << EOF
[Unit]
Description=Robot stack ($BRINGUP_PACKAGE)
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=$(id -un)
WorkingDirectory=$ROOT
EnvironmentFile=-$ENV_FILE
Environment=PYTHONUNBUFFERED=1
Environment=RCUTILS_COLORIZED_OUTPUT=0
ExecStart=/bin/bash -c 'source /opt/ros/$ROS_DISTRO/setup.bash && source $ROOT/install/setup.bash && exec ros2 launch $BRINGUP_PACKAGE robot.launch.py'
Restart=always
RestartSec=5
# SIGINT to ros2 launch only: it stops every node once; leftovers get SIGKILL after the timeout
KillSignal=SIGINT
KillMode=mixed
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF
}
check_service() {
    [[ "$IN_DOCKER" == "1" ]] && echo "skipped in docker" && return 0
    [[ -f "$SERVICE_FILE" ]] || { echo "$SERVICE_NAME.service not installed"; return 1; }
    service_unit | cmp -s - "$SERVICE_FILE" \
        || { echo "$SERVICE_FILE is outdated (other path or user)"; return 1; }
    systemctl is-enabled "$SERVICE_NAME.service" > /dev/null 2>&1 \
        || { echo "$SERVICE_NAME.service installed but not enabled at boot"; return 1; }
    echo "$SERVICE_NAME.service enabled ($(systemctl is-active "$SERVICE_NAME.service"))"
}
install_service() {
    if [[ ! -f "$ENV_FILE" ]]; then
        env_template | $SUDO install -D -m 640 -g "$(id -gn)" /dev/stdin "$ENV_FILE"
        log "created $ENV_FILE: set ROBOT_DRIVER, ROBOT_NS and SITE"
    fi
    service_unit | $SUDO tee "$SERVICE_FILE" > /dev/null
    $SUDO systemctl daemon-reload
    $SUDO systemctl enable "$SERVICE_NAME.service"
    log "start: sudo systemctl restart $SERVICE_NAME   logs: journalctl -fu $SERVICE_NAME"
}

# ---------------------------------------------------------------- driver

check_one() {
    local name=$1 detail status
    if detail=$("check_$name" 2>&1); then
        status="${GREEN}ok     ${RESET}"
    else
        status="${RED}missing${RESET}"
    fi
    printf '  %-10s %s  %s\n' "$name" "$status" "$(echo "$detail" | tail -n1)"
    [[ "$status" == *ok* ]]
}

do_check() {
    local failed=0 name
    echo "${BOLD}setup ($([[ $IN_DOCKER == 1 ]] && echo docker || echo host), $(uname -m), ROS $ROS_DISTRO)${RESET}"
    for name in "${ALL[@]}"; do
        check_one "$name" || failed=$((failed + 1))
    done
    if [[ $failed -eq 0 ]]; then
        echo "${GREEN}everything is ready${RESET}"
    else
        echo "${YELLOW}$failed component(s) need attention: scripts/setup.sh install <component>${RESET}"
    fi
}

do_install() {
    local targets=("$@") name
    [[ ${#targets[@]} -eq 0 ]] && targets=("${DEFAULT_INSTALL[@]}")
    [[ "${targets[0]}" == "all" ]] && targets=("${ALL[@]}")
    for name in "${targets[@]}"; do
        declare -F "install_$name" > /dev/null || { echo "${RED}unknown component: $name${RESET}"; exit 1; }
        if [[ "${FORCE:-0}" != "1" ]] && "check_$name" > /dev/null 2>&1; then
            echo "  $name: already ok"
            continue
        fi
        log "installing $name"
        "install_$name"
        check_one "$name" || { echo "${RED}$name still not ok after install${RESET}"; exit 1; }
    done
}

case "${1:-check}" in
    check) do_check ;;
    install) shift; do_install "$@" ;;
    -h | --help) usage ;;
    *) usage; exit 1 ;;
esac
