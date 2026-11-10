# Tiquetmania: pruebas de rendimiento con JMeter

Monorepo con la API simulada de compra de boletas de Tiquetmania (Colombia vs Chile), el plan de JMeter que ejecuta el pipeline y el plan de experimentación local.

```
tiquetmania/
├── api/
│   └── ticketmania_simple.py        # API en http://127.0.0.1:8080
├── pruebas/
│   ├── jmeter/                      # despliegue: lo ejecuta el pipeline
│   │   ├── Ticketmania.jmx
│   │   └── datos.csv
│   └── experimentacion/             # "¿Qué pasaría si...?": solo local, el pipeline no lo ejecuta
│       ├── Experimentacion.jmx
│       ├── datos.csv
│       ├── experimentos.sh
│       └── muestreo.py
├── .github/workflows/
│   └── rendimiento.yml              # pipeline de GitHub Actions
└── README.md
```

## API

```bash
python3 api/ticketmania_simple.py            # puerto 8080
curl http://127.0.0.1:8080/api/salud         # {"estado": "OK"}
```

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/api/salud` | Verifica que la API esté arriba |
| GET | `/api/tarifas` | Lista tarifas y precios |
| POST | `/api/seleccion` | Crea una reserva: `{"tarifa":"general","cantidad":2}` |
| POST | `/api/pago` | Paga la reserva: `{"reserva":"<id>"}` → `{"estado":"APROBADO"}` |

## Ejercicio 1: despliegue en el pipeline

### Plan `pruebas/jmeter/Ticketmania.jmx`

```
Ticketmania (Plan de Pruebas)
├── Valores por Defecto para Petición HTTP   127.0.0.1:8080
├── Gestor de Cookies HTTP
├── Configuración del CSV Data Set           datos.csv (ruta relativa) → ${tarifa}, ${cantidad}
├── Seleccion de tarifa y Pago (Grupo de Hilos: 200 hilos, subida 300 s, bucle 1)
│   ├── Tarifas                     GET  /api/tarifas
│   ├── SeleccionTarifaYCantidad    POST /api/seleccion
│   │   ├── Gestor de Cabecera HTTP          Accept / Content-Type: application/json
│   │   ├── JSON Extractor                   reserva → ${num_reserva}
│   │   └── Temporizador Aleatorio Uniforme  500 ms + 0..1000 ms (500 a 1500 ms)
│   ├── Pago                        POST /api/pago  {"reserva":"${num_reserva}"}
│   │   ├── Gestor de Cabecera HTTP
│   │   └── JSON Assertion                   estado = APROBADO
│   └── Debug Sampler (deshabilitado)
├── Ver Árbol de Resultados (deshabilitado)
└── Reporte resumen
```

El plan no usa plugins (jp@gc), porque la máquina virtual de GitHub Actions solo tiene JMeter base.

### Pipeline `.github/workflows/rendimiento.yml`

Se ejecuta con cada push a `main` o a mano desde la pestaña **Actions** (`workflow_dispatch`). Un solo job en `ubuntu-latest`:

1. Descarga el repositorio.
2. Instala Java 17 (Temurin).
3. Descarga JMeter 5.6.3 y agrega su carpeta `bin` al `PATH` con `$GITHUB_PATH`.
4. Levanta la API en segundo plano.
5. Espera hasta 30 s a que `/api/salud` responda.
6. Ejecuta el plan en no-GUI desde `pruebas/jmeter/`: `jmeter -n -t Ticketmania.jmx -l resultados.jtl -e -o reporte`.
7. Revisa el `.jtl`: si hay peticiones fallidas, el job termina en rojo. El resumen queda en la página del run.
8. Sube el reporte HTML, el `.jtl` y el log de la API como artefacto `reporte-jmeter`, con `if: always()`.

El reporte se descarga desde el run en **Actions → Artifacts → reporte-jmeter** y se abre `reporte/index.html`.

Este escenario comprueba que la carga corre de principio a fin. No mide la capacidad de la API, porque en el pipeline la API y JMeter comparten la misma máquina virtual.

### Ejecutarlo en local

```bash
python3 api/ticketmania_simple.py &
cd pruebas/jmeter
~/apache-jmeter-5.6.3/bin/jmeter -n -t Ticketmania.jmx -l resultados.jtl -e -o reporte
```

## Ejercicio 2: experimentación "¿Qué pasaría si...?"

`pruebas/experimentacion/Experimentacion.jmx` es un plan distinto al del despliegue. El pipeline no lo ejecuta. Tiene cuatro Grupos de Hilos. Cada escenario se configura con propiedades `-J`, y un grupo con 0 hilos no se ejecuta:

| Grupo | Propiedades | Preguntas |
|---|---|---|
| Flujo de compra (Tarifas → Selección → Pago) | `flujo.hilos`, `flujo.rampa`, `flujo.bucles`, `flujo.duracion` | 1, 2, 3, 4, 5, 9, 10 |
| Solo Tarifas | `tarifas.*` | 6 |
| Solo Seleccion | `seleccion.*` | 6 |
| Reservas simultaneas (Temporizador Sincronizado) | `conc.hilos`, `conc.rampa`, `conc.grupo` | 7, 8 |

Temporizador Aleatorio Uniforme: `timer.desplazamiento` (500 por defecto) y `timer.aleatorio` (1000 por defecto). Para quitarlo, ambos van en 0.

El CSV de experimentación tiene `tarifa,cantidad,total_esperado`. Dos aserciones JSON comparan el `total` de la selección y del pago contra `precio × cantidad` (pregunta 9).

```bash
cd pruebas/experimentacion
./experimentos.sh                 # todos los escenarios (unos 30 minutos)
./experimentos.sh q3-sin-temp     # uno solo
```

Cada escenario deja en `resultados/<escenario>/` el `.jtl`, el reporte HTML y `recursos.csv` con la CPU y la memoria de la API y de JMeter.

**PerfMon:** el plan incluye *jp@gc - PerfMon Metrics Collector* deshabilitado. Para usarlo, inicia el ServerAgent 2.2.1 (`./startAgent.sh`, puerto 4444), habilita el colector y ejecuta el escenario de la pregunta 10.

**Limitación:** en este ejercicio la API y JMeter comparten el mismo computador. En una prueba real, la API debe correr en un equipo dedicado.
