# Informe Técnico - Análisis de Performance API Cards

## Hallazgo 1 - Ruptura de asincronía end-to-end
### **Severidad:** 🔴 CRÍTICA
### **Descripción Técnica:**

El código utiliza patrones bloqueantes (`.Result`, `.GetAwaiter().GetResult()`, `.Wait()`) sobre operaciones asíncronas, causando **context deadlocks** bajo alta concurrencia. Esto agota el Thread Pool.

---

### **Problema 1.1: CardService.cs - Línea 68**
#### **Código Actual ❌:**

```csharp
// CardService.cs - Método GetCards
public async Task<Response<GetCardsResponse>> GetCards(string tppId, Query query, string token)
{
    
    var taskFranCardData = GetFranchisedCard(customerId!);
    var taskPrivCardData = GetPrivateCard(documentType!, documentNumber!);

    // ❌ PROBLEMA: GetAwaiter().GetResult() bloquea el hilo
    Task.WhenAll(taskFranCardData, taskPrivCardData)
        .ConfigureAwait(false)
        .GetAwaiter()
        .GetResult();
}
```
#### **Solución ✅:**

```csharp
// CardService.cs - Refactorizado
public async Task<Response<GetCardsResponse>> GetCards(string tppId, Query query, string token)
{
    
    var taskFranCardData = GetFranchisedCard(customerId!);
    var taskPrivCardData = GetPrivateCard(documentType!, documentNumber!);

    // ✅ CORRECTO: await libera el thread durante I/O
    await Task.WhenAll(taskFranCardData, taskPrivCardData);

}
```

---

### **Problema 1.2: CardDetailService.cs - Líneas 255 y 326**
#### **Código Actual ❌:**

```csharp
// CardDetailService.cs - Método GetCardDetailFranchised
private async Task<CardDetailResponseDto> GetCardDetailFranchised(
    CardDetailRequestQueryDto query, 
    string tppId, 
    Dictionary<string, string?> headers)
{
    
    var paymentValues = GetPaymentValuesCommon<PaymentValuesPrivateObject>(restPayment);
    var consultQuotas = GetConsultQuotasCommon<ConsultQuotasPrivateResponse>(restConsult);

    // ❌ PROBLEMA: Mismo patrón bloqueante
    Task.WhenAll(paymentValues, consultQuotas)
        .ConfigureAwait(false)
        .GetAwaiter()
        .GetResult();

}
```

#### **Solución ✅:**

```csharp
// CardDetailService.cs - Refactorizado
private async Task<CardDetailResponseDto> GetCardDetailFranchised(
    CardDetailRequestQueryDto query, 
    string tppId, 
    Dictionary<string, string?> headers)
{
    
    var paymentValues = GetPaymentValuesCommon<PaymentValuesPrivateObject>(restPayment);
    var consultQuotas = GetConsultQuotasCommon<ConsultQuotasPrivateResponse>(restConsult);

    // ✅ CORRECTO: await permite concurrencia sin bloquear
    await Task.WhenAll(paymentValues, consultQuotas);

}
```

---

### **Problema 1.3: BinesProductInfoService.cs - Líneas 53-55**
#### **Código Actual ❌:**

```csharp
// BinesProductInfoService.cs - Método GetInfoCardBin
public async Task<BinesProductIdDto?> GetInfoCardBin()
{
    // ❌ PROBLEMA: .Result bloquea el thread
    var resultCache = _cache.ConsultarRequest("BINESOPENAPI");
    if (resultCache.Result.Response is not null)
    {
        return resultCache.Result.Response;
    }
    
}
```

#### **Solución ✅:**

```csharp
// BinesProductInfoService.cs - Refactorizado
public async Task<BinesProductIdDto?> GetInfoCardBin()
{
    // ✅ CORRECTO: await en vez de .Result
    var resultCache = await _cache.ConsultarRequest("BINESOPENAPI");
    if (resultCache.Response is not null)
    {
        _logger.LogDebug("Cache hit para BINESOPENAPI");
        return resultCache.Response;
    }
}
```

---

### **Problema 1.4: ValidateTokenService.cs - Líneas 117 y 131**

#### **Código Actual ❌:**

