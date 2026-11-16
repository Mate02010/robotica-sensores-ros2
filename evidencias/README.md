# Evidencias de la práctica

## RPLIDAR

- [Video del montaje físico](videos/RPLIDAR_prueba_fisica_2026-11-13.mp4).
- [Foto del sensor conectado](capturas/lidar/03_RPLIDAR_conexion_fisica.png).
- [Mediciones originales y filtradas](capturas/lidar/05_RPLIDAR_mediciones_iniciales.png).
- [Respuesta de los servicios de parada y arranque](capturas/lidar/07_RPLIDAR_servicios_parada_arranque.png).
- [Parámetros y datos del sector amplio](capturas/lidar/11_RPLIDAR_prueba_3_parametros_datos.png).
- [Visualización en RViz](capturas/lidar/13_RPLIDAR_RViz.png).

### Resultados registrados

| Ensayo | Resumen | Barridos CSV | Parámetros del filtro |
|---|---|---|---|
| prueba 2 | [JSON](resultados/lidar/prueba_2/resumen.json) | [CSV](resultados/lidar/prueba_2/barridos.csv) | [YAML](resultados/lidar/prueba_2/filtro_lidar_inicio.yaml) |
| prueba 3, sector amplio | [JSON](resultados/lidar/prueba_3_sector_amplio/resumen.json) | [CSV](resultados/lidar/prueba_3_sector_amplio/barridos.csv) | [YAML](resultados/lidar/prueba_3_sector_amplio/filtro_lidar_inicio.yaml) |

La prueba 2 recibió 134 barridos por tópico; el filtro 1–6 m, 100–150° y salto 10 no conservó retornos válidos. La prueba 3 recibió 134 barridos originales y 133 filtrados, con 5985 retornos filtrados válidos acumulados; filtro 0,1–6 m, −90–90° y salto 2.

Se publican los resúmenes por barrido, parámetros de inicio/final e información de las bolsas. Los CSV completos de puntos y las bases rosbag permanecen en el archivo local. Las cuentas CSV y rosbag pueden diferir por suscripciones independientes.

Las capturas son originales conservados de la práctica. La respuesta de un servicio ROS no acredita por sí sola la respuesta física del motor. La imagen de RViz contiene un aviso TF y muestra barridos locales; no demuestra un mapa SLAM.

## Cámara PrimeSense

El código está publicado en [camara](../camara/). Las evidencias de esta cámara están pendientes de incorporación al repositorio.
