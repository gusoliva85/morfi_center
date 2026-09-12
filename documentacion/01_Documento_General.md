# MORFI CENTER
## 01 · Documento General (Funcional)

**Proyecto:** Morfi Center
**Documento:** Especificación general y funcional del producto (Fase 1)
**Basado en:** `MORFI_CENTER_INFO.md` (Especificación Maestra del Producto)
**Fecha:** 9 de septiembre de 2026
**Estado:** Versión 1.0 — base para diseño de mockups y arquitectura técnica

---

## Índice

1. Propósito del documento
2. Resumen ejecutivo
3. Objetivos del proyecto
4. Alcance
5. Actores y roles
6. Modelo operativo y ciclo diario
7. Requisitos funcionales por dominio
8. Flujos funcionales principales
9. Reglas de negocio
10. Máquina de estados del pedido
11. Modelo de datos funcional
12. Requisitos no funcionales
13. Arquitectura funcional y stack técnico
14. Diseño UI/UX y principios visuales
15. Estructura de pantallas
16. Notificaciones
17. Seguridad y privacidad
18. Decisiones abiertas y supuestos
19. Roadmap funcional por fases
20. Criterios de aceptación (MVP)
21. Glosario

---

## 1. Propósito del documento

Este documento traduce la visión conceptual de Morfi Center (descrita en `MORFI_CENTER_INFO.md`) en una **especificación funcional accionable**. Sirve como:

- Contrato funcional entre negocio y desarrollo.
- Base para el diseño de los mockups de la pantalla principal.
- Punto de partida para el modelo de datos relacional y la especificación de APIs.
- Referencia de criterios de aceptación del MVP.

No define implementación de código; define **qué** debe hacer el sistema, **para quién**, **con qué reglas** y **en qué orden** se construye.

---

## 2. Resumen ejecutivo

Morfi Center es una plataforma de **pedidos anticipados de comida** con producción centralizada y distribución programada. A diferencia del delivery inmediato, concentra la demanda antes de una **hora de cierre configurable**, permitiendo a la operación gastronómica planificar producción, stock, personal y rutas.

El público principal son **trabajadores de oficinas, fábricas y comercios** que resuelven su almuerzo durante la jornada laboral, muchas veces pidiendo varios a una misma dirección.

El flujo esencial es:

```
Catálogo → Pedido anticipado → Transferencia → Validación administrativa
→ Cierre de pedidos → Producción consolidada → Preparación
→ Asignación de delivery → Ruta optimizada → Entrega
```

El producto se construye **mobile-first** (uso principal del cliente y del repartidor) con una versión web de escritorio plenamente adaptada para la operación administrativa.

**Stack:** Frontend HTML + CSS + Tailwind. Backend Python + SQLite. Arquitectura simple, con carpetas `backend/` y `frontend/`, preparada para escalar.

---

## 3. Objetivos del proyecto

### 3.1 Objetivos de negocio

| # | Objetivo | Métrica de éxito |
|---|---|---|
| O1 | Anticipar y concentrar la demanda de almuerzos | % de pedidos recibidos antes del cierre |
| O2 | Planificar la producción según demanda real | Desvío entre producción estimada y pedidos aprobados |
| O3 | Reducir el costo logístico por pedido | Pedidos entregados por ruta / por repartidor |
| O4 | Dar previsibilidad al cliente (hora de entrega) | % de entregas dentro de la ventana estimada |
| O5 | Formalizar y controlar el cobro por transferencia | % de pagos validados antes de producción |

### 3.2 Objetivos de producto

- Que el cliente pueda **pedir en menos de 2 minutos** desde el teléfono.
- Que el cliente entienda **de un vistazo** si los pedidos están abiertos y cuánto tiempo queda.
- Que el administrador valide pagos y consolide producción **sin planillas externas**.
- Que el repartidor sepa **cuál es su próxima parada** sin fricción.

### 3.3 No-objetivos (fuera de foco inicial)

- Delivery inmediato / a demanda.
- Pago con tarjeta o procesadores externos (se deja la puerta abierta arquitectónicamente).
- App nativa iOS/Android (se entrega como web responsive / PWA a futuro).
- Múltiples turnos simultáneos (desayuno/cena) — la arquitectura no debe impedirlo.
- Pedidos grupales colaborativos.

---

## 4. Alcance

### 4.1 Dentro del alcance (Fase 1 → MVP funcional)

- Registro y autenticación (cuenta propia + Google).
- Catálogo administrable: categorías, productos, imágenes, stock.
- Promociones y Plato del Día con vigencia temporal.
- Carrito y creación de pedido.
- Direcciones del cliente y validación de cobertura (barrio y/o radio).
- Cálculo de costo de envío configurable.
- Ventana horaria de pedidos y cierre automático del turno.
- Pago por transferencia: datos de cuenta, monto exacto, carga de comprobante.
- Validación administrativa de pagos y aprobación de pedidos.
- Cancelación por el cliente con ventana límite y **saldo a favor**.
- Máquina de estados del pedido.
- Panel operativo: pedidos, validación, producción consolidada.
- Gestión de repartidores y asignación manual de pedidos.
- Seguimiento de entrega (estado + posición relativa en la ruta).
- Notificaciones in-app de eventos clave.

### 4.2 Fuera del alcance inmediato (fases posteriores)

- Optimización automática de rutas con proveedor externo de mapas.
- Seguimiento GPS en tiempo real de alta frecuencia.
- Asignación automática de pedidos a repartidores.
- Empresas como entidad con usuarios asociados.
- Analítica avanzada y reporting.
- Integración con pasarelas de pago.
- Propinas, evidencia de entrega con PIN/foto/firma.

---

## 5. Actores y roles

### 5.1 Actores

| Actor | Descripción | Dispositivo principal |
|---|---|---|
| **Cliente (CUSTOMER)** | Persona que realiza pedidos para sí o para su grupo/oficina | Móvil |
| **Administrador (ADMIN)** | Responsable de operación: catálogo, pagos, producción, logística | Escritorio |
| **Repartidor (DELIVERY)** | Transporta y entrega pedidos | Móvil |

### 5.2 Roles y autorización

- Modelo de autorización **basado en roles (RBAC)**.
- Roles iniciales: `CUSTOMER`, `ADMIN`, `DELIVERY`.
- Roles previstos a futuro: `SUPER_ADMIN`, `OPERATIONS_MANAGER`, `KITCHEN_STAFF`, `PAYMENT_VALIDATOR`, `SUPPORT`.
- **Toda autorización se valida en el backend.** El frontend solo oculta o muestra elementos por conveniencia de UX, nunca como control de seguridad.
- Un usuario tiene exactamente un rol primario en Fase 1 (extensible a múltiples roles).

### 5.3 Matriz de permisos (resumen)

