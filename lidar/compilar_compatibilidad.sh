#!/usr/bin/env bash
set -eo pipefail
base_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source /opt/ros/kilted/setup.bash
python3 "$base_dir/compatibilidad_firmware.py"
cd "$HOME/sensores_ws"
if ! colcon build --symlink-install --packages-select sllidar_ros2 --cmake-args -DCMAKE_BUILD_TYPE=Release > "$base_dir/COMPILACION_COMPATIBILIDAD_2026-11-13.log" 2>&1; then
    tail -50 "$base_dir/COMPILACION_COMPATIBILIDAD_2026-11-13.log"
    exit 1
fi
tail -5 "$base_dir/COMPILACION_COMPATIBILIDAD_2026-11-13.log"
exec bash "$base_dir/laboratorio.sh" --sin-menu
