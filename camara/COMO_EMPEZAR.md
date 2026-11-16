# Cámara PrimeSense: laboratorio de profundidad

Equipo USB identificado: PrimeSense PS1080, VID:PID 1d27:0601. El modelo comercial exacto de la etiqueta no está confirmado. El driver OpenNI2 se compiló desde la rama oficial jazzy, compatible con Kilted, en ~/camara_primesense_ws. Se conservan los programas y registros del RPLIDAR.

## Abrir en Ubuntu

Si la terminal dice PS C:\, primero ejecutar wsl -d Ubuntu-24.04 y pulsar Enter. Luego:

```bash
bash ~/laboratorio_camara/camara.sh
```

También existe ABRIR_CAMARA.cmd para abrir desde Windows. La cámara PrimeSense ya fue compartida con usbipd. El programa intenta reconectar únicamente el dispositivo 1d27:0601 cuando se reinicia WSL. No usa la cámara integrada del portátil.

## Opciones del menú

1. Ver datos reales durante 10 s: frecuencia recibida, resolución, píxeles válidos, porcentaje válido, distancias mínima/máxima y mediana de una zona central 5x5.
2. Cambiar filtros en vivo: distancia mínima/máxima en metros y rectángulo de imagen en porcentajes.
3. Cambiar adquisición: resolución QVGA_30Hz (320x240) o VGA_30Hz (640x480), y cuadros omitidos entre publicaciones. Requiere reiniciar el controlador, que realiza el menú.
4. Grabar ensayo con nombre y duración.
5. Consultar parámetros ROS reales.
6/7. Detener/reanudar la adquisición. Esta cámara no tiene el motor giratorio del RPLIDAR.
8. Abrir RViz con las nubes originales y filtradas.
9. Ver el log del controlador.
10. Mostrar CameraInfo.
0. Salir y cerrar los procesos propios.

## Qué significan los filtros

Las distancias se expresan en metros. La zona se define como izquierda/derecha y arriba/abajo, entre 0 y 100 % de la imagen. Por ejemplo, izquierda25,derecha75,arriba25,abajo75 conserva el rectángulo central que ocupa la mitad de ancho y alto, es decir el 25 % de los píxeles. Se ponen a cero las profundidades descartadas; no se cambia el tamaño de la imagen ni la matriz de cámara.

Estos porcentajes no son grados como en el LiDAR. El filtro no modifica el alcance físico ni calibra el equipo. Los datos originales siguen en /camera/depth_raw/image y la salida procesada en /camera/depth_filtrada/image_raw.

## Ensayos sugeridos y screenshots

1. Mantener la cámara quieta, orientada horizontalmente hacia objetos del laboratorio. Empezar con un cuaderno/caja aproximadamente a 1–2 m y observar dónde hay profundidad válida. Muy cerca puede no medir.
2. Opción5: capturar parámetros.
3. Opción1: capturar mediciones iniciales.
4. Opción4: guardar 20 s con nombre camara prueba 1.
5. Opción2: ajustar un límite de distancia y/o zona central. Para estudiar cada efecto por separado, cambiar un ajuste a la vez y conservar la escena.
6. Opción1: capturar el resultado.
7. Opción4: guardar otro ensayo con nombre distinto.
8. Opción8: grabar un video corto de RViz acercando/alejando un objeto dentro del campo visible y rango válido.

En resolución/omisión, data_skip=0 publica todos los cuadros; data_skip=2 publica uno de cada tres. Con un modo de 30 Hz se esperan aproximadamente 30 y 10 publicaciones/s, respectivamente, sujeto al rendimiento USB y recepción. El salto de cuadros no cambia la velocidad de captura física del modo seleccionado.

## Archivos guardados

En esta subcarpeta, registros/FECHA_NOMBRE/:

- rosbag/: imágenes originales de profundidad, imágenes filtradas, RGB, CameraInfo, TF estática y eventos de parámetros si existen. Se pueden reproducir con ros2 bag play.
- cuadros.csv: estadísticas de cada cuadro original/filtrado. Para no crear millones de filas por segundo, este CSV no contiene cada píxel individual.
- muestras_profundidad.npz: matrices completas de las primeras y últimas imágenes de profundidad, para analizar píxeles con NumPy. En 16UC1 los valores están en milímetros; 0 significa inválido/descartado.
- resumen.json: cantidades, frecuencia recibida y porcentaje válido.
- driver_inicio/final.yaml y filtro_inicio/final.yaml: configuración real inicial/final.
- rosbag_info.txt y rosbag.log.

Las imágenes completas quedan en rosbag. Se escriben primero en ~/camara_primesense_ws/bolsas/ (disco Linux, mejor rendimiento SQLite) y se copian al ensayo al terminar; se conserva la copia Linux. Los suscriptores CSV y rosbag tienen límites temporales independientes y sus cantidades pueden diferir.

## Otra terminal: comandos directos

Mantener abierto el menú de cámara. En una segunda terminal Ubuntu:

```bash
source /opt/ros/kilted/setup.bash
source ~/camara_primesense_ws/install/setup.bash
cd ~/laboratorio_camara
python3 ver_datos.py --segundos 10
python3 registrar.py --nombre "camara prueba 1" --segundos 20
```

Para aplicar filtros por comandos:

```bash
python3 aplicar_filtros.py --min 0.8 --max 3 --izquierda 25 --derecha 75 --arriba 25 --abajo 75
```

Consultar parámetros nativos:

```bash
ros2 param dump /camera/driver
ros2 param dump /filtro_profundidad
ros2 topic list -t
```

## RViz y límites de la evidencia

RViz usa el marco local camera_link y la rotación óptica convencional del sensor. La nube original es celeste y la filtrada amarilla; se pueden mostrar por separado con sus casillas. Son nubes XYZ de profundidad sin registro geométrico con RGB; no se presenta una nube XYZRGB calibrada ni un mapa acumulado.

El controlador informa que no encuentra una calibración personalizada guardada y usa sus valores predeterminados de cámara. Esto no impide recibir imágenes, pero las pruebas no acreditan calibración ni precisión absoluta. No se inventó un archivo de calibración para ocultar el aviso.

Esta práctica corresponde a la cámara de profundidad. Una nube 3D de esta cámara no demuestra haber utilizado un LiDAR 3D independiente.

Fuente del controlador: https://github.com/ros-drivers/openni2_camera/tree/jazzy . Revisión base 9574be235063d767a80f1ef2bc14f70d5f2365ca. No se modificó su fuente ni el firmware de la cámara. Los launch/filtros/menú son archivos de este laboratorio.