| Capacidad | CUSTOMER | ADMIN | DELIVERY |
|---|:--:|:--:|:--:|
| Ver catálogo y promociones | ✅ | ✅ | — |
| Crear/gestionar su carrito y pedido | ✅ | — | — |
| Cargar comprobante de pago | ✅ | ✅ | — |
| Cancelar su pedido (dentro de la ventana) | ✅ | ✅ | — |
| Usar su saldo a favor | ✅ | — | — |
| Ver el estado y seguimiento de su pedido | ✅ (solo el propio) | ✅ (todos) | ✅ (asignados) |
| Gestionar categorías/productos/stock/precios | — | ✅ | — |
| Crear promociones y Platos del Día | — | ✅ | — |
| Configurar horarios/cobertura/envío/datos de transferencia | — | ✅ | — |
| Validar pagos y aprobar/rechazar pedidos | — | ✅ | — |
| Ver producción consolidada | — | ✅ | — |
| Gestionar repartidores | — | ✅ | — |
| Asignar pedidos a repartidores | — | ✅ | — |
| Cambiar disponibilidad propia | — | ✅ | ✅ |
| Ver ruta y paradas asignadas | — | ✅ | ✅ |
| Marcar pedido como entregado / incidencia | — | ✅ | ✅ |

> **Visitante sin sesión (público):** puede ver la home, el menú por categorías, el
> detalle de producto, las promociones y el Plato del Día — todo lo que es
> "mirar la carta". **No** puede agregar al carrito, ver/usar el carrito, pedir,
> ver su perfil, sus direcciones, su saldo, sus pedidos ni su seguimiento: cualquiera
> de esas acciones dispara la pantalla de login/registro (ver RN-33 y §15.1).

---

## 6. Modelo operativo y ciclo diario

### 6.1 Concepto central

Morfi Center **no es delivery inmediato**. Opera por **turnos** (inicialmente: almuerzo). Cada turno tiene una ventana de recepción de pedidos y un cierre.

### 6.2 Ciclo diario del turno

| Fase | Descripción | Responsable |
|---|---|---|
| 1. Apertura | El sistema habilita los pedidos a la hora configurada | Sistema |
| 2. Recepción | Los clientes arman y confirman pedidos; transfieren y adjuntan comprobante | Cliente |
| 3. Validación | El admin valida pagos y aprueba/rechaza pedidos (idealmente en paralelo a la recepción) | Admin |
| 4. Cierre | A la hora de cierre no se aceptan nuevos pedidos; el turno pasa a modo cierre | Sistema |
| 5. Consolidación | El sistema genera el resumen de producción con los pedidos aprobados | Sistema |
| 6. Preparación | La cocina produce según el consolidado | Operación |
| 7. Asignación | El admin asigna pedidos listos a repartidores | Admin |
| 8. Ruteo | Se define el orden de paradas (manual en MVP, optimizado a futuro) | Admin / Sistema |
| 9. Distribución | Los repartidores retiran y entregan | Delivery |
| 10. Seguimiento | Cliente y admin ven el avance de la entrega | Sistema |

### 6.3 Parámetros configurables del turno

- Hora de apertura.
- Hora de cierre.
- Hora estimada de preparación / pedidos listos.
- Hora estimada de retiro de repartidores.
- Ventana de cancelación (por defecto: hasta 20 minutos antes del cierre).
- Zona horaria de operación (única y explícita).

---

## 7. Requisitos funcionales por dominio

Notación: **RF-[dominio]-[nº]**. Prioridad: `MUST` (MVP), `SHOULD` (deseable temprano), `COULD` (posterior).

### 7.1 Usuarios y autenticación (USR)

| ID | Requisito | Prioridad |
|---|---|:--:|
| RF-USR-01 | El registro es obligatorio; no hay pedidos como invitado | MUST |
| RF-USR-02 | Registro con cuenta propia: nombre, apellido, email, teléfono, contraseña | MUST |
| RF-USR-03 | Registro / inicio de sesión con Google, vinculado a una cuenta interna Morfi Center | SHOULD |
| RF-USR-04 | Un usuario mantiene identidad interna propia independientemente del método de login | MUST |
| RF-USR-05 | Inicio de sesión, cierre de sesión y sesión persistente segura | MUST |
| RF-USR-06 | Recuperación de contraseña por email | SHOULD |
| RF-USR-07 | El usuario puede editar sus datos de perfil y teléfono | MUST |
| RF-USR-08 | El usuario tiene un historial de pedidos accesible | MUST |
| RF-USR-09 | Cada usuario tiene un rol que determina su experiencia y permisos | MUST |
| RF-USR-10 | El admin puede crear usuarios `DELIVERY` y `ADMIN` | MUST |
| RF-USR-11 | Un visitante sin sesión puede navegar y ver todo el catálogo (home, menú, categorías, producto, promociones, Plato del Día) sin registrarse | MUST |
| RF-USR-12 | Toda acción que no sea "ver el catálogo" (agregar/ver el carrito, pedir, perfil, direcciones, saldo, mis pedidos, seguimiento) exige sesión iniciada; si no la hay, se ofrece login/registro en el momento — no un bloqueo previo de la navegación | MUST |

### 7.2 Catálogo: categorías y productos (CAT)

| ID | Requisito | Prioridad |
|---|---|:--:|
| RF-CAT-01 | El admin crea, edita, activa, desactiva y reordena categorías | MUST |
| RF-CAT-02 | Las categorías no son fijas ni están codificadas en el sistema | MUST |
| RF-CAT-03 | Cada producto tiene: nombre, descripción, categoría, imagen, precio base, stock, estado, fechas | MUST |
| RF-CAT-04 | El admin crea, edita y desactiva productos | MUST |
| RF-CAT-05 | El admin cambia precio base, imagen, descripción y stock de un producto | MUST |
| RF-CAT-06 | El producto existe independientemente de cualquier promoción | MUST |
| RF-CAT-07 | El catálogo público muestra solo productos y categorías activos | MUST |
| RF-CAT-08 | Un producto sin stock disponible se muestra como “sin stock” y no se puede agregar | MUST |
| RF-CAT-09 | Soporte de imagen por producto (una principal; múltiples a futuro) | MUST |

### 7.3 Promociones y Plato del Día (PRO)

| ID | Requisito | Prioridad |
|---|---|:--:|
| RF-PRO-01 | El admin define promociones con precio promocional y período de vigencia (inicio/fin) | MUST |
| RF-PRO-02 | El admin marca productos como Plato del Día para un día/fecha específicos | MUST |
| RF-PRO-03 | El precio promocional solo aplica dentro de su período de vigencia | MUST |
| RF-PRO-04 | Fuera de vigencia, el producto vuelve automáticamente a su precio base | MUST |
| RF-PRO-05 | El Plato del Día ocupa una posición visual destacada en la pantalla principal | MUST |
| RF-PRO-06 | Un producto puede tener múltiples promociones históricas registradas | MUST |
| RF-PRO-07 | Texto promocional opcional y prioridad visual configurable | SHOULD |
| RF-PRO-08 | Regla de prioridad ante promociones simultáneas (ver §9) | SHOULD |
| RF-PRO-09 | El precio aplicado al pedido es el vigente al momento de confirmar el pedido | MUST |

### 7.4 Stock (STK)

| ID | Requisito | Prioridad |
|---|---|:--:|
| RF-STK-01 | Todos los productos tienen control de stock | MUST |
| RF-STK-02 | El admin carga y actualiza el stock disponible del turno | MUST |
| RF-STK-03 | El sistema no permite vender por encima del stock disponible | MUST |
| RF-STK-04 | El stock disponible = stock inicial − reservado − vendido | MUST |
| RF-STK-05 | Reserva temporal de stock al crear el pedido, con vencimiento automático | MUST |
| RF-STK-06 | Al vencer la reserva sin pago, el stock vuelve a estar disponible | MUST |
| RF-STK-07 | Al aprobar el pago, la reserva se convierte en consumo firme | MUST |
| RF-STK-08 | Al cancelar/rechazar un pedido, el stock se libera | MUST |
| RF-STK-09 | El panel muestra: stock inicial, reservado, aprobado, disponible por producto | SHOULD |

