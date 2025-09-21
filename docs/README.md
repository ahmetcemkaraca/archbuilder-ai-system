# ArchBuilder.AI Cloud Server Documentation

Bu dökümanlar ArchBuilder.AI cloud server'ının nasıl çalıştığını ve kullanıldığını açıklar. Sistem, AI destekli mimari tasarım otomasyonu için Windows masaüstü uygulamasına hizmet veren bir bulut platformudur.

## 📚 Döküman İndeksi

### 🏗️ Sistem Mimarisi
- [**Genel Mimari**](./architecture/overview.md) - Sistem genel mimarisi ve bileşenler
- [**Veri Akışı**](./architecture/data-flow.md) - Veri akışı ve bileşenler arası iletişim
- [**Güvenlik Mimarisi**](./architecture/security.md) - STRIDE threat modeling ve güvenlik

### 🔧 Servisler Dökümantasyonu
- [**AIService**](./services/ai-service.md) - AI işleme ve model yönetimi servisi
- [**DocumentService**](./services/document-service.md) - Döküman işleme ve format dönüştürme servisi  
- [**RAGService**](./services/rag-service.md) - Retrieval-Augmented Generation servisi
- [**ProjectService**](./services/project-service.md) - Proje yönetimi ve workflow orchestration servisi

### 🌐 API Dökümantasyonu
- [**Documents API**](./api/documents.md) - Döküman yükleme ve işleme endpoints
- [**AI Processing API**](./api/ai.md) - AI işleme ve layout generation endpoints
- [**Projects API**](./api/projects.md) - Proje yönetimi endpoints
- [**Authentication API**](./api/auth.md) - Kimlik doğrulama endpoints

### 🛠️ Teknik Detaylar
- [**Database Models**](./technical/database.md) - Veritabanı şemaları ve modeller
- [**Caching Strategy**](./technical/caching.md) - Cache yönetimi ve performans
- [**Error Handling**](./technical/errors.md) - Hata yönetimi ve logging
- [**Performance**](./technical/performance.md) - Performans optimizasyonu

## 🚀 Hızlı Başlangıç

### Sistem Gereksinimleri
- Python 3.13+
- PostgreSQL 15+
- Redis 7+
- FastAPI 0.104+

### Kurulum
```bash
# Bağımlılıkları yükle
pip install -r requirements.txt

# Veritabanını başlat
python -m app.core.database

# Sunucuyu başlat
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### API Test Etme
```bash
# Health check
curl http://localhost:8000/health

# API dokümantasyonu
curl http://localhost:8000/docs
```

## 🔑 Temel Kavramlar

### Multi-Format CAD Support
Sistem DWG/DXF, IFC, PDF yönetmelik ve diğer mimari dosya formatlarını destekler.

### AI-Powered Design Generation
- **Vertex AI**: Gemini-2.5-Flash-Lite için büyük projeler
- **GitHub Models**: GPT-4.1 için hızlı işlemler
- **Hybrid Approach**: AI + rule-based fallback sistemi

### RAG-Based Knowledge
- Yönetmelik dökümanlarının embedding'le indexlenmesi
- Similarity search ile ilgili kuralların bulunması
- Context-aware AI prompt generation

### Human-in-the-Loop Workflow
- AI çıktılarının sandbox'ta test edilmesi
- Kullanıcı onayı gerektiren validasyon adımları
- Step-by-step project execution

## 📊 Performans Metrikleri

### Hedef Performans
- **API Response**: <500ms
- **Room Generation**: <30s
- **Floor Generation**: <5min
- **Building Generation**: 25min-5 hours

### Ölçeklenebilirlik
- **Concurrent Users**: 1000+
- **Document Processing**: 100MB/file
- **AI Model Switching**: <2s failover

## 🌍 Çok Dilli Destek

Sistem şu dilleri destekler:
- **Türkçe** (tr): Ana dil
- **İngilizce** (en): Varsayılan
- **Almanca** (de): Avrupa pazarı
- **Fransızca** (fr): Avrupa pazarı
- **İspanyolca** (es): Latin Amerika

## 🔒 Güvenlik Özellikleri

### Data Protection
- AES-256 encryption at rest
- TLS 1.3 for transit
- GDPR compliance
- Multi-tenant isolation

### AI Safety
- Output validation layers
- Confidence scoring
- Human review workflows
- Audit trails

## 📞 Destek ve İletişim

### Geliştirici Desteği
- **Issues**: GitHub repository
- **Documentation**: Bu dökümanlar
- **API Reference**: `/docs` endpoint

### Monitoring
- **Health Checks**: `/health` endpoint
- **Metrics**: Prometheus endpoints
- **Logs**: Structured JSON logs

---

**Son Güncelleme**: Eylül 2025  
**Versiyon**: 1.0.0  
**Durum**: Production Ready