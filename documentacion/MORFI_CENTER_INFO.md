# MORFI CENTER
## Especificación Maestra del Producto
### Plataforma de pedidos anticipados, producción y distribución programada de comidas

**Estado del documento:** Documento base de definición funcional y conceptual  
**Proyecto:** Morfi Center  
**Formato:** Especificación funcional y técnica inicial  
**Fecha:** 9 de septiembre de 2026  

---

# Índice

1. Visión del producto
2. Problema que resuelve
3. Propuesta de valor
4. Público objetivo
5. Modelo operativo general
6. Actores del sistema
7. Roles y permisos
8. Registro y autenticación
9. Experiencia y flujo del cliente
10. Catálogo y estructura de productos
11. Platos del día
12. Promociones y precios
13. Stock
14. Carrito y composición del pedido
15. Dirección y cobertura
16. Costos de envío
17. Horarios y cierre de pedidos
18. Pagos mediante transferencia
19. Comprobantes de pago
20. Validación administrativa de pagos
21. Cancelación de pedidos y saldo a favor
22. Estados del pedido
23. Panel operativo y producción
24. Gestión administrativa del catálogo
25. Gestión de deliveries
26. Asignación de pedidos a deliveries
27. Optimización de rutas
28. Seguimiento GPS en tiempo real
29. Experiencia del repartidor
30. Experiencia del cliente durante la entrega
31. Notificaciones
32. Privacidad y seguridad
33. Modelo conceptual de datos
34. Reglas de negocio
35. Casos especiales y escenarios límite
36. Arquitectura técnica conceptual
37. Diseño UI/UX
38. Panel administrativo
39. Decisiones abiertas
40. Roadmap conceptual

---

# 1. Visión del producto

**Morfi Center** será una plataforma digital orientada a la venta de comidas mediante un sistema de **pedido anticipado, producción centralizada y distribución programada**.

El foco principal del producto estará en personas que necesitan resolver su almuerzo durante la jornada laboral, especialmente:

- Personas que trabajan en oficinas.
- Trabajadores de fábricas.
- Comercios.
- Empresas.
- Centros de trabajo.
- Grupos de empleados que realizan pedidos para una misma ubicación.

La plataforma permitirá que los usuarios realicen sus pedidos dentro de una ventana horaria previamente configurada. Una vez finalizado el período de recepción de pedidos, el operador de Morfi Center podrá validar los pagos, consolidar la producción, preparar las comidas y organizar su distribución mediante deliveries.

El modelo central será:

```text
CATÁLOGO
   ↓
PEDIDO ANTICIPADO
   ↓
PAGO / TRANSFERENCIA
   ↓
VALIDACIÓN ADMINISTRATIVA
   ↓
CIERRE DE PEDIDOS
   ↓
PRODUCCIÓN CONSOLIDADA
   ↓
PREPARACIÓN
   ↓
ASIGNACIÓN DE DELIVERY
   ↓
OPTIMIZACIÓN DE RUTA
   ↓
DISTRIBUCIÓN
   ↓
ENTREGA
```

Morfi Center no debe conceptualizarse inicialmente como una aplicación de delivery inmediato. Su modelo operativo está basado en la concentración de pedidos antes de una hora límite y en la optimización de la producción y distribución posterior.

---

# 2. Problema que resuelve

Muchas personas que trabajan durante el mediodía enfrentan problemas recurrentes:

- No tienen tiempo para cocinar.
- No pueden salir a buscar comida.
- Deben decidir qué comer en poco tiempo.
- Los servicios de delivery inmediato pueden tener demoras elevadas.
- Los pedidos individuales dificultan la organización logística de un proveedor.
- Las empresas o zonas de oficinas pueden generar múltiples pedidos concentrados en franjas horarias similares.

Morfi Center busca centralizar y anticipar esta demanda.

El usuario realiza su pedido antes del cierre establecido. La operación gastronómica conoce con anticipación qué debe producir y puede organizar los envíos de forma agrupada.

---

# 3. Propuesta de valor

La propuesta de valor de Morfi Center se basa en cuatro pilares:

## 3.1 Pedido anticipado

Los clientes realizan su pedido antes de una hora de cierre configurable.

Esto permite planificar:

- Producción.
- Stock.
- Cantidad de comida.
- Personal.
- Repartidores.
- Rutas.

## 3.2 Menú diario y promociones

La plataforma puede destacar determinados productos como **Plato del Día**.

Estos productos pueden tener un precio promocional exclusivamente durante determinados días.

Ejemplo:

**Producto permanente**

Carne al horno con papas.

Precio base:

`$15.000`

**Promoción del lunes**

Plato del Día:

`$10.000`

El martes, si no existe una promoción activa, el producto vuelve a venderse a su precio base.

## 3.3 Producción basada en demanda

Los pedidos aprobados permiten generar automáticamente un resumen de producción.

Ejemplo:

| Producto | Cantidad |
|---|---:|
| Milanesa con guarnición | 31 |
| Canelones | 18 |
| Carne al horno con papas | 24 |
| Empanadas de carne | 47 |

## 3.4 Distribución organizada

Una vez preparada la comida:

- Los pedidos se asignan a repartidores.
- Se determina el orden de entrega.
- Se genera una ruta.
- Se realiza seguimiento de la ubicación del repartidor.
- El cliente puede conocer el estado de su entrega.

---

# 4. Público objetivo

El público inicial estará compuesto principalmente por:

## Usuarios finales

- Empleados de oficinas.
- Trabajadores de fábricas.
- Empleados de comercios.
- Equipos de trabajo.
- Personas que permanecen en un mismo lugar durante el horario del almuerzo.

## Operadores

- Administrador de Morfi Center.
- Personal encargado de producción.
- Personal encargado de validar pagos.
- Personal encargado de logística.

## Repartidores

- Motoqueros.
- Repartidores contratados.
- Personal de delivery propio o externo.

---

# 5. Modelo operativo general

El flujo diario esperado será:

```text
APERTURA DE PEDIDOS
        ↓
CLIENTES CONSULTAN EL MENÚ
        ↓
CLIENTES AGREGAN PRODUCTOS
        ↓
INGRESAN DIRECCIÓN
        ↓
SE CALCULA COBERTURA Y ENVÍO
        ↓
CLIENTE CONFIRMA EL PEDIDO
        ↓
CLIENTE TRANSFIERE EL DINERO
        ↓
CLIENTE PUEDE ADJUNTAR COMPROBANTE
        ↓
ADMINISTRADOR VALIDA EL PAGO
        ↓
PEDIDO APROBADO
        ↓
CIERRE DEL HORARIO DE PEDIDOS
        ↓
CONSOLIDACIÓN DE PRODUCCIÓN
        ↓
PREPARACIÓN DE COMIDAS
        ↓
PEDIDOS LISTOS
        ↓
ASIGNACIÓN A REPARTIDORES
        ↓
OPTIMIZACIÓN DEL RECORRIDO
        ↓
REPARTIDORES RETIRAN LOS PEDIDOS
        ↓
SEGUIMIENTO EN TIEMPO REAL
        ↓
ENTREGA
```

---

# 6. Actores del sistema

Inicialmente existirán tres actores principales.

## 6.1 Cliente

Usuario que realiza el pedido.

Puede:

- Registrarse.
- Iniciar sesión.
- Consultar el menú.
- Consultar promociones.
- Ver el Plato del Día.
- Consultar disponibilidad y stock.
- Agregar productos al carrito.
- Indicar dirección de entrega.
- Conocer el costo de envío.
- Confirmar el pedido.
- Realizar una transferencia.
- Adjuntar un comprobante.
- Consultar el estado.
- Cancelar el pedido dentro de las reglas permitidas.
- Utilizar saldo a favor generado por una cancelación.
- Seguir la entrega.

## 6.2 Administrador

Usuario responsable de la operación.

Puede:

- Gestionar productos.
- Gestionar categorías.
- Gestionar precios.
- Gestionar promociones.
- Definir Platos del Día.
- Gestionar stock.
- Configurar horarios.
- Configurar zonas de cobertura.
- Configurar radios de entrega.
- Configurar costos de envío.
- Gestionar pedidos.
- Validar pagos.
- Aprobar pedidos.
- Cancelar pedidos.
- Generar resúmenes de producción.
- Gestionar repartidores.
- Asignar pedidos.
- Consultar rutas.
- Supervisar deliveries en tiempo real.

## 6.3 Delivery / Repartidor

Usuario encargado de transportar pedidos.

Puede:

- Iniciar sesión.
- Indicar disponibilidad.
- Ver pedidos asignados.
- Consultar el orden de entrega.
- Consultar la ruta.
- Compartir su ubicación.
- Marcar entregas.
- Informar incidencias.

---

# 7. Roles y permisos

El sistema debe utilizar un modelo de autorización basado en roles.

Roles iniciales:

```text
CUSTOMER
ADMIN
DELIVERY
```

A futuro pueden agregarse roles adicionales:

```text
SUPER_ADMIN
OPERATIONS_MANAGER
KITCHEN_STAFF
PAYMENT_VALIDATOR
SUPPORT
```

El diseño de permisos debe evitar depender exclusivamente de comprobaciones visuales en el frontend. La autorización debe ser validada también por el backend.

---

# 8. Registro y autenticación

El registro será obligatorio.

No se contemplará inicialmente la realización de pedidos como invitado.

El usuario podrá registrarse mediante:

## 8.1 Cuenta propia de Morfi Center

Datos iniciales sugeridos:

- Nombre.
- Apellido.
- Email.
- Teléfono.
- Contraseña.

## 8.2 Google

El usuario podrá utilizar autenticación mediante Google.

El sistema deberá vincular la identidad autenticada con una cuenta interna de Morfi Center.