### 7.5 Carrito y pedido (ORD)

| ID | Requisito | Prioridad |
|---|---|:--:|
| RF-ORD-01 | El cliente agrega productos al carrito y ajusta cantidades | MUST |
| RF-ORD-02 | El carrito muestra subtotal, costo de envío, descuentos, saldo a favor aplicado y total | MUST |
| RF-ORD-03 | Un pedido puede contener múltiples productos con distintas cantidades | MUST |
| RF-ORD-04 | El carrito valida stock y horario antes de permitir confirmar | MUST |
| RF-ORD-05 | El cliente debe elegir/ingresar una dirección de entrega válida | MUST |
| RF-ORD-06 | El cliente ve el costo de envío recién después de una dirección válida | MUST |
| RF-ORD-07 | Al confirmar, el pedido pasa a `PENDING_PAYMENT` y se congela el precio y el total | MUST |
| RF-ORD-08 | El pedido registra fecha, turno, cliente, ítems, importes y dirección | MUST |
| RF-ORD-09 | Etiqueta “Para: [nombre]” por ítem (facilita reparto en oficina) | COULD |
| RF-ORD-10 | No se pueden crear pedidos fuera del horario habilitado | MUST |
| RF-ORD-11 | Antes de confirmar un pedido dentro del período no cancelable, se advierte claramente | MUST |

### 7.6 Direcciones y cobertura (COV)

| ID | Requisito | Prioridad |
|---|---|:--:|
| RF-COV-01 | El cliente guarda una o varias direcciones con alias (Casa, Oficina, etc.) | MUST |
| RF-COV-02 | El admin configura cobertura por barrio (habilitar/deshabilitar) | MUST |
| RF-COV-03 | El admin configura cobertura por radio máximo (km) desde el origen | MUST |
| RF-COV-04 | El admin activa/desactiva cada mecanismo: solo barrio, solo radio, barrio + radio | MUST |
| RF-COV-05 | El sistema geocodifica la dirección para obtener coordenadas | MUST |
| RF-COV-06 | El sistema valida la cobertura según la configuración activa | MUST |
| RF-COV-07 | Si la dirección está fuera de cobertura, el cliente no puede completar el pedido para esa dirección | MUST |
| RF-COV-08 | La capa de geocodificación/mapas es intercambiable (no acoplada a un proveedor) | SHOULD |

### 7.7 Costos de envío (SHP)

| ID | Requisito | Prioridad |
|---|---|:--:|
| RF-SHP-01 | El admin elige la modalidad de envío: gratis, costo fijo, o por distancia | MUST |
| RF-SHP-02 | Modalidad por distancia: tabla administrable de rangos (km → precio) | MUST |
| RF-SHP-03 | El admin puede desactivar totalmente el cálculo de envío → costo = $0 | MUST |
| RF-SHP-04 | El costo se calcula y muestra tras validar la dirección | MUST |
| RF-SHP-05 | El costo de envío mostrado se congela al confirmar el pedido | MUST |

### 7.8 Horarios y cierre (SCH)

| ID | Requisito | Prioridad |
|---|---|:--:|
| RF-SCH-01 | El admin configura apertura, cierre, preparación estimada y retiro estimado | MUST |
| RF-SCH-02 | La pantalla principal muestra estado (abierto/cerrado), hora límite y cuenta regresiva | MUST |
| RF-SCH-03 | La cuenta regresiva refleja exactamente la hora configurada y la zona horaria | MUST |
| RF-SCH-04 | Al llegar el cierre: no se crean pedidos, los productos dejan de estar disponibles, modo cierre | MUST |
| RF-SCH-05 | El sistema opera con una zona horaria única y explícita | MUST |
| RF-SCH-06 | Configuración de días operativos (p. ej. lunes a viernes) | SHOULD |

### 7.9 Pagos por transferencia y comprobantes (PAY)

| ID | Requisito | Prioridad |
|---|---|:--:|
| RF-PAY-01 | Tras confirmar, el cliente ve: alias, titular, banco/CBU, y monto exacto | MUST |
| RF-PAY-02 | El cliente puede adjuntar un comprobante (JPG, JPEG, PNG, WEBP, PDF) | MUST |
| RF-PAY-03 | El comprobante se asocia al pedido y registra tipo, fecha y usuario | MUST |
| RF-PAY-04 | El comprobante es una ayuda para validar, no la única evidencia válida | MUST |
| RF-PAY-05 | Los comprobantes no son accesibles por URL pública predecible; requieren autorización | MUST |
| RF-PAY-06 | La lógica del pedido no depende del medio de pago (integración futura sin reescribir el pedido) | SHOULD |
| RF-PAY-07 | El cliente puede reemplazar/agregar un comprobante mientras el pedido esté pendiente | SHOULD |

### 7.10 Validación administrativa (VAL)

| ID | Requisito | Prioridad |
|---|---|:--:|
| RF-VAL-01 | Todo pedido debe ser validado por un admin antes de considerarse confirmado | MUST |
| RF-VAL-02 | El admin ve monto esperado, comprobante (si existe) y datos para verificar | MUST |
| RF-VAL-03 | El admin puede aprobar un pedido con comprobante válido | MUST |
| RF-VAL-04 | El admin puede aprobar un pedido sin comprobante si verifica el pago por otra vía | MUST |
| RF-VAL-05 | El admin puede cancelar un pedido sin comprobante ni pago verificable | MUST |
| RF-VAL-06 | El admin puede rechazar, solicitar corrección o mantener pendiente ante pago que no coincide | MUST |
| RF-VAL-07 | El admin puede registrar un motivo/nota en cada decisión | SHOULD |
| RF-VAL-08 | El panel destaca “pedidos sin validar” y “críticos” (próximos al cierre) | MUST |
| RF-VAL-09 | Solo los pedidos aprobados entran automáticamente en la producción confirmada | MUST |
| RF-VAL-10 | Existe una vista de pedidos pendientes para decisiones operativas | SHOULD |

### 7.11 Cancelación y saldo a favor (BAL)

| ID | Requisito | Prioridad |
|---|---|:--:|
| RF-BAL-01 | El cliente puede cancelar su pedido hasta 20 min antes del cierre (configurable) | MUST |
| RF-BAL-02 | Pasada esa ventana, el cliente no puede cancelar; se informa claramente | MUST |
| RF-BAL-03 | El dinero de un pedido cancelado y pagado no se devuelve automáticamente | MUST |
| RF-BAL-04 | El importe queda como **saldo a favor** del cliente | MUST |
| RF-BAL-05 | El saldo a favor puede usarse en pedidos futuros | MUST |
| RF-BAL-06 | Uso parcial del saldo permitido | MUST |
| RF-BAL-07 | El saldo no es transferible a otra persona | MUST |
| RF-BAL-08 | Sin vencimiento en la versión inicial | MUST |
| RF-BAL-09 | El saldo se aplica antes del cálculo del total a pagar | MUST |
| RF-BAL-10 | Cada movimiento de saldo queda registrado (origen, monto, fecha, pedido) | MUST |

### 7.12 Estados del pedido y producción (OPS)

