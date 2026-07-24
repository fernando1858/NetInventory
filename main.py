import logging
import os

from dotenv import load_dotenv

from config import (
    AREA_RESPONSABLE,
    CARPETA_REPORTES,
    CARPETA_RESPALDOS,
    MAXIMO_RESPALDOS,
    NOMBRE_APLICACION,
    ORGANIZACION,
    RUTA_DB,
    RUTA_ENV,
    RUTA_EXCEL,
    SEPARADOR_PRINCIPAL,
    VERSION_APLICACION
)
from modulos.accesos_db import GestorAccesosDB
from modulos.analizador_red import AnalizadorRed
from modulos.analizador_reportes import AnalizadorReportes
from modulos.asistente_incidencias import AsistenteIncidencias
from modulos.buscador_universal import BuscadorUniversal
from modulos.centro_operaciones_noc import CentroOperacionesNOC
from modulos.centro_salud_red import CentroSaludRed
from modulos.centro_snmp_consola import CentroSNMPConsola
from modulos.dashboard import Dashboard
from modulos.exportador_excel import ExportadorExcel
from modulos.ficha_red import GestorFichasRed
from modulos.gestor_logs import GestorLogs
from modulos.gestor_topologia import GestorTopologia
from modulos.inventario import Inventario
from modulos.interfaz_consola import InterfazConsola
from modulos.relaciones import GestorRelaciones
from modulos.respaldos import GestorRespaldos
from modulos.revision_incompletos import RevisorIncompletos
from modulos.snmp_cliente import ClienteSNMP
from modulos.validador_inventario import ValidadorInventario


logger = logging.getLogger("netinventory")


def mostrar_encabezado_inicio():
    """Muestra la identificación principal de NetInventory."""
    ancho = len(SEPARADOR_PRINCIPAL)
    print(SEPARADOR_PRINCIPAL)
    print(NOMBRE_APLICACION.center(ancho))
    print(f"Versión {VERSION_APLICACION}".center(ancho))
    print(ORGANIZACION.center(ancho))
    print(AREA_RESPONSABLE.center(ancho))
    print(SEPARADOR_PRINCIPAL)


def validar_estructura_proyecto():
    """Comprueba los archivos y carpetas esenciales."""
    if not RUTA_EXCEL.exists():
        raise FileNotFoundError(
            "No se encontró el archivo Excel esperado:\n"
            f"{RUTA_EXCEL}"
        )

    CARPETA_REPORTES.mkdir(parents=True, exist_ok=True)
    CARPETA_RESPALDOS.mkdir(parents=True, exist_ok=True)
    RUTA_DB.parent.mkdir(parents=True, exist_ok=True)


def leer_entero_entorno(nombre, predeterminado):
    valor = os.getenv(nombre, str(predeterminado))

    try:
        return int(valor)
    except ValueError as error:
        raise ValueError(
            f"La variable {nombre} debe ser numérica."
        ) from error


def leer_decimal_entorno(nombre, predeterminado):
    valor = os.getenv(nombre, str(predeterminado))

    try:
        return float(valor)
    except ValueError as error:
        raise ValueError(
            f"La variable {nombre} debe ser numérica."
        ) from error


def leer_comunidades_entorno():
    valor = (
        os.getenv("SNMP_COMMUNITIES")
        or os.getenv("SNMP_COMMUNITY")
    )

    if not valor:
        raise ValueError(
            "No se encontró SNMP_COMMUNITIES "
            "en el archivo .env."
        )

    comunidades = [
        comunidad.strip()
        for comunidad in valor.split(",")
        if comunidad.strip()
    ]

    if not comunidades:
        raise ValueError(
            "No existen comunidades SNMP válidas."
        )

    return comunidades


def crear_cliente_snmp():
    try:
        return ClienteSNMP(
            comunidades=leer_comunidades_entorno(),
            puerto=leer_entero_entorno(
                "SNMP_PORT",
                161
            ),
            timeout=leer_decimal_entorno(
                "SNMP_TIMEOUT",
                3
            ),
            reintentos=leer_entero_entorno(
                "SNMP_RETRIES",
                1
            )
        )
    except (TypeError, ValueError) as error:
        print(
            "\n[AVISO] El Centro SNMP no estará disponible."
        )
        print(f"Detalle: {error}")
        return None


class CentroSNMPNoDisponible:
    def ejecutar(self):
        print(
            "\n[ERROR] El Centro SNMP no está disponible."
        )
        print(
            "Revisa SNMP_COMMUNITIES, SNMP_PORT, "
            "SNMP_TIMEOUT y SNMP_RETRIES en .env."
        )
        input("\nPresiona Enter para volver...")