```csharp
// ValidateTokenService.cs - Método ProccessCardToken
private void ProccessCardToken(CustomerTokenResponse customer, string customerToken, ConcurrentBag<CardData> cardsToken, string baseUrl, Dictionary<string, string> headers, CardData card)
{
    if (!string.IsNullOrEmpty(card.Expiration))
    {
        // ❌ PROBLEMA: uso de .Result dentro de método síncrono
        ValidateCardFranchisResponse(customer, customerToken, cardsToken, baseUrl, headers, card);
    }
    else
    {
        // ❌ PROBLEMA: uso de .Result dentro de método
        ValidateCardPrivateResponse(customer, customerToken, cardsToken, baseUrl, headers, card);
    }
}

private void ValidateCardPrivateResponse(CustomerTokenResponse customer, string customerToken, ConcurrentBag<CardData> cardsToken, string baseUrl, Dictionary<string, string> headers, CardData card)
{
    // ❌ PROBLEMA: .Result bloquea el Thread
    var resultado = PostCardTokenPrivate(card, customer, customerToken, baseUrl, headers).Result;
    if (resultado?.Data is not null)
    {
        card.Bin = card.CardToken?.Substring(0, 6);
        card!.CardProduct = resultado.Data.ProductID;
        card.CardToken = resultado.Data.CardToken;
        cardsToken.Add(card);
    }
}

private void ValidateCardFranchisResponse(CustomerTokenResponse customer, string customerToken, ConcurrentBag<CardData> cardsToken, string baseUrl, Dictionary<string, string> headers, CardData card)
{
    // ❌ PROBLEMA: .Result bloquea el Thread
    var resultado = PostCardTokenFranchis(card, customer, customerToken, baseUrl, headers).Result;
    if (resultado?.Data is not null)
    {
        card.Bin = card.CardToken?.Substring(0, 6);
        card!.CardProduct = resultado.Data.ProductID;
        card.CardToken = resultado.Data.CardToken;
        cardsToken.Add(card);
    }
}
```

#### **Solución ✅:**

```csharp
// ValidateTokenService.cs - Refactorizado

// 1. Cambiar método a async
private async Task<CardData?> ProccessCardTokenAsync(
    Customer customer, 
    CustomerToken customerToken, 
    string baseUrl, 
    Dictionary<string, string?> headers, 
    Data card)
{
    if (!string.IsNullOrEmpty(card.Expiration))
    {
        // ✅ CORRECTO: uso de await no bloqueante
        await ValidateCardFranchisResponseAsync(customer, customerToken, cardsToken, baseUrl, headers, card);
    }
    else
    {
        // ✅ CORRECTO: uso de await no bloqueante
        await ValidateCardPrivateResponseAsync(customer, customerToken, cardsToken, baseUrl, headers, card);
    }   
}

// 2. Cambiar método a async
private async Task ValidateCardFranchisResponseAsync(CustomerTokenResponse customer, string customerToken, ConcurrentBag<CardData> cardsToken, string baseUrl, Dictionary<string, string> headers, CardData card)
{
    ✅ CORRECTO: uso de await no bloqueante
    var resultado = await PostCardTokenFranchisAsync(card, customer, customerToken, baseUrl, headers);
    if (resultado?.Data is not null)
    {
        card.Bin = card.CardToken?.Substring(0, 6);
        card!.CardProduct = resultado.Data.ProductID;
        card.CardToken = resultado.Data.CardToken;
        cardsToken.Add(card);
    }
}

// 3. Cambiar método a async
private async Task ValidateCardPrivateResponseAsync(CustomerTokenResponse customer, string customerToken, ConcurrentBag<CardData> cardsToken, string baseUrl, Dictionary<string, string> headers, CardData card)
{
    ✅ CORRECTO: uso de await no bloqueante
    var resultado = await PostCardTokenPrivateAsync(card, customer, customerToken, baseUrl, headers);
    if (resultado?.Data is not null)
    {
        card.Bin = card.CardToken?.Substring(0, 6);
        card!.CardProduct = resultado.Data.ProductID;
        card.CardToken = resultado.Data.CardToken;
        cardsToken.Add(card);
    }
}
```

---

### **Problema 1.5: ErrorHandlerMiddleware.cs - Línea 73**
#### Código Actual ❌:

```csharp
// ErrorHandlerMiddleware.cs
public async Task InvokeAsync(HttpContext context, TraceIdentifier? traceIdentifier)
{
    try
    {
        // ❌ PROBLEMA: .ConfigureAwait innecesario
        await _next(context).ConfigureAwait(false);
    }
    catch (Exception error)
    {
         // ❌ PROBLEMA: uso interno de .Wait() bloquea el thread
         SetStatusCodeResponse(context, logger, traceIdentifier, persisteLog, error, responseModel);
    }
}

private static void SetStatusCodeResponse(HttpContext context, ILogger<ErrorHandlerMiddleware> logger, TraceIdentifier traceIdentifier, ICrudService persisteLog, Exception error, ErrorResponse responseModel)
{
    ...

    // ❌ PROBLEMA: .Wait() bloquea el thread
    if (context.Response.StatusCode != StatusCodes.Status400BadRequest)
        Task.Run(() => persisteLog.AddLog(traceIdentifier!.GUID, error, error.Message)).Wait(); 

}
```
#### Solución ✅:

```csharp
// ErrorHandlerMiddleware.cs - Refactorizado
public async Task InvokeAsync(HttpContext context, TraceIdentifier? traceIdentifier)
{
    try
    {
        // ✅ CORRECTO: eliminar .ConfigureAwait
        await _next(context);
    }
    catch (Exception error)
    {
        ...
        SetStatusCodeResponse(context, logger, traceIdentifier, persisteLog, error, responseModel);
        
        await context.Response.WriteAsync(response);
    }
}

private static void SetStatusCodeResponse(HttpContext context, ILogger<ErrorHandlerMiddleware> logger, TraceIdentifier traceIdentifier, ICrudService persisteLog, Exception error, ErrorResponse responseModel)
{
    responseModel.Code = context.Response.StatusCode.ToString(CultureInfo.CurrentCulture);

    if (context.Response.StatusCode.Equals(StatusCodes.Status500InternalServerError))
        responseModel.Message = Constants.PBCT_GENERAL_UNCONTROLLED_EXCEPTION;

    // ✅ CORRECTO: eliminar persistencia innecesaria -> Usar Instana

    logger.LogError(error, Constants.TEMPLATEITEM2, traceIdentifier, Constants.PBCT_GENERAL_UNCONTROLLED_INTERNAL_EXCEPTION);
}
```

---

## Hallazgo 2: Paralelismo Bloqueante por Asincronía Incompleta
### **Severidad:** 🔴 CRÍTICA
### **Ubicación:** `ValidateTokenService.cs` - Método `ValidateCard`

---

### **Código Actual ❌:**

```csharp
// ValidateTokenService.cs - Líneas 85-120
public async Task<List<CardData>> GetCardsToken(List<CardData> data,
    CustomerTokenResponse customer, string customerToken, string tppId)
{
    ...
    
    // ❌ PROBLEMA 1: Parallel.ForEachAsync con MaxDegreeOfParallelism arbitrario
    var options = new ParallelOptions { MaxDegreeOfParallelism = 5 };
    
    // ❌ PROBLEMA 2: Task.Run innecesario dentro de async
    await Parallel.ForEachAsync(data, options, async (card, token) =>
    {
        // ❌ PROBLEMA 3: Método síncrono que bloquea con .Result
        await Task.Run(() => {
            ProccessCardToken(customer, customerToken, cardsToken, baseUrl, headers, card);
        }, CancellationToken.None);
    });
}
```

### Solución ✅:

```csharp
// ValidateTokenService.cs - Refactorizado

public async Task<List<CardData>> GetCardsToken(List<CardData> data,
    CustomerTokenResponse customer, string customerToken, string tppId)
{
    ...
    // ✅ Hacer este valor parametrizable
    var options = new ParallelOptions {
        MaxDegreeOfParallelism = configuration.GetValue<int>("MaxDegreeOfParallelism", 5);
    };
    
    // ✅ Eliminar Task.Run innecesario dentro de async
    await Parallel.ForEachAsync(data, options, async (card, token) =>
    {
        // ✅ Método síncrono que no bloquea
        await ProccessCardTokenAsync(customer, customerToken, cardsToken, baseUrl, headers, card);
    });

    ...
}

```

## Hallazgo 3: Configuración Deficiente de HttpClient
### **Severidad:** 🔴 CRÍTICA
### **Ubicación:** `DependencyInjectionHandler.cs`

