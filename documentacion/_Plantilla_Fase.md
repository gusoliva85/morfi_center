<!--
  PLANTILLA · documento de cierre de fase.

  Cómo usarla:
  1. Al terminar la PRIMERA tarea aprobada de una fase, copiar este archivo a
     "documentacion/Fase 0X - <Nombre de la fase>.md" (2 dígitos, nombre corto
     tal como aparece en el índice de 03_Roadmap.md).
  2. Completar §1 y empezar a llenar §2 con lo que ya se aprobó.
  3. Cada vez que se aprueba una tarea nueva de esa fase, ACTUALIZAR este mismo
     archivo (no crear uno nuevo): sumar su tema/tarea en §2, y si corresponde
     tocar §3/§4/§5.
  4. Si el usuario pide corregir algo de una tarea ya aprobada, se corrige el
     contenido existente en §2 para que describa la VERSIÓN FINAL — no se narra
     el ida y vuelta ("primero hice X, después lo cambié"), simplemente se
     documenta cómo quedó funcionando.
  5. Cuando se aprueba la última tarea de la fase, completar §1 (estado, fecha
     de cierre) y §6.

  Este comentario y las notas en cursiva se borran al usar la plantilla.
-->

# Fase 0X · <Nombre de la fase>

**Proyecto:** Morfi Center
**Estado:** 🟨 En curso *(cambiar a "✅ Completa y aprobada" al cerrar la fase)*
**Inicio:** <fecha de la primera tarea aprobada>
**Cierre:** <fecha de la última tarea aprobada — dejar en blanco mientras esté en curso>
**Temas de esta fase:** <lista corta, ej. "0.1 Estructura · 0.2 Esqueleto backend · ...">
**Roadmap:** `documentacion/03_Roadmap.md` (Fase 0X)

---

## 1. Objetivo de la fase

<Uno o dos párrafos: qué buscaba resolver esta fase dentro del proyecto y qué
se puede hacer una vez cerrada que no se podía hacer antes. Copiar/adaptar la
descripción de la fase en el índice del roadmap.>

---

## 2. Qué quedó implementado

> Se documenta la **versión final** de cada tema, no el historial de cambios.
> Un tema = un `## Tema X.Y` del roadmap. Repetir esta subsección por cada tema
> de la fase, en orden.

### Tema 0.X · <Nombre del tema>

<Explicación en prosa de qué hace esta parte y por qué está resuelta así.
Pensada para que alguien que no vio el desarrollo entienda el resultado.>

```<lenguaje>
<fragmento de código representativo — el más ilustrativo, no todo el archivo>
```

**Archivos principales:** `ruta/al/archivo.ext`, `ruta/al/otro.ext`

**Tareas de este tema:** T-0.X.1 ✅ · T-0.X.2 ✅ · T-0.X.3 ✅

*(repetir por cada tema de la fase)*

---

## 3. Cómo probarlo

<Pasos concretos, reproducibles por cualquiera, para verificar que la fase
funciona de punta a punta. Preferir comandos y URLs concretas sobre
descripciones vagas. Ejemplo:>

1. Ejecutar `iniciar.bat` desde la raíz del proyecto.
2. Verificar que responda `http://localhost:8000/api/v1/health`.
3. Abrir `http://localhost:5500/` y confirmar que se ve <tal cosa>.
4. Correr `pytest` dentro de `backend/` → todo en verde.

---

## 4. Usuarios de prueba involucrados

<Si la fase creó o usa usuarios de prueba, referenciar `documentacion/Usuarios.md`
y aclarar cuáles aplican. Si no aplica, escribir "No aplica en esta fase".>

---

## 5. Decisiones y notas técnicas

<Decisiones de diseño tomadas durante la fase que no estaban explícitas en
`02_Documento_Tecnico.md` (o que lo ajustan), y el motivo. Ejemplo: un cambio
de estructura, una librería elegida, un límite descubierto. Si no hubo
decisiones nuevas, se omite esta sección.>

---

## 6. Estado final de la fase

| Tarea | Estado |
|---|---|
| T-0.X.1 | ✅ |
| T-0.X.2 | ✅ |
| ... | ... |

*Fase cerrada y aprobada el <fecha>. Continúa en `Fase 0Y - <siguiente>.md`.*