def crear_aplicacion():
    print("\nCargando inventario...")

    inventario = Inventario(RUTA_EXCEL)
    inventario.cargar_excel()
    inventario.detectar_tablas_switches()
    inventario.cargar_registros_switches()

    print("Inventario cargado correctamente.")

    gestor_accesos = GestorAccesosDB(RUTA_DB)

    print("Base de datos cargada correctamente.")

    gestor_relaciones = GestorRelaciones(
        inventario=inventario,
        gestor_accesos=gestor_accesos
    )

    gestor_topologia = GestorTopologia(
        gestor_accesos
    )

    analizador_red = AnalizadorRed(
        inventario=inventario,
        gestor_topologia=gestor_topologia
    )

    gestor_fichas = GestorFichasRed(
        inventario=inventario,
        gestor_relaciones=gestor_relaciones,
        gestor_accesos=gestor_accesos
    )

    revisor_incompletos = RevisorIncompletos(
        inventario=inventario
    )

    validador_inventario = ValidadorInventario(
        inventario=inventario,
        gestor_relaciones=gestor_relaciones
    )

    analizador_reportes = AnalizadorReportes(
        inventario=inventario,
        gestor_relaciones=gestor_relaciones,
        validador_inventario=validador_inventario
    )

    buscador_universal = BuscadorUniversal(
        inventario=inventario,
        gestor_accesos=gestor_accesos,
        gestor_relaciones=gestor_relaciones
    )

    exportador = ExportadorExcel(
        carpeta_reportes=CARPETA_REPORTES,
        nombre_archivo_origen=RUTA_EXCEL.name,
        analizador_reportes=analizador_reportes,
        validador_inventario=validador_inventario
    )

    gestor_respaldos = GestorRespaldos(
        ruta_db=RUTA_DB,
        carpeta_respaldos=CARPETA_RESPALDOS,
        maximo_respaldos=MAXIMO_RESPALDOS
    )

    dashboard = Dashboard(
        inventario=inventario,
        gestor_accesos=gestor_accesos,
        gestor_relaciones=gestor_relaciones,
        revisor_incompletos=revisor_incompletos,
        gestor_topologia=gestor_topologia,
        analizador_red=analizador_red,
        ruta_excel=RUTA_EXCEL
    )

    cliente_snmp = crear_cliente_snmp()

    if cliente_snmp is None:
        centro_snmp = CentroSNMPNoDisponible()
    else:
        centro_snmp = CentroSNMPConsola(
            cliente_snmp=cliente_snmp,
            gestor_accesos=gestor_accesos,
            gestor_topologia=gestor_topologia,
            inventario=inventario
        )

    centro_salud_red = CentroSaludRed(
        gestor_topologia=gestor_topologia,
        analizador_red=analizador_red,
        centro_snmp=centro_snmp
    )

    asistente_incidencias = AsistenteIncidencias(
        analizador_red=analizador_red,
        gestor_topologia=gestor_topologia,
        centro_snmp=centro_snmp
    )

    centro_operaciones_noc = CentroOperacionesNOC(
        inventario=inventario,
        gestor_accesos=gestor_accesos,
        gestor_relaciones=gestor_relaciones,
        gestor_topologia=gestor_topologia,
        revisor_incompletos=revisor_incompletos,
        centro_snmp=centro_snmp,
        analizador_red=analizador_red,
        centro_salud_red=centro_salud_red,
        asistente_incidencias=asistente_incidencias
    )

    print("Componentes iniciados correctamente.")
    dashboard.mostrar()

    return InterfazConsola(
        inventario=inventario,
        gestor_accesos=gestor_accesos,
        exportador=exportador,
        gestor_fichas=gestor_fichas,
        gestor_relaciones=gestor_relaciones,
        revisor_incompletos=revisor_incompletos,
        validador_inventario=validador_inventario,
        gestor_respaldos=gestor_respaldos,
        buscador_universal=buscador_universal,
        centro_snmp=centro_snmp,
        gestor_topologia=gestor_topologia,
        analizador_red=analizador_red,
        centro_salud_red=centro_salud_red,
        asistente_incidencias=asistente_incidencias,
        centro_operaciones_noc=centro_operaciones_noc,
        ruta_excel=RUTA_EXCEL
    )


def main():
    global logger

    gestor_logs = GestorLogs(
        carpeta_logs="logs",
        nombre_archivo="netinventory.log"
    )

    logger = gestor_logs.configurar()

    logger.info(
        "Inicio de NetInventory."
    )

    load_dotenv(RUTA_ENV)
    validar_estructura_proyecto()

    aplicacion = crear_aplicacion()
    aplicacion.ejecutar()

    logger.info(
        "NetInventory finalizó correctamente."
    )


if __name__ == "__main__":
    mostrar_encabezado_inicio()

    try:
        main()

    except KeyboardInterrupt:
        logger.warning(
            "Programa interrumpido por el usuario."
        )

        print(
            "\n\nPrograma interrumpido por el usuario."
        )

    except FileNotFoundError as error:
        logger.exception(
            "Error de archivo durante la ejecución."
        )

        print(
            f"\nError de archivo:\n{error}"
        )

        print(
            "\nEl detalle técnico fue guardado en "
            "logs/netinventory.log"
        )

    except PermissionError as error:
        logger.exception(
            "Error de permisos durante la ejecución."
        )

        print(
            "\nError de permisos. Comprueba que los archivos "
            "no estén abiertos o bloqueados."
        )

        print(
            f"Detalle: {error}"
        )

        print(
            "\nEl detalle técnico fue guardado en "
            "logs/netinventory.log"
        )

    except Exception as error:
        logger.exception(
            "Error inesperado no controlado."
        )

        print(
            "\nNetInventory encontró un error inesperado."
        )

        print(
            f"Detalle: {error}"
        )

        print(
            "\nEl traceback completo fue guardado en "
            "logs/netinventory.log"
        )