---

### **Código Actual ❌:**

```csharp
// DependencyInjectionHandler.cs
public static IServiceCollection DependencyInjectionConfig(this IServiceCollection services)
{
    // ❌ PROBLEMA: Sin timeout explícito, sin límite de conexiones
    services.AddHttpClient<IRestService, RestService>()
        .AddTransientHttpErrorPolicy(policyBuilder => 
            policyBuilder.WaitAndRetryAsync(
                Backoff.DecorrelatedJitterBackoffV2(TimeSpan.FromSeconds(1), 5)
            ));
    
    // ... resto de servicios
}
```

### **Solución:**
Es importante resaltar que los valores definidos para el número de reintentos, el timeout por petición y los parámetros de configuración del circuit breaker deben establecerse en función de indicadores objetivos, como la latencia observada, los tiempos de recuperación de los servicios externos y el SLA de API Cards.
Actualmente este SLA aún no está formalmente definido; sin embargo, en conversaciones con el especialista se ha mencionado que algunos clientes, como la APP, esperan respuestas en un máximo de 30 segundos.
Por ello, resulta fundamental contar con estas métricas para poder aplicar una configuración realmente óptima que equilibre resiliencia, rendimiento y experiencia del usuario.

También es conveniente separar IRestService por proveedor/endpoint, ya que actualmente consume varios servicios con perfiles de latencia y recuperación diferentes. Mantenerlos en un solo cliente dificulta ajustar timeouts, reintentos y circuit breakers de forma óptima para cada caso. Al separarlos, podremos asignar políticas específicas para cada endpoint.

```csharp
// DependencyInjectionHandler.cs

public static IServiceCollection DependencyInjectionConfig(
    this IServiceCollection services, 
    IConfiguration configuration)
{
    
    services.AddHttpClient<IRestService, RestService>()
    .AddStandardResilienceHandler(o =>
    {
        // Timeout por intento
        o.AttemptTimeout = new HttpTimeoutStrategyOptions
        {
            Timeout = TimeSpan.FromSeconds(10) // Ajustar al p90 o p95 de los servicios llamados por medio de IRestService
        };

        // Retries (1 reintento)
        o.Retry = new HttpRetryStrategyOptions
        {
            MaxRetryAttempts = 1
        };

        // Circuit breaker
        o.CircuitBreaker = new HttpCircuitBreakerStrategyOptions
        {
            FailureRatio = 0.7,                     // 70% fallos en ventana
            MinimumThroughput = 20,                 // al menos 20 requests
            SamplingDuration = TimeSpan.FromSeconds(30),
            BreakDuration = TimeSpan.FromSeconds(20) // El BreakDuration debería alinearse con el tiempo típico de recuperación del servicio externo
        };
    });
    
    ...
    
    return services;
}
```

---

## Hallazgo 4: Persistencia Innecesaria en Camino Crítico

### **Severidad:** 🟡 ALTA

### **Ubicación:** `CrudService.cs` - Método `AddOrUpdate`

---

### Código Actual ❌:

```csharp
// CardService.cs - GetCards
public async Task<Response<GetCardsResponse>> GetCards(...)
{
    ...
    
    // ❌ PROBLEMA: Escritura MongoDB BLOQUEA el response
    await _crudService.AddOrUpdate(_cardsEntity);
    
    return response;
}
```

---

### **Problemas con AddOrUpdate:**

```csharp
// CrudService.cs - Método AddOrUpdate
public async Task AddOrUpdate<TEntity>(TEntity data) where TEntity : CommonEntity
{
    var collection = _database.GetCollection<TEntity>(typeof(TEntity).Name);
    
    // ❌ PROBLEMA 1: UpdateOne con múltiples operaciones costosas
    var result = await collection.UpdateOneAsync(
        Builders<TEntity>.Filter.Eq(i => i.Id, data.Id),
        Builders<TEntity>.Update
            .SetOnInsert(s => s.Id, data.Id)
            .SetOnInsert(s => s.CreateDateTime, DateTime.Now)
            .Set(s => s.IdCard, data.IdCard)
            .Set(s => s.CardsQuantity, data.CardsQuantity)  // ← Race condition
            .Set(s => s.CardToken, data.CardToken)  // ← Sobrescribe
            .Set(s => s.SuccessfullResponse, data.SuccessfullResponse)
            .AddToSetEach(s => s.CardsNumber, data.CardsNumber)  // ← Costoso con arrays grandes
            .AddToSetEach(s => s.BrokerEndPoint, data.BrokerEndPoint),
        new UpdateOptions { IsUpsert = true }
    );
    
    // ❌ PROBLEMA 2: Sin índices → Scan completo de colección
    // ❌ PROBLEMA 3: Arrays crecen indefinidamente (CardsNumber con 1000+ elementos)
}
```

