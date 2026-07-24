import os

from config import (
    ANCHO_CONSOLA,
    NOMBRE_APLICACION,
    VERSION_APLICACION
)


class InterfazUsuario:
    """
    Centraliza la presentación y las interacciones
    comunes de la consola de NetInventory.

    Este módulo no contiene lógica de inventario ni
    modifica archivos o bases de datos.
    """

    PREFIJO_EXITO = "[OK]"
    PREFIJO_ERROR = "[ERROR]"
    PREFIJO_AVISO = "[AVISO]"
    PREFIJO_INFO = "[INFO]"

    RESPUESTAS_AFIRMATIVAS = {
        "s",
        "si",
        "sí"
    }

    @staticmethod
    def limpiar_pantalla():
        """
        Limpia la consola en Windows o sistemas Unix.
        """
        comando = (
            "cls"
            if os.name == "nt"
            else "clear"
        )

        os.system(comando)

    @staticmethod
    def linea(
        caracter="=",
        ancho=ANCHO_CONSOLA
    ):
        """
        Devuelve una línea separadora.
        """
        return caracter * ancho

    @classmethod
    def mostrar_titulo(
        cls,
        titulo,
        limpiar=False
    ):
        """
        Muestra un encabezado uniforme.
        """
        if limpiar:
            cls.limpiar_pantalla()

        print(
            "\n"
            + cls.linea()
        )

        print(
            str(titulo).upper().center(
                ANCHO_CONSOLA
            )
        )

        print(
            cls.linea()
        )

    @classmethod
    def mostrar_titulo_principal(cls):
        """
        Muestra el encabezado principal del programa.
        """
        cls.limpiar_pantalla()

        print(
            cls.linea()
        )

        print(
            NOMBRE_APLICACION.upper().center(
                ANCHO_CONSOLA
            )
        )

        print(
            f"Versión {VERSION_APLICACION}".center(
                ANCHO_CONSOLA
            )
        )

        print(
            cls.linea()
        )

    @classmethod
    def mostrar_subtitulo(
        cls,
        texto
    ):
        """
        Muestra una sección secundaria.
        """
        print(
            "\n"
            + cls.linea(
                caracter="-"
            )
        )

        print(
            str(texto).upper().center(
                ANCHO_CONSOLA
            )
        )

        print(
            cls.linea(
                caracter="-"
            )
        )

    @classmethod
    def mostrar_exito(
        cls,
        mensaje
    ):
        """
        Muestra un mensaje de éxito.
        """
        print(
            f"\n{cls.PREFIJO_EXITO} {mensaje}"
        )

    @classmethod
    def mostrar_error(
        cls,
        mensaje
    ):
        """
        Muestra un mensaje de error.
        """
        print(
            f"\n{cls.PREFIJO_ERROR} {mensaje}"
        )

    @classmethod
    def mostrar_aviso(
        cls,
        mensaje
    ):
        """
        Muestra una advertencia.
        """
        print(
            f"\n{cls.PREFIJO_AVISO} {mensaje}"
        )

    @classmethod
    def mostrar_info(
        cls,
        mensaje
    ):
        """
        Muestra información general.
        """
        print(
            f"\n{cls.PREFIJO_INFO} {mensaje}"
        )

    @classmethod
    def mostrar_lista_opciones(
        cls,
        opciones
    ):
        """
        Muestra una colección de opciones.

        Cada opción debe ser una tupla:
        (valor, descripción).
        """
        print()

        for valor, descripcion in opciones:
            print(
                f"{valor}) {descripcion}"
            )

        print(
            "\n"
            + cls.linea(
                caracter="-"
            )
        )

    @staticmethod
    def pedir_texto(
        mensaje,
        permitir_vacio=False
    ):
        """
        Solicita texto hasta recibir un valor válido.
        """
        while True:
            valor = input(
                mensaje
            ).strip()

            if valor or permitir_vacio:
                return valor

            print(
                "\n[AVISO] Este campo no puede "
                "quedar vacío."
            )

    @staticmethod
    def pedir_entero(
        mensaje,
        minimo=None,
        maximo=None
    ):
        """
        Solicita un número entero y valida su rango.
        """
        while True:
            valor = input(
                mensaje
            ).strip()

            try:
                numero = int(
                    valor
                )

            except ValueError:
                print(
                    "\n[ERROR] Debes ingresar un "
                    "número entero."
                )
                continue

            if (
                minimo is not None
                and numero < minimo
            ):
                print(
                    f"\n[ERROR] El valor mínimo "
                    f"permitido es {minimo}."
                )
                continue

            if (
                maximo is not None
                and numero > maximo
            ):
                print(
                    f"\n[ERROR] El valor máximo "
                    f"permitido es {maximo}."
                )
                continue

            return numero

    @classmethod
    def confirmar(
        cls,
        mensaje
    ):
        """
        Solicita una confirmación S/N.
        """
        respuesta = input(
            f"{mensaje} (S/N): "
        ).strip().lower()

        return (
            respuesta
            in cls.RESPUESTAS_AFIRMATIVAS
        )

    @staticmethod
    def confirmar_texto(
        mensaje,
        texto_esperado
    ):
        """
        Solicita una confirmación textual estricta.
        """
        respuesta = input(
            mensaje
        ).strip()

        return respuesta == texto_esperado

    @staticmethod
    def pausar(
        mensaje="Presiona ENTER para continuar..."
    ):
        """
        Detiene temporalmente la navegación.
        """
        input(
            f"\n{mensaje}"
        )