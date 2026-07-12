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
- Google Auth gestionado por Emergent: sesión, perfil con email/nombre/foto URL y logout.
- Reglas gratis/premium: gratis no publica artículos mayores a $2,000 MXN y no contacta trueques sobre ese valor.
- Planes: Premium Intercambia ≈ 2 USD/mes en moneda local y Cruce de datos ≈ 10 USD/mes en moneda local.
- Registro de “tiendas de trueque”: usuarios gratis 1 negocio; usuarios premium registros ilimitados.
- Checkout Stripe preparado por backend; requiere `STRIPE_SECRET_KEY` para crear sesiones reales.
- Gestión de publicaciones propias: acciones para activar, pausar, marcar vendido, marcar truequeado y eliminar de la bodega.
- Eliminación implementada como baja lógica: se oculta de feed/bodega sin destruir historial.
- Prueba completa de 7 días: al iniciar sesión con Google, usuarios nuevos reciben acceso temporal a funciones Premium y Cruce de datos.
- Durante la prueba se eliminan límites de $2,000 MXN, contacto premium y cantidad de tiendas de trueque registradas.
- Tiendas de trueque evolucionadas a subperfiles/páginas paralelas al perfil personal, con `persona física` o `persona moral`.
- Las páginas de negocio publican como entidad propia: ofertas, necesidades, productos y servicios aceptados en trueque, sin aparecer a nombre de la persona registrante.
- PDF de marca incorporado como guía visual: púrpura `#673AB7`, verde `#4CAF50`, blanco/off-white e icono generado con manos/flechas de intercambio.
- Publicaciones ahora aceptan imagen base64, tags obligatorios 3-5, descripción, valor y `qué acepta/busca` opcional.
- Búsqueda en Inicio por título, descripción, categoría o tags.
- Paneles de Inicio: Amigos con agregar/bloquear/reportar, Historial de trueques, Impacto económico por diferencia de valores.
- Premium visible limitado: usuarios gratis ven publicaciones premium sin detalles ni contacto; usuarios premium/business ven todo.
- Publicidad local usa el punto de trueque cercano registrado.
- Mapa incluye onboarding para registrar negocio como punto seguro antes del checkout.
- Cruce de datos sin IA: sugerencias por categoría/tags entre ofertas y deseos.
- Chats funcionales con lectura/envío de mensajes y auto-scroll.
- Precios actualizados: Premium $5 USD, Cruce de datos $10 USD, Premium Puntos de Trueque $20 USD.
- Menú superior de identidad: permite alternar entre perfil personal y páginas de negocio registradas.
- Gestión de negocios: crear, editar parcialmente y eliminar tiendas/páginas; negocios pueden representar productos, servicios o negocios digitales.
- Crear publicación ampliado con ciudad, radio de búsqueda y casillas de negociación: acepta mayor valor, trueque de oportunidad, venta preferida, dinero parcial y negociable.
- Deseos: entrada de etiquetas para describir lo que el usuario/negocio busca.
- Teléfono: registro/verificación de teléfono para reputación y agregar amigos por teléfono mediante solicitudes.
- Menú superior ajustado: Perfil, Ajustes, Seguridad, Preferencias, Permisos y cambio a páginas privadas de negocio.
- Mapa local con radio calibrable 1/5/10/25/50 km; el radio se configura en mapa, no al publicar.
- Publicación simplificada: solo oferta/venta/trueque/donación; se quitó “Busco” del formulario de Crear.
- Ubicación de publicación por país, estado y ciudad/municipio/comunidad; incluye opciones rápidas de ciudades mexicanas.
- Nueva opción “Lo regalo / donación”.
- Deseos divididos en categorías, productos específicos y etiquetas para alimentar cruce de datos.
- Invitación de amigos por contactos/SMS/WhatsApp y recompensas: 5/10/50 amigos para beneficios premium.
- Precios en MXN: Premium $50, Cruce $100, Punto físico $150, Negocio digital $50.
- Impacto renombrado a beneficio e inversión comunitaria; se eliminó lenguaje de pérdida.

## Backlog priorizado
- P0: Completar configuración Stripe y webhook para checkout real de planes MXN $50/$100/$150/$50 digital.
- P1: Persistencia de chats completos.
- P1: Mapa real con ubicación contextual y permisos correctos.
- P1: Administración avanzada de páginas de negocio, roles de empleados y validación de locales.
- P1: Flujo formal de ofertas/contraofertas que obligue a seleccionar bienes/servicios registrados para cuantificar el valor del acuerdo.
- P2: Reputación avanzada por teléfono validado, trueques completados, reportes y calificaciones.
- P2: Motor avanzado de coincidencias y cadenas de trueque.
- P2: Grupos, muros comunitarios y personalización avanzada de categorías.

## Próximas tareas
1. Conectar autenticación y perfiles reales.
2. Añadir mapa nativo con permisos de ubicación.
3. Crear módulo de negocios premium con planes y publicación destacada.
4. Mejorar motor de cruce de datos por categoría, distancia y valor.