---

### Solución OPCIÓN 1: Eliminar Persistencia ✅:

```csharp
// CardService.cs

public async Task<Response<GetCardsResponse>> GetCards(...)
{
    // ... obtener tarjetas de APIs externas (500ms)
    
    // ✅ NO persistir en MongoDB (usar Instana para trazabilidad)
    // await _crudService.AddOrUpdate(_cardsEntity);  // ← ELIMINAR
    
    // ✅ Retornar response INMEDIATAMENTE
    return response;
}
```

---

### **Solución OPCIÓN 3: Event Sourcing (cambio de arquitectura):**

```csharp
// CardAccessEvent.cs (nuevo modelo)
public class CardAccessEvent
{
    public string Id { get; set; }  // Guid único
    public string CustomerId { get; set; }
    public string Endpoint { get; set; }  // "GetCards"
    public List<string> CardsReturned { get; set; }
    public int CardsCount { get; set; }
    public DateTime Timestamp { get; set; }
    public string TraceId { get; set; }
}

// EventStoreService.cs (nuevo servicio)
public class EventStoreService : IEventStoreService
{
    private readonly IMongoDatabase _database;
    private readonly ILogger<EventStoreService> _logger;
    
    public async Task RecordCardAccessEvent(CardAccessEvent evt)
    {
        var collection = _database.GetCollection<CardAccessEvent>("CardAccessEvents");
        
        // ✅ InsertOne es MÁS RÁPIDO que UpdateOne
        await collection.InsertOneAsync(evt);
    }
}

// CardService.cs - Usando event sourcing
public async Task<Response<GetCardsResponse>> GetCards(...)
{
    // ... obtener tarjetas de APIs externas (500ms)
    
    // ✅ Registrar evento (fire-and-forget)
    _ = Task.Run(async () =>
    {
        try
        {
            var evt = new CardAccessEvent
            {
                Id = Guid.NewGuid().ToString(),
                CustomerId = query.customerId,
                Endpoint = "GetCards",
                CardsReturned = cardNumbers,
                CardsCount = cardNumbers.Count,
                Timestamp = DateTime.UtcNow,
                TraceId = HttpContext.TraceIdentifier
            };
            
            await _eventStoreService.RecordCardAccessEvent(evt);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error registrando evento de acceso");
        }
    });
    
    // ✅ Retornar response INMEDIATAMENTE
    return response;
}
```

**Beneficios:**
- ✅ InsertOne es 5-10x más rápido que UpdateOne
- ✅ Sin race conditions (cada evento es inmutable)
- ✅ Arrays no crecen indefinidamente
- ✅ Auditoría completa (histórico de eventos)
- ✅ Escalable (sharding fácil por CustomerId)

---

### **Crear Índices en MongoDB:**

```javascript
// Script de MongoDB para crear índices

// Índice compuesto para queries por customer
db.Cards.createIndex(
    { "IdCard": 1, "CreateDateTime": -1 },
    { 
        name: "idx_customer_date",
        background: true
    }
);

// Índice para event sourcing (si se implementa Opción 3)
db.CardAccessEvents.createIndex(
    { "CustomerId": 1, "Timestamp": -1 },
    {
        name: "idx_customer_timestamp",
        background: true
    }
);

// Índice para queries por TraceId (troubleshooting)
db.CardAccessEvents.createIndex(
    { "TraceId": 1 },
    {
        name: "idx_traceid",
        background: true
    }
);
```

---

## Hallazgo 5: Doble Capa de Cache con Serialización Innecesaria

### **Severidad:** 🟡 ALTA

### **Ubicación:** `CacheManager.cs` y `CacheService.cs`

---

### Código Actual ❌:

