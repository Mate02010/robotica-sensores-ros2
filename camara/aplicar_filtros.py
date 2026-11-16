import argparse
from pathlib import Path
import yaml
import rclpy
from rclpy.parameter import Parameter
from rclpy.parameter_client import AsyncParameterClient


def aplicar(valores):
    rclpy.init()
    node = rclpy.create_node('ajustar_profundidad')
    try:
        cliente = AsyncParameterClient(node, '/filtro_profundidad')
        if not cliente.wait_for_services(timeout_sec=5):
            raise RuntimeError('Abrir primero el menu de la camara.')
        futuro = cliente.set_parameters_atomically([Parameter(k, value=v) for k, v in valores.items()])
        rclpy.spin_until_future_complete(node, futuro, timeout_sec=8)
        if not futuro.done() or not futuro.result().result.successful:
            raise ValueError(futuro.result().result.reason if futuro.done() else 'Sin respuesta del filtro.')
        ruta = Path(__file__).resolve().parent / 'config/filtros.yaml'
        datos = yaml.safe_load(ruta.read_text())
        datos['filtro_profundidad']['ros__parameters'].update(valores)
        ruta.write_text(yaml.safe_dump(datos, sort_keys=False))
        print('FILTROS APLICADOS EN VIVO:\n' + yaml.safe_dump(datos, sort_keys=False))
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for argumento, nombre in [('min', 'distancia_min_m'), ('max', 'distancia_max_m'),
                              ('izquierda', 'izquierda_pct'), ('derecha', 'derecha_pct'),
                              ('arriba', 'arriba_pct'), ('abajo', 'abajo_pct')]:
        p.add_argument('--' + argumento, type=float, dest=nombre)
    aplicar({k: v for k, v in vars(p.parse_args()).items() if v is not None})
