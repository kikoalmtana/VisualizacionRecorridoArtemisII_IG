#!/usr/bin/env python3
"""
Convierte un fichero de efemérides de Horizons (Luna respecto a la Tierra)
a un JSON compatible con la estructura utilizada para orion.json.

Uso:
    python horizons_a_json.py horizons_results.txt -o luna.json

Opcionalmente, reduce el número de muestras:
    python horizons_a_json.py horizons_results.txt -o luna.json --step 2

Las coordenadas de entrada deben ser posiciones cartesianas en KM-S y
referidas al marco "Ecliptic of J2000.0".

El resultado:
- transforma Eclíptico J2000 -> EME2000;
- transforma los ejes a Three.js (Y arriba);
- expresa las posiciones en radios terrestres de 6371 km;
- calcula t en segundos respecto al inicio de la misión Orion.

Se conservan también las muestras de Horizons anteriores y posteriores
al intervalo de la misión. Por ello, t puede contener valores negativos
y valores algo superiores a la duración de la misión. Esto permite
interpolar correctamente en los extremos de la simulación.
"""

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone


R_TIERRA = 6371.0  # km
RADIO_LUNA = 1737.4  # km

# Oblicuidad media J2000 de acuerdo con el valor IAU76 indicado
# en la cabecera del fichero de Horizons: 84381.448 segundos de arco.
OBLICUIDAD_J2000 = math.radians(84381.448 / 3600.0)

# Épocas del JSON de Orion proporcionado como referencia.
# Se utilizan como referencia común para que estado.t sirva para ambos.
EPOCA_INICIO = "2026-04-02T01:58:21.397"
EPOCA_FIN = "2026-04-10T23:53:24.643"


def parsear_fecha_horizons(texto):
    """Convierte 'A.D. 2026-Apr-01 22:35:12.0000' a datetime UTC."""
    texto = texto.strip()
    texto = re.sub(r"^A\.D\.\s*", "", texto)

    try:
        fecha = datetime.strptime(texto, "%Y-%b-%d %H:%M:%S.%f")
    except ValueError:
        fecha = datetime.strptime(texto, "%Y-%b-%d %H:%M:%S")

    return fecha.replace(tzinfo=timezone.utc)


def parsear_fecha_iso(texto):
    """Convierte una época ISO a datetime UTC."""
    fecha = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)
    return fecha.astimezone(timezone.utc)


def leer_horizons(ruta):
    """Lee las filas situadas entre $$SOE y $$EOE."""
    puntos = []
    dentro_datos = False
    encontrado_inicio = False
    encontrado_fin = False

    with open(ruta, "r", encoding="utf-8", errors="replace") as fichero:
        for numero_linea, linea in enumerate(fichero, start=1):
            linea = linea.strip()

            if linea == "$$SOE":
                dentro_datos = True
                encontrado_inicio = True
                continue

            if linea == "$$EOE":
                dentro_datos = False
                encontrado_fin = True
                break

            if not dentro_datos or not linea:
                continue

            campos = [campo.strip() for campo in linea.split(",")]

            # Formato esperado:
            # JDUT, fecha calendario, X, Y, Z,
            if len(campos) < 5:
                continue

            try:
                fecha = parsear_fecha_horizons(campos[1])
                x, y, z = (float(campos[i]) for i in (2, 3, 4))
            except (ValueError, IndexError):
                # Ignora líneas que no sean muestras numéricas.
                continue

            puntos.append((fecha, x, y, z))

    if not encontrado_inicio or not encontrado_fin:
        raise ValueError("No se ha encontrado el bloque completo $$SOE / $$EOE.")

    if not puntos:
        raise ValueError("No se han encontrado muestras válidas en el fichero.")

    puntos.sort(key=lambda punto: punto[0])

    # Eliminar épocas duplicadas, si las hubiera.
    unicos = []
    fecha_anterior = None
    for punto in puntos:
        if punto[0] != fecha_anterior:
            unicos.append(punto)
            fecha_anterior = punto[0]

    return unicos