```csharp
// CacheManager.cs - Serialización JSON innecesaria
public class CacheManager : ICacheManager
{
    private readonly IMemoryCache _memoryCache;
    
    public CacheManager(IMemoryCache memoryCache)
    {
        _memoryCache = memoryCache;
    }
    
    // ❌ PROBLEMA: Serializa a JSON antes de guardar en memoria
    public Task<bool> Save(string key, object valor, int segundos)
    {
        // ⚠️ JsonConvert.SerializeObject es COSTOSO e INNECESARIO
        _memoryCache.Set(
            key, 
            JsonConvert.SerializeObject(valor),  // ← ~5ms + allocations
            new TimeSpan(0, 0, segundos)
        );
        return Task.FromResult(true);
    }
    
    // ❌ PROBLEMA: Deserializa desde JSON en cada lectura
    public Task<T> Get<T>(string key)
    {
        if (_memoryCache.TryGetValue(key, out string? valor))
        {
            // ⚠️ JsonConvert.DeserializeObject es COSTOSO e INNECESARIO
            return Task.FromResult(
                JsonConvert.DeserializeObject<T>(valor!)!  // ← ~5ms + allocations
            );
        }
        
        return Task.FromResult(default(T)!);
    }
}
```

### ¿Por qué es innecesario?
IMemoryCache ya almacena objetos en memoria (no necesita serialización)

---

### **OPCIÓN 2: Si se quiere mantener la abstracción, arreglar CacheManager:**

```csharp
// CacheManager.cs - sin serialización

public class CacheManager : ICacheManager
{
    private readonly IMemoryCache _memoryCache;
    private readonly ILogger<CacheManager> _logger;
    
    public CacheManager(IMemoryCache memoryCache, ILogger<CacheManager> logger)
    {
        _memoryCache = memoryCache;
        _logger = logger;
    }
    
    // ✅ CORRECTO: Guardar objeto directamente (sin serializar)
    public Task<bool> Save<T>(string key, T valor, int segundos)
    {
        // ✅ Guardar objeto directamente (IMemoryCache es genérico)
        _memoryCache.Set(key, valor, new new TimeSpan(0, 0, segundos));
        
        return Task.FromResult(true);
    }
    
    // ✅ CORRECTO: Obtener objeto directamente (sin deserializar)
    public Task<T?> Get<T>(string key)
    {
        if (_memoryCache.TryGetValue<T>(key, out var valor))
        {
            return Task.FromResult<T?>(valor);
        }

        return Task.FromResult<T?>(default);
    }
    
    ...
}
```

---

### **Actualizar ICacheManager interface:**

```csharp
// ICacheManager.cs - Actualizado

public interface ICacheManager
{
    Task<bool> Save<T>(string key, T valor, int segundos);  // ✅ Genérico
    Task<T?> Get<T>(string key);  // ✅ Genérico
}
```

## Hallazgo 6: Cache Registrado como Scoped (Cache Inútil)

### **Severidad:** 🔴 CRÍTICA

### **Ubicación:** `DependencyInjectionHandler.cs`

---

### **Código Actual ❌:**

```csharp
// DependencyInjectionHandler.cs

public static IServiceCollection DependencyInjectionConfig(this IServiceCollection services)
{
    // ❌ PROBLEMA CRÍTICO: Cache como Scoped = Cache no funcional, ya que se limpia en cada peticion
    services.AddScoped<ICacheManager, CacheManager>();
    services.AddScoped<ICacheService, CacheService>();
    
    ...
}
```

### Solución ✅:

```csharp
// DependencyInjectionHandler.cs

public static IServiceCollection DependencyInjectionConfig(
    this IServiceCollection services, 
    IConfiguration configuration)
{
    ...
    
    // ✅ CRÍTICO: La cache en memoria siempre debe ser Singleton
    services.AddSingleton<ICacheManager, CacheManager>();  // ← Singleton!
    services.AddSingleton<ICacheService, CacheService>();  // ← Singleton!
    
    // ✅ CrudService como Singleton (thread-safe, sin estado)
    services.AddSingleton<ICrudService, CrudService>();
    
    // ✅ HttpContextAccessor puede reemplazar implementacion de ITraceIdentifier ya que genera un TraceId por cada peticion.
    services.AddHttpContextAccessor();
    ...
}
```
