# NetInventory

**NetInventory** es una herramienta interna de gestión y documentación de infraestructura de red desarrollada para el Departamento TI del Colegio Inglés.

El sistema centraliza información proveniente de un archivo Excel, permite relacionar bloques documentados con switches físicos, consultar puertos, validar inconsistencias y generar reportes.

---

## Información del proyecto

- **Aplicación:** NetInventory
- **Versión:** 1.0.0
- **Organización:** Colegio Inglés
- **Área responsable:** Departamento TI
- **Lenguaje:** Python
- **Interfaz:** Consola
- **Base de datos:** SQLite
- **Archivo de inventario:** Excel

---

## Funcionalidades principales

### Inventario de red

- Lectura del archivo Excel sin modificarlo.
- Detección automática de hojas y bloques de switches.
- Carga de puertos, equipos, bocas patch y VLAN.
- Normalización de tipos de dispositivos.
- Detección de puertos duplicados.
- Identificación de datos incompletos.

### Ficha completa de red

Permite consultar un puerto seleccionando:

1. hoja o sector;
2. switch relacionado;
3. número de puerto.

La ficha muestra:

- ubicación;
- fila del Excel;
- puerto del switch;
- equipo conectado;
- tipo de equipo;
- boca del patch panel;
- VLAN;
- IP del switch;
- MAC;
- marca;
- modelo.

### Gestión de switches

La hoja `PASSSWITCH` funciona como fuente oficial para los datos de los switches.

El sistema permite:

- importar switches nuevos;
- actualizar switches existentes;
- detectar switches eliminados del Excel;
- relacionar switches con bloques;
- validar relaciones;
- consultar accesos;
- consultar historial de cambios.

### Seguridad

- Acceso protegido mediante variable de entorno.
- Contraseñas no registradas en el historial.
- Respaldo automático antes de operaciones críticas.
- Confirmación antes de eliminar o restaurar información.
- El archivo Excel original se utiliza únicamente en modo lectura.

### Respaldos

La base SQLite se respalda antes de:

- importar o actualizar switches;
- modificar relaciones;
- eliminar relaciones;
- limpiar relaciones inválidas;
- restaurar una versión anterior.

Los respaldos se almacenan en la carpeta:

```text
backups/
```

Se conservan automáticamente los respaldos más recientes definidos en `config.py`.

### Historial

El sistema registra:

- switches agregados;
- switches actualizados;
- switches eliminados;
- relaciones creadas;
- relaciones modificadas;
- relaciones eliminadas.

Los cambios de contraseña se registran únicamente como:

```text
Contraseña: modificada
```

Los valores de las contraseñas no se guardan en el historial.

### Validación del inventario

NetInventory detecta, entre otros:

- campos obligatorios vacíos;
- puertos duplicados;
- puertos fuera de rango;
- VLAN no numéricas;
- bocas patch no numéricas;
- tipos no normalizados;
- troncales sin destino;
- switches sin relación;
- relaciones hacia bloques inexistentes.

### Reportes

El sistema genera reportes Excel en:

```text
reportes/
```

Actualmente el reporte contiene:

- resumen;
- inventario general;
- bloques incompletos;
- puertos repetidos;
- información de versión y organización.

---

## Estructura del proyecto

```text
NETINVENTORY/
├── backups/
├── datos/
│   ├── Configuración de Equipos Aruba.xlsx
│   └── netinventory.db
├── modulos/
│   ├── __init__.py
│   ├── accesos_db.py
│   ├── base_datos.py
│   ├── buscador.py
│   ├── dashboard.py
│   ├── exportador_excel.py
│   ├── ficha_red.py
│   ├── historial.py
│   ├── interfaz_consola.py
│   ├── inventario.py
│   ├── relaciones.py
│   ├── respaldos.py
│   ├── revision_incompletos.py
│   └── validador_inventario.py
├── reportes/
├── .env
├── .env.example
├── .gitignore
├── config.py
├── main.py
├── README.md
└── requirements.txt
```

---

## Requisitos

- Python 3.10 o superior.
- Microsoft Excel o aplicación compatible para revisar reportes.
- Acceso local al archivo de inventario.
- PowerShell en Windows.

