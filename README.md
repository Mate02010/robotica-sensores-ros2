# Práctica de sensores con ROS 2

Código utilizado para trabajar con un RPLIDAR 2D y una cámara de profundidad PrimeSense en Ubuntu 24.04 / WSL 2 con ROS 2 Kilted. Repositorio independiente: no sustituye ni modifica los repositorios de las prácticas anteriores.

## Código

| Carpeta | Contenido |
|---|---|
| [lidar](lidar/) | Menú de terminal, filtros de distancia/sector/salto de puntos, estadísticas, registro y ajuste de compatibilidad del controlador. |
| [camara](camara/) | Lanzamiento OpenNI2, menú, filtros de profundidad/ROI, estadísticas y registro. |

Los controladores externos utilizados son [sllidar_ros2 de SLAMTEC](https://github.com/Slamtec/sllidar_ros2) y [openni2_camera, rama jazzy](https://github.com/ros-drivers/openni2_camera/tree/jazzy). Aquí se conservan los scripts de trabajo y el ajuste local, no una copia completa de dichos proyectos.

## Espacio para evidencias

Las carpetas permiten organizar los archivos de la práctica. Ya está publicado el video físico del RPLIDAR; las demás evidencias se podrán añadir posteriormente. El informe y la colección de Daniel se conservan fuera del repositorio.

- [Videos](evidencias/videos/): grabaciones de RViz y pruebas de los sensores.
- [Capturas](evidencias/capturas/): terminal, parámetros y visualización.
- [Resultados](evidencias/resultados/): parámetros y datos registrados en ensayos.
- [Índice de evidencias](evidencias/README.md): espacio para los enlaces de prueba.

## Video de la prueba física del RPLIDAR

[Ver video del RPLIDAR conectado en el laboratorio](evidencias/videos/RPLIDAR_prueba_fisica_2026-11-13.mp4) · [Abrir o descargar MP4](https://github.com/Mate02010/robotica-sensores-ros2/raw/refs/heads/main/evidencias/videos/RPLIDAR_prueba_fisica_2026-11-13.mp4).

Grabación de aproximadamente 11 segundos, aportada por el usuario desde Descargas. Muestra el montaje físico y la conexión del sensor. Es una evidencia distinta de una captura de ROS/RViz o de un registro numérico de distancias.

## Preparación y ejecución

Requisitos previos: ROS 2 Kilted, herramientas de compilación/colcon, dependencias de los controladores, rclpy, sensor_msgs, std_srvs, NumPy y PyYAML. El USB debe estar asignado a Ubuntu; LiDAR requiere permisos del puerto serie. Los scripts de preparación no instalan por sí solos todo el entorno.

```bash
git clone https://github.com/Mate02010/robotica-sensores-ros2.git
cd robotica-sensores-ros2

# LiDAR
bash lidar/preparar_controlador.sh
python3 lidar/compatibilidad_firmware.py
bash lidar/compilar_compatibilidad.sh
bash lidar/laboratorio.sh

# Cámara: ejecutar por separado según el sensor conectado.
bash camara/preparar_camara.sh
bash camara/camara.sh
```

El ajuste LiDAR corresponde a la revisión `34300099fadfc772965962dec837bf436706188f` del controlador; revisar cambios si se utiliza otra revisión. `legacy_standard=true` permite iniciar el modo Standard con el firmware 1.15 usado en la práctica. No modifica el firmware.

Los workspaces esperados son `~/sensores_ws` y `~/camara_primesense_ws`. Las guías históricas [LiDAR](lidar/COMO_EMPEZAR.md) y [cámara](camara/COMO_EMPEZAR.md) describen los accesos del equipo original; para este clon usar las rutas mostradas aquí. Los nuevos registros se guardan junto al código de cada sensor. Salir con la opción 0 del menú para cerrar sus procesos.

## Alcance

Los filtros cambian los datos procesados. No cambian por sí solos el alcance físico, la velocidad del motor ni la resolución óptica del LiDAR. Las frecuencias mostradas corresponden a recepción de mensajes. En cámara, los píxeles descartados pasan a cero; CSV y rosbag usan suscriptores independientes.

La visualización de barridos o nubes en RViz no acredita un mapa SLAM acumulado ni el uso de un LiDAR 3D independiente. No se realizó calibración de precisión independiente de la cámara.

Se verificó la sintaxis Python y que los archivos de código copiados coincidan mediante SHA256 con la práctica local. Esta revisión del paquete no supone una nueva ejecución física. [Manifiesto](ARCHIVOS_PUBLICADOS.json).
