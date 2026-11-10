#!/usr/bin/env bash
# Ejecuta los escenarios de "¿Qué pasaría si...?" con Experimentacion.jmx en modo no-GUI.
# Cada escenario reinicia la API (memoria limpia), muestrea CPU y memoria, y deja en
# resultados/<escenario>/ el .jtl, el reporte HTML y recursos.csv.
#
# Uso:  ./experimentos.sh                 # todos los escenarios
#       ./experimentos.sh q3-sin-temp     # solo los escenarios indicados
set -euo pipefail

cd "$(dirname "$0")"
JMETER="${JMETER:-$HOME/apache-jmeter-5.6.3/bin/jmeter}"
API="../../api/ticketmania_simple.py"
mkdir -p resultados

# nombre | propiedades -J (una variable cambia por pregunta)
ESCENARIOS=(
  # P1 y P4: carga y escalones de usuarios. Misma subida, duración y temporizador.
  "q1q4-020u|-Jflujo.hilos=20 -Jflujo.rampa=10 -Jflujo.bucles=-1 -Jflujo.duracion=60"
  "q1q4-050u|-Jflujo.hilos=50 -Jflujo.rampa=10 -Jflujo.bucles=-1 -Jflujo.duracion=60"
  "q1q4-100u|-Jflujo.hilos=100 -Jflujo.rampa=10 -Jflujo.bucles=-1 -Jflujo.duracion=60"
  "q1q4-250u|-Jflujo.hilos=250 -Jflujo.rampa=10 -Jflujo.bucles=-1 -Jflujo.duracion=60"
  "q1q4-500u|-Jflujo.hilos=500 -Jflujo.rampa=10 -Jflujo.bucles=-1 -Jflujo.duracion=60"
  # P2: solo cambia la subida.
  "q2-rampa01|-Jflujo.hilos=200 -Jflujo.rampa=1 -Jflujo.bucles=1"
  "q2-rampa60|-Jflujo.hilos=200 -Jflujo.rampa=60 -Jflujo.bucles=1"
  # P3: solo cambia el temporizador. P5: solo cambia la duración (la línea base es q3-con-temp).
  "q3-con-temp|-Jflujo.hilos=100 -Jflujo.rampa=10 -Jflujo.bucles=-1 -Jflujo.duracion=60"
  "q3-sin-temp|-Jflujo.hilos=100 -Jflujo.rampa=10 -Jflujo.bucles=-1 -Jflujo.duracion=60 -Jtimer.desplazamiento=0 -Jtimer.aleatorio=0"
  "q5-10min|-Jflujo.hilos=100 -Jflujo.rampa=10 -Jflujo.bucles=-1 -Jflujo.duracion=600"
  # P6: misma carga, solo cambia el endpoint.
  "q6-tarifas|-Jtarifas.hilos=100 -Jtarifas.rampa=10 -Jtarifas.bucles=-1 -Jtarifas.duracion=60"
  "q6-seleccion|-Jseleccion.hilos=100 -Jseleccion.rampa=10 -Jseleccion.bucles=-1 -Jseleccion.duracion=60"
  # P7: 500 reservas liberadas a la vez por el Temporizador Sincronizado.
  "q7-500-simultaneas|-Jconc.hilos=500 -Jconc.rampa=10 -Jconc.grupo=500"
  # P8: misma llegada (200 en 10 s); solo cambia si el Temporizador Sincronizado los agrupa.
  "q8-sincronizado|-Jconc.hilos=200 -Jconc.rampa=10 -Jconc.grupo=200"
  "q8-distribuido|-Jconc.hilos=200 -Jconc.rampa=10 -Jconc.grupo=1"
  # P10: 500 usuarios sostenidos 3 minutos, con muestreo de CPU y memoria.
  "q10-500u-3min|-Jflujo.hilos=500 -Jflujo.rampa=10 -Jflujo.bucles=-1 -Jflujo.duracion=180"
)

detener_api() { lsof -ti tcp:8080 | xargs kill 2>/dev/null || true; sleep 1; }

for e in "${ESCENARIOS[@]}"; do
  nombre="${e%%|*}"; props="${e#*|}"
  if [ $# -gt 0 ] && [[ ! " $* " =~ " $nombre " ]]; then continue; fi

  echo "=== $nombre ==="
  detener_api
  python3 "$API" > /dev/null 2>&1 &
  pid_api=$!
  until curl -fs http://127.0.0.1:8080/api/salud > /dev/null; do sleep 0.5; done

  dir="resultados/$nombre"
  rm -rf "$dir"; mkdir -p "$dir"
  # shellcheck disable=SC2086
  "$JMETER" -n -t Experimentacion.jmx -l "$dir/resultados.jtl" -e -o "$dir/reporte" -j "$dir/jmeter.log" $props > "$dir/consola.txt" 2>&1 &
  pid_jm=$!
  sleep 1
  pid_java=$(pgrep -f "ApacheJMeter.jar.*-l $dir/resultados.jtl" | head -1 || echo $pid_jm)
  python3 muestreo.py "$pid_api" "$pid_java" "$dir/recursos.csv" &
  pid_muestreo=$!
  wait $pid_jm || true
  wait $pid_muestreo || true
  grep "summary =" "$dir/consola.txt" | tail -1
done
detener_api
