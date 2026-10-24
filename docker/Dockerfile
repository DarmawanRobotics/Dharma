# syntax=docker/dockerfile:1.6
# Dharma dev container: ROS 2 (humble | jazzy), every rosdep key of src/, Livox-SDK2, the lint
# tools, and an XFCE desktop over VNC / noVNC for RViz. Built by compose.yaml (scripts/dev.sh up).
ARG ROS_DISTRO=humble

# Only the package manifests, so the rosdep layer is rebuilt when dependencies change, not code.
FROM alpine:3.20 AS manifests
COPY src /src
RUN find /src -type f ! -name package.xml ! -name '*_IGNORE' -delete \
    && find /src -depth -type d -empty -delete \
    && mkdir -p /src

FROM ros:${ROS_DISTRO}-ros-base
ARG ROS_DISTRO
ARG USERNAME=robot
ARG USER_UID=1000
ARG USER_GID=1000
ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    WS=/home/${USERNAME}/ws \
    DISPLAY=:1 \
    LIBGL_ALWAYS_SOFTWARE=1 \
    QT_X11_NO_MITSHM=1 \
    PIPX_HOME=/opt/pipx \
    PIPX_BIN_DIR=/usr/local/bin

# Desktop (TigerVNC + minimal XFCE + noVNC), dev tools, RViz and the Python packages of the stack
RUN apt-get update && apt-get install -y --no-install-recommends \
        tigervnc-standalone-server tigervnc-tools novnc websockify dbus-x11 \
        xfce4-session xfwm4 xfce4-panel xfdesktop4 xfce4-settings xfce4-terminal thunar \
        adwaita-icon-theme fonts-dejavu-core libgl1-mesa-dri mesa-utils \
        python3-colcon-common-extensions python3-vcstool python3-pip python3-pytest pipx \
        python3-loguru python3-scipy python3-yaml \
        build-essential cmake git tmux sudo curl ca-certificates iputils-ping nano less \
        bash-completion shellcheck xclip \
        ros-${ROS_DISTRO}-rviz2 \
    && rm -rf /var/lib/apt/lists/*

# Lint: the same hooks as CI (pre-commit) and ruff at the version of the hook
RUN pipx install "pre-commit>=3.5" && pipx install "ruff==0.16.9"

# Sensor SDK through the same installer the robot uses
COPY scripts/setup.sh /opt/dharma/setup.sh
RUN /opt/dharma/setup.sh install livox

# ROS dependencies of every package in src/ (vendor packages that are not checked out: skipped)
COPY --from=manifests /src /tmp/src
RUN apt-get update \
    && rosdep update --rosdistro "${ROS_DISTRO}" \
    && rosdep install --from-paths /tmp/src --ignore-src -r -y --rosdistro "${ROS_DISTRO}" \
        --skip-keys "livox_ros_driver2 fast_lio legkilo" \
    && rm -rf /var/lib/apt/lists/* /tmp/src

# User with the host's uid (the noble images already have uid 1000: ubuntu)
RUN if id -u ubuntu > /dev/null 2>&1; then userdel -r ubuntu || true; fi \
    && groupadd --gid "${USER_GID}" "${USERNAME}" \
    && useradd --uid "${USER_UID}" --gid "${USER_GID}" -m -s /bin/bash "${USERNAME}" \
    && echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > "/etc/sudoers.d/${USERNAME}" \
    && chmod 0440 "/etc/sudoers.d/${USERNAME}" \
    && mkdir -p "${WS}/build" "${WS}/install" "${WS}/log" "/home/${USERNAME}/.colcon" \
    && mkdir -p /tmp/.X11-unix && chmod 1777 /tmp/.X11-unix \
    && printf '%s\n' \
        "source /opt/ros/${ROS_DISTRO}/setup.bash" \
        '[ -f "$WS/install/setup.bash" ] && source "$WS/install/setup.bash"' \
        'f=/usr/share/colcon_argcomplete/hook/colcon-argcomplete.bash; [ -f "$f" ] && source "$f"' \
        'cd "$WS"' >> "/home/${USERNAME}/.bashrc" \
    && chown -R "${USERNAME}:${USERNAME}" "/home/${USERNAME}"

# XFCE: no compositor (useless over VNC, slows software-rendered RViz)
RUN mkdir -p "/home/${USERNAME}/.config/xfce4/xfconf/xfce-perchannel-xml" \
    && printf '%s\n' \
        '<?xml version="1.0" encoding="UTF-8"?>' \
        '<channel name="xfwm4" version="1.0">' \
        '  <property name="general" type="empty">' \
        '    <property name="use_compositing" type="bool" value="false"/>' \
        '  </property>' \
        '</channel>' \
        > "/home/${USERNAME}/.config/xfce4/xfconf/xfce-perchannel-xml/xfwm4.xml" \
    && chown -R "${USERNAME}:${USERNAME}" "/home/${USERNAME}/.config"

COPY --chown=${USERNAME}:${USERNAME} docker/colcon_defaults.yaml /home/${USERNAME}/.colcon/defaults.yaml
COPY --chown=${USERNAME}:${USERNAME} docker/tmux/tmux.conf /home/${USERNAME}/.tmux.conf
COPY docker/entrypoint.sh /entrypoint.sh

USER ${USERNAME}
WORKDIR ${WS}
EXPOSE 5901 6080
ENTRYPOINT ["/entrypoint.sh"]
CMD ["sleep", "infinity"]
