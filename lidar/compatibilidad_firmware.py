"""Ajuste local explicito para iniciar el modo Standard legado del SDK."""
from pathlib import Path
import subprocess

base = Path.home() / 'sensores_ws/src/sllidar_ros2'
ruta = base / 'src/sllidar_node.cpp'
texto = ruta.read_text()
if 'declare_parameter<bool>("legacy_standard"' not in texto:
    cambios = [
        ('this->declare_parameter<bool>("inverted", false);',
         'this->declare_parameter<bool>("legacy_standard", false);\n        this->declare_parameter<bool>("inverted", false);'),
        ('this->get_parameter_or<bool>("inverted", inverted, false);',
         'this->get_parameter_or<bool>("legacy_standard", legacy_standard, false);\n        this->get_parameter_or<bool>("inverted", inverted, false);'),
        ('ans=drv->startScan(0,1);', 'ans=drv->startScan(false, !legacy_standard);'),
        ('if (scan_mode.empty()) {',
         'if (legacy_standard) {\n            op_result = drv->startScan(false, false, 0, &current_scan_mode);\n        } else if (scan_mode.empty()) {'),
        ('bool inverted = false;', 'bool legacy_standard = false;\n    bool inverted = false;'),
        ('RCLCPP_INFO(this->get_logger(),"Hardware Rev: %d",(int)devinfo.hardware_version);',
         'RCLCPP_INFO(this->get_logger(),"Hardware Rev: %d",(int)devinfo.hardware_version);\n        RCLCPP_INFO(this->get_logger(),"Model code: %d", (int)devinfo.model);'),
    ]
    for viejo, nuevo in cambios:
        if texto.count(viejo) != 1:
            raise ValueError('La fuente cambio; no se aplica automaticamente: ' + viejo)
        texto = texto.replace(viejo, nuevo)
    ruta.write_text(texto)
parche = subprocess.run(['git', '-C', str(base), 'diff', '--', 'src/sllidar_node.cpp'],
                         capture_output=True, text=True, check=True).stdout
(Path(__file__).resolve().parent / 'compatibilidad_firmware_1_15.patch').write_text(parche)
print('Ajuste legado local preparado. No modifica el firmware del equipo.')
