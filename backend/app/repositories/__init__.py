"""Repositorios: único lugar con queries SQL/ORM del proyecto.

Un repositorio por agregado. Reciben la ``Session`` ya abierta (no la crean ni
la commitean — eso es responsabilidad de quien llama, normalmente un service
o la dependencia ``get_session``). Exponen métodos con intención de negocio,
nunca SQL crudo hacia afuera.
"""
