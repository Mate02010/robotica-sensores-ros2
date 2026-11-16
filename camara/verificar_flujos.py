"""Comprueba RGB, profundidad, nubes XYZ y CameraInfo con el equipo conectado."""
import json
from pathlib import Path
import time
import numpy as np
import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, PointCloud2, CameraInfo

base = Path(__file__).resolve().parent
rclpy.init()
node = rclpy.create_node('verificar_flujos_primesense')
cuentas = {}
detalles = {}
infos = {}


def recibir(msg, tema):
    cuentas[tema] = cuentas.get(tema, 0) + 1
    if tema in detalles:
        return
    if isinstance(msg, Image):
        detalles[tema] = dict(ancho=msg.width, alto=msg.height, encoding=msg.encoding)
    elif isinstance(msg, CameraInfo):
        detalles[tema] = dict(ancho=msg.width, alto=msg.height, frame=msg.header.frame_id, k=list(msg.k))
    else:
        campo = next(c for c in msg.fields if c.name == 'z')
        z = np.ndarray((msg.height, msg.width), dtype='>f4' if msg.is_bigendian else '<f4',
                       buffer=msg.data, offset=campo.offset, strides=(msg.row_step, msg.point_step))
        detalles[tema] = dict(ancho=msg.width, alto=msg.height, frame=msg.header.frame_id,
                             campos=[c.name for c in msg.fields], puntos_validos=int(np.isfinite(z).sum()))


temas = [('/camera/rgb/image_raw', Image), ('/camera/depth_raw/image', Image),
         ('/camera/depth_filtrada/image_raw', Image), ('/camera/depth/points', PointCloud2),
         ('/camera/depth_filtrada/points', PointCloud2), ('/camera/depth_raw/camera_info', CameraInfo)]
subs = [node.create_subscription(tipo, tema, lambda msg, t=tema: recibir(msg, t), qos_profile_sensor_data)
        for tema, tipo in temas]
limite = time.monotonic() + 8
while time.monotonic() < limite:
    rclpy.spin_once(node, timeout_sec=0.1)
resultado = dict(mensajes=cuentas, detalles=detalles)
(base / 'VERIFICACION_FLUJOS.json').write_text(json.dumps(resultado, indent=2))
print(json.dumps(resultado, indent=2))
node.destroy_node()
rclpy.shutdown()
assert all(cuentas.get(tema, 0) > 0 for tema, _ in temas), 'Faltan flujos esperados.'