| ID | Requisito | Prioridad |
|---|---|:--:|
| RF-OPS-01 | El pedido implementa una máquina de estados (ver §10) | MUST |
| RF-OPS-02 | Las transiciones se controlan y validan en el backend según rol | MUST |
| RF-OPS-03 | Cada cambio de estado se registra con actor, timestamp y motivo | MUST |
| RF-OPS-04 | El admin ve producción consolidada por producto (cantidad confirmada) | MUST |
| RF-OPS-05 | El admin ve producción consolidada por categoría | SHOULD |
| RF-OPS-06 | El admin ve el detalle por pedido (cliente, ítems) | MUST |
| RF-OPS-07 | La vista de producción se actualiza según el estado de los pedidos | MUST |
| RF-OPS-08 | La producción diferencia aprobados / pendientes / cancelados | MUST |

### 7.13 Repartidores y asignación (DLV)

| ID | Requisito | Prioridad |
|---|---|:--:|
| RF-DLV-01 | El admin gestiona una lista de repartidores (nombre, teléfono, transporte, capacidad opcional, estado) | MUST |
| RF-DLV-02 | Estados del repartidor: `DISPONIBLE`, `NO_DISPONIBLE`, `EN_RUTA`, `INACTIVO` | MUST |
| RF-DLV-03 | El repartidor puede cambiar su propia disponibilidad según reglas | MUST |
| RF-DLV-04 | El admin asigna manualmente pedidos a un repartidor | MUST |
| RF-DLV-05 | El repartidor ve solo sus pedidos asignados y el orden de entrega | MUST |
| RF-DLV-06 | El repartidor ve la dirección y datos mínimos de cada parada | MUST |
| RF-DLV-07 | El repartidor marca cada pedido como entregado o informa incidencia | MUST |
| RF-DLV-08 | Sugerencia automática de distribución de pedidos entre repartidores | COULD |

### 7.14 Rutas y seguimiento (TRK)

| ID | Requisito | Prioridad |
|---|---|:--:|
| RF-TRK-01 | El sistema arma una ruta ordenada de paradas por repartidor | SHOULD |
| RF-TRK-02 | El orden de paradas puede optimizarse mediante un `RouteService` intercambiable | COULD |
| RF-TRK-03 | La navegación puede delegarse a apps externas (Google/Waze) mediante enlace | SHOULD |
| RF-TRK-04 | El repartidor comparte su ubicación solo durante una ruta activa | COULD |
| RF-TRK-05 | El admin ve la posición/última ubicación conocida de cada repartidor en ruta | COULD |
| RF-TRK-06 | El cliente ve: estado, posición relativa en la ruta, paradas previas y ETA | SHOULD |
| RF-TRK-07 | El cliente nunca ve direcciones, datos ni pedidos de otros clientes | MUST |
| RF-TRK-08 | Ante pérdida de conexión, se muestra la última ubicación y su timestamp | SHOULD |

### 7.15 Configuración del sistema (CFG)

| ID | Requisito | Prioridad |
|---|---|:--:|
| RF-CFG-01 | El admin configura horarios del turno | MUST |
| RF-CFG-02 | El admin configura cobertura (barrios, radio, modo) | MUST |
| RF-CFG-03 | El admin configura la modalidad y tabla de costos de envío | MUST |
| RF-CFG-04 | El admin configura los datos de transferencia (alias, titular, banco, CBU/CVU) | MUST |
| RF-CFG-05 | El admin configura la ventana de cancelación | MUST |
| RF-CFG-06 | El admin configura la zona horaria y los días operativos | MUST |
| RF-CFG-07 | Toda la configuración se almacena en `SYSTEM_SETTINGS` y es versionable/auditable | SHOULD |

---

## 8. Flujos funcionales principales

### 8.1 Flujo del cliente: del catálogo a la entrega

```
1.  Ingresa / se registra
2.  Pantalla principal: ve estado (abierto), cuenta regresiva, Plato del Día, promos, menú
3.  Explora el catálogo por categorías
4.  Agrega productos al carrito y ajusta cantidades
5.  Abre el carrito: revisa subtotal
6.  Selecciona / agrega dirección de entrega
7.  Sistema geocodifica → valida cobertura → calcula envío
8.  (Opcional) Aplica saldo a favor
9.  Ve el total final y la advertencia de cancelación si corresponde
10. Confirma el pedido  → estado PENDING_PAYMENT, se reserva stock, se congelan importes
11. Ve datos de transferencia y monto exacto
12. Realiza la transferencia desde su banco
13. (Opcional) Adjunta comprobante  → estado PAYMENT_UNDER_REVIEW
14. Espera validación del admin
15. Pago aprobado  → estado PAYMENT_APPROVED (entra a producción)
16. Pedido en preparación → listo → asignado → en camino
17. Sigue la entrega: paradas previas + ETA
18. Recibe el pedido → estado DELIVERED
```

### 8.2 Flujo del administrador: validación y consolidación

```
1.  Abre el panel: dashboard del turno (pendientes de validar, críticos, ventas, stock)
2.  Entra a “Pedidos sin validar”
3.  Por cada pedido: compara monto esperado vs. comprobante / movimiento bancario
4.  Decide: Aprobar | Rechazar | Solicitar corrección | Mantener pendiente (+ nota)
5.  Repite priorizando los “críticos” (próximos al cierre)
6.  Llega la hora de cierre → el turno pasa a modo cierre
7.  Revisa la producción consolidada (por producto y categoría)
8.  La cocina prepara
9.  Marca pedidos como listos
10. Asigna pedidos a repartidores y define orden de paradas
11. Supervisa el avance de las entregas
```

### 8.3 Flujo del repartidor

```
1.  Inicia sesión → marca disponibilidad
2.  Ve sus pedidos asignados y el orden de entrega
3.  Inicia la ruta
4.  Navega a la siguiente parada (enlace a app de mapas)
5.  Entrega → marca “Entregado” (o “Incidencia” + motivo)
6.  Pasa a la siguiente parada
7.  Al terminar → vuelve a “Disponible”
```

### 8.4 Flujo de cancelación con saldo a favor

```
Cliente solicita cancelar
  ├── ¿Estamos dentro de la ventana (>20 min antes del cierre)?
  │      NO → Se rechaza; se informa que ya no es cancelable
  │      SÍ ↓
  ├── ¿El pedido estaba pagado/aprobado?
  │      NO → Se cancela sin movimiento de dinero
  │      SÍ ↓
  └── Se cancela; el importe pagado se acredita como SALDO A FAVOR
       Se registra BALANCE_TRANSACTION (origen: cancelación, pedido, monto, fecha)
       El stock reservado/consumido se libera
```

---

## 9. Reglas de negocio

Se consolidan las 22 reglas de la especificación maestra y se agregan precisiones funcionales.

