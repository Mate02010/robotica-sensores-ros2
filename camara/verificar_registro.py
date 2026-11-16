"""Comprueba el filtrado pixel a pixel sobre mensajes reales del rosbag."""
import json
from pathlib import Path
import sqlite3
import numpy as np
import yaml
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import Image
from datos_imagen import matriz, metros

base = Path(__file__).resolve().parent
carpeta = sorted((base / 'registros').glob('*verificacion_camara_registro_linux'))[-1]
p = yaml.safe_load((carpeta / 'filtro_inicio.yaml').read_text())['/filtro_profundidad']['ros__parameters']
db = sqlite3.connect(next((carpeta / 'rosbag').glob('*.db3')))
temas = dict(db.execute('SELECT id,name FROM topics'))
cuentas = {temas[t]: n for t, n in db.execute('SELECT topic_id,COUNT(*) FROM messages GROUP BY topic_id')}
raw_id = next(i for i, t in temas.items() if t == '/camera/depth_raw/image')
fil_id = next(i for i, t in temas.items() if t == '/camera/depth_filtrada/image_raw')
msgs = {raw_id: {}, fil_id: {}}
for tema, datos in db.execute('SELECT topic_id,data FROM messages WHERE topic_id IN (?,?) ORDER BY timestamp LIMIT 80', (raw_id, fil_id)):
    msg = deserialize_message(datos, Image)
    msgs[tema][(msg.header.stamp.sec, msg.header.stamp.nanosec)] = msg
pares = list(msgs[raw_id].keys() & msgs[fil_id].keys())[:10]
assert len(pares) >= 5
pixeles = 0
for t in pares:
    raw, fil = msgs[raw_id][t], msgs[fil_id][t]
    z = metros(raw)
    valido = np.isfinite(z) & (z >= p['distancia_min_m']) & (z <= p['distancia_max_m'])
    zona = np.zeros(z.shape, dtype=bool)
    zona[int(raw.height*p['arriba_pct']/100):int(raw.height*p['abajo_pct']/100),
         int(raw.width*p['izquierda_pct']/100):int(raw.width*p['derecha_pct']/100)] = True
    esperado = matriz(raw).copy()
    esperado[~(valido & zona)] = 0
    assert np.array_equal(esperado, matriz(fil))
    pixeles += esperado.size
assert cuentas.get('/camera/rgb/image_raw', 0) > 0
resultado = dict(registro=carpeta.name, pares_verificados=len(pares), pixeles_verificados=pixeles,
                 filtrado_correcto=True, mensajes_por_topico=cuentas)
(carpeta / 'verificacion_integridad.json').write_text(json.dumps(resultado, indent=2))
print(json.dumps(resultado, indent=2))
db.close()