Conceptualmente:

```text
USUARIO
   ├── Datos internos
   ├── Método de autenticación
   └── Historial de pedidos
```

El uso de autenticación externa no debe impedir que Morfi Center mantenga su propia identidad y estructura interna de usuario.

---

# 9. Experiencia y flujo del cliente

## 9.1 Pantalla principal

El cliente debe visualizar rápidamente:

- Si los pedidos están abiertos.
- Cuánto tiempo queda para pedir.
- La hora límite.
- El Plato del Día.
- Las promociones activas.
- El menú disponible.

Ejemplo:

```text
PEDIDOS ABIERTOS

Podés realizar tu pedido hasta las:

12:00

Tiempo restante:

01:42:15
```

El contador debe reflejar la hora configurada por el administrador.

## 9.2 Plato del Día

Debe ocupar una posición visual destacada.

Ejemplo:

```text
🔥 PLATO DEL DÍA

Carne al horno con papas

Antes: $15.000

HOY: $10.000
```

## 9.3 Catálogo

Los productos se organizarán por categorías administrables.

Ejemplo:

- Platos principales.
- Pastas.
- Empanadas.
- Pizza.
- Sándwiches.
- Acompañamientos.

El sistema no debe depender de categorías codificadas de forma fija.

El administrador debe poder:

- Crear.
- Editar.
- Reordenar.
- Activar.
- Desactivar.

## 9.4 Carrito

El cliente podrá:

- Agregar productos.
- Aumentar cantidades.
- Disminuir cantidades.
- Eliminar productos.
- Ver subtotal.
- Ver costo de envío.
- Ver descuentos.
- Ver saldo a favor utilizado.
- Ver total final.

---

# 10. Catálogo y estructura de productos

Cada producto debería tener, como mínimo:

```text
ID
Nombre
Descripción
Categoría
Imagen
Precio base
Stock disponible
Estado
Fecha de creación
Fecha de actualización
```

El producto debe existir independientemente de una promoción.

Ejemplo:

```text
PRODUCTO
Carne al horno con papas

PRECIO BASE
$15.000

PROMOCIÓN ACTIVA
Lunes

PRECIO PROMOCIONAL
$10.000
```

---

# 11. Platos del Día

El administrador podrá configurar productos como Platos del Día.

Debe poder definir:

- Producto.
- Día o fecha.
- Precio promocional.
- Fecha de inicio.
- Fecha de finalización.
- Estado.
- Texto promocional opcional.
- Prioridad visual.

La promoción debe modificar el precio mostrado y aplicado al pedido únicamente durante su período de vigencia.

---

# 12. Promociones y precios

El sistema debe separar:

## Precio base

Precio normal del producto.

## Precio promocional

Precio temporal asociado a una promoción.

La estructura conceptual debe permitir que un producto tenga múltiples promociones históricas.

Ejemplo:

```text
Producto: Milanesa

Precio base:
$12.000

Promoción 1:
Semana del 10 al 14
$10.500

Promoción 2:
Plato del Día - Miércoles
$9.500
```

Se deberá definir posteriormente una regla de prioridad si existieran múltiples promociones simultáneas.

---

# 13. Stock

Todos los productos tendrán control de stock.

El administrador será responsable de cargar y actualizar el stock disponible para preparar.

Ejemplo:

```text
Canelones

Stock inicial:
20

Pedidos aprobados:
12

Stock disponible:
8
```

El sistema debe impedir la venta por encima del stock disponible según las reglas de reserva definidas.

## Decisión técnica a definir

Debe establecerse exactamente en qué momento se reserva el stock:

1. Al agregar al carrito.
2. Al crear el pedido.
3. Al aprobar el pago.

La recomendación conceptual inicial es utilizar una reserva temporal cuando el pedido es creado, con vencimiento automático, para evitar sobreventa mientras se procesa el pago. Sin embargo, esta regla deberá diseñarse cuidadosamente para evitar que usuarios bloqueen stock sin completar la operación.

El administrador debe ser consciente de mantener el stock actualizado según su capacidad real de producción.

---

# 14. Carrito y composición del pedido

Un pedido podrá contener múltiples productos.

Ejemplo:

```text
2 x Milanesa
1 x Canelones
6 x Empanadas
```

Debe analizarse la posibilidad de agregar etiquetas por producto.

Ejemplo futuro:

```text
Milanesa
Para: Gustavo

Canelones
Para: María
```

Esto puede facilitar la distribución dentro de una oficina o empresa, aunque no es obligatorio para la primera implementación funcional.

---

# 15. Dirección y cobertura

La cobertura debe ser configurable por el administrador.

Se utilizarán dos mecanismos complementarios:

## 15.1 Cobertura por barrio

El administrador podrá habilitar o deshabilitar barrios.

Ejemplo:

```text
Boedo
Disponible

Caballito
Disponible

Belgrano
No disponible
```

