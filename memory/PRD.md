# Intercambia — PRD

## Problema
Crear una app móvil de trueque, venta e intercambio social para impulsar economía circular local: usuarios publican ofertas, deseos, servicios/oficios, conversan, descubren puntos de trueque y reciben sugerencias premium de cadenas de intercambio.

## Arquitectura
- Frontend: Expo SDK 54, React Native, navegación por tabs dentro de `/app/frontend`.
- Backend: FastAPI en `/app/backend/server.py` con MongoDB vía `MONGO_URL`.
- API pública bajo `/api`: bootstrap, items, intereses, puntos de trueque y cadenas.

## Identidad visual
- Actualizada según PDF del usuario: blanco/off-white, gris 20%, púrpura principal `#6B46C1` y verde contraste `#48BB78`.
- Estilo limpio, moderno, redondeado, inspirado en logotipo de intercambio con púrpura/verde.

## Personas
- Usuario general: intercambia productos/servicios y publica lista de deseos.
- Prestador/oficio: ofrece trabajo por hora o a destajo.
- Negocio local: desea ser punto de trueque premium.
- Usuario premium: busca cadenas de trueque y triangulación local.

## Implementado — 2026-06-04
- Feed social/marketplace con ofertas, deseos, filtros horizontales y publicidad básica.
- Categorías iniciales: Todo, Productos, Servicios, Oficios, Eco-hogar y Perfil local.
- Bodega/perfil con inventario y lista de deseos.
- Formulario flexible para publicar producto o servicio con valor, categoría y lo aceptado a cambio.
- Mapa visual de puntos de trueque con fichas de negocio.
- Charlas tipo inbox y cadenas premium sugeridas.
- Backend con datos iniciales reales, creación de publicaciones e interés por un item.

## Backlog priorizado
- P0: Autenticación real, perfiles multiusuario, persistencia de chats completos.
- P1: Mapa real con ubicación contextual y permisos correctos.
- P1: Registro premium de negocios/puntos de trueque.
- P2: Motor avanzado de coincidencias y cadenas de trueque.
- P2: Grupos, muros comunitarios y personalización avanzada de categorías.

## Próximas tareas
1. Conectar autenticación y perfiles reales.
2. Añadir mapa nativo con permisos de ubicación.
3. Crear módulo de negocios premium con planes y publicación destacada.
4. Mejorar motor de cruce de datos por categoría, distancia y valor.