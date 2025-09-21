# Dynamo Documentation - RevitAutoPlan Integration Guide

## 📋 Overview

Bu doküman, Dynamo (2.x/3.x) ekosisteminden RevitAutoPlan için pratikte işe yarayacak bilgileri ve kullanım senaryolarını içerir. Amaç, AI tarafından üretilen geometrik/iş akışı kararlarının Dynamo ile otomasyonunu hızlandırmak ve Revit API işlemlerini güvenli bir şekilde tamamlamaktır.

- Last Updated: 2025-09-10 13:01:51
- Version: 1.0

## 🧩 Dynamo Temelleri

### 1) Çalışma Modu
- Dynamo Sandbox: Revit harici bağımsız çalışma
- Dynamo for Revit: Revit model bağlamında çalışma
- Dynamo Player: Önceden hazırlanmış grafikleri tek tık çalıştırma

Nerede kullanılır:
- AI üretilen komutları kullanıcıya parametreli olarak sunmak (Dynamo Player)
- Revit içi geometri ve veri manipülasyonu (Dynamo for Revit)

### 2) Workspace Türleri
- Home Workspace: Ana grafik çalışma alanı
- Custom Nodes (dyf): Yeniden kullanılabilir düğümler
- Packages: Topluluk paketleri (Clockwork, Springs, Archi-lab, Data-Shapes)

Nerede kullanılır:
- Tekrarlı AI komutlarını Custom Node olarak paketlemek
- İleri seviye UI/IO için Data-Shapes kullanmak

---

## 🔗 Revit ↔ Dynamo Bağlantısı

### Revit.Elements vs. Revit.DB
- Dynamo düğümleri genelde `Revit.Elements` tipleri döndürür (sarmalanmış).
- Revit API seviyesine inmek için `Element.InternalElement` ile `Autodesk.Revit.DB.Element` alınır.

Nerede kullanılır:
- AI’dan gelen element id’leriyle Revit DB üzerinde işlem yapma

```python
# Python Node - Revit DB elementine erişim
# IN[0]: Revit.Elements.Element (Dynamo)
wrapped = IN[0]
revit_db_elem = wrapped.InternalElement
OUT = revit_db_elem.Id.IntegerValue
```

### Transaction Yönetimi
- Dynamo otomatik transaction yönetir. Python/zerotouch içinde manual transaction açılmaz (aksi önerilmez).
- Büyük işlemlerde grafiği bölmek ve veri akışını azaltmak performansı artırır.

Nerede kullanılır:
- Çok adımlı AI yerleşiminde grafiği modüler tasarlamak

---

## 🧠 AI + Dynamo İş Akışları

### 1) Parametrik Duvar/Kapı/Pencere Oluşturma
- Giriş: Noktalar (XYZ), doğrular (Line), yükseklik, tip adları
- İşlem: `Walls.ByCurveAndLevel`, `FamilyInstance.ByPointAndLevel`

Nerede kullanılır:
- AI çıktılarını parametrik olarak üretmek ve görsel doğrulama yapmak

```pseudo
Lines -> WallType -> Level -> Walls.ByCurveAndLevel -> Walls[]
DoorType -> HostWall -> Param(Offset/Ratio) -> FamilyInstance.ByPointAndLevel -> Doors[]
```

### 2) Oda Sınırı ve Alan Kontrolü
- `Room.ByPoint` veya `Space` düğümleri
- Boundary extraction için paketler: Clockwork (Room.Boundaries)

Nerede kullanılır:
- AI planındaki oda alanı/sınır uygunluğunu hızlı kontrol etmek

### 3) Human-in-the-Loop İnteraktif Akışlar
- Data-Shapes paketinin `UI.MultipleInputForm++` ile kullanıcıdan parametre toplama

Nerede kullanılır:
- AI önerisini kullanıcı tercihi ile birleştirme (ör. kapı konumu, pencere sayısı)

---

## 📦 Önerilen Paketler ve Kullanım Alanları

