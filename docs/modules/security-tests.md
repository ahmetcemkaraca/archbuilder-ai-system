# ArchBuilder.AI Güvenlik Test Sistemi Dokumentasyonu

## Genel Bakış
ArchBuilder.AI güvenlik test sistemi, STRIDE tehdit modeli temelinde kapsamlı güvenlik testleri gerçekleştiren bir test framework'üdür. Sistem, kimlik doğrulama, yetkilendirme, veri koruma ve sistem güvenliği konularında detaylı testler içerir.

## STRIDE Tehdit Modeli

### 🎭 Spoofing (Kimlik Sahtekarlığı) Koruması
- **JWT Token Doğrulama**: Geçerli token oluşturma ve doğrulama testleri
- **OAuth2 Entegrasyonu**: Harici kimlik sağlayıcıları ile güvenli entegrasyon
- **Token Süresi Denetimi**: Süresi dolmuş token'ların reddedilmesi
- **Multi-Factor Authentication**: Çok faktörlü kimlik doğrulama testleri

### 🔧 Tampering (Veri Bozma) Koruması  
- **Request İmza Doğrulama**: HMAC tabanlı istek imzalama sistemi
- **SQL Injection Koruması**: Parametreli sorgular ve input validation
- **Input Sanitization**: XSS ve diğer injection saldırılarına karşı koruma
- **Veri Bütünlüğü**: Kritik veriler için checksum kontrolü

### 📝 Repudiation (İnkar) Koruması
- **Audit Logging**: Tüm kullanıcı eylemlerinin kaydedilmesi
- **Digital Signatures**: Kritik operasyonlar için dijital imzalama
- **Immutable Logs**: Değiştirilemez denetim kayıtları
- **Non-Repudiation**: İnkar edilemez işlem kayıtları

### 🔒 Information Disclosure (Bilgi Sızıntısı) Koruması
- **Data Encryption at Rest**: Veritabanında şifrelenmiş veri saklama
- **HTTPS/TLS Enforcement**: Şifrelenmiş veri iletimi zorlaması
- **Tenant Data Isolation**: Çok kiracılı yapıda veri izolasyonu
- **PII Data Masking**: Kişisel verilerin maskelenmesi

### 🛡️ Denial of Service (Hizmet Reddi) Koruması
- **Rate Limiting**: API çağrı sınırlamaları
- **Request Size Limiting**: İstek boyutu kontrolü
- **Connection Limiting**: Eş zamanlı bağlantı sınırlamaları
- **Resource Monitoring**: Sistem kaynak izleme

### 🔐 Elevation of Privilege (Yetki Yükseltme) Koruması
- **Role-Based Access Control (RBAC)**: Rol tabanlı erişim kontrolü
- **Principle of Least Privilege**: En az yetki prensibi
- **Session Management**: Güvenli oturum yönetimi
- **API Key Validation**: Servis kimlik doğrulama

## Test Sınıfları ve Kapsamı

### TestSTRIDEThreatModel
Ana STRIDE test sınıfı ve güvenlik fixture'ları

### TestSpoofingPrevention
```python
# JWT Token testleri
test_jwt_token_validation()
test_invalid_jwt_token_rejection()
test_expired_token_rejection()
test_oauth2_authentication()
```

### TestTamperingPrevention  
```python
# Veri bütünlüğü testleri
test_request_signature_validation()
test_tampered_request_detection()
test_sql_injection_prevention()
test_input_validation_sanitization()
```

### TestRepudiationPrevention
```python
# Denetim ve kayıt testleri
test_audit_log_creation()
test_immutable_audit_logs()
test_digital_signatures()
```

### TestInformationDisclosurePrevention
```python
# Veri koruma testleri
test_data_encryption_at_rest()
test_data_encryption_in_transit()
test_tenant_data_isolation()
test_pii_data_masking()
```

### TestDenialOfServicePrevention
```python
# DoS koruma testleri
test_rate_limiting()
test_request_size_limiting()
test_connection_limiting()
test_resource_monitoring()
```

### TestElevationOfPrivilegePrevention
```python
# Yetki kontrolü testleri
test_role_based_access_control()
test_principle_of_least_privilege()
test_session_management()
test_api_key_validation()
```

## Kurulum ve Bağımlılıklar

```bash
# Güvenlik test bağımlılıkları
pip install pytest pytest-asyncio
pip install cryptography PyJWT bcrypt
pip install fastapi sqlalchemy
pip install structlog

# Test çalıştırma
cd src/cloud-server
pytest tests/test_security.py -v
```

## Konfigürasyon

### Çevre Değişkenleri
```bash
# Güvenlik ayarları
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENABLE_HTTPS_REDIRECT=true

# Test ortamı
TEST_DATABASE_URL=sqlite:///./test_security.db
ENABLE_AUDIT_LOGGING=true
```

### Test Konfigürasyonu
```python
# pytest.ini ayarları
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
asyncio_mode = auto
```

## Ana Güvenlik Modülleri

### SecurityManager
```python
from app.core.security import SecurityManager

security = SecurityManager()

# Request imzalama
signature = security.generate_request_signature(request_data)
is_valid = security.validate_request_signature(request_data, signature)

# Operasyon imzalama
op_signature = security.sign_operation(operation_data)
```