| ID | Regla |
|---|---|
| RN-01 | El registro es obligatorio para **pedir**. No hay pedidos como invitado (ver RN-33: navegar el catálogo sí es público). |
| RN-02 | Se puede iniciar sesión con cuenta Morfi Center o con Google. |
| RN-03 | No se pueden crear pedidos fuera del horario habilitado del turno. |
| RN-04 | El administrador configura el horario de apertura y cierre. |
| RN-05 | Todos los productos tienen stock y no se puede vender por encima del disponible. |
| RN-06 | El stock se **reserva al crear el pedido**, con vencimiento automático si no se paga. |
| RN-07 | La reserva vencida libera el stock; la aprobación del pago la vuelve consumo firme. |
| RN-08 | Los precios promocionales solo son válidos durante su período de vigencia. |
| RN-09 | El precio aplicado a un ítem es el vigente **al confirmar el pedido** y queda congelado. |
| RN-10 | Ante promociones simultáneas sobre un mismo producto, se aplica **el menor precio vigente** (recomendación inicial; el admin puede fijar prioridad explícita por promoción). |
| RN-11 | Todo pedido debe ser validado administrativamente antes de considerarse confirmado. |
| RN-12 | Un pedido puede aprobarse sin comprobante si el admin verifica el pago por otra vía. |
| RN-13 | Un pedido sin comprobante y sin pago verificable puede ser cancelado por el admin. |
| RN-14 | El cliente puede cancelar hasta 20 minutos antes del cierre (valor configurable). |
| RN-15 | Dentro de los últimos 20 minutos, el pedido no es cancelable por el cliente. |
| RN-16 | La condición “no cancelable” debe informarse **antes** de confirmar el pedido cuando aplica. |
| RN-17 | El dinero de un pedido cancelado no se devuelve automáticamente. |
| RN-18 | El importe de un pedido cancelado y pagado queda como saldo a favor del cliente. |
| RN-19 | El saldo a favor: uso parcial permitido, no transferible, sin vencimiento inicial. |
| RN-20 | El saldo a favor se aplica antes de calcular el total final a pagar. |
| RN-21 | La cobertura puede configurarse por barrio y/o radio; el admin activa cada mecanismo. |
| RN-22 | Una dirección es entregable solo si cumple **todas** las reglas de cobertura activas. |
| RN-23 | El costo de envío es configurable (gratis / fijo / por distancia). |
| RN-24 | Si el cálculo de envío está desactivado, el costo de envío es $0. |
| RN-25 | El costo de envío se informa recién tras validar una dirección y se congela al confirmar. |
| RN-26 | Solo los pedidos aprobados alimentan la producción consolidada confirmada. |
| RN-27 | El administrador asigna pedidos a repartidores (manual en MVP). |
| RN-28 | El orden de las entregas puede ser optimizado mediante un servicio de rutas. |
| RN-29 | La información de otros clientes nunca se expone entre usuarios. |
| RN-30 | La plataforma opera con una única zona horaria explícita para todos los cálculos de tiempo. |
| RN-31 | Cada cambio de estado, aprobación de pago, cancelación y modificación de precio/stock queda auditado (actor + timestamp). |
| RN-32 | Los comprobantes de pago solo son accesibles mediante acceso autorizado, nunca por URL pública predecible. |
| RN-33 | La navegación del catálogo (home, menú, categorías, producto, promociones, Plato del Día) es **pública**, sin sesión. Cualquier acción más allá de mirar (agregar/ver el carrito, confirmar un pedido, perfil, direcciones, saldo, mis pedidos, seguimiento) requiere sesión iniciada; se resuelve con una pantalla/modal de login-registro en el momento (con retorno a donde estaba), no con un muro de login al entrar al sitio. |

---

## 10. Máquina de estados del pedido

### 10.1 Estados

| Estado (interno) | Etiqueta visible | Descripción |
|---|---|---|
| `DRAFT` | Borrador | Carrito en construcción; aún no confirmado |
| `PENDING_PAYMENT` | Pendiente de pago | Confirmado; a la espera de la transferencia |
| `PAYMENT_UNDER_REVIEW` | Pago en verificación | Comprobante cargado o pago informado; admin revisando |
| `PAYMENT_APPROVED` | Pago aprobado | Validado por el admin; entra a producción |
| `PAYMENT_REJECTED` | Pago rechazado | El admin rechazó el pago; el cliente puede corregir |
| `CANCELLED` | Cancelado | Cancelado por cliente (con ventana) o por admin |
| `IN_PREPARATION` | En preparación | La cocina está produciendo el pedido |
| `READY_FOR_PICKUP` | Listo para retirar | Preparado; a la espera de asignación/retiro |
| `ASSIGNED_TO_DELIVERY` | Asignado a repartidor | Un repartidor lo tiene en su ruta |
| `OUT_FOR_DELIVERY` | En camino | El repartidor inició la entrega |
| `DELIVERED` | Entregado | Entrega confirmada |
| `DELIVERY_INCIDENT` | Incidencia | Problema en la entrega; requiere resolución |

### 10.2 Transiciones permitidas

| Desde | Hacia | Disparador | Actor |
|---|---|---|---|
| `DRAFT` | `PENDING_PAYMENT` | Confirmar pedido | CUSTOMER |
| `DRAFT` | `CANCELLED` | Abandonar / expira | CUSTOMER / Sistema |
| `PENDING_PAYMENT` | `PAYMENT_UNDER_REVIEW` | Carga comprobante / informa pago | CUSTOMER |
| `PENDING_PAYMENT` | `PAYMENT_APPROVED` | Admin verifica pago sin comprobante | ADMIN |
| `PENDING_PAYMENT` | `CANCELLED` | Cliente cancela (en ventana) / admin cancela / expira reserva | CUSTOMER / ADMIN / Sistema |
| `PAYMENT_UNDER_REVIEW` | `PAYMENT_APPROVED` | Admin aprueba | ADMIN |
| `PAYMENT_UNDER_REVIEW` | `PAYMENT_REJECTED` | Admin rechaza | ADMIN |
| `PAYMENT_UNDER_REVIEW` | `CANCELLED` | Cliente cancela (en ventana) / admin cancela | CUSTOMER / ADMIN |
| `PAYMENT_REJECTED` | `PAYMENT_UNDER_REVIEW` | Cliente re-carga comprobante | CUSTOMER |
| `PAYMENT_REJECTED` | `CANCELLED` | Cliente/admin cancela | CUSTOMER / ADMIN |
| `PAYMENT_APPROVED` | `IN_PREPARATION` | Inicio de producción del turno | ADMIN / Sistema |
| `PAYMENT_APPROVED` | `CANCELLED` | Cancelación excepcional (admin) | ADMIN |
| `IN_PREPARATION` | `READY_FOR_PICKUP` | Pedido preparado | ADMIN |
| `READY_FOR_PICKUP` | `ASSIGNED_TO_DELIVERY` | Admin asigna a repartidor | ADMIN |
| `ASSIGNED_TO_DELIVERY` | `OUT_FOR_DELIVERY` | Repartidor inicia ruta | DELIVERY |
| `OUT_FOR_DELIVERY` | `DELIVERED` | Repartidor marca entregado | DELIVERY |
| `OUT_FOR_DELIVERY` | `DELIVERY_INCIDENT` | Repartidor informa incidencia | DELIVERY |
| `DELIVERY_INCIDENT` | `OUT_FOR_DELIVERY` | Reintento de entrega | DELIVERY / ADMIN |
| `DELIVERY_INCIDENT` | `DELIVERED` | Resolución positiva | ADMIN |
| `DELIVERY_INCIDENT` | `CANCELLED` | Resolución negativa (+ saldo a favor si aplica) | ADMIN |

### 10.3 Reglas de la máquina de estados

