"""Verifica el filtrado contra los barridos originales guardados en el rosbag."""
import json
import math
from pathlib import Path
import sqlite3
import yaml
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import LaserScan

base = Path(__file__).resolve().parent
carpeta = sorted((base / 'registros').glob('*_verificacion_real_sector_2m'))[-1]
param = yaml.safe_load((carpeta / 'filtro_lidar_inicio.yaml').read_text())['/filtro_lidar']['ros__parameters']
db = sqlite3.connect(next((carpeta / 'rosbag').glob('*.db3')))
temas = dict(db.execute('SELECT id,name FROM topics'))
mensajes = {'/scan': {}, '/scan_filtrado': {}}
for tema_id, datos in db.execute('SELECT topic_id,data FROM messages ORDER BY timestamp'):
    tema = temas[tema_id]
    if tema in mensajes:
        msg = deserialize_message(datos, LaserScan)
        mensajes[tema][(msg.header.stamp.sec, msg.header.stamp.nanosec)] = msg
pares = mensajes['/scan'].keys() & mensajes['/scan_filtrado'].keys()
assert len(pares) >= 5, 'Faltan pares de barridos originales/filtrados en el rosbag.'
comparados = 0
for instante in pares:
    raw, filtrado = mensajes['/scan'][instante], mensajes['/scan_filtrado'][instante]
    paso = param['salto_puntos']
    indices = list(range(0, len(raw.ranges), paso))
    assert len(filtrado.ranges) == len(indices)
    assert math.isclose(filtrado.angle_increment, raw.angle_increment * paso, abs_tol=1e-7)
    for j, i in enumerate(indices):
        r = raw.ranges[i]
        angulo = (math.degrees(raw.angle_min + i * raw.angle_increment) + 180) % 360 - 180
        valido = (math.isfinite(r) and raw.range_min <= r <= raw.range_max
                  and param['distancia_min_m'] <= r <= param['distancia_max_m']
                  and param['angulo_inicio_deg'] <= angulo <= param['angulo_fin_deg'])
        assert filtrado.ranges[j] == r if valido else math.isinf(filtrado.ranges[j])
        comparados += 1
resultado = {'registro': carpeta.name, 'pares_comparados': len(pares), 'puntos_comparados': comparados,
             'filtrado_corresponde_a_original': True,
             'mensajes_rosbag': {tema: len(msgs) for tema, msgs in mensajes.items()}}
db.close()
(carpeta / 'verificacion_integridad.json').write_text(json.dumps(resultado, indent=2))
print(json.dumps(resultado, indent=2))
