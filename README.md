# guides

## ¿Cómo descargar los reportes?

Si ya tienes acceso al repositorio, tienes dos opciones sencillas:

### 1. Clonar o actualizar el repo

```bash
git clone <URL_DEL_REPO>
# o si ya lo tienes
git pull
```

Los reportes viven en `reports/` y también los copiamos en `artefactos/` para tener una carpeta lista para adjuntar:

- `reports/resumen_ejecutivo_api_tarjetas.md` / `artefactos/resumen_ejecutivo_api_tarjetas.md`
- `reports/reporte_tecnico_api_tarjetas.md` / `artefactos/reporte_tecnico_api_tarjetas.md`
- `reports/reporte_tecnico_api_tarjetas.pdf` / `artefactos/reporte_tecnico_api_tarjetas.pdf`

### 2. Copiar todo listo para compartir

Ejecuta el script de apoyo para copiar los artefactos a una carpeta local (y opcionalmente generar un ZIP):

```bash
python scripts/export_reports.py               # copia a dist/
python scripts/export_reports.py ~/Downloads   # copia a otra ruta
python scripts/export_reports.py --zip         # copia + crea dist/reportes_api_tarjetas.zip
```

El directorio de destino contendrá los tres archivos listos para enviar por email o compartir por cualquier canal.

### 3. Descargar archivos sueltos desde GitHub (opcional)

Si prefieres bajar un archivo puntual, abre el archivo en la interfaz web de GitHub y usa el botón **Download raw file** (normalmente visible al presionar el botón “Download”).
