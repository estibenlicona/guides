# Revisión de performance - Api Cards

Hola equipo,

De acuerdo con lo establecido en el plan de trabajo del lunes, les comparto el informe con los hallazgos identificados en el análisis de performance de API Cards.

### Hallazgo 1 - Ruptura de asincronía end-to-end
#### Severidad: Crítica
#### Descripción 
Se identificaron implementaciones en las que se rompe el flujo asincrónico end-to-end al utilizar patrones bloqueantes (.Result, .GetAwaiter().GetResult()). Esta práctica impide aprovechar la concurrencia nativa de .NET Core, generando mayor latencia en escenarios de alta concurrencia y riesgo de agotamiento de hilos, con la posibilidad de bloquear completamente el pod.

### Hallazgo 2 - Paralelismo bloqueante por asincronía incompleta
#### Severidad: Crítica
#### Descripción 
Se detectó uso de Parallel.ForEachAsync combinado con Task.Run y métodos que internamente bloquean con .Result. Esta combinación rompe la asincronía end-to-end, inmoviliza hilos del Thread Pool y degrada la escalabilidad bajo carga, elevando latencias y provocando timeouts en cascada.

### Hallazgo 3 - Configuración deficiente de HttpClient
#### Severidad: Crítica
#### Descripción
El HttpClient está registrado sin timeout explícito, sin límite de conexiones por servidor y con políticas Polly que no se aplican correctamente debido a llamadas bloqueantes con .Result. Esto eleva el riesgo de latencias de hasta 100s, agotamiento del connection pool, time outs en cascada y fugas de recursos bajo carga.

### Hallazgo 4 - Persistencia innecesaria
#### Severidad: Alta
#### Descripción
Actualmente se están realizando escrituras en MongoDB dentro del camino crítico de la petición con el objetivo de registrar trazabilidad, a pesar de que la plataforma ya cuenta con Instana para cubrir este propósito. Este punto ya fue conversado con Smith, quien está validando la viabilidad de eliminar dicha persistencia.
En caso de que se defina que la escritura en MongoDB debe mantenerse, es importante tener en cuenta que el método actual presenta varios problemas de diseño:
- Realiza consultas y validaciones costosas, que con grandes volúmenes de datos pueden generar una latencia significativa.
- Tiene una definición genérica, pero incluye implementaciones personalizadas que introducen confusión y dificultan su mantenimiento.
- Su diseño actual no escala adecuadamente y puede convertirse en un cuello de botella bajo alta concurrencia.

### Hallazgo 5 - Doble capa de cache con serialización innecesaria
#### Severidad: Alta
#### Descripción
Se identificó la presencia de una doble capa de caché (IMemoryCache y IDistributedCache). Actualmente IMemoryCache no se utiliza en la aplicación, pero en caso de ser activado, su implementación serializa y deserializa objetos a JSON antes de almacenarlos en memoria. Este patrón es innecesario y genera overhead de CPU y latencia adicional en cada operación de caché, sin aportar ningún beneficio.

### Hallazgo 6 - Servicios registrados incorrectamente en el contenedor de dependencias
#### Severidad: Media
#### Descripción
Se identificó que varios servicios han sido registrados con un ciclo de vida inadecuado en el contenedor de despencias DependencyInjectionHandler. En particular, los servicios de cache fueron configurados como Scoped, lo cual genera instancias nuevas en cada request, cuando en realidad son servicios sin estado que deberían ser Singleton.

### Hallazgo 7 - Falta de circuit breaker funcional (Polly inefectivo por uso bloqueante)
#### Severidad: Crítica
#### Descripción
Aunque Polly está configurado, no entra en efecto porque el acceso a HTTP se hace con patrones bloqueantes (.Result, .GetAwaiter().GetResult()), rompiendo la asincronía end-to-end. No existe un Circuit Breaker operativo, por lo que ante la caída de servicios externos se generan reintentos excesivos y timeouts acumulativos, con riesgo de fallas en cascada y degradación global.
