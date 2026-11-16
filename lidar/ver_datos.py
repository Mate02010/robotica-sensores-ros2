"""Muestra en la terminal una tabla de barridos reales, util como evidencia."""
import argparse
from datetime import datetime
import math
import time
from zoneinfo import ZoneInfo

import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--segundos', type=float, default=10)
    args = parser.parse_args()
    rclpy.init()
    node = rclpy.create_node('tabla_datos_lidar')
    anterior = {}
    ultimo_impreso = {}
    recibidos = {'/scan': 0, '/scan_filtrado': 0}
    print('\nMEDICIONES REALES RPLIDAR | ' + datetime.now(ZoneInfo('America/Bogota')).isoformat(timespec='seconds'))
    print('Hz es frecuencia recibida entre barridos; no es una velocidad ordenada al motor.')
    print('Tema            Hora ROS         Hz     Puntos Validos   Min(m) Max(m) Paso(deg)')
    print('-' * 86, flush=True)

    def recibir(msg, tema):
        ahora = time.monotonic()
        previo = anterior.get(tema)
        hz = 1 / (ahora - previo) if previo is not None and ahora > previo else 0
        anterior[tema] = ahora
        recibidos[tema] += 1
        if ahora - ultimo_impreso.get(tema, 0) < 1:
            return
        ultimo_impreso[tema] = ahora
        validos = [r for r in msg.ranges if math.isfinite(r) and msg.range_min <= r <= msg.range_max]
        distancia = lambda r: f'{r:6.2f}' if r is not None else '   ---'
        print(f'{tema:15} {msg.header.stamp.sec}.{msg.header.stamp.nanosec // 1000000:03d} '
              f'{hz:6.2f} {len(msg.ranges):7d} {len(validos):7d} '
              f'{distancia(min(validos) if validos else None)} {distancia(max(validos) if validos else None)} '
              f'{math.degrees(msg.angle_increment):8.3f}', flush=True)

    subs = [node.create_subscription(LaserScan, tema, lambda msg, tema=tema: recibir(msg, tema),
                                     qos_profile_sensor_data) for tema in recibidos]
    limite = time.monotonic() + args.segundos
    try:
        while time.monotonic() < limite:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        print('Barridos recibidos:', recibidos, flush=True)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0 if recibidos['/scan'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
