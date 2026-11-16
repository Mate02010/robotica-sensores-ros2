import argparse
from datetime import datetime
import time
from zoneinfo import ZoneInfo
import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from datos_imagen import estadisticas

TEMAS = ('/camera/depth_raw/image', '/camera/depth_filtrada/image_raw')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--segundos', type=float, default=10)
    args = parser.parse_args()
    rclpy.init()
    node = rclpy.create_node('tabla_profundidad')
    previo, ultimo = {}, {}
    cuenta = {t: 0 for t in TEMAS}
    print('\nCAMARA PRIMESENSE REAL | ' + datetime.now(ZoneInfo('America/Bogota')).isoformat(timespec='seconds'))
    print('Profundidades en metros; Centro = mediana de 5x5 pixeles centrales.')
    print('Imagen      Hz     Resolucion   Validos     %      Min(m) Max(m) Centro(m)')
    print('-' * 80, flush=True)

    def recibir(msg, tema):
        ahora = time.monotonic()
        hz = 1 / (ahora - previo[tema]) if tema in previo else 0
        previo[tema] = ahora
        cuenta[tema] += 1
        if ahora - ultimo.get(tema, 0) < 1:
            return
        ultimo[tema] = ahora
        e = estadisticas(msg)
        numero = lambda v: f'{v:6.3f}' if v is not None else '   ---'
        nombre = 'Original' if tema == TEMAS[0] else 'Filtrada'
        print(f'{nombre:9} {hz:6.2f} {msg.width:4}x{msg.height:<4} {e["validos"]:8} '
              f'{e["porcentaje_valido"]:6.1f} {numero(e["min_m"])} {numero(e["max_m"])} {numero(e["centro_m"])}', flush=True)

    subs = [node.create_subscription(Image, tema, lambda msg, tema=tema: recibir(msg, tema),
                                     qos_profile_sensor_data) for tema in TEMAS]
    limite = time.monotonic() + args.segundos
    try:
        while time.monotonic() < limite:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        print('Cuadros recibidos:', cuenta)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0 if cuenta[TEMAS[0]] else 1


if __name__ == '__main__':
    raise SystemExit(main())