## 15.2 Cobertura por radio

El administrador podrá configurar un radio máximo de entrega en kilómetros desde el punto de origen de Morfi Center.

Ejemplo:

```text
Radio máximo:

5 km
```

## Recomendación funcional

La mejor arquitectura conceptual es combinar ambos mecanismos.

Una dirección debe ser considerada entregable cuando cumpla las reglas configuradas.

El sistema debe poder soportar configuraciones tales como:

### Modo A

Solo barrios habilitados.

### Modo B

Solo radio máximo.

### Modo C

Barrio + radio.

### Modo D

Cualquier dirección dentro de una zona geográfica futura.

El administrador debe poder activar o desactivar los mecanismos.

## Flujo del usuario

El usuario ingresa una dirección.

El sistema:

```text
DIRECCIÓN
   ↓
GEOCODIFICACIÓN
   ↓
OBTENCIÓN DE COORDENADAS
   ↓
VALIDACIÓN DE COBERTURA
   ↓
CÁLCULO DE DISTANCIA
   ↓
CÁLCULO DE ENVÍO
   ↓
RESULTADO
```

---

# 16. Costos de envío

El costo de envío será configurable.

La plataforma debe permitir diferentes modalidades.

## Modalidad 1

Envío gratuito.

```text
Costo de envío:

$0
```

## Modalidad 2

Costo fijo.

Ejemplo:

```text
Costo:

$2.000
```

## Modalidad 3

Costo según distancia.

Ejemplo conceptual:

```text
0 a 2 km
$1.000

2 a 4 km
$1.500

4 a 6 km
$2.500
```

La configuración recomendada es una tabla administrable por rangos de distancia.

El costo debe informarse al usuario después de ingresar una dirección válida.

El administrador debe poder desactivar completamente el cálculo de envío. En ese caso:

```text
Costo de envío:

$0
```

---

# 17. Horarios y cierre de pedidos

El administrador podrá configurar:

- Hora de apertura.
- Hora de cierre.
- Hora estimada de preparación.
- Hora de retiro de repartidores.

Ejemplo:

```text
Apertura:
08:00

Cierre:
12:00

Retiro estimado:
12:15
```

Una vez alcanzada la hora de cierre:

- No se podrán crear nuevos pedidos para ese turno.
- Los productos dejarán de estar disponibles para compra.
- El sistema pasará a modo de cierre.

Ejemplo:

```text
PEDIDOS CERRADOS

Los pedidos para el turno actual ya finalizaron.
```

La plataforma debe trabajar con una zona horaria claramente definida para evitar errores.

---

# 18. Pagos mediante transferencia

Inicialmente el pago se realizará mediante transferencia.

Una vez confirmado el pedido, el usuario verá:

- Alias.
- Titular.
- Banco u otra información necesaria.
- Monto exacto a transferir.

Ejemplo:

```text
TOTAL A PAGAR

$41.000

ALIAS

MORFI.CENTER
```

La integración futura con procesadores de pago debe ser posible sin modificar la lógica principal del pedido.

---

# 19. Comprobantes de pago

El cliente podrá adjuntar un comprobante de transferencia.

Formatos posibles:

- JPG.
- JPEG.
- PNG.
- WEBP.
- PDF.

El comprobante será asociado al pedido.

Debe almacenarse:

```text
ID
Pedido
Archivo
Tipo
Fecha de carga
Usuario
```

El comprobante será una ayuda para la validación, pero no será obligatoriamente la única evidencia válida.

---

# 20. Validación administrativa de pagos

Todos los pedidos deben ser validados por el administrador.

El administrador deberá revisar:

- Monto esperado.
- Pago recibido.
- Comprobante adjuntado, si existe.
- Datos disponibles para validar la transferencia.

## Situación 1

El cliente adjuntó comprobante.

El administrador valida y aprueba.

## Situación 2

El cliente no adjuntó comprobante, pero el administrador detecta la transferencia.

El administrador puede aprobar el pedido igualmente.

## Situación 3

El cliente no adjuntó comprobante y no existe evidencia de pago.

El administrador puede cancelar el pedido.

## Situación 4

El comprobante existe, pero el pago no coincide.

El administrador puede:

- Rechazar.
- Solicitar corrección.
- Mantener el pedido pendiente de resolución.

## Recomendación operativa

El panel administrativo debe destacar los pedidos que se acercan a la hora de cierre y todavía no fueron validados.

Debe existir un indicador como:

```text
PEDIDOS SIN VALIDAR

12
```

Y, opcionalmente:

```text
CRÍTICOS

3 pedidos próximos al cierre operativo
```

El objetivo es que la validación ocurra antes de que el pedido pase a producción.

La producción consolidada debería diferenciar:

- Pedidos aprobados.
- Pedidos pendientes de validación.
- Pedidos cancelados.

La recomendación inicial es que **solo los pedidos aprobados entren automáticamente en la producción confirmada**, aunque el administrador podría contar con una vista de pedidos pendientes para tomar decisiones operativas.

