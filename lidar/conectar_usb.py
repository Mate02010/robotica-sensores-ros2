"""Reconecta a WSL el unico adaptador CP210x ya compartido desde Windows."""
from pathlib import Path
import re
import subprocess
import time


def conectar():
    if Path('/dev/ttyUSB0').exists():
        return
    exe = '/mnt/c/Program Files/usbipd-win/usbipd.exe'
    resultado = subprocess.run([exe, 'list'], capture_output=True, text=True, timeout=10)
    candidatos = re.findall(r'^\s*(\d+-\d+)\s+10c4:ea60\s', resultado.stdout, re.MULTILINE | re.IGNORECASE)
    if len(candidatos) != 1:
        raise RuntimeError('No hay un unico CP210x conectado. Revisar usbipd list y seleccionar el sensor manualmente.')
    print(f'Reconectando adaptador CP210x {candidatos[0]} a Ubuntu...', flush=True)
    resultado = subprocess.run([exe, 'attach', '--wsl', '--busid', candidatos[0]], capture_output=True,
                               text=True, timeout=30)
    print(resultado.stdout + resultado.stderr, flush=True)
    if resultado.returncode:
        raise RuntimeError('No se pudo adjuntar el USB. Comprobar que este compartido con usbipd bind en Windows.')
    for _ in range(20):
        if Path('/dev/ttyUSB0').exists():
            return
        time.sleep(0.5)
    raise RuntimeError('El adaptador se adjunto, pero aun no aparece /dev/ttyUSB0.')


if __name__ == '__main__':
    conectar()
