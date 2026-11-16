# Laboratorio RPLIDAR en la terminal de Ubuntu

Estado verificado el 13 de noviembre de 2026: el sensor real publica barridos. Se comprobó cambio de filtros en vivo y grabación en rosbag/CSV. El controlador utiliza un ajuste local para el modo Standard legado del firmware 1.15; no se modificó el firmware.

## Abrir el menú

En Ubuntu-24.04:

```bash
bash ~/laboratorio_sensores/laboratorio.sh
```

También puedes abrir ABRIR_LAB.cmd desde Windows. Dejar abierta esta terminal mientras se usa el sensor. El menú evita abrir dos controladores simultáneamente. Al salir con 0 detiene sus procesos y solicita detener el motor.

El USB ya está compartido con Ubuntu. Si WSL se reinicia pierde la conexión USB; al abrir el menú se intenta reconectar el único CP210x presente. Si no se reconoce, comprobar cable y ejecutar usbipd list en Windows. No seleccionar cámara, huella ni Bluetooth.

## Qué hacer para tus screenshots

1. Opción 5: muestra los parámetros actuales del controlador y del filtro. Tomar captura.
2. Opción 1: muestra durante 10 segundos los datos reales: frecuencia recibida, puntos por barrido, puntos válidos, distancias mínima/máxima y paso angular. Tomar captura.
3. Opción 2: cambiar distancia máxima a 2 m, sector a -90..90 grados y salto de puntos a 2. Enter conserva los demás valores.
4. Opción 1 nuevamente: comparar /scan con /scan_filtrado. El original conserva su adquisición; el filtrado debe mostrar aproximadamente la mitad de las posiciones angulares y las distancias fuera del filtro como inválidas.
5. Opción 4: dar nombre al ensayo y duración en segundos. Se admiten espacios y tildes: prueba 1 se guarda como prueba_1; el nombre original queda en resumen.json. Guarda los registros y muestra su resumen. Tomar captura del resultado.
6. Opción 10: muestra un mensaje LaserScan original completo, si necesitas evidenciar los campos y el vector de distancias.

Para comparar ensayos controlar la posición del sensor y los objetos; anotar los cambios de escena. Las pruebas registradas no demuestran calibración ni precisión absoluta.

## Controles disponibles

- 1: datos y estadísticas en la terminal.
- 2: filtros en vivo de distancia, sector angular y uno de cada N puntos.
- 3: compensación angular e inversión de adquisición. Reinicia el controlador para aplicar cambios reales.
- 4: grabación con nombre y duración.
- 5: parámetros ROS actuales.
- 6/7: solicitar parada/arranque del motor a través de los servicios del controlador; observar la respuesta física.
- 8: RViz con original en celeste y filtrado en amarillo.
- 9: log del controlador, firmware y estado de salud.
- 10: un mensaje ROS original.
- 0: salir.

Los filtros cambian el procesamiento de /scan_filtrado. No cambian el alcance físico, las RPM o la resolución óptica del sensor. El parámetro scan_frequency del controlador se usa para calcular compensación; no es un control de RPM en esta implementación. Las aproximadamente 6,6 Hz observadas son medidas de recepción, no una velocidad impuesta.

El SDK legado anuncia range_max=16 m como valor de compatibilidad; eso no certifica el alcance físico de este equipo. La distancia máxima observada corresponde a la escena medida.

## Archivos que guarda cada ensayo

En registros/FECHA_NOMBRE/:

- rosbag/: barridos originales y filtrados, TF si existen y eventos de parámetros, formato SQLite3. Permite reproducir los mensajes.
- puntos.csv: un rayo por fila; tópico, tiempo ROS, frame, ángulo, distancia, intensidad/calidad, validez y coordenadas X/Y en el frame del sensor. Inf indica sin retorno válido o punto excluido por el filtro, según el tópico.
- barridos.csv: resumen de cada barrido.
- resumen.json: frecuencia recibida, cantidades, distancias y porcentaje válido.
- sllidar_node_inicio/final.yaml y filtro_lidar_inicio/final.yaml: parámetros del ensayo.
- rosbag_info.txt y rosbag.log: contenido de la grabación y diagnóstico.

Los suscriptores CSV y rosbag tienen límites temporales independientes; sus cuentas pueden diferir. Se conservan ensayos anteriores y no se reutilizan nombres de carpeta.

## Comandos ROS directos, en otra terminal

Mantener abierto el menú. Preparar esta segunda terminal:

```bash
source /opt/ros/kilted/setup.bash
source ~/sensores_ws/install/setup.bash
ros2 param list /filtro_lidar
ros2 param get /filtro_lidar distancia_max_m
ros2 param set /filtro_lidar distancia_max_m 2.0
ros2 param dump /filtro_lidar
ros2 topic echo /scan --once --qos-reliability best_effort
```

El cambio directo se aplica en la sesión. La opción 2 del menú además guarda la configuración para el próximo arranque. Si haces cambios directos, revisar opción 5; el archivo de configuración puede conservar valores anteriores.

Para reproducir un ensayo, cerrar el menú con 0 y ejecutar:

```bash
source /opt/ros/kilted/setup.bash
ros2 bag play '/ruta/al/ensayo/rosbag'
```

No reproducirlo junto al sensor activo: mezclaría mediciones históricas y actuales en los mismos tópicos.

## Mapeo

Las herramientas y scripts de mapeo permanecen preparados. Todavía falta definir el montaje y la estimación de movimiento real odom -> base_link y el montaje base_link -> laser. Ver mediciones o cambiar filtros no demuestra que ya exista un mapa. No se ha generado un mapa con este equipo.

## Fuentes y ajuste de compatibilidad

Controlador oficial: https://github.com/Slamtec/sllidar_ros2 ; revisión base 34300099fadfc772965962dec837bf436706188f. El firmware 1.15/model code 0 respondió a la consulta de salud pero no entregó barridos con la selección Express del SDK. Se añadió el parámetro local legacy_standard=true para llamar startScan(false,false) del SDK existente. Cambio guardado en compatibilidad_firmware_1_15.patch; procedimiento en compatibilidad_firmware.py. Compilación y funcionamiento real comprobados. No se ha confirmado la revisión comercial mediante etiqueta.

USB/WSL: https://learn.microsoft.com/es-es/windows/wsl/connect-usb .

