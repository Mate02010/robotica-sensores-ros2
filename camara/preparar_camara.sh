#!/usr/bin/env bash
set -eo pipefail
base_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source /opt/ros/kilted/setup.bash
mkdir -p "$HOME/camara_primesense_ws/src"
if [ ! -d "$HOME/camara_primesense_ws/src/openni2_camera" ]; then
    git clone --branch jazzy https://github.com/ros-drivers/openni2_camera.git "$HOME/camara_primesense_ws/src/openni2_camera"
fi
cd "$HOME/camara_primesense_ws"
git -C src/openni2_camera rev-parse HEAD
if ! colcon build --symlink-install --packages-select openni2_camera --cmake-args -DBUILD_TESTING=OFF > "$base_dir/COMPILACION_OPENNI2.log" 2>&1; then
    tail -60 "$base_dir/COMPILACION_OPENNI2.log"
    exit 1
fi
tail -8 "$base_dir/COMPILACION_OPENNI2.log"
source install/setup.bash
ros2 pkg prefix openni2_camera
ros2 launch openni2_camera camera_with_cloud.launch.py --show-args
