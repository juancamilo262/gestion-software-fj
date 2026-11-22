from abc import ABC, abstractmethod
from datetime import datetime
import logging
from typing import Optional


def iniciar_log(archivo_log: str = "software_fj.log") -> logging.Logger:
    logger = logging.getLogger("SoftwareFJ")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        formato = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        manejador = logging.FileHandler(archivo_log, mode="a", encoding="utf-8")
        manejador.setFormatter(formato)
        logger.addHandler(manejador)

    return logger


class ErrorSoftwareFJ(Exception):
    pass


class ErrorValidacion(ErrorSoftwareFJ):
    pass


class ErrorDisponibilidad(ErrorSoftwareFJ):
    pass


class ErrorReserva(ErrorSoftwareFJ):
    pass


class ErrorCalculo(ErrorSoftwareFJ):
    pass


class EntidadBase(ABC):
    def __init__(self, codigo: str, logger: logging.Logger) -> None:
        if not isinstance(codigo, str) or not codigo.strip():
            raise ErrorValidacion("El código no puede estar vacío.")
        self._codigo = codigo.strip().upper()
        self._logger = logger
        self._creado_en = datetime.now()

    @property
    def codigo(self) -> str:
        return self._codigo

    @abstractmethod
    def resumen(self) -> str:
        pass


class Cliente(EntidadBase):
    def __init__(self, codigo: str, nombre: str, correo: str, logger: logging.Logger) -> None:
        super().__init__(codigo, logger)
        self.nombre = nombre
        self.correo = correo
        self._activo = True

    @property
    def nombre(self) -> str:
        return self._nombre

    @nombre.setter
    def nombre(self, valor: str) -> None:
        if not isinstance(valor, str) or len(valor.strip()) < 3:
            raise ErrorValidacion("Nombre inválido: debe tener mínimo 3 caracteres.")
        self._nombre = valor.strip()

    @property
    def correo(self) -> str:
        return self._correo

    @correo.setter
    def correo(self, valor: str) -> None:
        if not isinstance(valor, str) or "@" not in valor or "." not in valor.split("@")[-1]:
            raise ErrorValidacion(f"Correo no válido: {valor}")
        self._correo = valor.strip().lower()

    @property
    def activo(self) -> bool:
        return self._activo

    def resumen(self) -> str:
        estado = "Activo" if self._activo else "Inactivo"
        return f"Cliente {self._codigo} - {self._nombre} ({self._correo}) [{estado}]"


class Servicio(EntidadBase):
    def __init__(
        self,
        codigo: str,
        nombre: str,
        tarifa_base: float,
        logger: logging.Logger,
        disponible: bool = True,
    ) -> None:
        super().__init__(codigo, logger)
        self.validar_parametros(nombre=nombre, tarifa_base=tarifa_base)
        self._nombre = nombre.strip()
        self._tarifa_base = float(tarifa_base)
        self._disponible = disponible

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def tarifa_base(self) -> float:
        return self._tarifa_base

    @property
    def disponible(self) -> bool:
        return self._disponible

    def cambiar_disponibilidad(self, estado: bool) -> None:
        self._disponible = bool(estado)

    @abstractmethod
    def validar_parametros(self, **kwargs) -> None:
        pass

    @abstractmethod
    def describir(self) -> str:
        pass

    @abstractmethod
    def _subtotal_por_unidades(self, cantidad: int) -> float:
        pass

    def calcular_costo(
        self,
        cantidad: int,
        descuento: float = 0.0,
        impuesto: float = 19.0,
        recargo: float = 0.0,
    ) -> float:
        try:
            if not isinstance(cantidad, int) or isinstance(cantidad, bool) or cantidad <= 0:
                raise ErrorValidacion("La cantidad o duración debe ser un entero mayor que 0.")
            if descuento < 0 or descuento >= 100 or impuesto < 0 or recargo < 0:
                raise ErrorCalculo("Valores de descuento, impuesto o recargo fuera de rango.")

            base = self._subtotal_por_unidades(cantidad) + recargo
            con_desc = base * (1 - descuento / 100.0)
            total = con_desc * (1 + impuesto / 100.0)

            if total <= 0:
                raise ErrorCalculo("El total calculado no es válido.")
            return round(total, 2)
        except ErrorSoftwareFJ:
            raise
        except Exception as exc:
            raise ErrorCalculo("Fallo en el cálculo del costo.") from exc

    def resumen(self) -> str:
        disp = "Disponible" if self._disponible else "Ocupado"
        return f"{self.describir()} | Tarifa: ${self._tarifa_base:,.2f} | {disp}"


class ReservaSala(Servicio):
    def __init__(self, codigo: str, nombre: str, tarifa_hora: float, capacidad: int, logger: logging.Logger) -> None:
        self._capacidad = capacidad
        super().__init__(codigo, nombre, tarifa_hora, logger)

    def validar_parametros(self, **kwargs) -> None:
        nombre = kwargs.get("nombre", "")
        tarifa = kwargs.get("tarifa_base", 0)
        if not isinstance(nombre, str) or not nombre.strip():
            raise ErrorValidacion("Falta el nombre de la sala.")
        if tarifa is None or float(tarifa) <= 0:
            raise ErrorValidacion("La tarifa por hora debe ser positiva.")
        if not isinstance(self._capacidad, int) or self._capacidad <= 0:
            raise ErrorValidacion("La capacidad debe ser un entero mayor que 0.")

    def describir(self) -> str:
        return f"Sala {self._codigo} '{self._nombre}' (cap. {self._capacidad})"

    def _subtotal_por_unidades(self, cantidad: int) -> float:
        return self._tarifa_base * cantidad


