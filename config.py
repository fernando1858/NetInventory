from pathlib import Path


# ==========================================================
# INFORMACIÓN DE LA APLICACIÓN
# ==========================================================

NOMBRE_APLICACION = "NetInventory"
VERSION_APLICACION = "1.0.0"
ORGANIZACION = "Colegio Inglés"
AREA_RESPONSABLE = "Departamento TI"


# ==========================================================
# RUTAS PRINCIPALES
# ==========================================================

CARPETA_PROYECTO = Path(__file__).resolve().parent

CARPETA_DATOS = (
    CARPETA_PROYECTO
    / "datos"
)

CARPETA_REPORTES = (
    CARPETA_PROYECTO
    / "reportes"
)

CARPETA_RESPALDOS = (
    CARPETA_PROYECTO
    / "backups"
)

RUTA_EXCEL = (
    CARPETA_DATOS
    / "Configuración de Equipos Aruba.xlsx"
)

RUTA_DB = (
    CARPETA_DATOS
    / "netinventory.db"
)

RUTA_ENV = (
    CARPETA_PROYECTO
    / ".env"
)


# ==========================================================
# CONFIGURACIÓN DE RESPALDOS
# ==========================================================

MAXIMO_RESPALDOS = 20


# ==========================================================
# CONFIGURACIÓN DEL INVENTARIO
# ==========================================================

PUERTO_MINIMO = 1
PUERTO_MAXIMO = 48

PREFIJO_IP_SWITCHES = "192.168.5."


# ==========================================================
# FORMATO DE CONSOLA
# ==========================================================

ANCHO_CONSOLA = 46
SEPARADOR_PRINCIPAL = "=" * ANCHO_CONSOLA
SEPARADOR_SECUNDARIO = "-" * ANCHO_CONSOLA


# ==========================================================
# COLORES DEL REPORTE EXCEL
# ==========================================================

COLOR_TITULO = "1F4E78"
COLOR_ENCABEZADO = "1F4E78"
COLOR_SUBTITULO = "D9EAF7"

COLOR_CORRECTO = "E2F0D9"
COLOR_INFORMATIVO = "DDEBF7"
COLOR_ADVERTENCIA = "FFF2CC"
COLOR_CRITICO = "F4CCCC"

COLOR_TEXTO_CLARO = "FFFFFF"
COLOR_BORDE = "B7B7B7"