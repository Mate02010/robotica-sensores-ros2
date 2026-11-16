"""Graba imagenes completas en rosbag y estadisticas por cuadro en CSV."""
import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
import re
import signal
import shutil
import subprocess
import time
import unicodedata
from zoneinfo import ZoneInfo
import numpy as np
import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from datos_imagen import estadisticas, matriz
from ver_datos import TEMAS

BASE = Path(__file__).resolve().parent


def parametros(nodo):
    r = subprocess.run(['ros2', 'param', 'dump', nodo], capture_output=True, text=True, timeout=12)
    return r.stdout if r.returncode == 0 else r.stderr


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--nombre', default='ensayo camara')
    p.add_argument('--segundos', type=float, default=20)
    args = p.parse_args()
    nombre = re.sub(r'[^A-Za-z0-9_-]+', '_', unicodedata.normalize('NFKD', args.nombre).encode('ascii', 'ignore').decode()).strip('_-')[:100]
    if not nombre or not 1 <= args.segundos <= 600:
        p.error('Usar nombre descriptivo y 1..600 segundos.')
    fecha = datetime.now(ZoneInfo('America/Bogota'))
    carpeta = BASE / 'registros' / (fecha.strftime('%Y%m%d_%H%M%S_%f') + '_' + nombre)
    carpeta.mkdir(parents=True, exist_ok=False)
    # Las imagenes se escriben primero en el disco Linux: SQLite es mucho mas
    # lento en /mnt/c. La copia final queda junto a los demas archivos del ensayo.
    bolsa_local = Path.home() / 'camara_primesense_ws/bolsas' / carpeta.name
    bolsa_local.parent.mkdir(parents=True, exist_ok=True)
    for nodo, etiqueta in [('/camera/driver', 'driver'), ('/filtro_profundidad', 'filtro')]:
        (carpeta / (etiqueta + '_inicio.yaml')).write_text(parametros(nodo))
    rclpy.init()
    node = rclpy.create_node('registro_camara')
    archivo = (carpeta / 'cuadros.csv').open('w', newline='')
    campos = ['tema', 'stamp_sec', 'stamp_nanosec', 'encoding', 'ancho', 'alto', 'validos', 'pixeles',
              'porcentaje_valido', 'min_m', 'max_m', 'media_m', 'centro_m']
    escritor = csv.DictWriter(archivo, fieldnames=campos)
    escritor.writeheader()
    muestras = {}
    tiempos = {t: [] for t in TEMAS}
    totales = {t: dict(cuadros=0, pixeles=0, validos=0, min_m=None, max_m=None) for t in TEMAS}

    def recibir(msg, tema):
        e = estadisticas(msg)
        tiempos[tema].append(time.monotonic())
        escritor.writerow(dict(tema=tema, stamp_sec=msg.header.stamp.sec,
                                stamp_nanosec=msg.header.stamp.nanosec, encoding=msg.encoding, **e))
        s = totales[tema]
        s['cuadros'] += 1
        s['pixeles'] += e['pixeles']
        s['validos'] += e['validos']
        if e['min_m'] is not None:
            s['min_m'] = e['min_m'] if s['min_m'] is None else min(s['min_m'], e['min_m'])
            s['max_m'] = e['max_m'] if s['max_m'] is None else max(s['max_m'], e['max_m'])
        etiqueta = 'original' if tema == TEMAS[0] else 'filtrada'
        if etiqueta + '_primera' not in muestras:
            muestras[etiqueta + '_primera'] = matriz(msg).copy()
        muestras[etiqueta + '_ultima'] = matriz(msg).copy()

    subs = [node.create_subscription(Image, tema, lambda msg, tema=tema: recibir(msg, tema),
                                     qos_profile_sensor_data) for tema in TEMAS]
    temas_bag = [*TEMAS, '/camera/rgb/image_raw', '/camera/rgb/camera_info',
                 '/camera/depth_raw/camera_info', '/camera/depth_filtrada/camera_info',
                 '/tf_static', '/parameter_events']
    log = (carpeta / 'rosbag.log').open('w')
    bag = subprocess.Popen(['ros2', 'bag', 'record', '--storage', 'sqlite3', '-o', str(bolsa_local),
                            '--disable-keyboard-controls', '--topics', *temas_bag],
                           stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    inicio = time.monotonic()
    print(f'Grabando {args.segundos:g} segundos en {carpeta}', flush=True)
    print('Rosbag guarda imagenes; CSV guarda estadisticas por cuadro. NPZ conserva primeras/ultimas profundidades.', flush=True)
    try:
        while time.monotonic() - inicio < args.segundos:
            rclpy.spin_once(node, timeout_sec=0.05)
            if bag.poll() is not None:
                raise RuntimeError('Rosbag termino antes de tiempo; revisar rosbag.log.')
    except KeyboardInterrupt:
        pass
    finally:
        duracion = time.monotonic() - inicio
        if bag.poll() is None:
            bag.send_signal(signal.SIGINT)
            try:
                bag.wait(timeout=45)
            except subprocess.TimeoutExpired:
                bag.terminate()
                try:
                    bag.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    bag.kill()
                    bag.wait(timeout=5)
        archivo.close()
        log.close()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        for tema, s in totales.items():
            ts = tiempos[tema]
            s['hz_recibidos'] = (len(ts)-1)/(ts[-1]-ts[0]) if len(ts) > 1 else None
            s['porcentaje_valido'] = 100 * s['validos']/s['pixeles'] if s['pixeles'] else 0
        resultado = dict(nombre_ensayo=args.nombre, inicio_bogota=fecha.isoformat(), duracion_s=duracion,
                         rosbag_exit_code=bag.returncode, datos=totales,
                         rosbag_original_ubuntu=str(bolsa_local),
                         nota='CSV y rosbag son suscriptores independientes. NPZ usa valores originales/encoding del driver.')
        (carpeta / 'resumen.json').write_text(json.dumps(resultado, indent=2, allow_nan=False))
        if muestras:
            np.savez_compressed(carpeta / 'muestras_profundidad.npz', **muestras)
    for nodo, etiqueta in [('/camera/driver', 'driver'), ('/filtro_profundidad', 'filtro')]:
        (carpeta / (etiqueta + '_final.yaml')).write_text(parametros(nodo))
    print('Copiando la grabacion cerrada a la carpeta del ensayo...', flush=True)
    shutil.copytree(bolsa_local, carpeta / 'rosbag')
    info = subprocess.run(['ros2', 'bag', 'info', str(bolsa_local)], capture_output=True, text=True, timeout=15)
    (carpeta / 'rosbag_info.txt').write_text(info.stdout + info.stderr)
    print(json.dumps(resultado, indent=2))
    print('Registro guardado:', carpeta)
    if not totales[TEMAS[0]]['cuadros']:
        print('AVISO: no llegaron imagenes de profundidad; revisar la adquisicion.')
    return 0 if totales[TEMAS[0]]['cuadros'] and info.returncode == 0 and bag.returncode == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
