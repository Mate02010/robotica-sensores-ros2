#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/kilted/setup.bash
sensor_ws="$HOME/sensores_ws"
mkdir -p "$sensor_ws/src"
if [ ! -d "$sensor_ws/src/sllidar_ros2" ]; then
    git clone https://github.com/Slamtec/sllidar_ros2.git "$sensor_ws/src/sllidar_ros2"
fi
cd "$sensor_ws"
printf '\n=== Version del controlador ===\n'
git -C src/sllidar_ros2 remote get-url origin
git -C src/sllidar_ros2 rev-parse HEAD
colcon build --symlink-install --packages-select sllidar_ros2 --cmake-args -DCMAKE_BUILD_TYPE=Release
source install/setup.bash
printf '\n=== Ejecutables ===\n'
ros2 pkg executables sllidar_ros2
printf '\n=== Lanzador A1: analisis, sin conectar sensor ===\n'
ros2 launch sllidar_ros2 view_sllidar_a1_launch.py --show-args
printf '\n=== Mapeo instalado ===\n'
ros2 pkg prefix slam_toolbox
ros2 pkg prefix nav2_map_server
printf '\nPreparacion terminada. No se ha probado el hardware.\n'
