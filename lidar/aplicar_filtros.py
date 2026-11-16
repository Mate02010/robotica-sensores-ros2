"""Aplica todos los filtros juntos y guarda la configuracion solo si se acepta."""
import argparse
from pathlib import Path
import yaml

import rclpy
from rclpy.parameter import Parameter
from rclpy.parameter_client import AsyncParameterClient

BASE = Path(__file__).resolve().parent


def aplicar(valores):
    rclpy.init()
    node = rclpy.create_node('ajustar_filtros_lidar')
    try:
        cliente = AsyncParameterClient(node, '/filtro_lidar')
        if not cliente.wait_for_services(timeout_sec=5):
            raise RuntimeError('No esta activo /filtro_lidar. Abrir primero laboratorio.sh.')
        futuro = cliente.set_parameters_atomically([Parameter(k, value=v) for k, v in valores.items()])
        rclpy.spin_until_future_complete(node, futuro, timeout_sec=8)
        if not futuro.done():
            raise RuntimeError('El nodo no respondio a tiempo.')
        resultado = futuro.result().result
        if not resultado.successful:
            raise ValueError(resultado.reason)
        ruta = BASE / 'config/filtros.yaml'
        datos = yaml.safe_load(ruta.read_text())
        datos['filtro_lidar']['ros__parameters'].update(valores)
        ruta.write_text(yaml.safe_dump(datos, sort_keys=False))
        print('FILTROS APLICADOS EN VIVO:')
        print(yaml.safe_dump(datos, sort_keys=False))
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--min', type=float, dest='distancia_min_m')
    parser.add_argument('--max', type=float, dest='distancia_max_m')
    parser.add_argument('--inicio', type=float, dest='angulo_inicio_deg')
    parser.add_argument('--fin', type=float, dest='angulo_fin_deg')
    parser.add_argument('--paso', type=int, dest='salto_puntos')
    args = vars(parser.parse_args())
    aplicar({k: v for k, v in args.items() if v is not None})


if __name__ == '__main__':
    main()