- Clockwork: Element query, room/space işlemleri, parametre yönetimi
- Springs: Geometri yardımcıları, transform, direct shape işlemleri
- Archi-lab: Veri işleme, liste yönetimi, proje bilgileri
- Data-Shapes: Gelişmiş kullanıcı arayüzü formları (input/output)
- Rhythm: Family, view ve genel utility düğümleri

Nerede kullanılır:
- AI çıktısını Revit’e dönüştürürken hız ve görselleştirme avantajı

---

## 🧮 Geometri ve Dönüşümler

### Temel Tipler
- Point, Vector, Line, PolyCurve, Polygon, Surface, Solid

### Dönüşümler
- `Geometry.Translate/Rotate/Scale`
- `CoordinateSystem` ve `Transform` matrisleri

Nerede kullanılır:
- AI’dan gelen mm koordinatlarını Dynamo/Feet sistemine ve model koordinatına dönüştürmek

```python
# Python Node - mm -> feet
MM_TO_FEET = 0.0032808399
pts_mm = IN[0]  # [(x_mm, y_mm, z_mm), ...]
pts_xyz = [Point.ByCoordinates(x*MM_TO_FEET, y*MM_TO_FEET, z*MM_TO_FEET) for x,y,z in pts_mm]
OUT = pts_xyz
```

---

## 🧰 Parameter I/O ve Veri Yönetimi

### Parametre Okuma/Yazma
- `Element.GetParameterValueByName`
- `Element.SetParameterByName`

Nerede kullanılır:
- AI kararlarının (ör. `correlationId`, `requiresHumanReview`) element üzerine yazılması

### Veri Kaynağı Entegrasyonu
- CSV/Excel: `Data.ImportCSV`, `Data.ExportCSV`, `Excel.ReadFromFile`
- JSON: Python düğümü ile json serialize/deserialize

Nerede kullanılır:
- MCP Server ile veri alışverişi, audit kayıtları

---

## 🧩 Python Node İpuçları (Dynamo IronPython/CPython)

- IronPython (2.7) ve CPython (3.x) ortam farklılıklarına dikkat edin (Dynamo sürümüne göre).
- Revit API kullanımı için `RevitServices`, `Revit.Elements`, `RevitNodes` import edilmeli.
- UI freeze’i önlemek için ağır işlemleri parçalara bölün.

```python
# Python Node (örnek iskelet)
import clr
clr.AddReference('ProtoGeometry')
from Autodesk.DesignScript.Geometry import *

# Revit wrappers
clr.AddReference('RevitServices')
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager

clr.AddReference('RevitNodes')
import Revit
Revit.Elements

# Inputs
inputs = IN
# Processing ...
OUT = inputs
```

---

## ▶️ Dynamo Player Entegrasyonu

- Script parametrelerini `Input` nodeları ile dışa açın.
- Script’i paylaşılan bir klasörde tutarak ekip kullanımını kolaylaştırın.

Nerede kullanılır:
- AI → Human Review → Tek tık uygulanabilir script akışı

---

## 🧱 DirectShape ile Hızlı Görselleştirme

- AI taslağını DirectShape olarak modele basarak kullanıcıya hızlı önizleme sağlayın.
- Springs paketinde yardımcı düğümler bulunur; Python ile de yapılabilir.

Nerede kullanılır:
- İnteraktif onay öncesi prototip görüntüleme

---

## 🗺️ Koordinat Sistemleri ve Link’ler

- Linkli modellerde `RevitLinkInstance` transformunu Python düğümünde hesaba katın.
- `Transform.OfPoint` ile host koordinatına dönüşüm yapın.

Nerede kullanılır:
- Site/katmanlı projelerde AI’dan gelen mutlak/bağıl koordinatları yerelleştirmek

---

## 🔒 En İyi Güvenlik ve Stabilite Uygulamaları

- Parametre isimlerini doğrulayın; yoksa script fail vermesin (defensive checks).
- Paket sürümlerini pin’leyin; ekip içinde aynı versiyonları kullanın.
- Büyük listeleri parçalara ayırın; Watch nodelarını sınırlı kullanın.

---

## 🧭 RevitAutoPlan İş Akışında Dynamo’nun Yeri

