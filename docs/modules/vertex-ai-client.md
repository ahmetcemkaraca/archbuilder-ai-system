# Vertex AI Client Dokumentasyonu

## Genel Bakış
Vertex AI Client modülü, Google Cloud Vertex AI platformu üzerinden Gemini-2.5-Flash-Lite modelini kullanarak ArchBuilder.AI'nin AI tabanlı mimari tasarım otomasyonu işlevlerini gerçekleştirir.

## Ana Özellikleri
- **AI İçerik Üretimi**: Doğal dil promptları ile mimari tasarım önerileri
- **Layout Generasyonu**: Oda ve bina yerleşim planları oluşturma
- **Yapı Yönetmeliği Analizi**: Yerel/uluslararası yapı kodları ile uyumluluk kontrolü
- **Performans İzleme**: AI model çağrıları için performans takibi
- **Cache Yönetimi**: Sık kullanılan AI yanıtları için önbellekleme

## Kurulum ve Bağımlılıklar

```bash
# Gerekli Google Cloud SDK paketleri
pip install google-cloud-aiplatform vertexai google-auth

# Proje bağımlılıkları
pip install -r requirements.txt
```

## Konfigürasyon

### Çevre Değişkenleri
```bash
# Google Cloud Project ayarları
GOOGLE_CLOUD_PROJECT_ID=your-project-id
VERTEX_AI_LOCATION=us-central1

# Authentication
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
```

### Sınıf Konfigürasyonu
```python
from app.ai.vertex.client import VertexAIClient

client = VertexAIClient(
    project_id="your-project-id",
    location="us-central1"
)
```

## Ana Sınıflar ve Fonksiyonlar

### VertexAIClient Sınıfı
Vertex AI platformu ile iletişimi sağlayan ana sınıf.

#### Önemli Metodlar:

**generate_content()**
```python
async def generate_content(
    prompt: str,
    model: str = "gemini-2.5-flash-lite",
    temperature: float = 0.7,
    max_tokens: int = 1024
) -> Dict[str, Any]
```
- Genel AI içerik üretimi
- Giriş: prompt, model parametreleri
- Çıkış: AI yanıtı ve metadata

**generate_layout()**
```python
async def generate_layout(
    requirements: Dict[str, Any],
    building_type: str = "residential",
    constraints: Optional[Dict] = None
) -> Dict[str, Any]
```
- Mimari layout üretimi
- Giriş: tasarım gereksinimleri, bina tipi
- Çıkış: detaylı layout planı

**analyze_building_code()**
```python
async def analyze_building_code(
    project_data: Dict[str, Any],
    region: str = "turkey",
    regulations: List[str] = None
) -> Dict[str, Any]
```
- Yapı yönetmeliği uyumluluk analizi
- Giriş: proje verileri, bölge bilgisi
- Çıkış: uyumluluk raporu ve öneriler

## Kullanım Örnekleri

### Temel AI İçerik Üretimi
```python
from app.ai.vertex.client import VertexAIClient

client = VertexAIClient()

# Basit content generation
response = await client.generate_content(
    prompt="3 yatak odalı ev tasarla",
    temperature=0.8
)

print(response["content"])
```

### Layout Generasyonu
```python
# Oda layout'u oluşturma
layout_response = await client.generate_layout(
    requirements={
        "rooms": ["yatak odası", "salon", "mutfak", "banyo"],
        "total_area": 120,  # m²
        "floor_count": 1
    },
    building_type="residential"
)

layout_plan = layout_response["layout"]
```

### Yapı Yönetmeliği Kontrolü
```python
# Türkiye yapı yönetmeliği kontrolü
compliance_result = await client.analyze_building_code(
    project_data={
        "building_height": 15.5,  # metre
        "plot_ratio": 0.6,
        "building_type": "residential"
    },
    region="turkey"
)

if compliance_result["compliant"]:
    print("Proje yönetmeliklere uygun")
else:
    print("Uyumluluk sorunları:", compliance_result["issues"])
```

## Hata Yönetimi

### Yaygın Hatalar ve Çözümleri

**1. Authentication Hatası**
```python
# Hata: google.auth.exceptions.DefaultCredentialsError
# Çözüm: Service account key dosyasını ayarlayın
import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "path/to/key.json"
```

**2. Model Yanıt Hatası**
```python
# Hata: InvalidResponse
# Çözüm: Prompt formatını kontrol edin
try:
    response = await client.generate_content(prompt)
except Exception as e:
    logger.error(f"AI generation failed: {e}")
    # Fallback mekanizması
```

**3. Rate Limit Aşımı**
```python
# Hata: ResourceExhausted
# Çözüm: Retry mekanizması ve gecikme
import asyncio
await asyncio.sleep(1)  # 1 saniye bekle
```

## Performans Optimizasyonu

### Cache Kullanımı
```python
# Sık kullanılan promptlar için cache
@cache_result(expire_seconds=3600)
async def cached_generate_content(prompt: str):
    return await client.generate_content(prompt)
```

### Batch İşlemleri
```python
# Birden fazla layout için batch processing
layouts = await asyncio.gather(*[
    client.generate_layout(req) for req in layout_requests
])
```

## Güvenlik Notları

1. **API Key Güvenliği**: Service account anahtarlarını güvenli saklayın
2. **Input Validation**: Kullanıcı girişlerini doğrulayın
3. **Output Sanitization**: AI çıktılarını güvenlik için filtreleyin
4. **Rate Limiting**: API limitlerini aşmamaya dikkat edin

## İlgili Modüller

- `app.models.ai.ai_request`: AI istek/yanıt modelleri
- `app.core.performance`: Performans izleme
- `app.core.cache`: Cache yönetimi
- `app.core.config`: Konfigürasyon ayarları

## API Limitleri

- **Request/saniye**: 10 (varsayılan)
- **Max token/request**: 4096
- **Context window**: 32k tokens
- **Daily quota**: Proje ayarlarına bağlı

## Troubleshooting

### Debug Modunu Etkinleştirme
```python
import logging
logging.getLogger('vertexai').setLevel(logging.DEBUG)
```

### Yanıt Kalitesini Artırma
```python
# Daha detaylı promptlar kullanın
detailed_prompt = """
Görev: 3 yatak odalı ev tasarla
Gereksinimler:
- Total alan: 120m²
- Bütçe: Orta segment
- Lokasyon: İstanbul
- Aile profili: 4 kişi
- Özel istekler: Açık mutfak, geniş salon
"""
```

## Gelecek Geliştirmeler

- [ ] Multi-modal support (görsel + metin)
- [ ] Fine-tuned model desteği
- [ ] Real-time collaboration features
- [ ] Advanced building code database integration