class AlquilerEquipo(Servicio):
    def __init__(self, codigo: str, nombre: str, tarifa_dia: float, tipo_equipo: str, logger: logging.Logger) -> None:
        self._tipo_equipo = tipo_equipo
        super().__init__(codigo, nombre, tarifa_dia, logger)

    def validar_parametros(self, **kwargs) -> None:
        nombre = kwargs.get("nombre", "")
        tarifa = kwargs.get("tarifa_base", 0)
        if not isinstance(nombre, str) or not nombre.strip():
            raise ErrorValidacion("Falta el nombre del equipo.")
        if tarifa is None or float(tarifa) <= 0:
            raise ErrorValidacion("La tarifa diaria debe ser positiva.")
        if not isinstance(self._tipo_equipo, str) or not self._tipo_equipo.strip():
            raise ErrorValidacion("Falta el tipo de equipo.")

    def describir(self) -> str:
        return f"Equipo {self._codigo} '{self._nombre}' ({self._tipo_equipo})"

    def _subtotal_por_unidades(self, cantidad: int) -> float:
        return self._tarifa_base * cantidad


class AsesoriaEspecializada(Servicio):
    def __init__(self, codigo: str, nombre: str, tarifa_sesion: float, area: str, logger: logging.Logger) -> None:
        self._area = area
        super().__init__(codigo, nombre, tarifa_sesion, logger)

    def validar_parametros(self, **kwargs) -> None:
        nombre = kwargs.get("nombre", "")
        tarifa = kwargs.get("tarifa_base", 0)
        if not isinstance(nombre, str) or not nombre.strip():
            raise ErrorValidacion("Falta el nombre de la asesoría.")
        if tarifa is None or float(tarifa) <= 0:
            raise ErrorValidacion("La tarifa por sesión debe ser positiva.")
        if not isinstance(self._area, str) or not self._area.strip():
            raise ErrorValidacion("Falta el área de la asesoría.")

    def describir(self) -> str:
        return f"Asesoría {self._codigo} '{self._nombre}' (área {self._area})"

    def _subtotal_por_unidades(self, cantidad: int) -> float:
        subtotal = self._tarifa_base * cantidad
        if cantidad >= 3:
            subtotal *= 0.95
        return subtotal


class Reserva(EntidadBase):
    def __init__(
        self,
        codigo: str,
        cliente: Cliente,
        servicio: Servicio,
        duracion: int,
        logger: logging.Logger,
        descuento: float = 0.0,
        impuesto: float = 19.0,
    ) -> None:
        super().__init__(codigo, logger)
        if not isinstance(cliente, Cliente) or not cliente.activo:
            raise ErrorReserva("Cliente no válido o inactivo.")
        if not isinstance(servicio, Servicio):
            raise ErrorReserva("Servicio no válido.")
        if not servicio.disponible:
            raise ErrorDisponibilidad(f"El servicio {servicio.codigo} no está disponible.")

        self._cliente = cliente
        self._servicio = servicio
        self._duracion = duracion
        self._estado = "PENDIENTE"
        self._total = servicio.calcular_costo(
            cantidad=duracion,
            descuento=descuento,
            impuesto=impuesto,
        )

    @property
    def estado(self) -> str:
        return self._estado

    def confirmar(self) -> None:
        if self._estado == "CANCELADA":
            raise ErrorReserva("La reserva está cancelada y no puede confirmarse.")
        if not self._servicio.disponible and self._estado != "CONFIRMADA":
            raise ErrorDisponibilidad("El servicio ya no está disponible.")
        self._servicio.cambiar_disponibilidad(False)
        self._estado = "CONFIRMADA"

    def cancelar(self) -> None:
        if self._estado == "CANCELADA":
            raise ErrorReserva("La reserva ya estaba cancelada.")
        self._servicio.cambiar_disponibilidad(True)
        self._estado = "CANCELADA"

    def procesar(self) -> str:
        if self._estado != "CONFIRMADA":
            self.confirmar()
        self._estado = "PROCESADA"
        return f"Reserva {self._codigo} procesada. Total: ${self._total:,.2f}"

    def resumen(self) -> str:
        return (
            f"Reserva {self._codigo} | {self._cliente.nombre} | "
            f"{self._servicio.describir()} | Duración: {self._duracion} | "
            f"Total: ${self._total:,.2f} | {self._estado}"
        )