1) AI (MCP) aşaması: Yerleşim verisi ve kurallar üretilir
2) Dynamo: Parametrik geometri oluşturur, hızla görselleştirir
3) Revit API: Nihai ve kalıcı BIM elemanları üretir, parametreleri yazar

Nerede kullanılır:
- Geometri yoğun işlemleri Dynamo’ya delege ederek Revit API tarafında daha temiz ve güvenli final oluşturmak

---

## 📚 Kaynaklar

- Dynamo Primer: https://primer.dynamobim.org/
- Dynamo Dictionary: https://dictionary.dynamobim.com/
- Dynamo Forum: https://forum.dynamobim.com/
- Package Manager: https://dynamopackages.com/

---

## ⚙️ Lacing & Levels (List Düzeyleri) – İleri Seviye List İşleme

### Lacing Modları
- **Shortest**: En kısa liste biter bitmez durur (varsayılan, güvenli)
- **Longest**: Eksik taraf son elemanla doldurulur (padding)
- **Cross Product**: Kartesyen çarpım; tüm kombinasyonlar (m×n)

Nerede kullanılır:
- Duvar x kapı kombinasyonları üretmek (Cross Product)
- Aynı uzunlukta eşleşen noktalarla çizgi üretmek (Shortest)

### Levels (Use Levels)
- Düğümün liste içi hangi seviyede çalışacağını belirler
- Derin listelerde (Rooms→Walls→Segments→Points) hedef seviyeye işlemek için kritik

Nerede kullanılır:
- Oda → sınır segmentleri → noktalar hiyerarşisinde yalnızca segment seviyesinde transform uygulamak

İpucu:
- Önce `Watch` ile veri derinliğini görün; sonra `Use Levels` ve `List.Map`/`List.Combine` ile hedef seviyeyi seçin.

---

## ✍️ DesignScript Hızlı Başvuru

### Temel Söz Dizimi
- Atama: `a = 10;`
- Fonksiyon: `def add(x:int, y:int=0) { return = x + y; }`
- Aralıklar (Ranges):
  - Adım: `0..10..2` → 0,2,4,6,8,10
  - Adet: `0..10..#5` → 5 eşit parçalı dizi
  - Ters: `10..0..-2` → 10,8,6,4,2,0

Nerede kullanılır:
- Pencere yerleşimlerini eşit aralıklı noktalarla üretmek

İleri:
- `List.Reduce`, `List.Accumulate`, `List.Transpose`, `List.GroupByKey`

---

## 🗂️ Gelişmiş List Operasyonları

- `List.Flatten(depth)`: Fazla iç içe listeleri sadeleştirme
- `List.Chop(lengths)`: Belirli uzunluklarda alt listelere bölme
- `List.FilterByBoolMask(mask)`: Mantıksal maske ile eleme
- `List.DropItems`, `List.TakeItems`: Pencere/kaydırma işlemleri

Nerede kullanılır:
- AI’dan gelen ham JSON’u katmanlara ayırıp ilgili seviyelerde işlemek

---

## 🔁 JSON Boru Hattı (AI → Dynamo → Revit)

Adımlar:
1) MCP’den JSON al (Python düğümü)
2) Şema doğrula (anahtarlar, tipler)
3) mm → feet dönüşümleri uygula
4) Points/Curves/Solids üret
5) Revit.Elements’e aktar ve/veya DirectShape ile önizle

Nerede kullanılır:
- AI yerleşiminin güvenli, izlenebilir ve tekrarlanabilir uygulanması

Hata Stratejisi:
- `try/except` ile `OUT = (False, message)` döndür; üst düğümlerde kullanıcıya göster

---

## 🐍 CPython 3 ve Paket Kullanımı (Dynamo 2.x/3.x)

- CPython 3, IronPython’dan farklı bir ortamdır; harici `pip` paketleri her zaman desteklenmeyebilir.
- Kurumsal ortamda internet/paket kurulumu kısıtlı olabilir.
- Mümkünse saf-Python bağımlılıkları yerel dosya olarak grafiğe dahil edin.

Nerede kullanılır:
- JSON işleme, küçük geometri yardımcıları, metin/CSV işlemleri

