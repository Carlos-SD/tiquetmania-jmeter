#!/usr/bin/env python3
"""Muestrea CPU y memoria de la API y de JMeter cada segundo mientras dura una prueba.

Alternativa a PerfMon cuando el ServerAgent no está disponible. Escribe un CSV con:
segundo, cpu_api (%), mem_api (MB), cpu_jmeter (%), mem_jmeter (MB), cpu_equipo (% del total).

Uso: python3 muestreo.py <pid_api> <pid_jmeter> <salida.csv>
Termina solo cuando el proceso de JMeter termina.
"""
import os
import subprocess
import sys
import time

pid_api, pid_jmeter, salida = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
nucleos = os.cpu_count() or 1


def proceso(pid):
    r = subprocess.run(["ps", "-o", "%cpu=,rss=", "-p", str(pid)], capture_output=True, text=True)
    if not r.stdout.strip():
        return None
    cpu, rss = r.stdout.split()
    return float(cpu), int(rss) / 1024


def cpu_equipo():
    r = subprocess.run(["ps", "-A", "-o", "%cpu="], capture_output=True, text=True)
    return sum(float(x) for x in r.stdout.split()) / nucleos


inicio = time.time()
with open(salida, "w") as f:
    f.write("segundo,cpu_api,mem_api_mb,cpu_jmeter,mem_jmeter_mb,cpu_equipo\n")
    while True:
        jm = proceso(pid_jmeter)
        if jm is None:
            break
        api = proceso(pid_api) or (0.0, 0.0)
        f.write(f"{time.time() - inicio:.0f},{api[0]:.1f},{api[1]:.1f},{jm[0]:.1f},{jm[1]:.1f},{cpu_equipo():.1f}\n")
        f.flush()
        time.sleep(1)