class SistemaReservas:
    def __init__(self, archivo_log: str = "software_fj.log") -> None:
        self.logger = iniciar_log(archivo_log)
        self.clientes: list[Cliente] = []
        self.servicios: list[Servicio] = []
        self.reservas: list[Reserva] = []

    def agregar_cliente(self, codigo: str, nombre: str, correo: str) -> Optional[Cliente]:
        try:
            if any(c.codigo == codigo.strip().upper() for c in self.clientes):
                raise ErrorValidacion(f"Código de cliente repetido: {codigo}")
            cliente = Cliente(codigo, nombre, correo, self.logger)
        except ErrorSoftwareFJ as exc:
            self.logger.error(f"Error registrando cliente {codigo}: {exc}")
            print(f"Error al registrar cliente: {exc}")
            return None
        else:
            self.clientes.append(cliente)
            self.logger.info(f"Cliente agregado: {cliente.resumen()}")
            print(f"Registrado: {cliente.resumen()}")
            return cliente

    def agregar_servicio(self, servicio: Servicio) -> None:
        try:
            if any(s.codigo == servicio.codigo for s in self.servicios):
                raise ErrorValidacion(f"Código de servicio repetido: {servicio.codigo}")
        except ErrorSoftwareFJ as exc:
            self.logger.error(f"Error agregando servicio {servicio.codigo}: {exc}")
            print(f"Error al registrar servicio: {exc}")
        else:
            self.servicios.append(servicio)
            self.logger.info(f"Servicio agregado: {servicio.resumen()}")
            print(f"Registrado: {servicio.resumen()}")

    def hacer_reserva(
        self,
        codigo_reserva: str,
        codigo_cliente: str,
        codigo_servicio: str,
        duracion: int,
        descuento: float = 0.0,
    ) -> Optional[Reserva]:
        completada = False
        try:
            cliente = next((c for c in self.clientes if c.codigo == codigo_cliente.strip().upper()), None)
            if cliente is None:
                raise ErrorReserva(f"No existe el cliente {codigo_cliente}.")

            servicio = next((s for s in self.servicios if s.codigo == codigo_servicio.strip().upper()), None)
            if servicio is None:
                raise ErrorReserva(f"No existe el servicio {codigo_servicio}.")

            reserva = Reserva(
                codigo=codigo_reserva,
                cliente=cliente,
                servicio=servicio,
                duracion=duracion,
                logger=self.logger,
                descuento=descuento,
            )
            msg = reserva.procesar()
        except ErrorSoftwareFJ as exc:
            try:
                raise ErrorReserva(f"Fallo procesando reserva {codigo_reserva}") from exc
            except ErrorReserva as ex_encadenada:
                self.logger.error(f"{ex_encadenada}: {exc}")
                print(f"Error en reserva {codigo_reserva}: {exc}")
                return None
        else:
            self.reservas.append(reserva)
            completada = True
            self.logger.info(f"{msg} | {reserva.resumen()}")
            print(msg)
            return reserva
        finally:
            self.logger.info(f"Fin de intento de reserva {codigo_reserva} (completada={completada})")


def correr_pruebas() -> None:
    sistema = SistemaReservas("software_fj.log")

    sistema.agregar_cliente("CL1", "Camila Vargas", "camila.vargas@correo.com")
    sistema.agregar_cliente("CL2", "Mateo Rojas", "mateo_sin_arroba.com")
    sistema.agregar_cliente("CL3", "Sofía Mendoza", "sofia.mendoza@correo.com")

    try:
        sala = ReservaSala("SL1", "Sala Reuniones B", 75000, 10, sistema.logger)
        sistema.agregar_servicio(sala)
    except ErrorSoftwareFJ as exc:
        sistema.logger.error(f"Error creando sala SL1: {exc}")
        print(exc)

    try:
        equipo = AlquilerEquipo("EQ1", "Portátil Diseño", -15000, "Cómputo", sistema.logger)
        sistema.agregar_servicio(equipo)
    except ErrorSoftwareFJ as exc:
        sistema.logger.error(f"Error creando equipo EQ1: {exc}")
        print(exc)

    try:
        asesoria = AsesoriaEspecializada("AS1", "Consultoría Python", 120000, "Desarrollo", sistema.logger)
        sistema.agregar_servicio(asesoria)
    except ErrorSoftwareFJ as exc:
        sistema.logger.error(f"Error creando asesoría AS1: {exc}")
        print(exc)

    sistema.hacer_reserva("RS1", "CL1", "SL1", duracion=2, descuento=10.0)
    sistema.hacer_reserva("RS2", "CL3", "SL1", duracion=1)
    r3 = sistema.hacer_reserva("RS3", "CL3", "AS1", duracion=3, descuento=5.0)

    if r3 is not None:
        try:
            r3.cancelar()
            sistema.logger.info(f"Reserva {r3.codigo} cancelada.")
            print(f"Reserva {r3.codigo} cancelada.")
        except ErrorSoftwareFJ as exc:
            sistema.logger.error(f"Error cancelando {r3.codigo}: {exc}")
            print(exc)

    sistema.hacer_reserva("RS4", "CL1", "AS1", duracion=0)

    print(f"\nTotal clientes: {len(sistema.clientes)}")
    print(f"Total servicios: {len(sistema.servicios)}")
    print(f"Total reservas: {len(sistema.reservas)}")


if __name__ == "__main__":
    correr_pruebas()