İpucu:
- Ağ/kimlik doğrulaması gerektiren istekleri RevitAutoPlan MCP sunucusu üzerinden yapın; Dynamo tarafını ince tutun.

---

## 🧱 ZeroTouch & Custom Nodes (C#) – Özet

- C# ile özel Dynamo düğümleri yazılabilir (ZeroTouch)
- Avantaj: Performans, tip güvenliği, tek noktadan dağıtım
- Dezavantaj: Derleme ve paketleme süreci gerekir

Nerede kullanılır:
- Çok kullanılan, performans kritik geometri/parametre operasyonları

Dağıtım:
- `dyf` (Custom Node) veya `dll` (ZeroTouch) + `pkg.json` ile paketleyip ekip içinde sürümleyin.

---

## 📘 Graf Tarifleri (Cookbook)

1) Dış Duvar Zarfı (Rect/Kenar Noktalarından)
- Girdi: Bina genişlik/derinlik (m), duvar yüksekliği (mm)
- Çıktı: 4 çizgi → `Walls.ByCurveAndLevel`

2) Kapıları Eşit Aralıklarla Yerleştir
- Girdi: Host duvar(lar), adet veya oran listesi
- Çıktı: `FamilyInstance.ByPointAndLevel`

3) Pencereleri Cephe Boyunca Dağıt
- Girdi: Cephe uzunluğu, açıklık adedi, kotlar
- Çıktı: Pencere FamilyInstance listesi

4) Oda Sınırı ve Alan Kontrolü
- Girdi: Çokgen sınır noktaları
- Çıktı: `Room.ByPoint` ve BoundarySegments analizi

5) Koridor Genişliği Denetimi
- Girdi: Koridor polikurve, minimum genişlik
- Çıktı: Uyarı listesi (Data-Shapes UI)

6) Doğrulama Raporu (CSV/Excel)
- Girdi: İhlaller
- Çıktı: `Data.ExportCSV` veya `Excel.WriteToFile`

---

## 🧪 QA: Grafik Test Edilebilirliği

- Giriş/çıkış örneklerini `*.json`/CSV ile versiyonlayın
- Watch çıktılarının hash’ini alarak regresyon kontrolü
- Paket sürümlerini `pkg.json` ile sabitleyin

Nerede kullanılır:
- CI’de otomatik grafik doğrulama (gelişmiş senaryolarda Design Automation for Revit)

---

## 🖥️ Headless/CLI Çalıştırma Notları

- Dynamo CLI, yalnızca Core/Sandbox düğümlerini çalıştırabilir
- Revit düğümleri Revit bağlamı ister; headless için Design Automation for Revit veya otomasyon araçlarını araştırın

Nerede kullanılır:
- Rapor üretimi ve geometri ön-hazırlığı gibi Revit’e bağlı olmayan işler

---

## ▶️ Player Parametre Konvansiyonları

- Giriş düğümlerine anlamlı ad verin (ör. `Rooms JSON`, `Wall Height (mm)`)
- Türler: Number, String, Boolean, File Path, Directory, Dropdown
- Varsayılanları güvenli seçin; birim/formatı adın içinde belirtin

Nerede kullanılır:
- Mimara tek tıkla çalıştırılabilir AI → Dynamo uygulamaları

---

## 🧭 Data-Shapes Gelişmiş Kullanım

- Çok adımlı formlar, doğrulamalar, yardım metinleri
- Kullanıcı seçimlerini Revit Selection ile entegre etme

Nerede kullanılır:
- Human-in-the-loop: Kapı yerleri, pencere adedi, stil tercihleri

---

## 🧯 Troubleshooting – Sık Hatalar

- "Family not found": Family yükleyin ve `FamilySymbol.Activate()`
- "Curve is too short/zero length": mm/feet dönüşümlerini kontrol edin
- "Null element": Revit.Elements ↔ Revit.DB dönüşümü yapın (InternalElement)
- "Graph slow": Freeze/Disable Preview, kolektörleri yeniden kullanın

---

## 🚀 Performans El Kitabı

