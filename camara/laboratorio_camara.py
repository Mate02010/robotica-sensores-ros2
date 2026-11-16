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
from conectar_usb import conectar

BASE = Path(__file__).resolve().parent


def preparar_rviz():
    ruta = BASE / 'config/camara.rviz'
    if ruta.exists():
        return
    config = yaml.safe_load((BASE.parent / 'config/laboratorio.rviz').read_text())
    vista = config['Visualization Manager']
    grid = vista['Displays'][0]
    vista['Displays'] = [grid]
    for nombre, tema, color in [('Profundidad original', '/camera/depth/points', '0; 200; 255'),
                                 ('Profundidad filtrada', '/camera/depth_filtrada/points', '255; 200; 0')]:
        vista['Displays'].append({'Class': 'rviz_default_plugins/PointCloud2', 'Name': nombre,
                                  'Enabled': True, 'Value': True, 'Alpha': 0.8, 'Color': color,
                                  'Color Transformer': 'FlatColor', 'Position Transformer': 'XYZ',
                                  'Style': 'Points', 'Size (Pixels)': 2, 'Size (m)': 0.005,
                                  'Decay Time': 0, 'Selectable': True,
                                  'Topic': {'Value': tema, 'Reliability Policy': 'Best Effort',
                                            'Durability Policy': 'Volatile', 'Depth': 5}})
    vista['Global Options']['Fixed Frame'] = 'camera_link'
    vista['Views']['Current'].update({'Distance': 4.0, 'Pitch': 0.4, 'Yaw': 0.8,
                                     'Focal Point': {'X': 1.5, 'Y': 0.0, 'Z': 0.0}})
    ruta.write_text(yaml.safe_dump(config, sort_keys=False))


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
        proceso = self.procesos.get(nombre)
        if proceso and proceso.poll() is None:
            os.killpg(proceso.pid, signal.SIGINT)
            try:
                proceso.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(proceso.pid, signal.SIGTERM)
                proceso.wait(timeout=5)

    def driver(self):
        conectar()
        print('\nCONFIGURACION DE LA CAMARA (arranque):')
        print((BASE / 'config/driver.yaml').read_text(), flush=True)
        self.iniciar('camera', ['ros2', 'launch', str(BASE / 'camara.launch.py')])
        time.sleep(8)
        print((self.sesion / 'camera.log').read_text()[-4500:], flush=True)
        if self.procesos['camera'].poll() is not None:
            raise RuntimeError('El controlador termino. Revisar el log de esta sesion.')

    def ejecutar(self, *comando):
        r = subprocess.run(comando, cwd=BASE)
        if r.returncode:
            print('El comando termino con codigo', r.returncode)

    def filtros(self):
        from aplicar_filtros import aplicar
        datos = yaml.safe_load((BASE / 'config/filtros.yaml').read_text())['filtro_profundidad']['ros__parameters']
        print('Filtro de profundidad en metros y zona de imagen en porcentajes. Enter conserva el valor.')
        nuevos = {}
        for k, v in datos.items():
            texto = input(f'{k} [{v}]: ').strip()
            nuevos[k] = float(texto) if texto else v
        aplicar(nuevos)

    def adquisicion(self):
        ruta = BASE / 'config/driver.yaml'
        datos = yaml.safe_load(ruta.read_text())
        p = datos['/camera/driver']['ros__parameters']
        modo = input(f'Resolucion QVGA_30Hz (320x240) o VGA_30Hz (640x480) [{p["depth_mode"]}]: ').strip() or p['depth_mode']
        if modo not in ('QVGA_30Hz', 'VGA_30Hz'):
            raise ValueError('Elegir QVGA_30Hz o VGA_30Hz.')
        texto = input(f'Cuadros omitidos entre publicaciones, 0..9 [{p["data_skip"]}]: ').strip()
        salto = int(texto) if texto else p['data_skip']
        if not 0 <= salto <= 9:
            raise ValueError('Usar 0..9. Con 2 se publica uno de cada 3 cuadros.')
        p.update(depth_mode=modo, color_mode=modo, ir_mode=modo, data_skip=salto)
        anterior = ruta.read_text()
        self.detener('camera')
        ruta.write_text(yaml.safe_dump(datos, sort_keys=False))
        try:
            self.driver()
        except Exception:
            self.detener('camera')
            ruta.write_text(anterior)
            self.driver()
            raise

    def menu(self):
        while True:
            print('\n========== CAMARA PRIMESENSE / ROS 2 ==========')
            print('1. Ver profundidades y estadisticas reales (10 s)')
            print('2. Cambiar filtros EN VIVO: distancias y zona de imagen')
            print('3. Cambiar resolucion y salto de cuadros (reinicia camara)')
            print('4. Grabar ensayo: imagenes en rosbag + CSV + muestras NPZ + parametros')
            print('5. Consultar parametros ROS actuales')
            print('6. Detener adquisicion      7. Reanudar adquisicion')
            print('8. Abrir RViz 3D            9. Ver log de la camara')
            print('10. Mostrar datos de CameraInfo')
            print('0. Salir y cerrar los procesos de este laboratorio')
            try:
                opcion = input('Opcion: ').strip()
                if opcion == '0':
                    break
                if opcion == '1':
                    self.ejecutar(sys.executable, '-u', str(BASE / 'ver_datos.py'))
                elif opcion == '2':
                    self.filtros()
                elif opcion == '3':
                    self.adquisicion()
                elif opcion == '4':
                    nombre = input('Nombre del ensayo [prueba camara]: ').strip() or 'prueba camara'
                    segundos = input('Duracion en segundos [20]: ').strip() or '20'
                    self.ejecutar(sys.executable, '-u', str(BASE / 'registrar.py'), '--nombre', nombre, '--segundos', segundos)
                elif opcion == '5':
                    self.ejecutar('ros2', 'param', 'dump', '/camera/driver')
                    self.ejecutar('ros2', 'param', 'dump', '/filtro_profundidad')
                elif opcion == '6':
                    self.detener('camera')
                elif opcion == '7':
                    if 'camera' not in self.procesos or self.procesos['camera'].poll() is not None:
                        self.driver()
                elif opcion == '8':
                    if 'rviz' not in self.procesos or self.procesos['rviz'].poll() is not None:
                        self.iniciar('rviz', ['rviz2', '-d', str(BASE / 'config/camara.rviz')])
                elif opcion == '9':
                    print((self.sesion / 'camera.log').read_text()[-6000:])
                elif opcion == '10':
                    self.ejecutar('timeout', '12', 'ros2', 'topic', 'echo', '/camera/depth_raw/camera_info', '--once')
            except (RuntimeError, ValueError) as error:
                print('AVISO:', error)

    def cerrar(self):
        for nombre in reversed(list(self.procesos)):
            self.detener(nombre)
        for archivo in self.archivos:
            archivo.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--sin-menu', action='store_true')
    args = p.parse_args()
    bloqueo = open('/tmp/universidad_camara_primesense.lock', 'w')
    try:
        fcntl.flock(bloqueo, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print('La camara ya esta abierta en otra terminal.')
        return 1
    preparar_rviz()
    lab = Laboratorio()
    try:
        lab.driver()
        print('Logs de esta sesion:', lab.sesion, flush=True)
        if args.sin_menu:
            while True:
                time.sleep(1)
                if lab.procesos['camera'].poll() is not None:
                    raise RuntimeError('La adquisicion termino; revisar camera.log.')
        else:
            lab.menu()
    except (KeyboardInterrupt, EOFError):
        print('\nCerrando camara...')
    except RuntimeError as error:
        print('AVISO:', error)
        return 1
    finally:
        lab.cerrar()
        bloqueo.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