### TokenManager
```python
from app.core.security import TokenManager

token_manager = TokenManager()

# Token oluşturma
access_token = token_manager.create_access_token({"user_id": 1})
refresh_token = token_manager.create_refresh_token({"user_id": 1})

# Token doğrulama
payload = token_manager.verify_token(access_token)
```

### EncryptionService
```python
from app.core.encryption import EncryptionService

encryption = EncryptionService()

# Veri şifreleme
encrypted = encryption.encrypt("sensitive_data")
decrypted = encryption.decrypt(encrypted)

# Dosya şifreleme
encryption.encrypt_file("project.dwg", "project.dwg.encrypted")
```

## Kullanım Senaryoları

### 1. Kullanıcı Kimlik Doğrulama Testi
```python
async def test_user_authentication():
    # Geçerli kullanıcı girişi
    credentials = {"email": "user@archbuilder.ai", "password": "secure_pass"}
    result = await authenticate_user(credentials["email"], credentials["password"])
    assert result is not None
    assert result["email"] == credentials["email"]
```

### 2. API Güvenlik Testi
```python
async def test_api_security():
    # Rate limiting testi
    rate_limiter = RateLimiter(max_requests=5, window_seconds=60)
    client_ip = "192.168.1.100"
    
    # Normal kullanım
    for i in range(5):
        assert await rate_limiter.is_allowed(client_ip) == True
    
    # Limit aşımı
    assert await rate_limiter.is_allowed(client_ip) == False
```

### 3. Veri Şifreleme Testi
```python
async def test_data_encryption():
    encryption_service = EncryptionService()
    
    # Hassas veri şifreleme
    sensitive_data = "API_KEY_12345_SENSITIVE"
    encrypted = encryption_service.encrypt(sensitive_data)
    decrypted = encryption_service.decrypt(encrypted)
    
    assert encrypted != sensitive_data
    assert decrypted == sensitive_data
```

## Performans ve Güvenlik Benchmarkları

### Şifreleme Performansı
- **10KB veri şifreleme**: < 1 saniye
- **10KB veri şifre çözme**: < 1 saniye
- **Password hashing**: < 2 saniye (bcrypt)
- **JWT token doğrulama**: < 100ms

### Rate Limiting Performansı
- **İstek kontrolü**: < 10ms
- **Memory kullanımı**: < 1MB per 1000 client
- **Redis cache**: < 5ms (production ortamında)

## Güvenlik Raporlama

### Test Sonuçları
```bash
# Detaylı güvenlik testi
pytest tests/test_security.py -v --tb=short

# Coverage raporu
pytest tests/test_security.py --cov=app.core.security --cov-report=html
```

### Audit Log Analizi
```python
# Başarısız giriş denemeleri
failed_logins = audit_logger.get_failed_login_attempts(last_24_hours=True)

# Şüpheli aktiviteler
suspicious_activities = audit_logger.get_suspicious_activities()

# Güvenlik olayları
security_events = audit_logger.get_security_events(severity="high")
```

## Compliance ve Standartlar

### GDPR Uyumluluğu
- **Data Encryption**: Kişisel verilerin şifrelenmesi
- **Right to be Forgotten**: Veri silme mekanizmaları
- **Data Portability**: Veri dışa aktarma özellikleri
- **Consent Management**: Rıza yönetimi sistemleri

### ISO 27001 Uyumluluğu
- **Access Control**: Erişim kontrolü mekanizmaları
- **Incident Management**: Güvenlik olay yönetimi
- **Risk Assessment**: Risk değerlendirme süreçleri
- **Security Monitoring**: Güvenlik izleme sistemleri

## Troubleshooting

### Yaygın Güvenlik Sorunları

**1. Token Doğrulama Hatası**
```python
# Problem: Invalid token signature
# Çözüm: SECRET_KEY kontrolü
assert settings.SECRET_KEY is not None
```

**2. Rate Limiting Çalışmıyor**
```python
# Problem: Redis bağlantı hatası
# Çözüm: Redis konfigürasyonu
redis_client = redis.Redis(host='localhost', port=6379, db=0)
```

**3. Şifreleme Hatası**
```python
# Problem: Key generation error
# Çözüm: Cryptography paket kurulumu
pip install cryptography
```

## Gelecek Geliştirmeler

### Planned Security Features
- [ ] **Biometric Authentication**: Biyometrik kimlik doğrulama
- [ ] **Zero-Trust Architecture**: Sıfır güven mimarisi
- [ ] **AI-Based Threat Detection**: AI tabanlı tehdit tespiti
- [ ] **Blockchain Integration**: Blockchain tabanlı güvenlik
- [ ] **Quantum-Resistant Cryptography**: Kuantum dirençli şifreleme

### Security Monitoring
- [ ] **Real-time Security Dashboard**: Gerçek zamanlı güvenlik paneli
- [ ] **Automated Incident Response**: Otomatik olay müdahalesi
- [ ] **Security Analytics**: Güvenlik analitikleri
- [ ] **Compliance Reporting**: Uyumluluk raporlaması

Bu dokumentasyon, ArchBuilder.AI güvenlik test sisteminin kapsamlı bir rehberidir ve sürekli güncellenmektedir.