- Toda transición no listada está prohibida y debe rechazarse en el backend.
- La cancelación por el cliente solo es válida en `PENDING_PAYMENT`, `PAYMENT_UNDER_REVIEW` y `PAYMENT_REJECTED`, y únicamente dentro de la ventana de cancelación.
- Al entrar en `CANCELLED` desde un estado con pago aprobado, se genera automáticamente el saldo a favor.
- Al entrar en `CANCELLED` o `PAYMENT_REJECTED` (terminal), se libera el stock reservado/consumido.
- Solo `PAYMENT_APPROVED` y posteriores cuentan para la producción consolidada.

---

## 11. Modelo de datos funcional

### 11.1 Entidades y relaciones (nivel funcional)

```
USERS 1─n USER_AUTH_PROVIDERS
USERS 1─1 CUSTOMER_PROFILES | ADMIN_PROFILES | DELIVERY_PROFILES
USERS 1─n ADDRESSES
USERS 1─1 CUSTOMER_BALANCES 1─n BALANCE_TRANSACTIONS

CATEGORIES 1─n PRODUCTS 1─n PRODUCT_IMAGES
PRODUCTS 1─1 PRODUCT_STOCK
PRODUCTS 1─n PROMOTIONS
PRODUCTS 1─n DAILY_SPECIALS

USERS 1─1 CARTS 1─n CART_ITEMS n─1 PRODUCTS

USERS 1─n ORDERS 1─n ORDER_ITEMS n─1 PRODUCTS
ORDERS 1─n ORDER_STATUS_HISTORY
ORDERS 1─1 PAYMENTS 1─n PAYMENT_PROOFS
ORDERS n─1 ADDRESSES
ORDERS n─1 SHIFTS (turno)

DELIVERY_DRIVERS 1─n DELIVERY_AVAILABILITY
DELIVERY_ASSIGNMENTS n─1 DELIVERY_DRIVERS
DELIVERY_ASSIGNMENTS 1─n ORDERS
DELIVERY_ROUTES 1─n DELIVERY_STOPS n─1 ORDERS
DELIVERY_DRIVERS 1─n DRIVER_LOCATIONS

DELIVERY_ZONES (barrios / radio)
SYSTEM_SETTINGS (configuración global)
```

### 11.2 Atributos mínimos por entidad clave

**USERS:** id, nombre, apellido, email (único), teléfono, hash de contraseña (nullable si solo Google), rol, estado, fecha de alta.

**USER_AUTH_PROVIDERS:** id, user_id, provider (`local` | `google`), provider_uid, fecha de vinculación.

**PRODUCTS:** id, nombre, descripción, category_id, precio_base, estado, fecha_creación, fecha_actualización.

**PRODUCT_STOCK:** product_id, stock_inicial_turno, reservado, consumido, disponible (derivado).

**PROMOTIONS:** id, product_id, precio_promocional, fecha_inicio, fecha_fin, estado, texto, prioridad.

**DAILY_SPECIALS:** id, product_id, día/fecha, precio_promocional, fecha_inicio, fecha_fin, estado, texto, prioridad_visual.

**ORDERS:** id, código, user_id, shift_id, address_id, estado, subtotal, costo_envío, descuentos, saldo_aplicado, total, es_cancelable (derivado), fecha_creación, fecha_confirmación.

**ORDER_ITEMS:** id, order_id, product_id, nombre_congelado, cantidad, precio_unitario_congelado, subtotal, etiqueta_para (nullable).

**ORDER_STATUS_HISTORY:** id, order_id, estado_anterior, estado_nuevo, actor_id, motivo, timestamp.

**PAYMENTS:** id, order_id, método (`transfer`), monto_esperado, estado, validado_por, fecha_validación, nota.

**PAYMENT_PROOFS:** id, payment_id, archivo (ruta protegida), tipo, subido_por, fecha.

**CUSTOMER_BALANCES:** user_id, saldo_actual.

**BALANCE_TRANSACTIONS:** id, user_id, tipo (`credit` | `debit`), monto, origen (`cancelación` | `uso_en_pedido` | `ajuste_admin`), order_id, fecha, saldo_resultante.

**DELIVERY_ZONES:** id, tipo (`barrio` | `radio`), nombre_barrio (nullable), radio_km (nullable), habilitado.

**SYSTEM_SETTINGS:** clave, valor, tipo, descripción, fecha_actualización, actualizado_por. (Horarios, cobertura, modo de envío, tabla de rangos, datos de transferencia, ventana de cancelación, zona horaria, días operativos.)

**SHIFTS:** id, fecha, hora_apertura, hora_cierre, hora_prep_estimada, hora_retiro_estimada, estado (`abierto` | `cerrado` | `en_producción` | `en_distribución` | `finalizado`).

> El modelo físico definitivo (tipos SQLite, índices, claves foráneas, restricciones) se especifica en el documento técnico.

---

## 12. Requisitos no funcionales

| Categoría | Requisito |
|---|---|
| **Plataforma** | Web responsive, **mobile-first**. Al superar el breakpoint móvil, se adopta un layout de escritorio propio (no solo estirado): barras de navegación, grillas y tarjetas rediseñadas para aprovechar el espacio, sin botones ni cards ensanchados. |
| **Rendimiento** | Pantalla principal utilizable en < 2 s en 4G. Interacciones de carrito < 200 ms percibidos. |
| **Disponibilidad** | Operación crítica en la franja del turno (mañana). Ventana de mantenimiento fuera de horario operativo. |
| **Escalabilidad** | Arquitectura simple pero modular por dominios; SQLite en Fase 1, con capa de acceso a datos que permita migrar a otro motor sin reescribir la lógica de negocio. |
| **Compatibilidad** | Últimas 2 versiones de Chrome, Safari, Firefox, Edge. Safari iOS y Chrome Android. |
| **Accesibilidad** | Contraste AA, foco visible, navegación por teclado en el panel admin, tamaños de toque ≥ 44px. |
| **Zona horaria** | Única, explícita y coherente en backend y frontend. |
| **Seguridad** | Autorización en backend; contraseñas con hashing fuerte; archivos protegidos; validación de entrada. |
| **Auditabilidad** | Historial de estados y acciones sensibles (pagos, cancelaciones, precios, stock). |
| **Internacionalización** | Español (es-AR) en Fase 1. Moneda: peso argentino, formato `$00.000`. |
| **Observabilidad** | Logs estructurados de operaciones críticas (creación de pedido, validación, cambios de estado). |
| **Backup** | Copia diaria del archivo SQLite y de los comprobantes. |
| **Mantenibilidad** | Separación clara `backend/` y `frontend/`; convenciones consistentes; documentación viva (`que_hice.html`, roadmap). |

---

## 13. Arquitectura funcional y stack técnico

### 13.1 Stack

| Capa | Tecnología |
|---|---|
| Frontend | HTML + CSS + Tailwind CSS (+ JavaScript para interactividad) |
| Backend | Python (framework web ligero, API REST) |
| Base de datos | SQLite (Fase 1) |
| Autenticación | Sesión/token propia + OAuth Google |
| Almacenamiento de archivos | Sistema de archivos local con acceso autorizado (comprobantes) |
| Tiempo real (fases posteriores) | Polling en MVP; websockets/SSE cuando se aborde GPS |

### 13.2 Organización

