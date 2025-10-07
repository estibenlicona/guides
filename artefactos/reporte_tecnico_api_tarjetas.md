# Reporte técnico - API Consulta Tarjetas de Crédito

Este documento acompaña el resumen ejecutivo y está pensado para que el equipo de desarrollo tenga todo lo necesario para aplicar los fixes.

---

## ERR-001 · Deadlocks por mezclar async/sync
- **Criticidad:** Crítica
- **Ubicación:** `CardService.cs` (línea 68), `CardDetailService.cs` (líneas 64, 255, 326), `BinesProductInfoService.cs` (líneas 53-55), `ErrorHandlerMiddleware.cs` (línea 73)
- **Explicación:** Las llamadas usan `.Result`, `.Wait()` o `GetAwaiter().GetResult()` dentro de flujos `async`. Cuando aumenta la concurrencia se agota el thread pool y aparecen deadlocks.

### Código con problema
```csharp
Task.WhenAll(taskFranCardData, taskPrivCardData).ConfigureAwait(false).GetAwaiter().GetResult();
var cardData = _validateTokenService.ValidateCardToken(cardToken).Result;
Task.Run(() => persisteLog.AddLog(traceIdentifier!.GUID, error, error.Message)).Wait();
```

### Código propuesto
```csharp
await Task.WhenAll(taskFranCardData, taskPrivCardData);
var cardData = await _validateTokenService.ValidateCardToken(cardToken);
await persisteLog.AddLog(traceIdentifier!.GUID, error, error.Message);
```

---

## ERR-002 · Paralelismo falso en `ValidateTokenService`
- **Criticidad:** Crítica
- **Ubicación:** `ValidateTokenService.cs` (líneas 85-135)
- **Explicación:** `Parallel.ForEachAsync` invoca lógica síncrona dentro de `Task.Run`. En picos de uso replica el problema de ERR-001 y no devuelve resultados parciales hasta que termina el lote.

```mermaid
flowchart LR
    A[Parallel.ForEachAsync] --> B[Task.Run síncrono]
    B --> C[ProccessCardToken bloqueante]
    C --> D[Thread pool agotado]
```

### Código con problema
```csharp
await Parallel.ForEachAsync(data, options, async (card, token) =>
{
    await Task.Run(() =>
    {
        ProccessCardToken(customer, customerToken, cardsToken, baseUrl, headers, card);
    }, CancellationToken.None);
});
```

### Código propuesto
```csharp
var tasks = data.Select(card => ProccessCardTokenAsync(
    customer, customerToken, baseUrl, headers, card));

var results = await Task.WhenAll(tasks);
var cardsToken = results.Where(card => card is not null).ToList();
```

---

## ERR-003 · `HttpClient` sin límites ni resiliencia
- **Criticidad:** Crítica
- **Ubicación:** `DependencyInjectionHandler.cs` (configuración del cliente), `RestService.cs` (`CreateClient`, `PostServiceAsync`)
- **Explicación:** Cada request crea un cliente nuevo sin timeout, reutiliza un handler propio y carece de circuit breaker. Cuando un proveedor tarda minutos respondemos con timeouts generales.

### Código con problema
```csharp
services.AddHttpClient<IRestService, RestService>()
    .AddTransientHttpErrorPolicy(policyBuilder =>
        policyBuilder.WaitAndRetryAsync(Backoff.DecorrelatedJitterBackoffV2(TimeSpan.FromSeconds(1), 5)));

HttpClientHandler l_objHttpClientHandler = new HttpClientHandler();
using var httpClient = CreateClient();
```

### Código propuesto
```csharp
services.AddHttpClient<IRestService, RestService>(client =>
{
    client.Timeout = TimeSpan.FromSeconds(10);
})
.ConfigurePrimaryHttpMessageHandler(() => new HttpClientHandler
{
    MaxConnectionsPerServer = 50,
})
.AddTransientHttpErrorPolicy(builder =>
    builder.WaitAndRetryAsync(Backoff.DecorrelatedJitterBackoffV2(TimeSpan.FromSeconds(1), 3)))
.AddTransientHttpErrorPolicy(builder =>
    builder.CircuitBreakerAsync(5, TimeSpan.FromSeconds(30)))
.AddPolicyHandler(Policy.TimeoutAsync<HttpResponseMessage>(TimeSpan.FromSeconds(5)));

public async Task<T> PostServiceAsync<T>(string baseUrl, object parameters, IDictionary<string, string?> headers)
{
    _createClient.DefaultRequestHeaders.Clear();
    _createClient.DefaultRequestHeaders.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));
    AddHeadersForReq(headers!, _createClient);

    HttpContent jsonObject = new StringContent(
        JsonConvert.SerializeObject(parameters),
        Encoding.UTF8,
        "application/json");

    HttpResponseMessage res = await _createClient.PostAsync(baseUrl, jsonObject);
    var data = await res.Content.ReadAsStringAsync();
    return JsonConvert.DeserializeObject<T>(data)!;
}
```

