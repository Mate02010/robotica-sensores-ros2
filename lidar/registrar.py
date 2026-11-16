"""Registra datos reales en rosbag, CSV y un resumen; no sobrescribe ensayos."""
import argparse
import csv
from datetime import datetime
import json
import math
from pathlib import Path
import re
import signal
import subprocess
import time
import unicodedata
from zoneinfo import ZoneInfo

import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan

BASE = Path(__file__).resolve().parent


def nombre_carpeta(nombre):
    texto = unicodedata.normalize('NFKD', nombre).encode('ascii', 'ignore').decode()
    return re.sub(r'[^A-Za-z0-9_-]+', '_', texto).strip('_-')[:100]


def parametros(nodo):
    resultado = subprocess.run(['ros2', 'param', 'dump', nodo], capture_output=True, text=True, timeout=12)
    return resultado.stdout if resultado.returncode == 0 else resultado.stderr


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--segundos', type=float, default=30)
    parser.add_argument('--nombre', default='ensayo')
    args = parser.parse_args()
    nombre = nombre_carpeta(args.nombre)
    if not 1 <= args.segundos <= 3600:
        parser.error('La duracion debe estar entre 1 y 3600 segundos.')
    if not nombre:
        parser.error('Escribir un nombre que contenga al menos una letra o numero.')
    if nombre != args.nombre:
        print(f'Nombre de carpeta: {nombre} (espacios y signos normalizados).', flush=True)
    ahora = datetime.now(ZoneInfo('America/Bogota'))
    carpeta = BASE / 'registros' / (ahora.strftime('%Y%m%d_%H%M%S_%f') + '_' + nombre)
    carpeta.mkdir(parents=True, exist_ok=False)
    for nodo in ('/sllidar_node', '/filtro_lidar'):
        (carpeta / (nodo[1:] + '_inicio.yaml')).write_text(parametros(nodo))
    rclpy.init()
    node = rclpy.create_node('registro_lidar')
    estadisticas = {tema: {'barridos': 0, 'puntos': 0, 'validos': 0,
                            'min_m': None, 'max_m': None, 'primero': None, 'ultimo': None}
                    for tema in ('/scan', '/scan_filtrado')}
    archivo = (carpeta / 'puntos.csv').open('w', newline='')
    csv_puntos = csv.writer(archivo)
    csv_puntos.writerow(['tema', 'barrido', 'stamp_sec', 'stamp_nanosec', 'frame',
                         'indice', 'angulo_rad', 'distancia_m', 'intensidad', 'valido', 'x_m', 'y_m'])
    resumen_archivo = (carpeta / 'barridos.csv').open('w', newline='')
    csv_barridos = csv.writer(resumen_archivo)
    csv_barridos.writerow(['tema', 'stamp_sec', 'stamp_nanosec', 'puntos', 'validos',
                           'min_m', 'max_m', 'angle_increment_rad', 'scan_time_s'])

    def recibir(msg, tema):
        e = estadisticas[tema]
        t = time.monotonic()
        e['primero'] = t if e['primero'] is None else e['primero']
        e['ultimo'] = t
        e['barridos'] += 1
        validos = []
        for i, r in enumerate(msg.ranges):
            a = msg.angle_min + i * msg.angle_increment
            valido = math.isfinite(r) and msg.range_min <= r <= msg.range_max
            intensidad = msg.intensities[i] if i < len(msg.intensities) else ''
            csv_puntos.writerow([tema, e['barridos'], msg.header.stamp.sec, msg.header.stamp.nanosec,
                                 msg.header.frame_id, i, a, r, intensidad, int(valido),
                                 r * math.cos(a) if valido else '', r * math.sin(a) if valido else ''])
            if valido:
                validos.append(r)
        e['puntos'] += len(msg.ranges)
        e['validos'] += len(validos)
        if validos:
            e['min_m'] = min(validos) if e['min_m'] is None else min(e['min_m'], min(validos))
            e['max_m'] = max(validos) if e['max_m'] is None else max(e['max_m'], max(validos))
        csv_barridos.writerow([tema, msg.header.stamp.sec, msg.header.stamp.nanosec, len(msg.ranges),
                               len(validos), min(validos) if validos else '', max(validos) if validos else '',
                               msg.angle_increment, msg.scan_time])

    subs = [node.create_subscription(LaserScan, tema, lambda msg, tema=tema: recibir(msg, tema),
                                     qos_profile_sensor_data) for tema in estadisticas]
    bag_log = (carpeta / 'rosbag.log').open('w')
    bag = subprocess.Popen(['ros2', 'bag', 'record', '--storage', 'sqlite3', '-o', str(carpeta / 'rosbag'),
                            '--qos-profile-overrides-path', str(BASE / 'config/qos_grabacion.yaml'),
                            '--disable-keyboard-controls', '--topics',
                            '/scan', '/scan_filtrado', '/tf', '/tf_static', '/parameter_events'],
                           stdout=bag_log, stderr=subprocess.STDOUT, start_new_session=True)
    inicio = time.monotonic()
    interrumpido = False
    print(f'Grabando {args.segundos:g} segundos en {carpeta}', flush=True)
    try:
        while time.monotonic() - inicio < args.segundos:
            rclpy.spin_once(node, timeout_sec=0.1)
            if bag.poll() is not None:
                raise RuntimeError('Rosbag termino antes de tiempo; revisar rosbag.log.')
    except KeyboardInterrupt:
        interrumpido = True
    finally:
        duracion = time.monotonic() - inicio
        if bag.poll() is None:
            bag.send_signal(signal.SIGINT)
            try:
                bag.wait(timeout=20)
            except subprocess.TimeoutExpired:
                bag.terminate()
                bag.wait(timeout=5)
        bag_log.close()
        archivo.close()
        resumen_archivo.close()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        for tema, e in estadisticas.items():
            intervalo = (e['ultimo'] - e['primero']) if e['barridos'] > 1 else 0
            e['hz_recibidos'] = (e['barridos'] - 1) / intervalo if intervalo > 0 else None
            e['porcentaje_valido'] = 100 * e['validos'] / e['puntos'] if e['puntos'] else 0
            e.pop('primero')
            e.pop('ultimo')
        resultado = {'nombre_ensayo': args.nombre, 'nombre_carpeta': nombre,
                     'inicio_bogota': ahora.isoformat(), 'duracion_s': duracion,
                     'interrumpido': interrumpido, 'rosbag_exit_code': bag.returncode,
                     'datos': estadisticas,
                     'nota': 'CSV y rosbag son suscriptores independientes; sus limites temporales pueden diferir.'}
        (carpeta / 'resumen.json').write_text(json.dumps(resultado, indent=2, allow_nan=False))
    for nodo in ('/sllidar_node', '/filtro_lidar'):
        (carpeta / (nodo[1:] + '_final.yaml')).write_text(parametros(nodo))
    info = subprocess.run(['ros2', 'bag', 'info', str(carpeta / 'rosbag')], capture_output=True, text=True, timeout=15)
    (carpeta / 'rosbag_info.txt').write_text(info.stdout + info.stderr)
    print(json.dumps(resultado, indent=2, allow_nan=False))
    print('Registro guardado:', carpeta)
    if not estadisticas['/scan']['barridos']:
        print('AVISO: no llegaron barridos originales; esta captura no contiene mediciones. Comprobar opcion 1.')
    elif estadisticas['/scan_filtrado']['barridos'] and not estadisticas['/scan_filtrado']['validos']:
        print('AVISO: llegaron barridos, pero ningun punto paso los filtros. Revisar distancia, sector y salto de puntos.')
    return 0 if estadisticas['/scan']['barridos'] and info.returncode == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
