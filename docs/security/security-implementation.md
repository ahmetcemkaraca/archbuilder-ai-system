# Güvenlik Katmanı Uygulaması Dokumentasyonu

## Genel Bakış
Bu belge, ArchBuilder.AI projesinin güvenlik katmanının nasıl uygulandığını ve yönetildiğini detaylandırmaktadır. Bu katman, kimlik doğrulama, yetkilendirme, şifre yönetimi, güvenlik middleware'leri ve denetim günlükleri gibi temel güvenlik mekanizmalarını içermektedir.

## Kurulum ve Bağımlılıklar
Güvenlik katmanı aşağıdaki Python kütüphanelerini kullanmaktadır:

```bash
pip install fastapi python-jose[cryptography] passlib[bcrypt] python-multipart uvicorn sqlalchemy asyncpg psycopg2-binary alembic structlog slowapi redis
```

## Kimlik Doğrulama ve Yetkilendirme Modülleri

### `src/cloud-server/app/security/authentication.py`
Bu modül, JWT (JSON Web Token) tabanlı erişim token'larının ve API anahtarlarının oluşturulması ve doğrulanmasından sorumludur. Ayrıca, kullanıcının e-posta ve parola ile kimlik doğrulamasını yapar ve mevcut kullanıcıyı `Depends` bağımlılığı aracılığıyla sağlar.

**Ana Fonksiyonlar:**
- `create_access_token`: JWT erişim token'ı oluşturur.
- `create_api_key`: Kullanıcıya özel bir API anahtarı oluşturur.
- `authenticate_user`: E-posta ve parola ile kullanıcı kimlik bilgilerini doğrular.
- `get_current_user`: JWT token veya API anahtarı kullanarak mevcut kullanıcıyı alır.
- `get_current_active_user`: Aktif mevcut kullanıcıyı kontrol eder.
- `get_current_active_admin`: Yönetici rolüne sahip aktif mevcut kullanıcıyı kontrol eder.
- `verify_subscription`: Kullanıcının aktif bir aboneliği olup olmadığını kontrol eder.

### `src/cloud-server/app/security/authorization.py`
Bu modül, rol tabanlı erişim kontrolünü (RBAC) uygular ve kullanıcıların belirli işlemleri gerçekleştirmek için gerekli rollere sahip olup olmadığını kontrol eden bağımlılıklar sağlar.

**Ana Fonksiyonlar:**
- `check_roles`: Belirtilen rollerden birine sahip olup olmadığını kontrol eden bir yetkilendirme bağımlılığı oluşturur.
- `is_admin`: Kullanıcının yönetici olup olmadığını kontrol eder.
- `is_architect`: Kullanıcının mimar olup olmadığını kontrol eder.
- `can_edit_project`: Kullanıcının belirli bir projeyi düzenleyip düzenleyemeyeceğini kontrol eder.

### `src/cloud-server/app/security/password.py`
Bu modül, kullanıcı şifrelerinin güvenli bir şekilde hash'lenmesi ve doğrulanması için yardımcı fonksiyonlar sağlar. `bcrypt` algoritması kullanılmaktadır.

**Ana Fonksiyonlar:**
- `get_password_hash`: Parolanın hash'ini oluşturur.
- `verify_password`: Düz metin parolayı hash'lenmiş parolayla doğrular.

## Güvenlik Middleware'leri

### `src/cloud-server/app/core/middleware.py`
Bu dosya, FastAPI uygulamasına entegre edilen çeşitli middleware'leri içerir. Bu middleware'ler, performansı izlemek, kaynak kullanımını denetlemek, korelasyon kimliklerini yönetmek, hız sınırlaması uygulamak ve güvenlik HTTP başlıkları eklemek için kullanılır.

**Eklenen Güvenlik Middleware'leri:**
- **`RateLimitingMiddleware`**: `slowapi` kütüphanesini kullanarak istemci IP adresine göre hız sınırlaması uygular. Aşırı istekleri engeller ve hizmet reddi (DoS) saldırılarına karşı koruma sağlar.
- **`SecurityHeadersMiddleware`**: Yanıtlara temel güvenlik HTTP başlıklarını (`X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`, `Referrer-Policy`, `Content-Security-Policy`, `X-Permitted-Cross-Domain-Policies`) ekler. Bu başlıklar, çeşitli web güvenlik açıklarını (örneğin, XSS, tıklama hırsızlığı) azaltmaya yardımcı olur.

## Kullanıcı ve Abonelik Yönetimi API'ları Güncellemesi

### `src/cloud-server/app/api/auth.py`
Bu dosyadaki `register`, `login`, `refresh`, `api-key` ve `me` gibi kimlik doğrulama ile ilgili API endpointleri, yeni güvenlik modüllerini kullanacak şekilde güncellenmiştir. Özellikle:
- Kullanıcı kaydı sırasında şifre hash'leme için `password.py` kullanılmıştır.
- Kimlik doğrulama sırasında `authentication.py` modülündeki `authenticate_user` fonksiyonu kullanılmıştır.
- `get_current_user`, `get_current_active_user` ve `verify_subscription` bağımlılıkları, API çağrılarında kullanıcı kimlik doğrulaması ve abonelik durumunu kontrol etmek için entegre edilmiştir.

### `src/cloud-server/app/api/billing.py`
Faturalandırma ile ilgili API endpointleri (`pricing-plans`, `customer`, `subscription/start`, `subscription/{subscription_id}`, `info`, `usage/track`, `usage/limits/{usage_type}`, `webhook`, `health`) de güncellenmiştir. Bu endpointler artık `get_current_active_user` ve `verify_subscription` bağımlılıklarını kullanarak kimliği doğrulanmış ve aktif aboneliği olan kullanıcılar için işlem yapmaktadır.

## Güvenlik Denetim Günlükleri

### `src/cloud-server/app/security/audit.py`
Bu modül, uygulama genelindeki önemli güvenlik olaylarını (kimlik doğrulama girişimleri, yetkilendirme kararları, hassas veri erişimleri ve sistem olayları) kaydetmek için kullanılır. Bu günlükler, güvenlik denetimleri ve adli analizler için kritik öneme sahiptir.

**Ana Fonksiyonlar:**
- `log_event`: Genel bir denetim olayını loglar.
- `log_authentication_event`: Kimlik doğrulama olaylarını loglar.
- `log_authorization_event`: Yetkilendirme olaylarını loglar.
- `log_data_access_event`: Hassas veri erişim olaylarını loglar.
- `log_system_event`: Sistemle ilgili olayları loglar.

## Sonuç
Bu güvenlik katmanı uygulaması, ArchBuilder.AI Cloud Server'ın güvenliğini sağlamak için çok katmanlı bir yaklaşım benimsemektedir. Kimlik doğrulama, yetkilendirme, güvenli iletişim ve kapsamlı denetim günlükleri ile sistem, yetkisiz erişime ve potansiyel tehditlere karşı korunmaktadır.