---

# 21. Cancelación de pedidos y saldo a favor

El cliente podrá cancelar un pedido.

Sin embargo, existe una ventana límite.

La cancelación será posible hasta:

```text
20 minutos antes de la hora de cierre
```

Ejemplo:

```text
Hora de cierre:
12:00

Última hora para cancelar:
11:40
```

Después de esa hora:

```text
LA CANCELACIÓN YA NO ESTÁ DISPONIBLE
```

Esta condición debe informarse claramente al usuario.

Especialmente si el pedido se realiza dentro del período en el cual ya no es cancelable.

Ejemplo:

```text
IMPORTANTE

Este pedido se está realizando dentro del período no cancelable.
Una vez confirmado, no podrá cancelarse para este turno.
```

## Dinero de pedidos cancelados

Si un pedido fue pagado y se cancela dentro del período permitido:

- El dinero no se devuelve automáticamente.
- El importe queda registrado como saldo a favor del usuario.

Ejemplo:

```text
SALDO A FAVOR

$15.000
```

Ese saldo podrá utilizarse en pedidos futuros.

## Reglas que deberán definirse

- Si el saldo puede utilizarse parcialmente.
- Si tiene vencimiento.
- Si puede combinarse con promociones.
- Si puede transferirse a otra persona.

Recomendación inicial:

- Uso parcial permitido.
- No transferible.
- Sin vencimiento inicialmente.
- Aplicable antes del cálculo del monto final a pagar, respetando las reglas fiscales y comerciales que se definan.

---

# 22. Estados del pedido

El sistema debe implementar una máquina de estados.

Estados conceptuales:

```text
DRAFT
PENDING_PAYMENT
PAYMENT_UNDER_REVIEW
PAYMENT_APPROVED
PAYMENT_REJECTED
CANCELLED
IN_PREPARATION
READY_FOR_PICKUP
ASSIGNED_TO_DELIVERY
OUT_FOR_DELIVERY
DELIVERED
DELIVERY_INCIDENT
```

La traducción visible para el usuario puede ser:

```text
Borrador
Pendiente de pago
Pago en verificación
Pago aprobado
Pago rechazado
Cancelado
En preparación
Listo para retirar
Asignado a repartidor
En camino
Entregado
Incidencia
```

Las transiciones deben estar controladas por reglas del backend.

No todos los actores podrán mover un pedido entre todos los estados.

---

# 23. Panel operativo y producción

Una vez que los pedidos estén validados, el administrador necesita una vista consolidada de producción.

Ejemplo:

# PRODUCCIÓN DEL TURNO

| Producto | Cantidad confirmada |
|---|---:|
| Milanesa | 31 |
| Canelones | 18 |
| Carne al horno | 24 |
| Empanadas de carne | 47 |

El sistema debería permitir consultar:

## Consolidado por producto

Cuánto debe prepararse.

## Consolidado por categoría

Ejemplo:

```text
Empanadas:
70 unidades

Platos principales:
55 unidades
```

## Detalle por pedido

```text
Pedido #1245

Cliente:
Gustavo

Productos:
2 Milanesa
1 Canelones
```

La vista de producción debe actualizarse según el estado de los pedidos.

---

# 24. Gestión administrativa del catálogo

El administrador debe disponer de un panel para:

## Categorías

- Crear.
- Editar.
- Activar.
- Desactivar.
- Reordenar.

## Productos

- Crear.
- Editar.
- Desactivar.
- Cambiar precio.
- Cambiar imagen.
- Modificar descripción.
- Modificar stock.

## Promociones

- Crear.
- Programar.
- Activar.
- Desactivar.

## Platos del Día

- Seleccionar producto.
- Definir día.
- Definir precio promocional.
- Configurar visibilidad.

---

# 25. Gestión de deliveries

El administrador podrá gestionar una lista de repartidores.

Datos sugeridos:

```text
ID
Nombre
Apellido
Teléfono
Estado
Medio de transporte
Capacidad opcional
Estado de disponibilidad
```

Estados posibles:

```text
DISPONIBLE
NO_DISPONIBLE
EN_RUTA
INACTIVO
```

El delivery también podrá cambiar su propia disponibilidad según las reglas definidas.

---

# 26. Asignación de pedidos a deliveries

El administrador podrá asignar pedidos a un repartidor.

Ejemplo:

```text
REPARTIDOR

Juan Pérez

PEDIDOS

#1245
#1246
#1251
#1258
```

La asignación inicial puede ser manual.

Luego el sistema podrá calcular el orden óptimo de las paradas.

A futuro, el sistema podría sugerir automáticamente cómo distribuir los pedidos entre repartidores.

---

# 27. Optimización de rutas

La plataforma deberá incorporar una capa de optimización logística.

Una vez asignados los pedidos a un repartidor:

```text
PUNTO DE ORIGEN
      ↓
DIRECCIÓN A
      ↓
DIRECCIÓN B
      ↓
DIRECCIÓN C
      ↓
DIRECCIÓN D
```

El sistema deberá determinar el orden más conveniente.

Factores futuros posibles:

- Distancia.
- Tiempo estimado.
- Tránsito.
- Cantidad de pedidos.
- Capacidad del repartidor.
- Horarios especiales.

## Recomendación arquitectónica

La lógica de Morfi Center no debe quedar fuertemente acoplada a un único proveedor de mapas.

Debe existir una capa conceptual como:

```text
ROUTE SERVICE
```

Que permita utilizar diferentes proveedores.

---

# 28. Seguimiento GPS en tiempo real

El repartidor utilizará un dispositivo móvil.

Durante una ruta activa:

```text
TELÉFONO DEL DELIVERY
        ↓
GPS
        ↓
SERVICIO DE UBICACIÓN
        ↓
BACKEND
        ↓
ACTUALIZACIONES EN TIEMPO REAL
        ↓
ADMINISTRADOR / CLIENTE
```

El sistema deberá considerar:

- Frecuencia de actualización.
- Consumo de batería.
- Pérdida de conexión.
- Última ubicación conocida.
- Permisos del dispositivo.
- Privacidad.

---

# 29. Experiencia del repartidor

El delivery deberá contar con una interfaz específica, preferentemente mobile-first.

Debe poder visualizar:

- Estado actual.
- Ruta asignada.
- Lista de paradas.
- Orden de entrega.
- Dirección de cada parada.
- Datos mínimos necesarios para realizar la entrega.

Acciones:

```text
INICIAR RUTA
↓
NAVEGAR A SIGUIENTE PARADA
↓
MARCAR PEDIDO COMO ENTREGADO
↓
SIGUIENTE PARADA
```

La navegación puede integrarse inicialmente mediante apertura de aplicaciones especializadas.

La aplicación Morfi Center seguirá funcionando como sistema de control y seguimiento.

---

# 30. Experiencia del cliente durante la entrega

Cuando el pedido esté en camino, el cliente podrá ver:

```text
TU PEDIDO ESTÁ EN CAMINO
```

Información posible:

- Estado.
- Ubicación aproximada del repartidor.
- Posición relativa dentro de la ruta.
- Cantidad de paradas previas.
- Tiempo estimado de llegada.

Ejemplo:

```text
Paradas antes de tu entrega:

1

Entrega estimada:

12:47
```

El cliente no debe visualizar:

- Direcciones de otros clientes.
- Datos personales de otros clientes.
- Contenido de otros pedidos.

---

# 31. Notificaciones

El sistema deberá estar preparado para notificar eventos importantes.

Eventos:

- Pedido creado.
- Comprobante recibido.
- Pago aprobado.
- Pago rechazado.
- Pedido cancelado.
- Pedido en preparación.
- Pedido en camino.
- Pedido entregado.

Canales futuros:

- Notificación dentro de la plataforma.
- Email.
- Push notification.
- Otros canales a definir.

---

# 32. Privacidad y seguridad

El sistema manejará información sensible desde el punto de vista operativo:

- Direcciones.
- Teléfonos.
- Historial de pedidos.
- Comprobantes de pago.
- Ubicación de repartidores.

Principios necesarios:

## Mínimo acceso

Cada actor debe ver solamente la información necesaria.

## Protección de archivos

Los comprobantes no deben ser accesibles públicamente mediante URLs previsibles.

## Autorización backend

Las restricciones de acceso deben validarse en el servidor.

## Ubicación

La ubicación en tiempo real debe estar vinculada únicamente a una ruta activa.

## Auditoría

A futuro será recomendable registrar:

- Quién aprobó un pago.
- Quién canceló un pedido.
- Cuándo cambió el estado.
- Quién modificó precios o stock.

---

# 33. Modelo conceptual de datos

Entidades iniciales:

```text
USERS
USER_AUTH_PROVIDERS

CUSTOMER_PROFILES
ADMIN_PROFILES
DELIVERY_PROFILES

ADDRESSES
DELIVERY_ZONES

CATEGORIES
PRODUCTS
PRODUCT_IMAGES
PRODUCT_STOCK

PROMOTIONS
DAILY_SPECIALS

CARTS
CART_ITEMS

ORDERS
ORDER_ITEMS
ORDER_STATUS_HISTORY

PAYMENTS
PAYMENT_PROOFS

CUSTOMER_BALANCES
BALANCE_TRANSACTIONS

DELIVERY_DRIVERS
DELIVERY_AVAILABILITY

DELIVERY_ASSIGNMENTS
DELIVERY_ROUTES
DELIVERY_STOPS

DRIVER_LOCATIONS

SYSTEM_SETTINGS
```

Esta estructura es conceptual.

El modelo definitivo deberá construirse después de definir:

- Tecnología.
- Base de datos.
- Relaciones.
- Integridad referencial.
- Auditoría.
- Escalabilidad.

---

# 34. Reglas de negocio principales

## Regla 1

El registro es obligatorio.

## Regla 2

Se podrá iniciar sesión mediante cuenta Morfi Center o Google.

## Regla 3

No se podrán crear pedidos fuera del horario habilitado.

## Regla 4

El administrador podrá configurar el horario de cierre.

## Regla 5

Los productos tendrán stock.

## Regla 6

No se deberá vender por encima del stock permitido.

## Regla 7

Los precios promocionales solo serán válidos durante su período de vigencia.

## Regla 8

Todos los pedidos deberán ser validados administrativamente antes de considerarse confirmados.

## Regla 9

Un pedido puede aprobarse aunque no tenga comprobante adjunto si el administrador puede verificar que la transferencia fue recibida.

## Regla 10

Un pedido sin comprobante y sin pago verificable puede ser cancelado por el administrador.

## Regla 11

El cliente podrá cancelar hasta 20 minutos antes de la hora de cierre.

## Regla 12

Dentro de los últimos 20 minutos antes del cierre, el pedido no será cancelable por el cliente.

## Regla 13

La condición de no cancelable debe informarse claramente antes de confirmar un pedido realizado dentro de ese período.

## Regla 14

El dinero correspondiente a un pedido cancelado no se devolverá automáticamente.

## Regla 15

El importe de un pedido cancelado quedará como saldo a favor del cliente.

## Regla 16

La cobertura podrá configurarse por barrio y/o radio.

## Regla 17

El costo de envío podrá configurarse y calcularse según distancia.

## Regla 18

Si el cálculo de envío está desactivado, el costo de envío será $0.

## Regla 19

Los pedidos aprobados deberán alimentar la producción consolidada.

## Regla 20

El administrador podrá asignar pedidos a repartidores.

## Regla 21

El orden de las entregas podrá ser optimizado mediante un servicio de rutas.

## Regla 22

La información de otros clientes no deberá exponerse entre usuarios.

---

# 35. Casos especiales y escenarios límite

## Caso 1: pedido creado sin comprobante

El pedido queda pendiente de validación.

El administrador:

- Puede aprobarlo si identifica el pago.
- Puede mantenerlo pendiente.
- Puede cancelarlo si no existe pago verificable.

## Caso 2: comprobante falso

El administrador rechaza o no aprueba el pago.

El pedido no debe pasar a producción como confirmado.

## Caso 3: pago incompleto

El pedido queda pendiente de resolución.

El administrador debe poder registrar el motivo.

## Caso 4: pedido creado cerca del cierre

El sistema debe informar si ya se encuentra dentro del período no cancelable.

## Caso 5: stock agotado

El producto debe dejar de estar disponible según la política de reserva definida.

## Caso 6: dirección fuera de cobertura

El usuario no podrá completar el pedido para esa dirección.

## Caso 7: repartidor pierde conexión

El sistema debe mostrar la última ubicación conocida y el momento de actualización.

## Caso 8: cliente cancela un pedido

El importe aplicable debe registrarse como saldo a favor según las reglas del sistema.

---

# 36. Arquitectura técnica conceptual

La arquitectura general puede representarse como:

```text
                    MORFI CENTER
                         │
       ┌─────────────────┼─────────────────┐
       │                 │                 │
       ▼                 ▼                 ▼

    CLIENTE          ADMINISTRADOR       DELIVERY
       │                 │                 │
       └─────────────────┼─────────────────┘
                         │
                         ▼

                    BACKEND API
                         │
       ┌─────────────────┼─────────────────┐
       │                 │                 │
       ▼                 ▼                 ▼

   BASE DE DATOS     ARCHIVOS          TIEMPO REAL
                    COMPROBANTES
                         │
       ┌─────────────────┼─────────────────┐
       │                 │                 │
       ▼                 ▼                 ▼

 AUTENTICACIÓN      MAPAS/RUTAS       NOTIFICACIONES
```

La arquitectura definitiva debe ser seleccionada posteriormente según:

- Tecnología preferida.
- Presupuesto.
- Escalabilidad.
- Experiencia de desarrollo.
- Infraestructura disponible.

---

# 37. Diseño UI/UX

Morfi Center debe diseñarse inicialmente como:

> Mobile-first.

Razones:

- Los clientes probablemente realizarán pedidos desde el teléfono.
- Los repartidores trabajarán principalmente desde dispositivos móviles.
- El administrador necesitará también una buena experiencia de escritorio.

Se recomienda:

## Cliente

Interfaz rápida y visual.

Prioridades:

1. Ver qué se puede pedir.
2. Ver el Plato del Día.
3. Conocer cuánto tiempo queda.
4. Realizar el pedido rápidamente.

## Administrador

Interfaz orientada a operación.

Prioridades:

1. Pedidos pendientes.
2. Validación de pagos.
3. Producción.
4. Stock.
5. Asignación logística.