def ecliptico_a_three(x, y, z):
    """
    Convierte Eclíptico J2000 (km) a EME2000 y después a Three.js.

    1. Rotación alrededor de X por la oblicuidad:
       x_eme = x
       y_eme = y*cos(eps) - z*sin(eps)
       z_eme = y*sin(eps) + z*cos(eps)

    2. Cambio de ejes a Three.js (Y arriba):
       (x_three, y_three, z_three) = (x_eme, z_eme, -y_eme)

    3. Conversión de km a radios terrestres.
    """
    cos_eps = math.cos(OBLICUIDAD_J2000)
    sin_eps = math.sin(OBLICUIDAD_J2000)

    x_eme = x
    y_eme = y * cos_eps - z * sin_eps
    z_eme = y * sin_eps + z * cos_eps

    return [
        round(x_eme / R_TIERRA, 5),
        round(z_eme / R_TIERRA, 5),
        round(-y_eme / R_TIERRA, 5),
    ]


def convertir(puntos, epoca_inicio, epoca_fin, step):
    """Construye el diccionario con el formato de orion.json."""
    seleccionados = puntos[::step]

    # Igual que en oem_a_json.py, conservar siempre la última muestra.
    if seleccionados[-1][0] != puntos[-1][0]:
        seleccionados.append(puntos[-1])

    posiciones = []
    tiempos = []
    distancias = []

    for fecha, x, y, z in seleccionados:
        tiempos.append(round((fecha - epoca_inicio).total_seconds(), 3))
        posiciones.append(ecliptico_a_three(x, y, z))
        distancias.append(round(math.sqrt(x*x + y*y + z*z), 1))

    return {
        "objeto": "MOON",
        "centro": "EARTH",
        "marco": "EME2000",
        "sistema_tiempo": "UTC",
        "unidad_posicion": "radios terrestres (6371 km), ejes three.js (Y arriba)",
        "epoca_inicio": epoca_inicio.isoformat(timespec="milliseconds").replace("+00:00", ""),
        "epoca_fin": epoca_fin.isoformat(timespec="milliseconds").replace("+00:00", ""),
        "t": tiempos,
        "pos": posiciones,
        "dist_tierra_km": distancias,
        "radio_tierra": 1.0,
        "luna_radio": round(RADIO_LUNA / R_TIERRA, 5),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Convierte las efemérides de la Luna de Horizons a JSON para Three.js."
    )
    parser.add_argument("horizons", help="Fichero horizons_results.txt")
    parser.add_argument("-o", "--out", default="luna.json", help="JSON de salida (por defecto: luna.json)")
    parser.add_argument("--step", type=int, default=1,
                        help="Conservar 1 de cada N muestras (por defecto: 1, todas)")
    parser.add_argument("--epoch-start", default=EPOCA_INICIO,
                        help="Época inicial de referencia, igual que en orion.json")
    parser.add_argument("--epoch-end", default=EPOCA_FIN,
                        help="Época final de la misión, igual que en orion.json")
    args = parser.parse_args()

    if args.step < 1:
        parser.error("--step debe ser un entero mayor o igual que 1")

    try:
        epoca_inicio = parsear_fecha_iso(args.epoch_start)
        epoca_fin = parsear_fecha_iso(args.epoch_end)
        puntos = leer_horizons(args.horizons)

        resultado = convertir(puntos, epoca_inicio, epoca_fin, args.step)

        with open(args.out, "w", encoding="utf-8") as fichero:
            json.dump(resultado, fichero, separators=(",", ":"), ensure_ascii=False)

        print(f"{len(puntos)} muestras leídas de Horizons.")
        print(f"{len(resultado['t'])} muestras escritas en {args.out}.")
        print(f"Época de referencia: {resultado['epoca_inicio']}")
        print(f"Rango temporal de las muestras: "
              f"{resultado['t'][0]} s a {resultado['t'][-1]} s.")
        print(f"Distancia Tierra-Luna: "
              f"{min(resultado['dist_tierra_km']):.1f} - "
              f"{max(resultado['dist_tierra_km']):.1f} km.")

    except (OSError, ValueError) as error:
        sys.exit(f"Error: {error}")


if __name__ == "__main__":
    main()