- Preview’u ağır düğümlerde kapatın, gerektiğinde `Freeze`
- Watch düğümlerini minimumda tutun
- Grafik üçe bölün: (Girdi) → (Geometri) → (Yerleştirme)
- Büyük listelerde `List.Chop` ile parçalı işlem

---

## 🔐 Güvenlik & Tekrarlanabilirlik

- API anahtarlarını asla grafikte saklamayın; MCP üzerinden yönetin
- Paket ve grafik sürümlerini kilitleyin; değişiklikleri `CHANGELOG` ile izleyin
- Loglarda kullanıcı girdilerini anonimleştirin (hash)

---

## 🗺️ RevitAutoPlan Eşleştirme Tablosu (Özet)

| İhtiyaç | Dynamo Çözümü | Nerede Kullanılır |
|---|---|---|
| AI JSON → Geometri | Python Node + DesignScript | Yerleşim prototipi, önizleme |
| Hızlı doğrulama | Clockwork Room/Boundary | Minimum alan/koridor kontrolü |
| İnsan onayı | Data-Shapes Form | Parametreli yerleşim kararı |
| Kitle yerleşim | Lacing Cross Product | Kapı/pencere dağıtımı |
| Raporlama | CSV/Excel | İhlal/özet raporları |
| Revit yerleştirme | Walls/FamilyInstance | Nihai BIM üretimi |

---

## 🔄 Element Binding (Trace) ve Yinelenen Oluşturmayı Önleme

- Dynamo, bazı düğümler için üretilen Revit elemanlarını “Trace” ile hatırlar.
- Aynı girdilerle tekrar çalıştırınca mevcut elemanları günceller; kopya oluşturmaz.

Nerede kullanılır:
- AI yerleşimi tekrarlandığında duvar/kapıların kopyalanmasını önlemek.

İpucu:
- Girdi kimliklerini stabil tutun (ör. `correlationId`), önemli parametre değişirse yeni üretim makuldür.

---

## 🏃 Çalıştırma Modu: Automatic / Manual / Periodic

- Automatic: Küçük grafiklerde hızlı iterasyon
- Manual: Büyük grafiklerde performans ve kontrol
- Periodic: Zamanlayarak çalıştırma (demo/izleme)

Nerede kullanılır:
- AI → İnsan onayı → Manual; küçük düzeltmelerde Automatic

---

## 📝 Grafik Dokümantasyonu ve Organizasyon

- Notes/Groups ile açıklama ve renk kodu
- Giriş/çıkış nodelarını tek bölgede toplayın
- Alt akışları Custom Node’a taşıyın

Nerede kullanılır:
- Ekip paylaşımlarında anlaşılabilirlik ve bakım kolaylığı

---

## 🧾 JSON Şema Doğrulama (Python 3)

```python
import json

def validate_layout(payload: dict) -> tuple[bool,str]:
    required = ["walls","rooms"]
    for k in required:
        if k not in payload:
            return False, f"Missing key: {k}"
    return True, "ok"

data = json.loads(IN[0])
ok,msg = validate_layout(data)
OUT = ok, msg
```

Nerede kullanılır:
- MCP’den gelen AI JSON’unu hızlı ön-kontrolden geçirmek

---

## 🧠 Adjacency → Oda Grafı (Örnek Patern)

Adımlar:
1) Oda isimleri ve adjacencies → komşuluk listesi
2) Çakışma kontrolü → hatalı eşleşmeleri raporla
3) Kapı konum adayları → oran tabanlı noktalar
4) Önizleme (DirectShape) → İnsan onayı

Nerede kullanılır:
- AI’nin önerdiği komşuluk kararlarını görselleştirme ve düzeltme

---

## 🧪 Dynamo Graph Test Pratikleri

- Sabit giriş JSON’ları ile çıktı hash’i karşılaştır
- Kritik nodelar için küçük örnek grafikleri ayrı test et

Nerede kullanılır:
- Geriye dönük uyumluluğu ve paket güncellemelerini güvenle almak

---

## 🛡️ Gizlilik ve Ekip Kullanımı

- Kullanıcı verilerini anonimleştirin (hash); kişisel verileri grafiğe yazmayın
- Paket ve grafik versiyonlarını kilitleyin; changelog tutun



