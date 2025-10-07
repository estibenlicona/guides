"""Utilidades para copiar o empaquetar los reportes generados."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "reports"
DEFAULT_DEST = REPO_ROOT / "dist"
REPORT_FILES = (
    "resumen_ejecutivo_api_tarjetas.md",
    "reporte_tecnico_api_tarjetas.md",
    "reporte_tecnico_api_tarjetas.pdf",
)


def collect_report_paths() -> Iterable[Path]:
    for name in REPORT_FILES:
        yield REPORTS_DIR / name


def copy_reports(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for report_path in collect_report_paths():
        if not report_path.exists():
            raise FileNotFoundError(f"No se encontró el archivo esperado: {report_path}")
        shutil.copy2(report_path, destination / report_path.name)


def build_zip(destination: Path) -> Path:
    zip_base = destination / "reportes_api_tarjetas"
    archive_path = shutil.make_archive(str(zip_base), "zip", destination)
    return Path(archive_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copia los reportes al directorio de salida y opcionalmente genera un ZIP listo para compartir.",
    )
    parser.add_argument(
        "dest",
        nargs="?",
        default=str(DEFAULT_DEST),
        help="Ruta donde se copiarán los reportes (por defecto: dist/).",
    )
    parser.add_argument(
        "--zip",
        action="store_true",
        help="Además de copiar los archivos, genera un ZIP con todos los reportes.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dest_path = Path(args.dest).expanduser().resolve()
    copy_reports(dest_path)
    if args.zip:
        zip_path = build_zip(dest_path)
        print(f"ZIP generado en: {zip_path}")
    print(f"Reportes copiados en: {dest_path}")


if __name__ == "__main__":
    main()
