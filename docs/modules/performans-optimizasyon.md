# ArchBuilder.AI Performans Optimizasyon Modülleri Dokümantasyonu

## Genel Bakış

ArchBuilder.AI performans optimizasyon sistemi, cloud server'ın optimal performansını sağlamak için geliştirilmiş kapsamlı bir modül setidir. Bu sistem şu bileşenlerden oluşur:

- **PerformanceTracker**: İşlem takibi ve performans ölçümü
- **AsyncCache**: Çok seviyeli önbellekleme sistemi  
- **OptimizedDatabaseService**: Veritabanı performans optimizasyonu
- **PerformanceMiddleware**: FastAPI middleware ile gerçek zamanlı izleme

## Performans Hedefleri

Sistem aşağıdaki performans hedeflerini karşılayacak şekilde tasarlanmıştır:

- **Basit sorgular**: <2 saniye
- **AI işlemleri**: <30 saniye
- **Doküman OCR**: <2 dakika  
- **Bellek kullanımı**: <500MB
- **CPU kullanımı**: <80%

## Modül Detayları

### 1. PerformanceTracker (app/core/performance.py)

#### Amaç
İşlemlerin süresini, kaynak kullanımını ve performans hedeflerini takip eder.

#### Ana Özellikler
- Asenkron context manager ile işlem takibi
- Decorator'lar ile otomatik performans izleme
- Gerçek zamanlı performans uyarıları
- Kapsamlı metrik toplama ve raporlama
- Redis tabanlı metrik depolama

#### Kullanım Örnekleri

```python
# Context manager ile kullanım
async with performance_tracker.track_operation("ai_layout_generation", correlation_id="123"):
    result = await ai_service.generate_layout(request)

# Decorator ile kullanım
@async_monitor_performance("database_query", target_seconds=2.0)
async def get_user_data(user_id: str):
    return await db.query(User).filter(User.id == user_id).first()

# Performans raporu alma
report = await performance_tracker.get_performance_report(hours=24)
health = await performance_tracker.get_system_health()
```

#### Konfigürasyon
```python
# Performans hedefleri
performance_targets = {
    "simple_query": 2.0,        # 2 saniye
    "ai_operation": 30.0,       # 30 saniye
    "document_ocr": 120.0,      # 2 dakika
    "layout_generation": 30.0,  # 30 saniye
    "validation": 5.0,          # 5 saniye
}

# Bellek limiti
max_memory_mb = 500  # 500MB
```

### 2. AsyncCache (app/core/cache.py)

#### Amaç
Çok seviyeli önbellekleme sistemi ile uygulama performansını artırır.

#### Ana Özellikler
- Memory cache (yerel, hızlı erişim)
- Redis cache (dağıtık, kalıcı)
- LRU eviction policy
- TTL (Time To Live) desteği
- Tag tabanlı cache invalidation
- Akıllı cache seviye seçimi

#### Kullanım Örnekleri

```python
# Cache initialize etme
initialize_cache(redis_client)

# Değer saklama ve alma
cache = get_cache()
await cache.set("user:123", user_data, ttl_seconds=3600, tags=["user_data"])
user = await cache.get("user:123")

# Decorator ile caching
@cached(ttl_seconds=300, tags=["ai_results"])
async def generate_layout(request):
    return await ai_service.process(request)

# Tag ile cache temizleme
await cache.delete_by_tags(["user_data", "expired_content"])
```

#### Cache Stratejisi
1. **Memory Cache**: En hızlı erişim için küçük ve sık kullanılan veriler
2. **Redis Cache**: Dağıtık ortamlar ve büyük veriler için
3. **Hybrid Mode**: Memory'de yoksa Redis'ten al, sonra memory'e kaydet

### 3. OptimizedDatabaseService (app/core/database_optimized.py)

#### Amaç
Veritabanı işlemlerini optimize eder ve performans izleme sağlar.

#### Ana Özellikler
- Async connection pooling
- Query performance monitoring
- Batch operations
- Otomatik query optimization
- Health monitoring
- Connection lifecycle management

#### Kullanım Örnekleri

```python
# Database service initialize
config = DatabaseConfig(
    database_url="postgresql+asyncpg://user:pass@localhost/db",
    pool_size=20,
    max_overflow=30
)
initialize_database(config)

# Optimized CRUD operations
db = get_database()

# Model alma
user = await db.get_model_by_id(User, user_id, correlation_id="req123")

# Filtreleme
users = await db.get_models_by_filter(
    User, 
    {"status": "active", "role": "architect"},
    limit=50,
    offset=0,
    order_by="created_at"
)

# Batch işlemler
operations = [
    {"type": "select", "query": select(User).where(User.active == True)},
    {"type": "update", "query": update(Project).where(Project.status == "draft")}
]
results = await db.execute_batch(operations, correlation_id="batch123")

# Health status
health = await db.get_health_status()
```

#### Connection Pool Optimizasyonu
```python
# Pool ayarları
pool_size=20,        # Minimum connection sayısı
max_overflow=30,     # Maximum ek connection
pool_timeout=30,     # Connection alma timeout
pool_recycle=3600,   # Connection yenileme süresi
pool_pre_ping=True   # Connection sağlık kontrolü
```

### 4. PerformanceMiddleware (app/core/middleware.py)

#### Amaç
FastAPI uygulamasına performans izleme middleware'i ekler.

#### Ana Özellikler
- Request/response timing
- Kaynak kullanım izleme
- Yavaş request tespiti
- Bellek kullanım uyarıları
- Gerçek zamanlı alerting
- Detaylı request loglama

