# Revit API Documentation - RevitAutoPlan Integration Guide

## 📋 Overview

Bu doküman RevitAutoPlan projesi için Revit API 2026 dokümanlarından çıkarılan kritik bilgileri içerir. Proje geliştirme sürecinde Revit API entegrasyonu için referans kaynağı olarak kullanılacaktır.

## 🔧 Revit API 2026 - Major Changes

### ⚠️ Critical Changes for Add-in Development

#### 1. **CefSharp Removal**
- **Impact**: Tüm Revit CefSharp bağımlılıkları kaldırıldı
- **Action Required**: Add-in'lerin kendi CefSharp bağımlılıklarını yönetmesi gerekiyor
- **Risk**: Assembly version conflicts hala mümkün

#### 2. **Add-in Dependency Isolation** ⭐ **CRITICAL FOR REVITAUTOPLAN**
- **New Feature**: Add-in'lerin ayrı Assembly load context'te çalışması
- **Benefit**: Assembly version conflicts'lerin azalması/eliminasyonu
- **Implementation**: Manifest'te `UseRevitContext="False"` ayarı

```xml
<?xml version="1.0" encoding="utf-8"?>
<RevitAddIns>
  <AddIn Type="DBApplication">
    <Name>RevitAutoPlan</Name>
    <FullClassName>RevitAutoPlan.Application</FullClassName>
    <Assembly>RevitAutoPlan.dll</Assembly>
    <ClientId>C96B32A3-98C6-4B47-99DA-562E64689C6F</ClientId>
    <VendorId>RevitAutoPlan</VendorId>
  </AddIn>
  <ManifestSettings>
    <UseRevitContext>False</UseRevitContext>
    <ContextName>RevitAutoPlanContext</ContextName>
  </ManifestSettings>
</RevitAddIns>
```

#### 3. **Parameter API Changes**
- **Classification Codes**: BuiltInParameter değerleri yeniden adlandırıldı
- **Assembly Codes**: UI değişiklikleriyle uyumlu hale getirildi

## 🏗️ Core Revit API Namespaces

### Essential Namespaces for RevitAutoPlan

| Namespace | Purpose | Usage in RevitAutoPlan |
|-----------|---------|------------------------|
| `Autodesk.Revit.DB` | Core database operations | Element creation, geometry, transactions |
| `Autodesk.Revit.UI` | User interface | Ribbon panels, commands, dialogs |
| `Autodesk.Revit.ApplicationServices` | Application management | Startup/shutdown, document events |
| `Autodesk.Revit.Creation` | Element creation | Walls, doors, windows, rooms |
| `Autodesk.Revit.DB.Architecture` | Architectural elements | Room boundaries, space planning |
| `Autodesk.Revit.DB.Structure` | Structural elements | Load-bearing walls, structural analysis |
| `Autodesk.Revit.DB.Events` | Event handling | Document changes, element modifications |
| `Autodesk.Revit.Exceptions` | Error handling | Custom exception management |

### Specialized Namespaces

| Namespace | Purpose | Usage |
|-----------|---------|-------|
| `Autodesk.Revit.DB.Analysis` | Analysis tools | Energy analysis, lighting |
| `Autodesk.Revit.DB.IFC` | IFC import/export | BIM interoperability |
| `Autodesk.Revit.DB.PointClouds` | Point cloud data | Site analysis |
| `Autodesk.Revit.DB.Visual` | Visualization | 3D rendering, materials |

## 🎯 Key API Commands for RevitAutoPlan

### Document Management
- **NewProject**: Yeni Revit projesi oluşturma
- **OpenCloudModel**: Cloud model açma
- **OpenIFC**: IFC dosyası açma

### Element Creation Commands
- **Wall Creation**: Duvar oluşturma
- **Door Placement**: Kapı yerleştirme
- **Window Placement**: Pencere yerleştirme
- **Room Creation**: Oda tanımlama
- **Offset**: Elementleri offset'leme

### Architectural Tools
- **ObjectStyles**: Line weights, colors, patterns
- **NoteBlock**: Annotation scheduling
- **OneWayIndicator**: Direction annotations

## 🔧 RevitAutoPlan Integration Requirements

### 1. **Transaction Management** ⭐ **CRITICAL**
```csharp
// Required pattern for all Revit operations
using (var transaction = new Transaction(doc, "RevitAutoPlan Operation"))
{
    try
    {
        transaction.Start();
        // Revit API operations
        transaction.Commit();
        return Result.Succeeded;
    }
    catch (Exception ex)
    {
        transaction.RollBack();
        return Result.Failed;
    }
}
```

