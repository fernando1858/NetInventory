# NetInventory 2.0

**NetInventory** es una plataforma de gestión, documentación y análisis
de infraestructura de red desarrollada para el **Departamento TI del
Colegio Inglés**.

El sistema integra un **inventario físico basado en Microsoft Excel**
con una **base de datos SQLite** para administrar información operativa,
relaciones entre switches, topología de red, historial de cambios,
respaldos, monitoreo SNMP y herramientas de diagnóstico.

Su filosofía es simple: **el Excel continúa siendo la fuente oficial del
inventario**, mientras que **SQLite administra la información
operativa**, sin modificar nunca la documentación oficial.

------------------------------------------------------------------------

# Información del proyecto

-   **Aplicación:** NetInventory
-   **Versión:** 2.0.0
-   **Organización:** Colegio Inglés
-   **Área responsable:** Departamento TI
-   **Lenguaje:** Python
-   **Interfaz:** Consola (Rich)
-   **Arquitectura:** Excel + SQLite + SNMP
-   **Base de datos:** SQLite
-   **Inventario oficial:** Microsoft Excel

------------------------------------------------------------------------

# Funcionalidades

## Inventario

-   Lectura del Excel en modo solo lectura.
-   Detección automática de hojas y bloques.
-   Inventario de puertos, VLAN, patch panel y equipos.
-   Validación del inventario.
-   Detección de inconsistencias.

## Gestión de Switches

La hoja **PASSSWITCH** continúa siendo la fuente oficial de los
switches.

SQLite almacena además: - relaciones con bloques; - topología; -
historial; - criticidad; - clasificación; - fechas de actualización.

## Dashboard

Resumen general del estado del inventario, cobertura y salud de la
infraestructura.

## Buscador Universal

Búsqueda por IP, MAC, VLAN, patch panel, puerto, equipo, hoja, ubicación
o switch.

## Topología

-   Árbol jerárquico.
-   Relaciones padre-hijo.
-   Puertos de enlace.
-   Ruta hacia el Core.
-   Validación de ciclos.

## Centro de Impacto

-   Sectores afectados.
-   Descendientes.
-   Cobertura.
-   Prioridad.
-   Ruta hacia el Core.

## Centro de Salud

Análisis SNMP de tráfico, utilización, errores e incidencias.

## Descubrimiento SNMP

Descubre dispositivos nuevos y los compara con la base SQLite.

## Reportes

Generación automática de reportes Excel.

## Historial y Respaldos

Registro de cambios y respaldos automáticos antes de operaciones
críticas.

------------------------------------------------------------------------

# Menú principal

``` text
1. Buscar en NetInventory
2. Mostrar resumen general
3. Consultar ficha completa de red
4. Validar inventario
5. Gestionar switches y accesos
6. Generar reporte Excel
7. Centro de monitoreo SNMP
8. Centro de impacto de red
9. Centro de salud de la red
10. Asistente de incidencias
0. Salir
```

------------------------------------------------------------------------

# Instalación

``` powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Crear un archivo `.env`

``` env
CLAVE_ACCESOS=TU_CLAVE
```

Ubicar el Excel en:

``` text
datos/Configuración de Equipos Aruba.xlsx
```

Ejecutar:

``` powershell
python main.py
```

------------------------------------------------------------------------

# Filosofía

> El Excel continúa siendo la fuente oficial del inventario.
>
> SQLite administra la información operativa.
>
> NetInventory nunca modifica automáticamente la documentación oficial.

------------------------------------------------------------------------

# Desarrollo futuro

-   Interfaz gráfica.
-   Reportes PDF.
-   Mapa de topología.
-   Google Drive.
-   Zabbix.
-   LLDP/CDP.
-   API REST.

------------------------------------------------------------------------

# Seguridad

No publicar: - `.env` - Base SQLite - Respaldos - Reportes - Excel
oficial - Credenciales

------------------------------------------------------------------------

# Autor

**Fernando Espinosa**\
Práctica Profesional --- Departamento TI\
Colegio Inglés

**Versión 2.0.0**
