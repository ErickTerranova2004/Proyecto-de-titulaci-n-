#!/usr/bin/env python3
"""Registra un archivo descargado en registro_datasets.csv (trazabilidad académica).

Uso:
  python register_file.py RUTA --dataset GHALogs \
      --url "https://zenodo.org/records/14796970" \
      --license "<texto tal como lo muestra la ficha>" \
      --version "10.5281/zenodo.14796970 v1.0.1" \
      --md5-oficial d6c83b48b14351b16766ca1f01290e87 \
      --obs "sin incidencias"

--md5-oficial: el md5 que Zenodo muestra junto al archivo (opcional).
La fecha de descarga se toma de la fecha de modificación del archivo; si
copiaste o moviste el archivo, indícala con --fecha AAAA-MM-DD.
"""
import argparse, csv, datetime as dt, hashlib, os

COLS = ["dataset","archivo","url_origen","licencia_mostrada","version_o_doi","fecha_descarga",
        "tamano_bytes","sha256","md5","md5_oficial","md5_coincide","observaciones"]

def hashes(path, chunk=8 * 1024 * 1024):
    s, m = hashlib.sha256(), hashlib.md5()
    with open(path, "rb") as f:
        while b := f.read(chunk):
            s.update(b); m.update(b)
    return s.hexdigest(), m.hexdigest()

def main():
    a = argparse.ArgumentParser()
    a.add_argument("path"); a.add_argument("--dataset", required=True)
    a.add_argument("--url", required=True); a.add_argument("--license", default="")
    a.add_argument("--version", default=""); a.add_argument("--md5-oficial", default="")
    a.add_argument("--fecha", default=""); a.add_argument("--obs", default="")
    a.add_argument("--registro", default="registro_datasets.csv")
    x = a.parse_args()

    size = os.path.getsize(x.path)
    sha, md5 = hashes(x.path)
    fecha = x.fecha or dt.datetime.fromtimestamp(os.path.getmtime(x.path)).date().isoformat()
    oficial = x.md5_oficial.strip().lower()
    coincide = "" if not oficial else ("SI" if oficial == md5 else "NO")
    row = dict(dataset=x.dataset, archivo=os.path.basename(x.path), url_origen=x.url,
               licencia_mostrada=x.license, version_o_doi=x.version, fecha_descarga=fecha,
               tamano_bytes=size, sha256=sha, md5=md5, md5_oficial=oficial,
               md5_coincide=coincide, observaciones=x.obs)
    nuevo = not os.path.exists(x.registro)
    with open(x.registro, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        if nuevo: w.writeheader()
        w.writerow(row)
    print(f"{row['archivo']}: {size:,} bytes | sha256={sha[:16]}… | md5={md5}")
    if coincide == "NO":
        print("ADVERTENCIA: el md5 NO coincide con el oficial; la descarga puede estar incompleta o corrupta.")

if __name__ == "__main__":
    main()
