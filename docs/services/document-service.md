# DocumentService Dökümantasyonu

DocumentService, ArchBuilder.AI'ın belge işleme ve içerik çıkarma motorudur. Bu servis, DWG/DXF, IFC, PDF yönetmelik ve diğer mimari dosya formatlarını işleyerek AI sistemi için kullanılabilir hale getirir.

## 📋 İçindekiler

1. [Genel Bakış](#genel-bakış)
2. [Desteklenen Dosya Formatları](#desteklenen-dosya-formatları)
3. [Ana Bileşenler](#ana-bileşenler)
4. [Dosya Upload Sistemi](#dosya-upload-sistemi)
5. [Parser Mimarisi](#parser-mimarisi)
6. [RAG Entegrasyonu](#rag-entegrasyonu)
7. [Güvenlik ve Doğrulama](#güvenlik-ve-doğrulama)
8. [Kullanım Örnekleri](#kullanım-örnekleri)
9. [Performans Optimizasyonu](#performans-optimizasyonu)

## 🔍 Genel Bakış

DocumentService aşağıdaki temel işlevleri sağlar:

### Ana İşlevler
- **Multi-format Upload**: DWG, DXF, IFC, PDF dosya upload'u
- **Content Extraction**: Dosyalardan metin, geometry ve metadata çıkarma
- **Format Conversion**: Dosya format dönüşümleri
- **Validation**: Dosya integrity ve format kontrolü
- **RAG Integration**: Çıkarılan içeriği knowledge base'e entegre etme
- **Security**: Güvenli dosya işleme ve sanitization

### Desteklenen İş Akışları
```mermaid
graph LR
    A[File Upload] --> B[Security Scan]
    B --> C[Format Detection]
    C --> D[Content Parsing]
    D --> E[Validation]
    E --> F[RAG Integration]
    F --> G[Storage]
```

## 📁 Desteklenen Dosya Formatları

### CAD Dosyaları
- **DWG**: AutoCAD Drawing files
- **DXF**: Drawing Exchange Format
- **IFC**: Industry Foundation Classes
- **3DM**: Rhino 3D models

### Yönetmelik Belgeleri
- **PDF**: Building codes ve regulations
- **DOC/DOCX**: Word documents
- **TXT**: Plain text regulations

### Görüntü Dosyaları
- **JPG/PNG**: Architectural drawings
- **TIFF**: High-resolution plans
- **SVG**: Vector graphics

### Maksimum Dosya Boyutları
```python
FILE_SIZE_LIMITS = {
    "dwg": 500 * 1024 * 1024,    # 500 MB
    "dxf": 200 * 1024 * 1024,    # 200 MB
    "ifc": 1024 * 1024 * 1024,   # 1 GB
    "pdf": 100 * 1024 * 1024,    # 100 MB
    "image": 50 * 1024 * 1024,   # 50 MB
}
```

## 🧩 Ana Bileşenler

### 1. FileUploadHandler
Güvenli dosya upload ve ilk validation işlemlerini yönetir.

```python
class FileUploadHandler:
    async def upload_document(
        self,
        file: UploadFile,
        project_id: str,
        user_id: str,
        correlation_id: str
    ) -> DocumentUploadResponse
```

**Özellikler**:
- Multi-chunk upload desteği
- Virus scanning
- File type validation
- Size limit kontrolü
- Temporary storage management

**Upload Workflow**:
```python
# 1. Security validation
await self._validate_file_security(file)

# 2. File type detection
file_type = await self._detect_file_type(file)

# 3. Size validation
await self._validate_file_size(file, file_type)

# 4. Temporary storage
temp_path = await self._store_temporarily(file)

# 5. Virus scan
await self._scan_for_viruses(temp_path)

# 6. Move to secure storage
final_path = await self._move_to_secure_storage(temp_path)
```

### 2. DocumentParser
Format-specific parsing işlemlerini koordine eder.

```python
class DocumentParser:
    async def parse_document(
        self,
        file_path: str,
        file_type: str,
        parse_options: ParseOptions
    ) -> DocumentParseResult
```

**Parser Types**:
- **DWGParser**: AutoCAD dosyaları için
- **IFCParser**: BIM model parsing
- **PDFParser**: Text extraction ve OCR
- **ImageParser**: Drawing recognition

### 3. DocumentService (Ana Koordinatör)
Tüm document operations'ı koordine eder.

```python
class DocumentService:
    async def process_document(
        self,
        request: DocumentProcessRequest,
        correlation_id: str
    ) -> DocumentProcessResponse
```

## 📤 Dosya Upload Sistemi

### Upload Request Format
```python
@dataclass
class DocumentUploadRequest:
    file: UploadFile
    project_id: str
    document_type: str  # "cad", "regulation", "reference"
    description: Optional[str]
    tags: List[str]
    language: str = "tr"
```

### Security Validation
```python
async def _validate_file_security(self, file: UploadFile) -> None:
    # 1. File extension whitelist check
    allowed_extensions = [".dwg", ".dxf", ".ifc", ".pdf", ".jpg", ".png"]
    if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        raise InvalidFileTypeException()
    
    # 2. MIME type validation
    mime_type = await self._detect_mime_type(file)
    if mime_type not in ALLOWED_MIME_TYPES:
        raise InvalidMimeTypeException()
    
    # 3. Magic number validation
    magic_bytes = await file.read(1024)
    await file.seek(0)
    if not self._validate_magic_number(magic_bytes, file.filename):
        raise CorruptedFileException()
```

### Upload Progress Tracking
```python
@dataclass
class UploadProgress:
    upload_id: str
    total_size: int
    uploaded_size: int
    status: str  # "uploading", "processing", "completed", "failed"
    estimated_time_remaining: Optional[int]
    current_stage: str  # "upload", "virus_scan", "parsing", "indexing"
```

## 🔧 Parser Mimarisi

### DWG/DXF Parser
```python
class DWGParser:
    async def parse_dwg_file(
        self,
        file_path: str,
        correlation_id: str
    ) -> CADParseResult:
        
        # 1. Load DWG using ezdxf/pyautocad
        try:
            doc = ezdxf.readfile(file_path)
        except Exception as e:
            raise CADParsingException(f"Failed to read DWG: {e}")
        
        # 2. Extract geometric entities
        entities = await self._extract_entities(doc)
        
        # 3. Extract layers and metadata
        layers = await self._extract_layers(doc)
        
        # 4. Extract dimensions and text
        dimensions = await self._extract_dimensions(doc)
        text_elements = await self._extract_text(doc)
        
        return CADParseResult(
            entities=entities,
            layers=layers,
            dimensions=dimensions,
            text_elements=text_elements,
            metadata=await self._extract_metadata(doc)
        )
```

### IFC Parser
```python
class IFCParser:
    async def parse_ifc_file(
        self,
        file_path: str,
        correlation_id: str
    ) -> BIMParseResult:
        
        # 1. Load IFC model
        model = ifcopenshell.open(file_path)
        
        # 2. Extract building elements
        elements = await self._extract_building_elements(model)
        
        # 3. Extract spatial structure
        spatial_structure = await self._extract_spatial_structure(model)
        
        # 4. Extract properties and relationships
        properties = await self._extract_properties(model)
        relationships = await self._extract_relationships(model)
        
        return BIMParseResult(
            elements=elements,
            spatial_structure=spatial_structure,
            properties=properties,
            relationships=relationships,
            model_metadata=await self._extract_model_metadata(model)
        )
```

### PDF Parser (Regulations)
```python
class PDFParser:
    async def parse_pdf_regulations(
        self,
        file_path: str,
        language: str,
        correlation_id: str
    ) -> RegulationParseResult:
        
        # 1. Extract text using PyPDF2/pdfplumber
        text_content = await self._extract_text_content(file_path)
        
        # 2. OCR for scanned PDFs
        if self._is_scanned_pdf(file_path):
            ocr_text = await self._perform_ocr(file_path, language)
            text_content = self._merge_text_sources(text_content, ocr_text)
        
        # 3. Structure detection
        structure = await self._detect_document_structure(text_content)
        
        # 4. Extract regulations and rules
        regulations = await self._extract_regulations(text_content, structure)
        
        return RegulationParseResult(
            text_content=text_content,
            structure=structure,
            regulations=regulations,
            metadata=await self._extract_pdf_metadata(file_path)
        )
```

## 🔗 RAG Entegrasyonu

### Document Chunking
```python
async def _prepare_for_rag(
    self,
    parse_result: DocumentParseResult,
    document_info: DocumentInfo
) -> List[DocumentChunk]:
    
    chunks = []
    
    # Content-aware chunking
    if document_info.document_type == "regulation":
        # Regulation-specific chunking (by sections, articles)
        chunks = await self._chunk_regulation_content(parse_result)
    elif document_info.document_type == "cad":
        # CAD-specific chunking (by layers, entities)
        chunks = await self._chunk_cad_content(parse_result)
    else:
        # Generic content chunking
        chunks = await self._chunk_generic_content(parse_result)
    
    return chunks
```

### RAG Integration Workflow
```python
async def _integrate_with_rag(
    self,
    chunks: List[DocumentChunk],
    document_info: DocumentInfo,
    correlation_id: str
) -> None:
    
    # 1. Generate embeddings for each chunk
    for chunk in chunks:
        embedding = await self.rag_service.generate_embedding(
            text=chunk.content,
            chunk_type=chunk.chunk_type
        )
        chunk.embedding = embedding
    
    # 2. Store in vector database
    await self.rag_service.store_document_chunks(
        chunks=chunks,
        document_id=document_info.document_id,
        correlation_id=correlation_id
    )
    
    # 3. Update search indexes
    await self.rag_service.update_search_indexes(
        document_id=document_info.document_id
    )
```

## 🛡️ Güvenlik ve Doğrulama

### File Security Pipeline
```python
class FileSecurityValidator:
    async def validate_security(
        self,
        file_path: str,
        file_type: str
    ) -> SecurityValidationResult:
        
        results = []
        
        # 1. Virus scan
        virus_result = await self._scan_for_viruses(file_path)
        results.append(virus_result)
        
        # 2. Malware detection
        malware_result = await self._detect_malware(file_path)
        results.append(malware_result)
        
        # 3. Content sanitization
        sanitization_result = await self._sanitize_content(file_path, file_type)
        results.append(sanitization_result)
        
        # 4. Privacy scan (PII detection)
        privacy_result = await self._scan_for_pii(file_path)
        results.append(privacy_result)
        
        return SecurityValidationResult(
            is_safe=all(r.is_safe for r in results),
            validation_results=results,
            risk_level=self._calculate_risk_level(results)
        )
```

### Content Validation
```python
async def _validate_parsed_content(
    self,
    parse_result: DocumentParseResult,
    expected_format: str
) -> ValidationResult:
    
    validations = []
    
    # 1. Format consistency check
    format_validation = self._validate_format_consistency(
        parse_result, expected_format
    )
    validations.append(format_validation)
    
    # 2. Content completeness check
    completeness_validation = self._validate_content_completeness(parse_result)
    validations.append(completeness_validation)
    
    # 3. Data integrity check
    integrity_validation = self._validate_data_integrity(parse_result)
    validations.append(integrity_validation)
    
    return ValidationResult(
        is_valid=all(v.is_valid for v in validations),
        validation_details=validations,
        confidence_score=self._calculate_confidence(validations)
    )
```

## 💡 Kullanım Örnekleri

### DWG Dosyası Upload ve İşleme
```python
# DWG file upload
upload_request = DocumentUploadRequest(
    file=uploaded_file,
    project_id="proj_123",
    document_type="cad",
    description="Site plan drawing",
    tags=["site-plan", "architectural"],
    language="tr"
)

# Upload and process
response = await document_service.upload_and_process_document(
    request=upload_request,
    correlation_id="upload_456"
)

# Check results
if response.success:
    print(f"Document processed: {response.document_id}")
    print(f"Extracted entities: {len(response.parse_result.entities)}")
    print(f"RAG chunks created: {response.rag_integration.chunk_count}")
```

### PDF Yönetmelik Upload
```python
# PDF regulation upload
pdf_request = DocumentUploadRequest(
    file=regulation_pdf,
    project_id="proj_123",
    document_type="regulation",
    description="Turkish Building Code - Fire Safety",
    tags=["fire-safety", "building-code", "turkey"],
    language="tr"
)

# Process regulation document
response = await document_service.upload_and_process_document(
    request=pdf_request,
    correlation_id="regulation_789"
)

# Access extracted regulations
regulations = response.parse_result.regulations
for regulation in regulations:
    print(f"Article {regulation.article_number}: {regulation.title}")
    print(f"Content: {regulation.content[:200]}...")
```

### IFC Model Processing
```python
# IFC model upload
ifc_request = DocumentUploadRequest(
    file=ifc_model,
    project_id="proj_123",
    document_type="cad",
    description="Building Information Model",
    tags=["bim", "3d-model", "structural"],
    language="en"
)

# Process IFC model
response = await document_service.upload_and_process_document(
    request=ifc_request,
    correlation_id="ifc_101"
)

# Access BIM data
bim_data = response.parse_result
print(f"Building elements: {len(bim_data.elements)}")
print(f"Spatial structure levels: {len(bim_data.spatial_structure)}")
```

### Bulk Document Processing
```python
# Process multiple documents
document_files = [
    ("site_plan.dwg", "cad"),
    ("building_code.pdf", "regulation"),
    ("existing_model.ifc", "cad")
]

results = []
for file_name, doc_type in document_files:
    request = DocumentUploadRequest(
        file=open(file_name, 'rb'),
        project_id="proj_123",
        document_type=doc_type,
        language="tr"
    )
    
    result = await document_service.upload_and_process_document(
        request=request,
        correlation_id=f"bulk_{uuid.uuid4()}"
    )
    results.append(result)

# Summary
successful = sum(1 for r in results if r.success)
print(f"Processed {successful}/{len(results)} documents successfully")
```

## ⚡ Performans Optimizasyonu

### Async Processing Pipeline
```python
async def process_document_pipeline(
    self,
    request: DocumentProcessRequest
) -> DocumentProcessResponse:
    
    # Parallel processing stages
    async with asyncio.TaskGroup() as tg:
        # Security validation (parallel)
        security_task = tg.create_task(
            self._validate_security(request.file_path)
        )
        
        # Metadata extraction (parallel)
        metadata_task = tg.create_task(
            self._extract_metadata(request.file_path)
        )
        
        # Basic format validation (parallel)
        format_task = tg.create_task(
            self._validate_format(request.file_path, request.file_type)
        )
    
    # Sequential processing (depends on validation)
    if security_task.result().is_safe:
        parse_result = await self._parse_document(request)
        rag_result = await self._integrate_with_rag(parse_result, request)
        
        return DocumentProcessResponse(
            success=True,
            parse_result=parse_result,
            rag_integration=rag_result
        )
```

### Caching Strategy
```python
# Parser result caching
@cache_result(ttl=3600)  # 1 hour cache
async def _parse_document_cached(
    self,
    file_hash: str,
    file_type: str,
    parse_options: ParseOptions
) -> DocumentParseResult:
    return await self._parse_document_internal(file_hash, file_type, parse_options)

# Metadata caching
@cache_result(ttl=86400)  # 24 hour cache
async def _extract_metadata_cached(
    self,
    file_hash: str
) -> DocumentMetadata:
    return await self._extract_metadata_internal(file_hash)
```

### Resource Management
```python
class ResourceManager:
    def __init__(self):
        self.processing_semaphore = asyncio.Semaphore(5)  # Max 5 parallel
        self.memory_monitor = MemoryMonitor()
        self.temp_cleaner = TempFileCleaner()
    
    async def process_with_resource_management(
        self,
        processing_func: Callable,
        file_path: str
    ) -> Any:
        async with self.processing_semaphore:
            # Monitor memory usage
            initial_memory = self.memory_monitor.get_usage()
            
            try:
                result = await processing_func(file_path)
                return result
            finally:
                # Clean up temp files
                await self.temp_cleaner.clean_file_related_temps(file_path)
                
                # Check memory leaks
                final_memory = self.memory_monitor.get_usage()
                if final_memory - initial_memory > 100 * 1024 * 1024:  # 100MB
                    logger.warning(f"Potential memory leak detected: {final_memory - initial_memory} bytes")
```

## 📊 Performance Metrikleri

### Target Performance
- **File Upload**: <30 seconds for 100MB files
- **DWG Parsing**: <2 minutes for complex drawings
- **PDF Processing**: <1 minute per 100 pages
- **IFC Processing**: <5 minutes for large models
- **RAG Integration**: <30 seconds per document

### Monitoring Metrics
```python
{
    "document_service_metrics": {
        "total_uploads": 2847,
        "successful_parses": 2698,
        "parse_success_rate": 0.947,
        "average_upload_time_ms": 18500,
        "average_parse_time_ms": 45000,
        "cache_hit_rate": 0.34,
        "format_distribution": {
            "dwg": 0.42,
            "pdf": 0.31,
            "ifc": 0.18,
            "dxf": 0.09
        },
        "security_incidents": 0
    }
}
```

## 🔧 Configuration

### Environment Variables
```bash
# File Storage
UPLOAD_STORAGE_PATH=/app/uploads
TEMP_STORAGE_PATH=/tmp/archbuilder
MAX_UPLOAD_SIZE_MB=1000

# Security
ENABLE_VIRUS_SCANNING=true
VIRUS_SCANNER_ENDPOINT=http://clamav:3310
ENABLE_CONTENT_SANITIZATION=true

# Processing
MAX_PARALLEL_PROCESSING=5
PROCESSING_TIMEOUT_MINUTES=30
ENABLE_PROCESSING_CACHE=true

# RAG Integration
ENABLE_RAG_INTEGRATION=true
RAG_CHUNK_SIZE=1000
RAG_CHUNK_OVERLAP=200
```

### Parser Configuration
```python
PARSER_CONFIG = {
    "dwg": {
        "extract_entities": True,
        "extract_dimensions": True,
        "extract_text": True,
        "extract_metadata": True,
        "coordinate_precision": 3
    },
    "pdf": {
        "enable_ocr": True,
        "ocr_languages": ["tur", "eng"],
        "extract_images": False,
        "preserve_formatting": True
    },
    "ifc": {
        "extract_geometry": True,
        "extract_properties": True,
        "extract_relationships": True,
        "load_full_model": False
    }
}
```

---

**Bu dokümantasyon DocumentService'in tüm dosya işleme yeteneklerini kapsamaktadır. Detaylı parser implementation'ları için kaynak kod incelenebilir.**