```
Morfi Center/
├── backend/          # API, lógica de negocio, modelos, migraciones, servicios
│   ├── domain/       # reglas de negocio por dominio (usuarios, catálogo, pedidos, pagos, logística)
│   ├── api/          # endpoints REST
│   ├── data/         # acceso a datos / repositorios / SQLite
│   ├── services/     # geocodificación, rutas, notificaciones (interfaces intercambiables)
│   └── config/
├── frontend/         # HTML + Tailwind + JS
│   ├── cliente/
│   ├── admin/
│   └── delivery/
├── documentacion/
│   ├── 01_Doc_Funcional.md
│   └── mockups/
├── iniciar.bat
└── que_hice.html
```

### 13.3 Principios arquitectónicos

- **Separación por dominios**, no por pantallas.
- **Lógica de negocio primero, backend después, frontend al final** de cada tarea, para poder probar incrementalmente.
- **Servicios externos detrás de interfaces** (`GeocodingService`, `RouteService`, `NotificationService`, `PaymentGateway`) para no acoplar la lógica a un proveedor.
- **La autorización vive en el backend.**
- **El estado del pedido es la fuente de verdad**; el frontend refleja, no decide.

---

## 14. Diseño UI/UX y principios visuales

### 14.1 Lineamientos generales

- **Mobile-first**: el diseño nace en móvil y escala a escritorio con un layout propio.
- **Adaptación real a escritorio**: barra de navegación superior/lateral, grillas de varias columnas, uso pleno del ancho, sin elementos estirados.
- Estética **artesanal y cálida** (papel kraft, formas orgánicas, cocina casera). **Sin neón.** Efectos visuales sutiles: textura de papel, sombras suaves, microtransiciones, toques a mano alzada.
- Jerarquía visual clara: lo primero que ve el cliente es **estado del turno + cuenta regresiva + Plato del Día**.
- Consistencia de componentes: tarjetas de producto, badges de promoción, botones, chips de categoría, barra de carrito.

### 14.2 Prioridades por actor

**Cliente (móvil):**
1. ¿Está abierto? ¿Cuánto tiempo queda? ¿Hasta qué hora?
2. Plato del Día y promociones activas.
3. Menú por categorías, fácil de escanear.
4. Agregar al carrito y confirmar rápido.

Los puntos 1 a 3 son **navegación pública**: se ven sin necesidad de tener una
cuenta. Recién al intentar el punto 4 (o cualquier otra acción personal —
carrito, pedidos, perfil) se le pide iniciar sesión o registrarse, en el
momento y sin perder el lugar donde estaba (ver RF-USR-11/12 y RN-33).

**Administrador (escritorio):**
1. Pedidos pendientes de validar / críticos.
2. Validación de pagos.
3. Producción consolidada.
4. Stock y catálogo.
5. Asignación logística.

**Repartidor (móvil):**
1. Próxima parada.
2. Navegación.
3. Estado.
4. Confirmación de entrega.

### 14.3 Sistema visual (definido)

Mockup aprobado: **`documentacion/mockups/04_Artesanal_Organico.html`** — estilo **"Artesanal · Cocina de Olla"**. El detalle completo (tokens, tipografía, utilidades, componentes) vive en la skill del proyecto `.claude/skills/morfi-frontend/`.

- **Paleta** (modo claro): `kraft #E9DFC9` (fondo), `cream #F6EFDD` (superficie), `bark #3B2E22` (texto), `forest #2F5D3A` (positivo/primario), `mustard #D69A2D` (acento 2°), `brick #B0472F` (acento 1°/CTA).
- **Tipografía**: Bricolage Grotesque (títulos, nombres, precios, números) + Caveat (acentos a mano, con moderación) + Inter (cuerpo/UI).
- **Tarjetas**: papel crema con textura, bordes `border-2`, formas orgánicas (`.blob`) en elementos interactivos, hover con leve giro.
- **Cuenta regresiva**: ticket de kraft con cinta de papel y línea perforada. **Plato del Día**: sello inclinado + precio en `brick`.
- **Navegación**: bottom bar en móvil / top nav en el header en escritorio.

(Se exploraron 10 mockups en `documentacion/mockups/`; el elegido es el 04 y sus variantes premium 06–10.)

---

## 15. Estructura de pantallas

### 15.1 Cliente

| Pantalla | Contenido principal | Acceso |
|---|---|:--:|
| Inicio / Home | Estado del turno, cuenta regresiva, hora límite, Plato del Día, promos, accesos a categorías | Público |
| Catálogo / Categoría | Lista de productos por categoría, precio (base o promo), stock, botón agregar | Público |
| Detalle de producto | Imagen, descripción, precio, cantidad, agregar al carrito | Público (agregar exige sesión) |
| Carrito | Ítems, subtotal, dirección, envío, saldo a favor, total, advertencia de cancelación, confirmar | 🔒 Sesión |
| Dirección | Selección/alta de dirección, geocodificación, resultado de cobertura | 🔒 Sesión |
| Pago | Datos de transferencia, monto exacto, carga de comprobante | 🔒 Sesión |
| Mis pedidos | Historial y estado de cada pedido | 🔒 Sesión |
| Seguimiento del pedido | Estado actual, línea de tiempo, paradas previas, ETA | 🔒 Sesión |
| Perfil | Datos personales, direcciones, saldo a favor | 🔒 Sesión |

**Público** = se ve sin iniciar sesión. **🔒 Sesión** = si no hay sesión, en vez de
mostrar la pantalla se ofrece login/registro ahí mismo (con retorno automático a
la acción que se quería hacer una vez logueado). En **"Detalle de producto"** la
ficha se ve libremente; el botón "Agregar al carrito" es el que dispara el login
si hace falta.
| Auth | Registro, login, login con Google, recuperar contraseña |

### 15.2 Administrador

| Módulo | Contenido |
|---|---|
| Dashboard | Pedidos del día, sin validar, críticos, ventas, stock, deliveries disponibles |
| Pedidos | Lista, filtros por estado, validación, historial |
| Validación de pagos | Cola priorizada, comparación monto/comprobante, aprobar/rechazar/pendiente + nota |
| Producción | Consolidado por producto, por categoría, detalle por pedido |
| Productos | Catálogo, precios, imágenes, stock |
| Categorías | Alta, edición, orden, activación |
| Promociones / Platos del Día | Alta, programación, vigencia, prioridad |
| Deliveries | Lista, disponibilidad, asignaciones |
| Logística | Rutas, pedidos asignados, seguimiento |
| Configuración | Horarios, cobertura, radios, envíos, datos de transferencia, ventana de cancelación, zona horaria |

### 15.3 Repartidor

| Pantalla | Contenido |
|---|---|
| Inicio | Disponibilidad, resumen de la ruta del turno |
| Ruta | Lista ordenada de paradas |
| Parada | Dirección, datos mínimos, enlace a navegación, marcar entregado / incidencia |
| Historial | Entregas realizadas |

---

## 16. Notificaciones

### 16.1 Eventos notificables

| Evento | Destinatario |
|---|---|
| Pedido creado | Cliente + Admin |
| Comprobante recibido | Admin |
| Pago aprobado | Cliente |
| Pago rechazado / corrección solicitada | Cliente |
| Pedido cancelado (por cliente o admin) | Cliente + Admin |
| Saldo a favor acreditado | Cliente |
| Pedido en preparación | Cliente |
| Pedido listo / asignado | Cliente + Repartidor |
| Pedido en camino | Cliente |
| Pedido entregado | Cliente + Admin |
| Incidencia de entrega | Admin |
| Pedidos sin validar próximos al cierre | Admin |

### 16.2 Canales