#### Konfigürasyon
```python
# Middleware ekleme
add_performance_middleware(
    app,
    enable_detailed_monitoring=True,
    slow_request_threshold=5.0,     # 5 saniye
    memory_alert_threshold=500,     # 500MB
    enable_resource_monitoring=True,
    cpu_alert_threshold=80.0        # 80% CPU
)
```

#### Sağlanan Endpoints
- `GET /api/system/performance` - Performans istatistikleri
- `GET /api/system/performance/health` - Sistem sağlık durumu

## Kurulum ve Bağımlılıklar

### Gerekli Paketler
```bash
pip install psutil==6.1.0
pip install memory-profiler==0.61.0
pip install redis[asyncio]==5.1.1
pip install sqlalchemy[asyncio]==2.0.36
```

### Redis Kurulumu (Opsiyonel)
```bash
# Docker ile Redis
docker run -d -p 6379:6379 redis:alpine

# Veya sistem paketi
sudo apt-get install redis-server
```

## Yapılandırma

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/archbuilder
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30

# Redis (opsiyonel)
REDIS_URL=redis://localhost:6379/0

# Performance
ENABLE_PERFORMANCE_MONITORING=true
SLOW_REQUEST_THRESHOLD=5.0
MEMORY_ALERT_THRESHOLD=500
```

### Settings.py Güncellemesi
```python
class Settings(BaseSettings):
    # Existing settings...
    
    # Performance settings
    redis_url: Optional[str] = None
    db_pool_size: int = 20
    db_max_overflow: int = 30
    db_pool_timeout: int = 30
    db_pool_recycle: int = 3600
    
    enable_performance_monitoring: bool = True
    slow_request_threshold: float = 5.0
    memory_alert_threshold: int = 500
```

## Monitoring ve Alerting

### Metrik Türleri
1. **İşlem Metrikleri**: Süre, bellek, CPU kullanımı
2. **Cache Metrikleri**: Hit/miss oranları, boyut bilgileri
3. **Database Metrikleri**: Query süreleri, connection pool durumu
4. **System Metrikleri**: CPU, bellek, disk kullanımı

### Alert Türleri
1. **Performance Target Exceeded**: Hedef süre aşıldığında
2. **High Memory Usage**: Bellek limiti aşıldığında  
3. **Slow Request**: Yavaş request tespit edildiğinde
4. **Database Performance**: Database işlemleri yavaşladığında

### Monitoring Dashboard Verileri
Redis'te saklanan veriler:
- `metrics:{operation}:{date}` - Günlük metrikler
- `performance_alerts` - Performans uyarıları
- `memory_alerts` - Bellek uyarıları
- `user_metrics:{user_id}:{date}` - Kullanıcı bazlı metrikler

## API Kullanımı

### Performans İstatistikleri
```bash
curl "http://localhost:8000/api/system/performance"
```

### Sistem Sağlığı
```bash
curl "http://localhost:8000/api/system/performance/health"
```

### Belirli İşlem Raporu
```python
report = await performance_tracker.get_performance_report(
    operation_name="ai_layout_generation",
    user_id="user123",
    hours=24
)
```

## Hata Yönetimi

### Yaygın Hatalar ve Çözümleri

#### 1. Redis Bağlantı Hatası
```
Error: Redis connection failed
Çözüm: Redis servisini başlatın veya memory-only mode kullanın
```

#### 2. Database Pool Exhausted
```
Error: QueuePool limit of size 20 overflow 30 reached
Çözüm: Pool ayarlarını artırın veya connection leak kontrolü yapın
```

#### 3. Memory Limit Exceeded
```
Warning: Memory usage 600MB exceeds limit 500MB
Çözüm: Cache boyutunu azaltın veya memory limit artırın
```

#### 4. Slow Query Alert
```
Warning: Query duration 5.2s exceeds target 2.0s
Çözüm: Query'yi optimize edin veya index ekleyin
```

## En İyi Uygulamalar

### 1. Cache Kullanımı
- Sık erişilen verileri cache'leyin
- Uygun TTL değerleri belirleyin
- Tag'ler ile cache invalidation yapın
- Memory cache için küçük değerler kullanın

### 2. Database Optimizasyonu  
- Uygun connection pool boyutu ayarlayın
- Batch operations kullanın
- Query performance'ını izleyin
- Connection leak'lerini önleyin

### 3. Performance Monitoring
- Her kritik işlemi izleyin
- Uygun performance target'ları belirleyin
- Alert'lere hızlı yanıt verin
- Düzenli performance review yapın

### 4. Resource Management
- Bellek kullanımını kontrol edin
- CPU yoğun işlemleri async yapın
- File handle'ları kapatın
- Graceful shutdown implementasyonu

## Troubleshooting

### Performance Debug
```python
# Detaylı performance tracking
async with performance_tracker.track_operation(
    "debug_operation", 
    correlation_id="debug123"
) as metrics:
    # İşlem buraya
    pass
    
print(f"Duration: {metrics.duration}")
print(f"Memory: {metrics.memory_usage}MB")
```

### Cache Debug
```python
# Cache istatistikleri
stats = await cache.get_stats()
print(f"Memory hit rate: {stats['memory_cache']['hit_rate']}")
print(f"Redis hit rate: {stats['redis_cache']['hit_rate']}")
```

### Database Debug
```python
# Database health check
health = await db_service.get_health_status()
print(f"Status: {health['status']}")
print(f"Pool stats: {health['connection_pool']}")
```

Bu performans optimizasyon sistemi, ArchBuilder.AI'ın production ortamında yüksek performans ve güvenilirlik sağlayacak şekilde tasarlanmıştır. Tüm modüller birlikte çalışarak kapsamlı performans izleme ve optimizasyon sunar.