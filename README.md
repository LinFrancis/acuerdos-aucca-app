# Acuerdos AUCCA — App modular (Streamlit)

## Estructura
```
acuerdos_app/
├─ acuerdos.py
├─ secciones/
│  ├─ links_claves.py
│  ├─ acuerdos_internos.py
│  ├─ acuerdos_externos.py
│  └─ checklist.py
├─ ui/estilos.py
├─ data/google.py
├─ utils/busqueda.py
├─ images/
│  ├─ logo_aucca.png
│  └─ queltehue.png
└─ .streamlit/
   ├─ secrets.example.toml
   └─ secrets.toml (no versionar)
```

## Configuración
1. Crea y activa tu entorno (recomendado):
   ```bash
   python -m venv venv && source venv/bin/activate  # Linux/Mac
   # o en Windows (PowerShell):
   # python -m venv venv; venv\Scripts\Activate.ps1
   ```

2. Instala dependencias:
   ```bash
   pip install -r requirements.txt
   ```

3. Configura credenciales de Google en `.streamlit/secrets.toml` (NO subas este archivo a Git):
   - Usa el ejemplo en `.streamlit/secrets.example.toml` y pega tu JSON de service account bajo `[gspread]`.

4. Ejecuta la app:
   ```bash
   streamlit run acuerdos.py
   ```

## Notas
- El `SHEET_KEY` está en `data/google.py`. Si cambia, actualízalo allí.
- Puedes crear más temas/estilos en `ui/` y cambiar el import en `acuerdos.py`.
- Cada sección expone `render()` para mantener el router súper simple.

## Pestañas nuevas

### Eventos (`secciones/gestion_eventos.py`)
Punto de venta y cierre de eventos. **No lee ni escribe la hoja `finanzas`**: al cerrar un evento solo informa cuánto debe ingresarse *manualmente* como dinero de AUCCA. Usa las hojas `evt_*`.

### Cooperativa de Trabajo (`secciones/cooperativa.py`)
Proyectos con oferta (servicios y productos), ventas, producción, costos y horas; reparto del dinero con 6 métodos comparables (A–F); escenarios de parámetros; planificación de actividades futuras; pagos y fondos del proyecto (separados de AUCCA); perfiles; círculos, acuerdos y tensiones; manual.

```
secciones/coop_motor.py    # cálculos (sin Streamlit; con tests)
secciones/coop_datos.py    # Google Sheets (hojas coop_*) o archivo local si no hay credenciales
secciones/coop_ejemplo.py  # datos de ejemplo del viernes 13 de nov (SIMULADOS)
secciones/cooperativa.py   # pantallas
docs/                      # manual, supuestos y fórmulas, reglamento borrador, notas legales
tests/test_coop_motor.py   # pytest
```

Hojas que se crean solas en el Google Sheet: `coop_proyectos`, `coop_items`, `coop_ventas`, `coop_produccion`, `coop_costos`, `coop_registro`, `coop_personas`, `coop_parametros`, `coop_pagos`, `coop_fondos`, `coop_gobernanza`.

Probar sin credenciales (guarda en `data/local_coop/`, ignorado por git):
```bash
streamlit run acuerdos.py
python -m pytest tests -q
```