### 2. **Element Creation Patterns**
```csharp
// Wall creation with validation
public Wall CreateWallSafely(Curve centerLine, WallType wallType, Level level)
{
    ValidateInputs(centerLine, wallType, level);
    var wall = Wall.Create(doc, centerLine, wallType.Id, level.Id, false);
    return wall ?? throw new ElementCreationException();
}
```

### 3. **Efficient Element Filtering**
```csharp
// Performance-optimized element collection
var walls = new FilteredElementCollector(doc)
    .OfClass(typeof(Wall))
    .OfCategory(BuiltInCategory.OST_Walls)
    .OfType<Wall>()
    .Where(w => w.WallType.Id == targetTypeId)
    .ToList();
```

## 🚨 Critical Warnings for RevitAutoPlan

### ⚠️ **MANDATORY REVIT API STUDY REQUIRED**
RevitAutoPlan projesi için **mutlaka** aşağıdaki konular derinlemesine incelenmelidir:

1. **Revit API Threading Model**
   - UI thread vs. background thread operations
   - External events handling
   - Async operations in Revit context

2. **Element Lifecycle Management**
   - Element creation and deletion
   - Parameter modification
   - Family and type management

3. **Document and Transaction Management**
   - Transaction boundaries
   - Document locking
   - Undo/redo considerations

4. **Memory Management**
   - Element references and disposal
   - Large model handling
   - Performance optimization

5. **Error Handling and Recovery**
   - Revit-specific exceptions
   - Transaction rollback scenarios
   - User notification patterns

## 📚 Recommended Learning Resources