## Delivery

Interfaz extremadamente simple.

Prioridades:

1. Próxima parada.
2. Navegación.
3. Estado.
4. Confirmación de entrega.

---

# 38. Panel administrativo

El panel podría organizarse en módulos.

## Dashboard

- Pedidos del día.
- Pedidos pendientes de validar.
- Ventas.
- Stock.
- Deliveries disponibles.

## Pedidos

- Lista.
- Filtros.
- Estados.
- Validación.
- Historial.

## Producción

- Resumen por producto.
- Cantidades.
- Detalle.

## Productos

- Catálogo.
- Precios.
- Stock.

## Promociones

- Platos del Día.
- Precios promocionales.

## Deliveries

- Lista.
- Disponibilidad.
- Asignaciones.

## Logística

- Rutas.
- Pedidos asignados.
- Seguimiento.

## Configuración

- Horarios.
- Cobertura.
- Radios.
- Envíos.
- Datos de transferencia.

---

# 39. Decisiones abiertas

Los siguientes puntos todavía deben definirse antes de una especificación técnica definitiva.

## 39.1 Reserva de stock

Definir en qué momento se descuenta o reserva.

## 39.2 Saldo a favor

Definir:

- Vencimiento.
- Uso parcial.
- Uso combinado.
- Tratamiento ante nuevos pedidos.

## 39.3 Promociones simultáneas

Definir prioridad.

## 39.4 Empresas y ubicaciones frecuentes

Evaluar si una empresa debe poder registrarse como entidad propia.

Ejemplo:

```text
EMPRESA
   ├── Nombre
   ├── Dirección
   └── Usuarios asociados
```

Esto puede ser especialmente útil para oficinas y fábricas.

## 39.5 Múltiples turnos

Inicialmente el foco es el almuerzo.

A futuro podría existir:

- Desayuno.
- Almuerzo.
- Cena.

La arquitectura debería evitar impedir esta expansión.

## 39.6 Pedidos grupales

Evaluar la posibilidad de que varias personas participen en un pedido compartido.

No es requisito inicial.

## 39.7 Propina

Definir si existirá.

## 39.8 Evidencia de entrega

Definir si el delivery debe:

- Marcar manualmente.
- Solicitar PIN.
- Tomar foto.
- Obtener firma.

## 39.9 Notificaciones

Definir canales prioritarios.

---

# 40. Roadmap conceptual

El desarrollo debe organizarse por dominios funcionales y no simplemente por pantallas.

Orden conceptual recomendado:

## Etapa 1: Fundaciones

- Usuarios.
- Roles.
- Autenticación.
- Base de datos.
- Configuración.

## Etapa 2: Catálogo comercial

- Categorías.
- Productos.
- Stock.
- Precios.
- Promociones.
- Platos del Día.

## Etapa 3: Pedido

- Carrito.
- Dirección.
- Cobertura.
- Envío.
- Confirmación.

## Etapa 4: Pago y validación

- Transferencia.
- Comprobantes.
- Validación.
- Saldo a favor.
- Cancelaciones.

## Etapa 5: Operación

- Estados.
- Producción.
- Panel administrativo.

## Etapa 6: Logística

- Repartidores.
- Asignación.
- Rutas.

## Etapa 7: Tiempo real

- GPS.
- Seguimiento.
- Estados en vivo.

## Etapa 8: Evolución

- Automatización.
- Optimización avanzada.
- Analítica.
- Integraciones de pago.

---

# Conclusión

Morfi Center es una plataforma de pedidos programados orientada a resolver el proceso completo de venta y distribución de comidas en una ventana temporal concentrada.

Su arquitectura funcional se basa en cinco dominios principales:

```text
1. COMERCIO
   Productos
   Precios
   Promociones
   Stock

2. PEDIDOS
   Carrito
   Dirección
   Estados
   Cancelaciones

3. PAGOS
   Transferencias
   Comprobantes
   Validación
   Saldo a favor

4. OPERACIÓN
   Producción
   Consolidación
   Administración

5. LOGÍSTICA
   Repartidores
   Asignaciones
   Rutas
   GPS
   Entregas
```

El principal objetivo de este documento es servir como base estructurada para continuar definiendo el producto y, posteriormente, utilizarlo como contexto de alto nivel para herramientas de desarrollo asistido por LLM.

Antes de iniciar la implementación definitiva, se recomienda realizar una segunda fase de especificación que incluya:

- Requisitos funcionales detallados.
- Requisitos no funcionales.
- Modelo de datos relacional.
- Diagramas de entidades.
- Máquina formal de estados.
- Casos de uso.
- Especificación de APIs.
- Arquitectura tecnológica.
- Flujos UI/UX por pantalla.
- Reglas de validación.
- Estrategia de seguridad.
- Estrategia de tiempo real y geolocalización.

Este documento debe considerarse la base conceptual inicial del proyecto Morfi Center.
