import math
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rcl_interfaces.msg import SetParametersResult
from sensor_msgs.msg import Image, CameraInfo
from datos_imagen import matriz, metros


class Filtro(Node):
    def __init__(self):
        super().__init__('filtro_profundidad')
        self.nombres = ('distancia_min_m', 'distancia_max_m', 'izquierda_pct', 'derecha_pct', 'arriba_pct', 'abajo_pct')
        for nombre, valor in zip(self.nombres, (0.3, 4.0, 0.0, 100.0, 0.0, 100.0)):
            self.declare_parameter(nombre, valor)
        self.add_on_set_parameters_callback(self.validar)
        if not self.validar([]).successful:
            raise ValueError('Filtros iniciales invalidos.')
        # depth_image_proc usa suscripcion fiable para esta imagen.
        self.pub = self.create_publisher(Image, '/camera/depth_filtrada/image_raw', 10)
        # El filtrado no cambia dimensiones ni geometria de la imagen.
        self.info_pub = self.create_publisher(CameraInfo, '/camera/depth_filtrada/camera_info', 10)
        self.info_sub = self.create_subscription(CameraInfo, '/camera/depth_raw/camera_info',
                                                 self.info_pub.publish, qos_profile_sensor_data)
        self.sub = self.create_subscription(Image, '/camera/depth_raw/image', self.filtrar, qos_profile_sensor_data)

    def validar(self, cambios):
        p = {k: self.get_parameter(k).value for k in self.nombres}
        p.update({v.name: v.value for v in cambios if v.name in p})
        ok = (all(math.isfinite(float(v)) for v in p.values()) and
              0 <= p['distancia_min_m'] < p['distancia_max_m'] <= 20 and
              0 <= p['izquierda_pct'] < p['derecha_pct'] <= 100 and
              0 <= p['arriba_pct'] < p['abajo_pct'] <= 100)
        return SetParametersResult(successful=ok, reason='' if ok else 'Revisar min<max y limites de zona 0..100%.')

    def filtrar(self, msg):
        p = {k: self.get_parameter(k).value for k in self.nombres}
        z = metros(msg)
        mascara = np.isfinite(z) & (z >= p['distancia_min_m']) & (z <= p['distancia_max_m'])
        zona = np.zeros(z.shape, dtype=bool)
        x1, x2 = int(msg.width * p['izquierda_pct'] / 100), int(msg.width * p['derecha_pct'] / 100)
        y1, y2 = int(msg.height * p['arriba_pct'] / 100), int(msg.height * p['abajo_pct'] / 100)
        zona[y1:y2, x1:x2] = True
        datos = matriz(msg).copy()
        datos[~(mascara & zona)] = 0 if datos.dtype.kind == 'u' else np.nan
        salida = Image(header=msg.header, height=msg.height, width=msg.width, encoding=msg.encoding,
                       is_bigendian=msg.is_bigendian, step=msg.width * datos.dtype.itemsize,
                       data=datos.tobytes())
        self.pub.publish(salida)


def main():
    rclpy.init()
    nodo = Filtro()
    try:
        rclpy.spin(nodo)
    except KeyboardInterrupt:
        pass
    finally:
        nodo.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
