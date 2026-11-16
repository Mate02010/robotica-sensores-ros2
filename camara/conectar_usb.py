from pathlib import Path
import re
import subprocess
import time


def conectada():
    for p in Path('/sys/bus/usb/devices').glob('*'):
        try:
            if (p / 'idVendor').read_text().strip() == '1d27' and (p / 'idProduct').read_text().strip() == '0601':
                return True
        except FileNotFoundError:
            pass
    return False


def conectar():
    if conectada():
        return
    exe = '/mnt/c/Program Files/usbipd-win/usbipd.exe'
    lista = subprocess.run([exe, 'list'], capture_output=True, text=True, timeout=10)
    candidatos = re.findall(r'^\s*(\d+-\d+)\s+1d27:0601\s', lista.stdout, re.MULTILINE | re.IGNORECASE)
    if len(candidatos) != 1:
        raise RuntimeError('No se identifica una unica PrimeSense 1d27:0601. Revisar cable y usbipd list.')
    resultado = subprocess.run([exe, 'attach', '--wsl', '--busid', candidatos[0]], capture_output=True, text=True, timeout=30)
    print(resultado.stdout + resultado.stderr, flush=True)
    if resultado.returncode:
        raise RuntimeError('No se pudo conectar la PrimeSense a WSL. Revisar usbipd bind en Windows.')
    for _ in range(20):
        if conectada():
            return
        time.sleep(0.5)
    raise RuntimeError('El USB todavia no aparece en Ubuntu.')
