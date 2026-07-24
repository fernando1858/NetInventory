from __future__ import annotations

import re
import shutil
import sqlite3
from datetime import datetime
from getpass import getpass
from ipaddress import IPv4Address
from pathlib import Path
from typing import Any

from modulos.visual import visual


class RegistradorDispositivoSNMP:
    """
    Registra de forma controlada un dispositivo descubierto
    por SNMP dentro de SQLite.

    Seguridad:
    - valida duplicados;
    - crea un respaldo antes de insertar;
    - solicita confirmación explícita;
    - oculta la contraseña con getpass;
    - registra el alta en el historial;
    - nunca modifica el Excel.
    """

    ROLES = [
        "CORE",
        "DISTRIBUCION",
        "ACCESO",
        "NO DEFINIDO"
    ]

    CRITICIDADES = [
        "CRITICA",
        "ALTA",
        "MEDIA",
        "BAJA",
        "NO DEFINIDA"
    ]

    def __init__(self, gestor_accesos):
        self.gestor_accesos = gestor_accesos
        self.base_datos = gestor_accesos.base_datos
        self.historial = gestor_accesos.historial

    @staticmethod
    def valor_visible(
        valor: Any,
        predeterminado: str = "-"
    ) -> str:
        if valor is None:
            return predeterminado

        texto = str(valor).strip()
        return texto or predeterminado

    @staticmethod
    def limpiar_texto(valor: Any) -> str | None:
        if valor is None:
            return None

        texto = str(valor).strip()
        return texto or None

    @staticmethod
    def ultimo_octeto(ip: str) -> int:
        direccion = IPv4Address(ip)
        return int(str(direccion).split(".")[-1])

    def detectar_marca_modelo(
        self,
        descripcion: str | None
    ) -> tuple[str | None, str | None]:
        texto = self.limpiar_texto(descripcion)

        if texto is None:
            return None, None

        marcas = {
            "aruba": "Aruba",
            "hewlett packard enterprise": "Aruba",
            "hpe": "Aruba",
            "cisco": "Cisco",
            "d-link": "D-Link",
            "dlink": "D-Link",
            "netgear": "Netgear",
            "mikrotik": "MikroTik",
            "ubiquiti": "Ubiquiti",
            "huawei": "Huawei",
            "dahua": "Dahua",
            "hp ": "HP"
        }

        marca = None
        texto_inferior = texto.lower()

        for patron, nombre in marcas.items():
            if patron in texto_inferior:
                marca = nombre
                break

        modelo = None

        patrones_modelo = [
            r"\b(JL\d{3,4}[A-Z]?)\b",
            r"\b(WS-C\d{4}[A-Z0-9\-]*)\b",
            r"\b(CBS\d{3,4}[A-Z0-9\-]*)\b",
            r"\b(SG\d{3,4}[A-Z0-9\-]*)\b",
            r"\b(CRS\d{3,4}[A-Z0-9\-]*)\b",
            r"\b(CSS\d{3,4}[A-Z0-9\-]*)\b"
        ]

        for patron in patrones_modelo:
            coincidencia = re.search(
                patron,
                texto,
                flags=re.IGNORECASE
            )

            if coincidencia:
                modelo = coincidencia.group(1).upper()
                break

        return marca, modelo

    def existe_ip(self, ip: str) -> bool:
        with self.base_datos.conectar() as conexion:
            fila = conexion.execute(
                """
                SELECT id
                FROM accesos_switches
                WHERE ip = ?;
                """,
                (ip,)
            ).fetchone()

        return fila is not None

    def existe_octeto(self, octeto: int) -> bool:
        with self.base_datos.conectar() as conexion:
            fila = conexion.execute(
                """
                SELECT id
                FROM accesos_switches
                WHERE ultimo_octeto = ?;
                """,
                (octeto,)
            ).fetchone()

        return fila is not None

    def crear_respaldo(self) -> Path | None:
        ruta_db = Path(
            self.base_datos.ruta_db
        )

        if not ruta_db.exists():
            return None

        carpeta = (
            ruta_db.parent
            / "respaldos_descubrimiento"
        )

        carpeta.mkdir(
            parents=True,
            exist_ok=True
        )

        marca_tiempo = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        destino = carpeta / (
            f"netinventory_antes_alta_{marca_tiempo}.db"
        )

        shutil.copy2(
            ruta_db,
            destino
        )

        return destino

    @staticmethod
    def pedir_opcion(
        titulo: str,
        opciones: list[str],
        predeterminado: str
    ) -> str:
        visual.subtitulo(titulo)

        for numero, opcion in enumerate(
            opciones,
            start=1
        ):
            visual.info(
                f"{numero}) {opcion}"
            )

        while True:
            entrada = input(
                f"Selecciona una opción "
                f"[{predeterminado}]: "
            ).strip()

            if not entrada:
                return predeterminado

            try:
                indice = int(entrada)
            except ValueError:
                visual.error(
                    "Debes ingresar un número."
                )
                continue

            if 1 <= indice <= len(opciones):
                return opciones[indice - 1]

            visual.error(
                "La opción seleccionada no existe."
            )

    @staticmethod
    def pedir_booleano(
        titulo: str
    ) -> int | None:
        while True:
            entrada = input(
                f"{titulo} [S/N/Enter sin definir]: "
            ).strip().lower()

            if not entrada:
                return None

            if entrada in {"s", "si", "sí"}:
                return 1

            if entrada in {"n", "no"}:
                return 0

            visual.error(
                "Escribe S, N o presiona Enter."
            )

    def construir_datos(
        self,
        dispositivo
    ) -> dict:
        marca_sugerida, modelo_sugerido = (
            self.detectar_marca_modelo(
                dispositivo.descripcion
            )
        )

        visual.limpiar()
        visual.titulo(
            "REGISTRAR SWITCH DESCUBIERTO",
            dispositivo.ip
        )

        visual.tabla(
            "Información obtenida por SNMP",
            [
                {
                    "nombre": "Campo",
                    "style": "cyan",
                    "no_wrap": True
                },
                "Valor"
            ],
            [
                (
                    "IP",
                    dispositivo.ip
                ),
                (
                    "Nombre SNMP",
                    self.valor_visible(
                        dispositivo.nombre
                    )
                ),
                (
                    "Descripción SNMP",
                    self.valor_visible(
                        dispositivo.descripcion
                    )
                ),
                (
                    "Comunidad utilizada",
                    self.valor_visible(
                        dispositivo.comunidad
                    )
                )
            ],
            expandir=True,
            mostrar_lineas=True
        )

        nombre_sugerido = (
            self.limpiar_texto(
                dispositivo.nombre
            )
            or f"Switch {dispositivo.ip}"
        )

        nombre = input(
            f"\nNombre [{nombre_sugerido}]: "
        ).strip() or nombre_sugerido

        ubicacion = input(
            "Ubicación: "
        ).strip()

        if not ubicacion:
            raise ValueError(
                "La ubicación es obligatoria."
            )

        marca = input(
            "Marca"
            f" [{marca_sugerida or 'sin definir'}]: "
        ).strip() or marca_sugerida

        modelo = input(
            "Modelo"
            f" [{modelo_sugerido or 'sin definir'}]: "
        ).strip() or modelo_sugerido

        usuario = input(
            "Usuario administrativo [admin]: "
        ).strip() or "admin"

        password = getpass(
            "Contraseña administrativa "
            "[Enter para dejar vacía]: "
        ).strip() or None

        rol = self.pedir_opcion(
            "Rol del switch",
            self.ROLES,
            "NO DEFINIDO"
        )

        criticidad = self.pedir_opcion(
            "Criticidad",
            self.CRITICIDADES,
            "NO DEFINIDA"
        )

        tiene_poe = self.pedir_booleano(
            "¿Tiene PoE?"
        )

        tiene_ups = self.pedir_booleano(
            "¿Tiene respaldo UPS?"
        )

        observaciones = input(
            "Observaciones "
            "[Descubierto automáticamente por SNMP]: "
        ).strip() or (
            "Descubierto automáticamente por SNMP. "
            f"sysDescr: {self.valor_visible(dispositivo.descripcion)}"
        )

        return {
            "ultimo_octeto": self.ultimo_octeto(
                dispositivo.ip
            ),
            "nombre": nombre,
            "ip": dispositivo.ip,
            "mac": None,
            "marca": marca,
            "modelo": modelo,
            "usuario": usuario,
            "password": password,
            "ubicacion": ubicacion,
            "observaciones": observaciones,
            "nombre_logico": nombre,
            "rol": rol,
            "criticidad": criticidad,
            "tiene_poe": tiene_poe,
            "tiene_ups": tiene_ups
        }

    def mostrar_resumen(
        self,
        datos: dict
    ) -> None:
        visual.tabla(
            "Resumen antes de guardar",
            [
                {
                    "nombre": "Campo",
                    "style": "yellow",
                    "no_wrap": True
                },
                "Valor"
            ],
            [
                ("IP", datos["ip"]),
                (
                    "Último octeto",
                    str(datos["ultimo_octeto"])
                ),
                ("Nombre", datos["nombre"]),
                ("Ubicación", datos["ubicacion"]),
                (
                    "Marca",
                    self.valor_visible(datos["marca"])
                ),
                (
                    "Modelo",
                    self.valor_visible(datos["modelo"])
                ),
                ("Usuario", datos["usuario"]),
                (
                    "Contraseña",
                    "Configurada"
                    if datos["password"]
                    else "Sin configurar"
                ),
                ("Rol", datos["rol"]),
                ("Criticidad", datos["criticidad"]),
                (
                    "PoE",
                    self.texto_booleano(datos["tiene_poe"])
                ),
                (
                    "UPS",
                    self.texto_booleano(datos["tiene_ups"])
                )
            ],
            expandir=True,
            mostrar_lineas=True
        )

    @staticmethod
    def texto_booleano(
        valor: int | None
    ) -> str:
        if valor == 1:
            return "Sí"

        if valor == 0:
            return "No"

        return "Sin definir"

    def insertar(
        self,
        datos: dict
    ) -> dict:
        consulta = """
        INSERT INTO accesos_switches (
            ultimo_octeto,
            nombre,
            ip,
            mac,
            marca,
            modelo,
            usuario,
            password,
            ubicacion,
            observaciones,
            nombre_logico,
            rol,
            criticidad,
            tiene_poe,
            tiene_ups
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """

        valores = (
            datos["ultimo_octeto"],
            datos["nombre"],
            datos["ip"],
            datos["mac"],
            datos["marca"],
            datos["modelo"],
            datos["usuario"],
            datos["password"],
            datos["ubicacion"],
            datos["observaciones"],
            datos["nombre_logico"],
            datos["rol"],
            datos["criticidad"],
            datos["tiene_poe"],
            datos["tiene_ups"]
        )

        try:
            with self.base_datos.conectar() as conexion:
                cursor = conexion.execute(
                    consulta,
                    valores
                )

                conexion.commit()

                switch_id = cursor.lastrowid

        except sqlite3.IntegrityError as error:
            raise ValueError(
                "No se pudo registrar porque la IP o el "
                "último octeto ya están utilizados."
            ) from error

        self.historial.registrar(
            accion="AGREGADO",
            entidad="switch",
            ultimo_octeto=datos["ultimo_octeto"],
            ip=datos["ip"],
            ubicacion=datos["ubicacion"],
            detalle=[
                {
                    "campo": "Switch descubierto",
                    "anterior": None,
                    "nuevo": datos["nombre"]
                },
                {
                    "campo": "Origen",
                    "anterior": None,
                    "nuevo": "Descubrimiento SNMP"
                }
            ],
            origen="Descubrimiento SNMP"
        )

        resultado = dict(datos)
        resultado["id"] = switch_id

        return resultado

    def registrar(
        self,
        dispositivo
    ) -> dict | None:
        if dispositivo.registrado:
            visual.info(
                "Este dispositivo ya está registrado."
            )
            return None

        if self.existe_ip(dispositivo.ip):
            raise ValueError(
                "La IP ya existe en SQLite."
            )

        octeto = self.ultimo_octeto(
            dispositivo.ip
        )

        if self.existe_octeto(octeto):
            raise ValueError(
                "El último octeto ya está siendo utilizado "
                "por otro registro."
            )

        datos = self.construir_datos(
            dispositivo
        )

        self.mostrar_resumen(
            datos
        )

        confirmacion = input(
            "\n¿Guardar este switch en SQLite? (S/N): "
        ).strip().lower()

        if confirmacion not in {"s", "si", "sí"}:
            visual.info(
                "Registro cancelado. No se realizaron cambios."
            )
            return None

        respaldo = self.crear_respaldo()

        if respaldo is not None:
            visual.ok(
                "Respaldo previo creado correctamente."
            )
            visual.info(
                f"Ruta: {respaldo}"
            )

        resultado = self.insertar(
            datos
        )

        dispositivo.registrado = True

        visual.ok(
            "Switch registrado correctamente en SQLite."
        )
        visual.info(
            "Ya está disponible para búsquedas, SNMP "
            "y clasificación topológica."
        )

        return resultado