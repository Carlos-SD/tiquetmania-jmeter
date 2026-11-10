# API simple de compra de boletas — TicketMania

Esta versión tiene solo dos pasos, sin topes de capacidad, sin cola, sin límite de boletas y sin token de sesión.

## Cómo ejecutarla

```bash
python3 ticketmania_simple.py
```

Queda en `http://127.0.0.1:8080`. Para usar otro puerto: `python3 ticketmania_simple.py --puerto 9000`. Para detenerla, Ctrl+C. Requiere Python 3.8 o superior, sin librerías adicionales.

## Endpoints

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/api/tarifas` | Lista las tarifas y sus precios |
| POST | `/api/seleccion` | Paso 1: crea una reserva con tarifa y cantidad |
| POST | `/api/pago` | Paso 2: paga la reserva y la consume |
| GET | `/api/salud` | Verifica que la API esté arriba |

Tarifas: `general` ($80.000), `occidental` ($120.000), `preferencial` ($180.000), `vip` ($350.000).

## Probar con curl

```bash
curl -s localhost:8080/api/tarifas

curl -s -X POST localhost:8080/api/seleccion \
  -H 'Content-Type: application/json' \
  -d '{"tarifa":"general","cantidad":2}'
# -> {"reserva": "abc123...", "total": 160000, ...}

curl -s -X POST localhost:8080/api/pago \
  -H 'Content-Type: application/json' \
  -d '{"reserva":"abc123..."}'
# -> {"estado": "APROBADO", ...}
```

Si se paga la misma reserva dos veces, la segunda responde 404, porque la reserva ya se consumió.

## Usar con JMeter

1. **Thread Group**: número de usuarios y tiempo de subida (ramp-up).
2. **HTTP Request Defaults**: Server Name `localhost`, Port `8080`.
3. **HTTP Request 1, selección**: POST, path `/api/seleccion`, cuerpo `{"tarifa":"general","cantidad":1}`, header `Content-Type: application/json`.
4. **Regular Expression Extractor** (hijo de la petición 1):
   - Reference Name: `reserva`
   - Regular Expression: `"reserva":"([^"]+)"`
   - Template: `$1$`
5. **HTTP Request 2, pago**: POST, path `/api/pago`, cuerpo `{"reserva":"${reserva}"}`, header `Content-Type: application/json`.
6. **Response Assertion** en la petición 2: código 200.
7. Listeners: Summary Report y View Results Tree.

## Limitaciones de la simulación

- Todo está en memoria: al reiniciar la API, las reservas se pierden.
- El pago siempre se aprueba y responde al instante; no simula tiempos de espera ni rechazos.
- No hay validación de sesión.
