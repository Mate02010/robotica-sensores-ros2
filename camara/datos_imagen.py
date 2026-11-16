"""Convierte profundidades ROS a metros respetando encoding, paso y endianidad."""
import numpy as np


def matriz(msg):
    if msg.encoding in ('16UC1', 'mono16'):
        tipo = np.dtype('>u2' if msg.is_bigendian else '<u2')
    elif msg.encoding == '32FC1':
        tipo = np.dtype('>f4' if msg.is_bigendian else '<f4')
    else:
        raise ValueError('Encoding de profundidad no soportado: ' + msg.encoding)
    return np.ndarray((msg.height, msg.width), dtype=tipo, buffer=msg.data, strides=(msg.step, tipo.itemsize))


def metros(msg):
    original = matriz(msg)
    salida = original.astype(np.float32)
    if original.dtype.kind == 'u':
        salida[original == 65535] = np.nan
        salida *= 0.001
    salida[salida <= 0] = np.nan
    return salida


def estadisticas(msg):
    z = metros(msg)
    validos = z[np.isfinite(z)]
    y, x = msg.height // 2, msg.width // 2
    centro = z[max(0, y-2):y+3, max(0, x-2):x+3]
    centro = centro[np.isfinite(centro)]
    return dict(ancho=msg.width, alto=msg.height, validos=int(validos.size), pixeles=int(z.size),
                porcentaje_valido=100 * float(validos.size) / z.size,
                min_m=float(validos.min()) if validos.size else None,
                max_m=float(validos.max()) if validos.size else None,
                media_m=float(validos.mean()) if validos.size else None,
                centro_m=float(np.median(centro)) if centro.size else None)
