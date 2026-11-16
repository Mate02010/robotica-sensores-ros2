"""Menu de terminal: controla solo los procesos creados por este laboratorio."""
import argparse
from datetime import datetime
import fcntl
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from zoneinfo import ZoneInfo
import yaml

BASE = Path(__file__).resolve().parent


class Laboratorio:
    def __init__(self):
        self.procesos = {}
        self.archivos = []
        fecha = datetime.now(ZoneInfo('America/Bogota')).strftime('%Y%m%d_%H%M%S_%f')
        self.sesion = BASE / 'registros/sesiones' / fecha
        self.sesion.mkdir(parents=True)

    def iniciar(self, nombre, comando):
        archivo = (self.sesion / (nombre + '.log')).open('a')
        self.archivos.append(archivo)
        self.procesos[nombre] = subprocess.Popen(comando, cwd=BASE, stdout=archivo,
                                                stderr=subprocess.STDOUT, start_new_session=True)

    def detener(self, nombre):
        p = self.procesos.get(nombre)
        if p and p.poll() is None:
            os.killpg(p.pid, signal.SIGINT)
            try:
                p.wait(timeout=12)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGTERM)
                p.wait(timeout=5)

    def driver(self):
        config = yaml.safe_load((BASE / 'config/adquisicion.yaml').read_text())['sllidar_node']['ros__parameters']
        puerto = Path(config['serial_port'])
        if not puerto.exists() and str(puerto) == '/dev/ttyUSB0':
            from conectar_usb import conectar
            conectar()
        if not puerto.exists():
            raise RuntimeError(f'No existe {puerto}. Conectar el USB a Ubuntu con usbipd.')
        if not os.access(puerto, os.R_OK | os.W_OK):
            raise RuntimeError(f'Faltan permisos en {puerto}. Abrir una terminal nueva para activar dialout.')
        print('\nCONFIGURACION DE ADQUISICION (se aplica al arrancar):')
        print(yaml.safe_dump(config, sort_keys=False), flush=True)
        self.iniciar('driver', ['ros2', 'run', 'sllidar_ros2', 'sllidar_node', '--ros-args',
                                '--params-file', str(BASE / 'config/adquisicion.yaml')])
        time.sleep(7)
        print((self.sesion / 'driver.log').read_text()[-2400:], flush=True)
        if self.procesos['driver'].poll() is not None:
            raise RuntimeError('El controlador termino. Revisar el puerto y driver.log.')

    def cerrar(self):
        for nombre in reversed(list(self.procesos)):
            self.detener(nombre)
        for archivo in self.archivos:
            archivo.close()

    def ejecutar(self, *comando):
        resultado = subprocess.run(comando, cwd=BASE)
        if resultado.returncode:
            print(f'El comando termino con codigo {resultado.returncode}. Revisar el mensaje anterior.')

    def cambiar_filtros(self):
        from aplicar_filtros import aplicar
        datos = yaml.safe_load((BASE / 'config/filtros.yaml').read_text())['filtro_lidar']['ros__parameters']
        print('Cambian /scan_filtrado; /scan conserva la medicion original. Enter conserva el valor.')
        nuevos = {}
        etiquetas = {'distancia_min_m': 'Distancia minima (m)', 'distancia_max_m': 'Distancia maxima (m)',
                     'angulo_inicio_deg': 'Inicio del sector (grados, -180..180)',
                     'angulo_fin_deg': 'Fin del sector (grados, -180..180)',
                     'salto_puntos': 'Conservar 1 de cada N puntos (1..20)'}
        for k, valor in datos.items():
            texto = input(f'{etiquetas[k]} [{valor}]: ').strip()
            nuevos[k] = (int(texto) if k == 'salto_puntos' else float(texto)) if texto else valor
        aplicar(nuevos)

    def cambiar_driver(self):
        ruta = BASE / 'config/adquisicion.yaml'
        datos = yaml.safe_load(ruta.read_text())
        p = datos['sllidar_node']['ros__parameters']
        print('Estos ajustes requieren reiniciar la adquisicion. No cambian las RPM del motor.')
        for k in ('angle_compensate', 'inverted'):
            texto = input(f'{k} [{str(p[k]).lower()}] (true/false, Enter conserva): ').strip().lower()
            if texto:
                if texto not in ('true', 'false'):
                    raise ValueError('Escribir true o false.')
                p[k] = texto == 'true'
        anterior = ruta.read_text()
        self.detener('driver')
        ruta.write_text(yaml.safe_dump(datos, sort_keys=False))
        try:
            self.driver()
        except Exception:
            self.detener('driver')
            ruta.write_text(anterior)
            self.driver()
            raise

    def menu(self):
        while True:
            print('\n========== LABORATORIO RPLIDAR / ROS 2 ==========')
            print('1. Ver mediciones y estadisticas en la terminal (10 s)')
            print('2. Cambiar filtros EN VIVO: distancia, sector y cantidad de puntos')
            print('3. Cambiar adquisicion: compensacion/inversion (reinicia controlador)')
            print('4. Grabar ensayo: rosbag + CSV + parametros + resumen')
            print('5. Consultar todos los parametros actuales')
            print('6. Detener motor     7. Arrancar motor')
            print('8. Abrir RViz        9. Ver ultimo log del controlador')
            print('10. Mostrar un mensaje ROS original completo (/scan)')
            print('0. Salir y detener los procesos del laboratorio')
            try:
                opcion = input('Opcion: ').strip()
                if opcion == '0':
                    break
                if opcion == '1':
                    self.ejecutar(sys.executable, '-u', str(BASE / 'ver_datos.py'))
                elif opcion == '2':
                    self.cambiar_filtros()
                elif opcion == '3':
                    self.cambiar_driver()
                elif opcion == '4':
                    nombre = input('Nombre del ensayo [ensayo]: ').strip() or 'ensayo'
                    segundos = input('Duracion en segundos [30]: ').strip() or '30'
                    self.ejecutar(sys.executable, '-u', str(BASE / 'registrar.py'), '--nombre', nombre, '--segundos', segundos)
                elif opcion == '5':
                    self.ejecutar('ros2', 'param', 'dump', '/sllidar_node')
                    self.ejecutar('ros2', 'param', 'dump', '/filtro_lidar')
                elif opcion in ('6', '7'):
                    servicio = '/stop_motor' if opcion == '6' else '/start_motor'
                    self.ejecutar('timeout', '10', 'ros2', 'service', 'call', servicio, 'std_srvs/srv/Empty', '{}')
                elif opcion == '8':
                    if 'rviz' not in self.procesos or self.procesos['rviz'].poll() is not None:
                        self.iniciar('rviz', ['rviz2', '-d', str(BASE / 'config/laboratorio.rviz')])
                elif opcion == '9':
                    print((self.sesion / 'driver.log').read_text()[-5000:])
                elif opcion == '10':
                    self.ejecutar('timeout', '12', 'ros2', 'topic', 'echo', '/scan', '--once',
                                  '--qos-reliability', 'best_effort')
            except (ValueError, RuntimeError) as error:
                print('AVISO:', error)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sin-menu', action='store_true', help='Mantiene adquisicion activa para verificaciones.')
    args = parser.parse_args()
    bloqueo = open('/tmp/universidad_rplidar_lab.lock', 'w')
    try:
        fcntl.flock(bloqueo, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print('El laboratorio ya esta abierto en otra terminal.')
        return 1
    nodos = subprocess.run(['ros2', 'node', 'list'], capture_output=True, text=True, timeout=12).stdout.splitlines()
    if '/sllidar_node' in nodos or '/filtro_lidar' in nodos:
        print('Ya hay un controlador o filtro activo. Usar esa sesion o cerrarla antes de abrir otra.')
        return 1
    lab = Laboratorio()
    try:
        lab.driver()
        lab.iniciar('filtro', [sys.executable, '-u', str(BASE / 'filtro_scan.py'), '--ros-args',
                              '--params-file', str(BASE / 'config/filtros.yaml')])
        print('Logs de esta sesion:', lab.sesion, flush=True)
        if args.sin_menu:
            while True:
                time.sleep(1)
                if any(p.poll() is not None for p in lab.procesos.values()):
                    raise RuntimeError('Un proceso termino; revisar logs de sesion.')
        else:
            lab.menu()
    except (KeyboardInterrupt, EOFError):
        print('\nCerrando laboratorio...')
    except RuntimeError as error:
        print('AVISO:', error)
        return 1
    finally:
        lab.cerrar()
        bloqueo.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
