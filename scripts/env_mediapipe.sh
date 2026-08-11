#!/bin/bash
# Source this script before running MediaPipe, OpenCV, or this ROS 2 package on MES20.
#
# Usage from the source tree:
#   source scripts/env_mediapipe.sh
#   source scripts/env_mediapipe.sh --ros
#
# Usage after colcon build:
#   PKG_SHARE="$(ros2 pkg prefix topsbot_hand_det_mediapipe)/share/topsbot_hand_det_mediapipe"
#   source "$PKG_SHARE/scripts/env_mediapipe.sh" --ros
set -e

export LD_LIBRARY_PATH=/usr/lib/riscv64-linux-gnu:${LD_LIBRARY_PATH:-}

if [ "${1:-}" = "--ros" ]; then
  if [ -f /opt/ros/humble/setup.bash ]; then
    # shellcheck source=/dev/null
    source /opt/ros/humble/setup.bash
    export LD_LIBRARY_PATH=/opt/ros/humble/lib:/usr/lib/riscv64-linux-gnu:${LD_LIBRARY_PATH:-}
  else
    echo "WARN: /opt/ros/humble/setup.bash not found" >&2
  fi
fi
