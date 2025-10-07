# Resumen ejecutivo - API Consulta Tarjetas de Crédito

Hola equipo,

Les dejo el resumen rápido de lo que encontramos en la API para que tengan el panorama completo sin meternos a los detalles técnicos.

## Qué está pasando
- La API mezcla código síncrono y asíncrono; el thread pool se vacía y terminamos con solicitudes colgadas.
- Las llamadas externas no tienen límites ni circuit breaker, así que cuando un proveedor falla dejamos hilos bloqueados por minutos.
- Persistimos y validamos datos pesados dentro del camino crítico, sumando varios cientos de milisegundos a cada request.
- La configuración de dependencias fuerza recrear clientes HTTP y caches en cada petición, generando consumo extra de CPU.

## Por qué importa
- Los clientes ven timeouts y fallas en picos de carga.
- Estamos sobredimensionando infraestructura solo para mantener el servicio vivo.
- Cada incidente deja datos inconsistentes y un costo operativo alto para soporte.

## Movidas inmediatas
1. Reescribir los puntos críticos que usan `.Result` y `.Wait()` para que todo sea realmente `async/await`.
2. Configurar `HttpClient` con timeouts cortos y un circuito de protección para dejar de colgar hilos.
3. Sacar las escrituras pesadas de MongoDB y el procesamiento paralelo falso del request.

## Beneficio esperado
- Latencia P95 por debajo de **500 ms**.
- Deadlocks fuera del panorama y un thread pool disponible para nuevos requests.
- API preparada para la carga pico sin tener que agregar más nodos.