Dependencias externas:

```text
openpyxl
python-dotenv
```

---

## Instalación en Windows

### 1. Abrir PowerShell en la carpeta del proyecto

```powershell
cd C:\Users\USUARIO\Ruta\NetInventory
```

### 2. Crear el entorno virtual

```powershell
python -m venv venv
```

### 3. Permitir temporalmente la activación

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

### 4. Activar el entorno virtual

```powershell
.\venv\Scripts\Activate.ps1
```

Cuando esté activo, PowerShell mostrará:

```text
(venv) PS C:\...\NetInventory>
```

### 5. Instalar dependencias

```powershell
python -m pip install -r requirements.txt
```

### 6. Configurar la clave de acceso

Crear un archivo llamado `.env` en la raíz:

```env
CLAVE_ACCESOS=CLAVE_SEGURA
```

### 7. Colocar el Excel

El archivo debe estar ubicado en:

```text
datos/Configuración de Equipos Aruba.xlsx
```

### 8. Ejecutar

```powershell
python main.py
```

---

## Menú principal

```text
1. Mostrar resumen general
2. Consultar ficha completa de red
3. Validar inventario
4. Gestionar switches y accesos
5. Generar reporte Excel
6. Salir
```

---

## Flujo recomendado de trabajo

1. Actualizar la información directamente en el Excel.
2. Guardar el Excel.
3. Ejecutar NetInventory nuevamente.
4. Revisar el dashboard.
5. Ejecutar la validación del inventario.
6. Corregir los datos pendientes en el Excel.
7. Importar o actualizar switches desde `PASSSWITCH`.
8. Generar un nuevo reporte.

---

## Fuente oficial de los datos

### Inventario y puertos

El archivo Excel es la fuente oficial para:

- hojas;
- bloques;
- puertos;
- equipos;
- bocas patch;
- VLAN;
- tipos de conexión.

NetInventory no modifica esta información.

### Switches

La hoja `PASSSWITCH` es la fuente oficial para:

- IP;
- descripción;
- marca;
- modelo;
- ubicación;
- MAC;
- contraseña.

La base SQLite mantiene:

- copia de consulta;
- relaciones con bloques;
- historial;
- fechas de actualización.

---

## Convenciones del Excel

Cada fila debe representar un puerto físico.

Formato recomendado:

```text
Tipo | Equipo | Boca Patch | Puerto Switch | VLAN
```

Reglas:

- mantener una fila por puerto;
- usar números en puerto, boca patch y VLAN;
- escribir `DISPONIBLE` para puertos libres;
- escribir `SIN IDENTIFICAR` cuando exista una conexión aún no reconocida;
- no eliminar filas de puertos libres;
- evitar celdas combinadas en las filas de datos;
- mantener encabezados consistentes;
- no dejar encabezados adicionales dentro de un bloque.

---

## Restauración de respaldos

Desde el módulo protegido:

```text
Gestionar switches y accesos
→ Restaurar respaldo
```

Al restaurar:

1. se valida el respaldo;
2. se crea una copia del estado actual;
3. se reemplaza la base SQLite;
4. se solicita reiniciar NetInventory.

La restauración no modifica el archivo Excel.

---

## Seguridad y privacidad

No deben compartirse ni subirse públicamente:

- `.env`;
- base de datos SQLite;
- respaldos;
- archivo Excel;
- reportes;
- contraseñas;
- credenciales de red.

El archivo `.gitignore` está configurado para proteger estos elementos.

---

## Desarrollo futuro

Las mejoras previstas son:

1. limpieza y estabilización final;
2. dashboard avanzado en el reporte;
3. gráficos de ocupación y distribución;
4. buscador universal;
5. lectura del Excel sincronizado mediante Google Drive;
6. integración SNMP de solo lectura;
7. integración complementaria con Zabbix.

---

## Política de modificación

NetInventory está diseñado para:

- consultar el inventario;
- validar información;
- generar reportes;
- administrar relaciones internas;
- mantener respaldos e historial.

Las correcciones de puertos, VLAN, equipos y patch panel deben realizarse directamente en el Excel oficial.