#!/usr/bin/env python3
"""
API simulada SIMPLE de compra de boletas TicketMania (Colombia vs Chile).
Para enseñar JMeter. Sin topes, sin cola, sin límite de boletas y sin token.
Solo usa la biblioteca estándar de Python (3.8 o superior).

Uso:
  python3 ticketmania_simple.py              # puerto 8080
  python3 ticketmania_simple.py --puerto 9000

Flujo:
  1) POST /api/seleccion  {"tarifa": "general", "cantidad": 2}  -> {"reserva": "..."}
  2) POST /api/pago       {"reserva": "..."}                    -> {"estado": "APROBADO", ...}
"""
import argparse
import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TARIFAS = {
    "general":      {"nombre": "Gradería general",     "precio": 80000},
    "occidental":   {"nombre": "Gradería occidental",  "precio": 120000},
    "preferencial": {"nombre": "Preferencial",         "precio": 180000},
    "vip":          {"nombre": "VIP",                  "precio": 350000},
}

lock = threading.Lock()
reservas = {}  # id -> datos de la reserva (en memoria)


class Handler(BaseHTTPRequestHandler):
    server_version = "TicketManiaSimple/1.0"

    def _json(self, codigo, objeto):
        cuerpo = json.dumps(objeto, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, formato, *args):
        pass

    def do_GET(self):
        if self.path == "/api/tarifas":
            lista = [{"id": k, "nombre": v["nombre"], "precio": v["precio"]} for k, v in TARIFAS.items()]
            self._json(200, {"evento": "Colombia vs Chile", "tarifas": lista})
        elif self.path == "/api/salud":
            self._json(200, {"estado": "OK"})
        else:
            self._json(404, {"error": "Ruta no encontrada"})

    def do_POST(self):
        largo = int(self.headers.get("Content-Length") or 0)
        try:
            datos = json.loads(self.rfile.read(largo) or b"{}")
        except json.JSONDecodeError:
            return self._json(400, {"error": "JSON inválido"})

        if self.path == "/api/seleccion":
            tarifa = datos.get("tarifa")
            cantidad = datos.get("cantidad", 1)
            if tarifa not in TARIFAS:
                return self._json(400, {"error": "Tarifa inexistente", "tarifas": list(TARIFAS)})
            if not isinstance(cantidad, int) or cantidad < 1:
                return self._json(400, {"error": "La cantidad debe ser un entero mayor que 0"})
            rid = uuid.uuid4().hex
            total = TARIFAS[tarifa]["precio"] * cantidad
            with lock:
                reservas[rid] = {"tarifa": tarifa, "cantidad": cantidad, "total": total}
            return self._json(201, {"reserva": rid, "tarifa": tarifa, "cantidad": cantidad, "total": total})

        if self.path == "/api/pago":
            rid = datos.get("reserva")
            with lock:
                r = reservas.pop(rid, None)
            if r is None:
                return self._json(404, {"error": "Reserva no encontrada"})
            return self._json(200, {"estado": "APROBADO", "compra": uuid.uuid4().hex, **r})

        self._json(404, {"error": "Ruta no encontrada"})


def main():
    ap = argparse.ArgumentParser(description="API simple de compra de boletas TicketMania")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--puerto", type=int, default=8080)
    args = ap.parse_args()
    servidor = ThreadingHTTPServer((args.host, args.puerto), Handler)
    print(f"API TicketMania (simple) en http://{args.host}:{args.puerto}")
    print("Detener con Ctrl+C")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nAPI detenida")


if __name__ == "__main__":
    main()