---

## ERR-004 · Escrituras pesadas en MongoDB dentro del request
- **Criticidad:** Alta
- **Ubicación:** `CrudService.cs` (`AddOrUpdate`)
- **Explicación:** Se actualizan colecciones grandes con `AddToSetEach` dentro del request. El hilo queda bloqueado hasta que Mongo confirma.

### Código con problema
```csharp
result = await collection.UpdateOneAsync(
    Builders<TEntity>.Filter.Eq(i => i.Id, data.Id),
    Builders<TEntity>.Update
        .SetOnInsert(s => s.Id, data.Id)
        .SetOnInsert(s => s.CreateDateTime, DateTime.Now)
        .Set(s => s.IdCard, data.IdCard)
        .AddToSetEach(s => s.CardsNumber, data.CardsNumber)
        .AddToSetEach(s => s.CardsToken, data.CardsToken)
        .AddToSetEach(s => s.CardsType, data.CardsType),
    new UpdateOptions { IsUpsert = true });
```

### Código propuesto
```csharp
public async Task QueueCardUpdateAsync(CardData data)
{
    await _eventBus.PublishAsync("card-data-updated", data);
}

public async Task HandleCardUpdateAsync(CardData data)
{
    await _collection.UpdateOneAsync(
        Builders<CardData>.Filter.Eq(i => i.Id, data.Id),
        Builders<CardData>.Update
            .SetOnInsert(s => s.Id, data.Id)
            .SetOnInsert(s => s.CreateDateTime, DateTime.UtcNow)
            .Set(s => s.IdCard, data.IdCard)
            .AddToSetEach(s => s.CardsNumber, data.CardsNumber)
            .AddToSetEach(s => s.CardsToken, data.CardsToken)
            .AddToSetEach(s => s.CardsType, data.CardsType),
        new UpdateOptions { IsUpsert = true });
}
```

---

## ERR-005 · Cache duplicado y costoso en `CardDetailService`
- **Criticidad:** Media
- **Ubicación:** `CardDetailService.cs` (líneas 40-58)
- **Explicación:** Cada request reconstruye un cache en memoria y además consulta Redis sin invalidación clara.

### Código con problema
```csharp
var cacheKey = $"card-detail-{cardId}";
if (!_memoryCache.TryGetValue(cacheKey, out CardDetail? detail))
{
    detail = _redisCache.Get<CardDetail>(cacheKey);
    if (detail is null)
    {
        detail = GetCardDetailFromDb(cardId);
        _redisCache.Set(cacheKey, detail, TimeSpan.FromMinutes(5));
    }
    _memoryCache.Set(cacheKey, detail, TimeSpan.FromMinutes(1));
}
return detail;
```

### Código propuesto
```csharp
public async Task<CardDetail?> GetCardDetailAsync(Guid cardId)
{
    var cacheKey = $"card-detail-{cardId}";
    return await _distributedCache.GetOrCreateAsync(cacheKey, async entry =>
    {
        entry.AbsoluteExpirationRelativeToNow = TimeSpan.FromMinutes(5);
        return await _cardRepository.GetCardDetailAsync(cardId);
    });
}
```

---

## ERR-006 · Logging bloqueante en middleware de errores
- **Criticidad:** Media
- **Ubicación:** `ErrorHandlerMiddleware.cs` (líneas 68-90)
- **Explicación:** El middleware atrapa excepciones pero registra el error con `.Wait()`, devolviendo la respuesta tarde y bloqueando el pipeline.

### Código con problema
```csharp
Task.Run(() =>
{
    persisteLog.AddLog(traceIdentifier!.GUID, error, error.Message);
}).Wait();
```

### Código propuesto
```csharp
await persisteLog.AddLog(traceIdentifier!.GUID, error, error.Message);
```

---

Si necesitan más contexto o pairing para aplicar los cambios, avísenme y lo vemos juntos.