### Official Documentation
- [Revit API 2026 Reference Guide](https://www.revitapidocs.com/2026/)
- [Revit API Developer Center](https://www.autodesk.com/developer-network/platform-technologies/revit-api)

### Key Topics for RevitAutoPlan Team
1. **Element Creation and Modification**
2. **Geometric Operations and Transformations**
3. **Parameter Management**
4. **Family and Type System**
5. **Document Events and Lifecycle**
6. **Performance Optimization**
7. **Error Handling Patterns**

## 🔄 Integration with RevitAutoPlan Architecture

### C# Plugin Layer
- **Namespace**: `src/revit-plugin/`
- **API Usage**: Direct Revit API calls
- **Responsibilities**: 
  - Element creation
  - UI interaction
  - Transaction management
  - Error handling

### Python MCP Server Layer
- **Namespace**: `src/mcp-server/`
- **API Usage**: Indirect through C# plugin
- **Responsibilities**:
  - AI processing
  - Data validation
  - Business logic
  - External API calls

### Communication Protocol
- **MCP Protocol**: Revit Plugin ↔ MCP Server
- **Data Format**: JSON with Revit element definitions
- **Error Handling**: Structured error responses

## 📋 Action Items for RevitAutoPlan Development

### Immediate Actions Required
1. **Revit API Study**: Team members must study Revit API fundamentals
2. **Development Environment**: Set up Revit 2026 SDK
3. **Test Project**: Create simple Revit add-in for testing
4. **Error Handling**: Implement comprehensive Revit exception handling
5. **Performance Testing**: Test with large Revit models

### Development Phases
1. **Phase 1**: Basic element creation (walls, doors, windows)
2. **Phase 2**: Advanced geometry operations
3. **Phase 3**: Parameter management and customization
4. **Phase 4**: Performance optimization and large model support
5. **Phase 5**: Advanced features and integrations

## 🎯 Success Criteria

### Technical Requirements
- ✅ All Revit operations wrapped in transactions
- ✅ Comprehensive error handling
- ✅ Memory leak prevention
- ✅ Performance optimization for large models
- ✅ User-friendly error messages

### Quality Assurance
- ✅ Unit tests for all Revit operations
- ✅ Integration tests with real Revit models
- ✅ Performance benchmarks
- ✅ Error scenario testing
- ✅ User acceptance testing

---

**⚠️ CRITICAL NOTE**: Bu doküman RevitAutoPlan projesi için temel referans kaynağıdır. Tüm Revit API entegrasyonları bu dokümandaki patterns ve warnings'e uygun olarak geliştirilmelidir.

**📅 Last Updated**: 2025-01-10
**🔄 Version**: 1.0
**👥 Target Audience**: RevitAutoPlan Development Team

## 🆕 İleri Konular (Devam)

### 19) Uygulama ve Doküman Olayları (Events)
- Application: `Application.DocumentOpened`, `DocumentClosed`, `FailuresProcessing` vb.
- Document: `DocumentChanged`, `ViewPrinted`, `ViewActivated` vb.

Nerede kullanılır:
- İnsan onayı sonrası değişiklikleri yakalayıp loglamak; otomatik doğrulama tetiklemek.

```csharp
public Result OnStartup(UIControlledApplication a)
{
    a.ControlledApplication.DocumentOpened += OnOpened;
    a.ControlledApplication.DocumentChanged += OnChanged;
    return Result.Succeeded;
}

private void OnOpened(object sender, DocumentOpenedEventArgs e)
{
    Log.Information("Document opened {Name}", e.Document.Title);
}

private void OnChanged(object sender, DocumentChangedEventArgs e)
{
    var ids = e.GetModifiedElementIds();
    // Değişiklikleri denetim izine ekle
}
```

---

### 20) ElementTransformUtils – Taşı/Döndür/Kopyala/Ayna
- `MoveElement`, `RotateElement`, `CopyElement`, `MirrorElements`

Nerede kullanılır:
- AI önerisindeki küçük düzeltmeleri kullanıcı etkileşimiyle güvenli şekilde uygulamak.

```csharp
ElementTransformUtils.MoveElement(doc, wall.Id, new XYZ(1,0,0));
ElementTransformUtils.RotateElement(doc, wall.Id, Line.CreateBound(p1,p2), Math.PI/2);
```

---

### 21) Sketch Tabanlı Elemanlar (Floor/Roof/Opening)
- Sınır eğrileri: `CurveArray`/`IList<Curve>`; oluşturma: `Floor.Create`, `FootPrintRoof.Create`

Nerede kullanılır:
- AI’nın bina zarfı/kat planı sınırlarından döşeme/çatı üretmek.

```csharp
IList<Curve> boundary = new List<Curve>{ l1,l2,l3,l4 };
Floor floor = Floor.Create(doc, boundary, floorType.Id, level.Id);
```

---

### 22) Boyutlar ve Kısıtlar (Dimensions/Constraints)
- `Dimension.Create` ile ölçülendirme; `Parameter.Set` + `IsReadOnly`
- `Lock`/`Equality` kısıtları için referanslar üzerinden kural

Nerede kullanılır:
- Minimum koridor genişliği gibi kuralları görünür ve kalıcı hale getirmek.

---

### 23) Parametre Filtreleri ve Görünüm Filtreleri
- `ParameterFilterElement` ile görünümde koşullu renklendirme

Nerede kullanılır:
- İnsan incelemesi için “AI üretilen” elemanları renkle vurgulamak.

```csharp
var rules = new List<FilterRule>{ rule1 };
var pfe = ParameterFilterElement.Create(doc, "AI Elements", new List<ElementId>{ catId }, rules);
view.AddFilter(pfe.Id);
view.SetFilterOverrides(pfe.Id, ogs);
```

---

### 24) Regeneration ve Performans
- `doc.Regenerate()` yalnızca gerektiğinde çağrılmalı
- `Transaction` içinde toplu değişiklik → tek seferde regenerate

Nerede kullanılır:
- 500ms API hedefi ve 30sn yerleşim hedefi için kritik.

---

### 25) View/Sheet/Print
- Sheet oluşturma: `ViewSheet.Create`
- Görünüm yerleştirme: `Viewport.Create`
- Yazdırma setleri ve `PrintManager`

Nerede kullanılır:
- AI planlarının QA için sayfa düzeni ve PDF çıktısı.

---

### 26) Worksharing – Sahiplik ve Erişim
- `WorksharingUtils.GetCheckoutStatus`
- Hata: “not editable” → kullanıcıya kilit/sahiplik uyarısı

Nerede kullanılır:
- Çok kullanıcılı projelerde AI otomasyonunun çakışmaları önlemesi.

---

### 27) Kategoriler ve BuiltInCategory Eşlemesi
- Tip/kategori doğrulaması; yanlış kategoride eleman yerleşimini önleme

Nerede kullanılır:
- AI’nın tip adı üretimine rağmen doğru Revit kategorisini zorlamak.

---

### 28) Güvenli Silme ve Geri Alma
- `doc.Delete(elementId)` → bağımlı eleman etkileri
- Büyük silmelerde önce önizleme/DirectShape ile kullanıcı onayı al

---

### 29) API Çağrı Koruma Kalıpları (Guards)
- Null/invalid referans kontrolleri, birim dönüşümü doğrulamaları
- Try-catch + `RevitAPIExceptions` ayrımı

Nerede kullanılır:
- AI belirsizliği durumunda stabiliteyi korumak.

## 📘 Gelişmiş Revit API Konuları (+ Nerede Kullanılır)

### 1) UIApplication / UIDocument / Document Nesne Modeli
- `UIApplication`: Revit uygulama kapsamı (UI seviyesinde). Add-in başlangıcı, Ribbon kurulumları.
- `UIDocument`: Aktif UI dokümanı (seçim, aktif görünüm, kullanıcı etkileşimi).
- `Document`: Model veritabanı (element oluşturma/değiştirme/okuma).

Nerede kullanılır:
- AI ile üretilen komutları uygularken `UIDocument.Document` üzerinden değişiklik yapmak.
- İnsan onayı sonrası kullanıcı seçimlerini almak için `UIDocument.Selection`.

```csharp
public Result Execute(ExternalCommandData data, ref string message, ElementSet elements)
{
    UIApplication uiApp = data.Application;
    UIDocument uiDoc = uiApp.ActiveUIDocument;
    Document doc = uiDoc.Document;
    // ... doc üzerinde işlemler
    return Result.Succeeded;
}
```

---

### 2) İleri Seviye Transaction Yönetimi (TransactionGroup, SubTransaction, Failures)
- `TransactionGroup`: Birden çok işlemi tek “undo” adımı altında toplar.
- `SubTransaction`: Aynı Transaction içinde küçük, geri alınabilir adımlar.
- `IFailuresPreprocessor`: Otomatik hata/uyarı işleme (örn. uyarıları gizlemek, hatayı düzeltmek).

Nerede kullanılır:
- AI’nin ürettiği birden fazla adımı tek seferde uygulayıp gerekirse topluca geri almak.
- Geometri kesişmeleri gibi bilinen uyarıları otomatik bastırmak.

```csharp
using (var tg = new TransactionGroup(doc, "AutoPlan Batch"))
{
    tg.Start();
    using (var t = new Transaction(doc, "Walls"))
    {
        t.Start();
        // Duvarlar oluştur
        t.Commit();
    }
    using (var t2 = new Transaction(doc, "Doors"))
    {
        t2.Start();
        // Kapılar oluştur
        t2.Commit();
    }
    tg.Assimilate(); // Tek undo adımı
}
```

Basit Failure handler:
```csharp
class SilentWarnings : IFailuresPreprocessor
{
    public FailureProcessingResult PreprocessFailures(FailuresAccessor a)
    {
        foreach (var f in a.GetFailureMessages()) a.DeleteWarning(f);
        return FailureProcessingResult.Continue;
    }
}
```

---

### 3) Seçim ve Referanslar (Selection, ISelectionFilter, Reference)
- `UIDocument.Selection.PickObject(s)`: Kullanıcıdan tek/çok seçim.
- `ISelectionFilter`: Kategori/sınıf bazlı seçim kısıtı.
- `Reference`: Seçilen geometri/elemanın referansı (yüz, kenar, nokta).

Nerede kullanılır:
- İnsan-in-the-loop düzeltmelerde kullanıcıya belirli elemanları seçtirmek.

```csharp
class WallOnlyFilter : ISelectionFilter
{
    public bool AllowElement(Element e) => e is Wall;
    public bool AllowReference(Reference r, XYZ p) => true;
}

Reference r = uiDoc.Selection.PickObject(ObjectType.Element, new WallOnlyFilter(), "Select a wall");
Element e = doc.GetElement(r);
```

---

### 4) FilteredElementCollector – Performanslı Filtreleme
- Önce hızlı filtreler: `.OfClass()`, `.OfCategory()`
- Sonra parametre filtreleri: `ElementParameterFilter` + `FilterRule`
- Mantıksal filtreler: `LogicalAndFilter`, `LogicalOrFilter`

Nerede kullanılır:
- AI çıktısındaki tip adlarına göre mevcut türleri bulup eşlemek.

```csharp
var collector = new FilteredElementCollector(doc)
    .OfClass(typeof(WallType))
    .OfCategory(BuiltInCategory.OST_Walls);

var provider = new ParameterValueProvider(new ElementId(BuiltInParameter.ALL_MODEL_TYPE_NAME));
var rule = new FilterStringRule(provider, new FilterStringEquals(), "Generic - 200mm", true);
var paramFilter = new ElementParameterFilter(rule);

var wallType = collector.WherePasses(paramFilter).Cast<WallType>().FirstOrDefault();
```

---

### 5) Parametreler ve Birimler (StorageType, UnitUtils, SpecTypeId)
- `Parameter.StorageType`: Double (feet), Integer, String, ElementId.
- `UnitUtils` ve `SpecTypeId`: Modern birim sistemi (Revit 2021+).
- String ile set: `SetValueString()`; sayısal ile set: `Set(double)`.

Nerede kullanılır:
- AI çıktısındaki mm/m² değerlerini Revit iç birimine (feet) dönüştürüp yazmak.

```csharp
double heightMm = 2700;
double heightFeet = UnitUtils.ConvertToInternalUnits(heightMm, UnitTypeId.Millimeters);
Parameter p = wall.get_Parameter(BuiltInParameter.WALL_USER_HEIGHT_PARAM);
p.Set(heightFeet);
```

---

### 6) Geometri API (Solid/Face/Edge, Intersections, Boole)
- `Options` ile yüksek doğruluklu geometri çıkarımı.
- `SolidCurveIntersectionOptions`, `BooleanOperationsUtils` ile kesişimler/booleanlar.

Nerede kullanılır:
- AI planındaki oda sınırlarının geçerli ve çakışmasız olduğunun kontrolü.

```csharp
Options opt = new Options { ComputeReferences = true, DetailLevel = ViewDetailLevel.Fine };
GeometryElement g = wall.get_Geometry(opt);
foreach (var obj in g)
{
    Solid solid = obj as Solid;
    if (solid != null && solid.Volume > 0)
    {
        // Solid ile analiz
    }
}
```

---

### 7) Family API (Load, Activate, Place)
- `FamilySymbol` yükleme/aktivasyon sonrası yerleştirme gerekir.
- Yerleştirme: `doc.Create.NewFamilyInstance(XYZ, symbol, level, StructuralType.NonStructural)`.

Nerede kullanılır:
- AI kapı/pencere türlerini projeye yükleyip doğru seviyede yerleştirmek.

```csharp
FamilySymbol sym = familySymbol;
if (!sym.IsActive) sym.Activate();
doc.Create.NewFamilyInstance(new XYZ(10,0,0), sym, level, StructuralType.NonStructural);
```

---

### 8) Odalar ve Sınırlar (Rooms, SpatialElementBoundary)
- Oda oluşturma: `doc.Create.NewRoom(level, location)`.
- Sınır alma: `room.GetBoundarySegments(new SpatialElementBoundaryOptions())`.

Nerede kullanılır:
- AI ürettiği oda yerleşimini gerçek oda nesneleri olarak oluşturmak ve alan kontrollleri.

```csharp
var opts = new SpatialElementBoundaryOptions();
IList<IList<BoundarySegment>> loops = room.GetBoundarySegments(opts);
// Segmentlerden çevre uzunluğu/alan kontrolü yapılabilir
```

---

### 9) Görünümler ve Grafik (ViewPlan, View3D, Overrides)
- Görünüm oluşturma: `ViewPlan.Create`, `View3D.CreateIsometric`.
- Grafik üzerine yazma: `OverrideGraphicSettings` ile renk/çizgi kalınlığı.

Nerede kullanılır:
- İnsan incelemesi için AI çıktısını vurgulu renklerle gösteren özel görünüm.

```csharp
var vft = new FilteredElementCollector(doc).OfClass(typeof(ViewFamilyType))
    .Cast<ViewFamilyType>().First(x => x.ViewFamily == ViewFamily.FloorPlan);
ViewPlan plan = ViewPlan.Create(doc, vft.Id, level.Id);

var ogs = new OverrideGraphicSettings();
ogs.SetProjectionLineColor(new Color(255, 0, 0));
plan.SetElementOverrides(wall.Id, ogs);
```

---

### 10) Linkler ve Transformlar (RevitLinkInstance)
- Link dokümanı: `link.GetLinkDocument()`
- Koordinat dönüşümü: `link.GetTotalTransform()`

Nerede kullanılır:
- Harici referans (DWG/IFC/Revit link) koordinatlarında AI yerleşimlerini ana modele çevirmek.

```csharp
var link = new FilteredElementCollector(doc).OfClass(typeof(RevitLinkInstance))
    .Cast<RevitLinkInstance>().FirstOrDefault();
Transform t = link.GetTotalTransform();
XYZ hostPoint = t.OfPoint(linkPoint);
```

---

### 11) External Events & Idling – Modeless UI ile Güvenli İşlem
- `ExternalEvent` modeless pencereden güvenli Revit çağrısı.
- `Idling` olayında uzun işlemleri parçalara bölmek.

Nerede kullanılır:
- AI işlem ilerleme penceresi açıkken model değişikliklerini güvenli tetiklemek.

```csharp
public class DoModelChange : IExternalEventHandler
{
    public void Execute(UIApplication app)
    {
        var doc = app.ActiveUIDocument.Document;
        using (var t = new Transaction(doc, "Change")) { t.Start(); /* ... */ t.Commit(); }
    }
    public string GetName() => "DoModelChange";
}
// UI tarafında: ExternalEvent.Create(new DoModelChange())
```

---

### 12) Updater API (IUpdater) – Otomatik Kısıt/Doğrulama
- Modelde belirli değişiklikleri yakalayıp kural çalıştırma.

Nerede kullanılır:
- Kullanıcı manuel düzenleme yapsa bile AI kurallarının korunması (örn. kapı minimum genişliği).

```csharp
class MinDoorWidthUpdater : IUpdater
{
    public void Execute(UpdaterData data)
    {
        var doc = data.GetDocument();
        foreach (var id in data.GetModifiedElementIds())
        {
            var door = doc.GetElement(id) as FamilyInstance;
            // kapı genişliği kontrolü
        }
    }
    public string GetUpdaterName() => "MinDoorWidth";
    public UpdaterId GetUpdaterId() => new UpdaterId(new Guid("11111111-2222-3333-4444-555555555555"), new Guid("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"));
}
```

---

### 13) DirectShape – Özel Geometri Basma
- `DirectShape.CreateElement` ile custom mesh/solid modeli kategoriye basma.

Nerede kullanılır:
- AI prototip çıktısını inceleme için hızlı görselleştirme (üretim öncesi).

---

### 14) Extensible Storage – Özel Veri Saklama
- `Schema` + `Entity` ile element üzerine özel metadata (örn. `correlationId`).

Nerede kullanılır:
- AI tarafından oluşturulan elemanları izleme, geri alma ve denetim izi.

---

### 15) Worksharing – Workset ve Sahiplik
- Eleman Workset atama/okuma, izin hataları ve kilitlenmeler.

Nerede kullanılır:
- Ekip halinde çalışırken AI’nın yazacağı elemanları belirli bir Workset’e koymak.

---

### 16) Failure API – Otomatik Çözüm Stratejileri
- Belirli uyarıları bastırma, bazı hataları otomatik çözme.

Nerede kullanılır:
- Toplu AI işlemleri sırasında kullanıcıyı uyarı yağmurundan korumak.

---

### 17) Performans İpuçları
- Kolektörleri yeniden kullanın; mümkünse element Id cache’i tutun.
- Regeneration’ı gereksiz tetiklemeyin, tek transaction’da gruplayın.
- Ağır geometri çıkarımlarını minimuma indirin; `Options.DetailLevel` ayarlayın.
- Büyük modellerde görünüm kapsamını sınırlayın (Section Box, View Filter).

Nerede kullanılır:
- 30 sn altı yerleşim hedefi için kritik optimizasyonlar.

---

### 18) Ölçü ve Yerleşim Yardımcıları
- `Transform`, `XYZ`, `UV`, `BoundingBoxXYZ` ile konumlandırma.
- Duvar yerleşiminde `LocationCurve` doğrultusuna göre kapı/pen. konumu.

Nerede kullanılır:
- AI oran/konum çıktısını Revit koordinat sistemine doğru yerleştirmek.

```csharp
Curve c = (wall.Location as LocationCurve).Curve;
XYZ p = c.Evaluate(doorRatio, true); // 0..1 oranında nokta
```

---

## 🎒 Hızlı Bağlantı: RevitAutoPlan’da Neyi Nerede Kullanayım?

- AI Layout oluşturma → TransactionGroup + hızlı filtre + FamilyInstance placement
- İnsan onayı → Selection + View Overrides ile görsel vurgulama
- Regülasyon/kurallar → Updater API + ValidationService (Python) senkron kontrol
- Büyük model performansı → Quick filters, cache, tek transaction, sınırlı geometri
- Link koordinatları → RevitLinkInstance.GetTotalTransform ile dönüşüm
- İzlenebilirlik → Extensible Storage ile `correlationId` saklama
- Otomatik uyarı yönetimi → IFailuresPreprocessor ile uyarı bastırma

---

**📅 Last Updated (extended)**: 2025-09-10