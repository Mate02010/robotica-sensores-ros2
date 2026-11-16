"""Filtros de LaserScan ajustables en vivo; conserva /scan sin modificar."""
import math
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rcl_interfaces.msg import SetParametersResult
from sensor_msgs.msg import LaserScan


class Filtro(Node):
    def __init__(self):
        super().__init__('filtro_lidar')
        for nombre, valor in dict(distancia_min_m=0.1, distancia_max_m=6.0,
                                  angulo_inicio_deg=-180.0, angulo_fin_deg=180.0,
                                  salto_puntos=1).items():
            self.declare_parameter(nombre, valor)
        self.add_on_set_parameters_callback(self.validar)
        resultado = self.validar([])
        if not resultado.successful:
            raise ValueError(resultado.reason)
        self.pub = self.create_publisher(LaserScan, '/scan_filtrado', qos_profile_sensor_data)
        self.sub = self.create_subscription(LaserScan, '/scan', self.filtrar, qos_profile_sensor_data)

    def validar(self, cambios):
        valores = {p: self.get_parameter(p).value for p in
                   ('distancia_min_m', 'distancia_max_m', 'angulo_inicio_deg', 'angulo_fin_deg', 'salto_puntos')}
        valores.update({p.name: p.value for p in cambios if p.name in valores})
        try:
            assert all(math.isfinite(float(v)) for v in valores.values())
            assert 0 <= valores['distancia_min_m'] < valores['distancia_max_m'] <= 100
            assert -180 <= valores['angulo_inicio_deg'] < valores['angulo_fin_deg'] <= 180
            assert type(valores['salto_puntos']) is int and 1 <= valores['salto_puntos'] <= 20
        except (AssertionError, TypeError, ValueError):
            return SetParametersResult(successful=False, reason='Revisar min<max, sector -180..180 y salto entero 1..20.')
        return SetParametersResult(successful=True)

    def filtrar(self, msg):
        valor = lambda nombre: self.get_parameter(nombre).value
        paso = valor('salto_puntos')
        minimo, maximo = valor('distancia_min_m'), valor('distancia_max_m')
        inicio, fin = valor('angulo_inicio_deg'), valor('angulo_fin_deg')
        salida = LaserScan()
        salida.header = msg.header
        salida.angle_min = msg.angle_min
        salida.angle_increment = msg.angle_increment * paso
        salida.scan_time = msg.scan_time
        salida.time_increment = msg.time_increment * paso
        salida.range_min, salida.range_max = msg.range_min, msg.range_max
        rangos, intensidades = [], []
        for i in range(0, len(msg.ranges), paso):
            r = msg.ranges[i]
            angulo = (math.degrees(msg.angle_min + i * msg.angle_increment) + 180) % 360 - 180
            valido = (math.isfinite(r) and msg.range_min <= r <= msg.range_max
                      and minimo <= r <= maximo and inicio <= angulo <= fin)
            rangos.append(r if valido else math.inf)
            if len(msg.intensities) == len(msg.ranges):
                intensidades.append(msg.intensities[i])
        salida.ranges, salida.intensities = rangos, intensidades
        salida.angle_max = salida.angle_min + max(0, len(rangos) - 1) * salida.angle_increment
        self.pub.publish(salida)


def main():
    rclpy.init()
    node = Filtro()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