- **MVP:** notificación in-app (centro de notificaciones).
- **Fase posterior:** email, push (PWA), otros a definir.

---

## 17. Seguridad y privacidad

- **Mínimo acceso:** cada actor ve solo la información que necesita. El cliente nunca ve datos de otros clientes.
- **Autorización en backend:** cada endpoint valida rol y propiedad del recurso.
- **Comprobantes protegidos:** almacenamiento no público; descarga solo con sesión autorizada; nombres no predecibles.
- **Contraseñas:** hashing fuerte con sal; nunca en texto plano ni en logs.
- **Ubicación de repartidores:** solo se registra/comparte durante una ruta activa.
- **Auditoría:** quién aprobó un pago, quién canceló, cuándo cambió el estado, quién modificó precios o stock.
- **Datos sensibles:** direcciones, teléfonos, comprobantes e historial se tratan con confidencialidad.
- **Validación de entrada:** todo dato del cliente se valida y sanitiza en el backend.
- **Sesiones:** expiración razonable, cierre de sesión efectivo, protección contra CSRF/XSS en el frontend.

---

## 18. Decisiones abiertas y supuestos

### 18.1 Decisiones tomadas para Fase 1 (supuestos operativos)

| Tema | Decisión inicial |
|---|---|
| Reserva de stock | Al **crear el pedido**, con vencimiento automático (temporizador configurable, sugerido 30–45 min) |
| Saldo a favor | Uso parcial sí; no transferible; sin vencimiento; se aplica antes del total |
| Promociones simultáneas | Se aplica el **menor precio vigente**; el admin puede fijar prioridad explícita |
| Turnos | Uno solo (almuerzo); la arquitectura contempla `SHIFTS` para no bloquear la expansión |
| Empresas | No como entidad en Fase 1; se usa “dirección de oficina” + etiqueta por ítem |
| Propina | No en Fase 1 |
| Evidencia de entrega | Marca manual del repartidor en Fase 1 |
| Zona horaria | America/Argentina/Buenos_Aires (configurable) |
| Notificaciones | In-app en Fase 1 |
| Asignación de repartidores | Manual en Fase 1 |
| Optimización de rutas | Manual en MVP; `RouteService` intercambiable en fase de logística |

### 18.2 Decisiones que siguen abiertas

- Vencimiento y combinación del saldo a favor con promociones.
- Regla fina de prioridad entre promoción general y Plato del Día cuando el admin no la define.
- Empresas como entidad con usuarios asociados (§39.4 de la spec maestra).
- Pedidos grupales colaborativos.
- Canales prioritarios de notificación.
- Método de evidencia de entrega definitivo (PIN, foto, firma).
- Proveedor de geocodificación y de mapas/rutas.
- Frecuencia de actualización del GPS y manejo de batería/conexión.

---

## 19. Roadmap funcional por fases

> El detalle granular por tareas (lógica → backend → frontend, una a una, con validación del usuario) se desarrolla en `03_Roadmap.md`. Aquí se fija el orden funcional de alto nivel.

| Fase | Dominio | Entregable funcional |
|---|---|---|
| **Fase 0** | Base visual | HTML base con el estilo aprobado (mockup elegido), sin funcionalidad |
| **Fase 1** | Fundaciones | Usuarios, roles, autenticación (local + Google), configuración base, SHIFTS |
| **Fase 2** | Catálogo comercial | Categorías, productos, imágenes, stock, precios, promociones, Platos del Día |
| **Fase 3** | Pedido | Carrito, direcciones, cobertura, cálculo de envío, confirmación, reserva de stock |
| **Fase 4** | Pago y validación | Datos de transferencia, comprobantes, validación admin, saldo a favor, cancelaciones |
| **Fase 5** | Operación | Máquina de estados completa, producción consolidada, panel administrativo |
| **Fase 6** | Logística | Repartidores, disponibilidad, asignación manual, paradas y orden de entrega |
| **Fase 7** | Tiempo real | Seguimiento de entrega para el cliente, ubicación del repartidor, estados en vivo |
| **Fase 8** | Evolución | Optimización de rutas, asignación automática, analítica, integraciones de pago, notificaciones multicanal |

---

## 20. Criterios de aceptación (MVP)

El MVP se considera aceptado cuando:

1. Un cliente puede **registrarse, iniciar sesión** (local y Google) y editar su perfil.
2. El admin puede **crear categorías y productos con stock y precio**, y publicarlos.
3. El admin puede **definir un Plato del Día y una promoción** con vigencia; el cliente ve el precio correcto dentro y fuera de vigencia.
4. La **pantalla principal** muestra estado del turno, cuenta regresiva exacta, hora límite, Plato del Día y promos.
5. Un cliente puede **armar un carrito, elegir dirección, ver cobertura y costo de envío**, y **confirmar** un pedido dentro del horario.
6. Al confirmar, se **reserva stock**, se **congelan importes** y el pedido queda `PENDING_PAYMENT` con datos de transferencia y monto exacto.
7. El cliente puede **adjuntar un comprobante**; el admin lo ve en una **cola priorizada** y puede **aprobar / rechazar / mantener pendiente** con nota.
8. Solo los pedidos **aprobados** aparecen en la **producción consolidada** por producto.
9. El cliente puede **cancelar dentro de la ventana**; el importe pagado se convierte en **saldo a favor** utilizable parcialmente en un pedido futuro.
10. Fuera de la ventana, la cancelación está **bloqueada e informada**; los pedidos hechos en ese período muestran la **advertencia previa**.
11. El admin puede **crear repartidores y asignarles pedidos**; el repartidor ve su lista y **marca entregas**.
12. El cliente ve el **estado y seguimiento** de su pedido sin ver datos de terceros.
13. Todas las **transiciones de estado y acciones sensibles quedan auditadas**.
14. La **autorización se valida en el backend** para cada rol.
15. La interfaz se ve **profesional y aprovecha el espacio tanto en móvil como en escritorio**.

---

## 21. Glosario

| Término | Definición |
|---|---|
| **Turno** | Ventana operativa diaria (inicialmente el almuerzo) con apertura, cierre y distribución |
| **Cierre de pedidos** | Momento en que no se aceptan nuevos pedidos para el turno |
| **Plato del Día** | Producto destacado con precio promocional para un día/fecha determinados |
| **Promoción** | Precio temporal asociado a un producto con período de vigencia |
| **Precio base** | Precio normal del producto, independiente de promociones |
| **Reserva de stock** | Bloqueo temporal de unidades al crear un pedido, con vencimiento automático |
| **Saldo a favor** | Crédito del cliente originado por una cancelación, usable en pedidos futuros |
| **Producción consolidada** | Resumen de cantidades a preparar, calculado con los pedidos aprobados |
| **Cobertura** | Conjunto de reglas (barrio y/o radio) que determinan si una dirección es entregable |
| **Ventana de cancelación** | Tiempo antes del cierre durante el cual el cliente aún puede cancelar (por defecto 20 min) |
| **RouteService** | Capa abstracta que calcula y ordena rutas, con proveedor intercambiable |
| **RBAC** | Control de acceso basado en roles |
| **ETA** | Hora estimada de llegada de la entrega |

---

*Fin del documento 01 · Documento General (Funcional). Mockup de front aprobado: `documentacion/mockups/04_Artesanal_Organico.html` (estilo "Artesanal · Cocina de Olla"). Continúa en `02_Documento_Tecnico.md`.*
