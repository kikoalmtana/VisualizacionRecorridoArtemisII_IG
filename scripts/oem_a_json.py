#!/usr/bin/env python3
"""
Convierte EM2_FODNAVBET_revF_PUBLIC.oem (trayectoria Orion, Artemis II)
a un JSON ligero para three.js.

Uso básico (sin dependencias):
    python oem_a_json.py EM2_FODNAVBET_revF_PUBLIC.oem -o orion.json --step 20

Con posición de la Luna (requiere: pip install spiceypy, y los kernels
naif0012.tls y de440s.bsp descargados de
https://naif.jpl.nasa.gov/pub/naif/generic_kernels/ ):
    python oem_a_json.py EM2_FODNAVBET_revF_PUBLIC.oem -o orion.json --step 20 \
        --moon --lsk naif0012.tls --spk de440s.bsp

Salida: posiciones en radios terrestres (1 unidad = 6371 km), ejes ya
convertidos a three.js (Y arriba): three = (x, z, -y) del marco inercial.
"""
import argparse, json, re, sys
from datetime import datetime, timezone, timedelta

R_TIERRA = 6371.0  # km


def parse_epoch(s):
    s = s.strip()
    # Formato año-día-del-año: 2026-092T01:58:00.000
    m = re.match(r"(\d{4})-(\d{3})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?$", s)
    if m:
        y, doy, hh, mm, ss, frac = m.groups()
        base = datetime(int(y), 1, 1, tzinfo=timezone.utc) + timedelta(days=int(doy) - 1)
        base = base.replace(hour=int(hh), minute=int(mm), second=int(ss))
        if frac:
            base += timedelta(microseconds=round(float(frac) * 1e6))
        return base
    # Formato calendario: 2026-04-02T01:58:00.000
    if "." in s:
        a, b = s.split(".")
        s = a + "." + (b + "000000")[:6]
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


def leer_oem(ruta):
    meta, puntos = {}, []
    en_meta = False
    with open(ruta, "r", encoding="utf-8", errors="replace") as f:
        for linea in f:
            l = linea.strip()
            if not l or l.startswith("COMMENT"):
                continue
            if l == "META_START":
                en_meta = True
                continue
            if l == "META_STOP":
                en_meta = False
                continue
            if en_meta or ("=" in l and not l[0].isdigit()):
                k, _, v = l.partition("=")
                meta.setdefault(k.strip(), v.strip())
                continue
            p = l.split()
            if len(p) >= 7 and p[0][0].isdigit():
                try:
                    vals = [float(x) for x in p[1:7]]
                except ValueError:
                    continue
                puntos.append((parse_epoch(p[0]), p[0], vals))
    puntos.sort(key=lambda t: t[0])
    # Elimina épocas duplicadas (extremos de bloque)
    unicos, ult = [], None
    for t in puntos:
        if t[0] != ult:
            unicos.append(t)
            ult = t[0]
    return meta, unicos


def a_three(x, y, z):
    return [round(x / R_TIERRA, 5), round(z / R_TIERRA, 5), round(-y / R_TIERRA, 5)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("oem")
    ap.add_argument("-o", "--out", default="orion.json")
    ap.add_argument("--step", type=int, default=20, help="1 de cada N puntos")
    ap.add_argument("--moon", action="store_true")
    ap.add_argument("--lsk", default="naif0012.tls")
    ap.add_argument("--spk", default="de440s.bsp")
    a = ap.parse_args()

    meta, pts = leer_oem(a.oem)
    if not pts:
        sys.exit("No se encontraron datos de estado en el OEM")
    print("Cabecera OEM:", {k: meta[k] for k in
          ("OBJECT_NAME", "CENTER_NAME", "REF_FRAME", "TIME_SYSTEM") if k in meta})
    print(f"{len(pts)} estados leídos")

    sel = pts[:: a.step]
    if sel[-1] is not pts[-1]:
        sel.append(pts[-1])  # conserva siempre el último punto (llegada)

    t0 = sel[0][0]
    out = {
        "objeto": meta.get("OBJECT_NAME", "Orion"),
        "centro": meta.get("CENTER_NAME"),
        "marco": meta.get("REF_FRAME"),
        "sistema_tiempo": meta.get("TIME_SYSTEM"),
        "unidad_posicion": "radios terrestres (6371 km), ejes three.js (Y arriba)",
        "epoca_inicio": sel[0][1],
        "epoca_fin": sel[-1][1],
        "t": [round((p[0] - t0).total_seconds(), 1) for p in sel],  # s desde inicio
        "pos": [a_three(*p[2][:3]) for p in sel],
        "vel_kms": [round((p[2][3] ** 2 + p[2][4] ** 2 + p[2][5] ** 2) ** 0.5, 4) for p in sel],
        "dist_tierra_km": [round((p[2][0] ** 2 + p[2][1] ** 2 + p[2][2] ** 2) ** 0.5, 1) for p in sel],
    }

    if a.moon:
        import spiceypy as sp
        sp.furnsh(a.lsk)
        sp.furnsh(a.spk)
        sufijo = " TDB" if (meta.get("TIME_SYSTEM", "").upper() == "TDB") else " UTC"
        moon = []
        for p in sel:
            et = sp.str2et(p[1] + sufijo)
            st, _ = sp.spkpos("MOON", et, "J2000", "NONE", "EARTH")
            moon.append(a_three(*st))
        out["luna_pos"] = moon
        out["luna_radio"] = round(1737.4 / R_TIERRA, 5)
        print("Posición de la Luna añadida")

    out["radio_tierra"] = 1.0
    with open(a.out, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    print(f"Escrito {a.out}: {len(sel)} muestras")


if __name__ == "__main__":
    main()
