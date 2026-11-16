#!/usr/bin/env bash
set -eo pipefail
base_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$base_dir"
source /opt/ros/kilted/setup.bash
source "$HOME/sensores_ws/install/setup.bash"
exec python3 -u "$base_dir/laboratorio.py" "$@"
