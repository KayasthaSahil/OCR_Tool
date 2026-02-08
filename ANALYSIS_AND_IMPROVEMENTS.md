# OCR Tool - Analysis & Performance Improvements

## Current Architecture Overview

### Project Structure
```
OCR_tool/
├── app.py                 # Streamlit UI (Multi-core parallel processing)
├── ocr_worker.py         # Worker process for parallel execution
├── ocr_engine.py         # Serial OCR processor (Legacy/Unused?)
└── requirements.txt      # Dependencies
```

### Current Implementation Analysis

#### ✅ **Strengths**
1. **Hybrid Strategy**: Digital text extraction + OCR fallback
2. **Multi-core Processing**: Uses ProcessPoolExecutor for parallel page processing
3. **Efficient PDF Handling**: PyMuPDF (fitz) for fast PDF operations
4. **Smart Text Detection**: 50-char threshold to avoid unnecessary OCR
5. **Model Reuse**: Global OCR engine loaded once per worker process

#### ⚠️ **Current Issues & Bottlenecks**

##### 1. **Inefficient Page Loading**
```python
# Current approach in ocr_worker.py
doc = fitz.open(pdf_path)  # Opens entire PDF for each page
page = doc.load_page(page_num)
```
**Problem**: Each worker process opens the entire PDF file, even though it only needs one page.

##### 2. **Suboptimal Image Resolution**
```python
pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
```
**Problem**: Fixed 2x scaling may be:
- Too high for high-DPI documents (waste processing time)
- Too low for low-quality scans (poor OCR accuracy)

##### 3. **No Batching Strategy**
Each page is processed independently. No batch processing for OCR operations.

##### 4. **Memory Management**
- No explicit memory cleanup
- Pixmap objects not explicitly deleted (rely on garbage collection)
- Could cause memory spikes with large PDFs

##### 5. **No Progress Granularity**
Progress updates only after entire page completes. For large pages with complex OCR, UI appears frozen.

##### 6. **Error Recovery**
Minimal error handling. One corrupted page could affect processing.

##### 7. **Duplicate Code**
`ocr_engine.py` appears to be legacy code - similar functionality to `ocr_worker.py` but serial processing.

---

## 🚀 Proposed Improvements

### **Phase 1: Critical Performance Optimizations**

#### 1.1 **Adaptive Image Scaling**
```python
def get_optimal_scale(page):
    """Dynamically adjust scaling based on page resolution"""
    rect = page.rect
    page_dpi = min(rect.width, rect.height)
    
    if page_dpi < 500:
        return 3.0  # Low-res scan needs more scaling
    elif page_dpi < 1000:
        return 2.0  # Medium quality
    else:
        return 1.5  # High-res digital document
```

#### 1.2 **Chunked Page Processing**
Instead of opening the entire PDF per worker:
```python
def extract_page_as_bytes(pdf_path, page_num):
    """Extract a single page as a new PDF document"""
    doc = fitz.open(pdf_path)
    extracted_doc = fitz.open()  # Empty PDF
    extracted_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
    
    page_bytes = extracted_doc.tobytes()
    doc.close()
    extracted_doc.close()
    return page_bytes
```

#### 1.3 **Batch OCR Processing**
Group pages for OCR to reduce overhead:
```python
def process_batch(pages_batch):
    """Process multiple pages in one OCR session"""
    results = []
    for page_bytes in pages_batch:
        result = ocr_engine(page_bytes)
        results.append(result)
    return results
```

#### 1.4 **Memory Management**
```python
# Explicit cleanup
pix = page.get_pixmap()
img_bytes = pix.tobytes("png")
del pix  # Explicitly free memory
```

### **Phase 2: Enhanced Chunking Strategy**

#### 2.1 **Smart PDF Chunking**
```python
def chunk_pdf_by_size(pdf_path, chunk_mb=10):
    """Split PDF into manageable chunks based on file size"""
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    
    # Estimate pages per chunk
    file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
    pages_per_chunk = max(1, int(chunk_mb * total_pages / file_size_mb))
    
    chunks = []
    for i in range(0, total_pages, pages_per_chunk):
        chunks.append((i, min(i + pages_per_chunk, total_pages)))
    
    doc.close()
    return chunks
```

#### 2.2 **Intelligent Text Density Detection**
```python
def estimate_text_density(page):
    """More sophisticated text detection than 50-char threshold"""
    text = page.get_text()
    blocks = page.get_text("blocks")
    
    # Calculate coverage ratio
    text_length = len(text.strip())
    num_blocks = len(blocks)
    
    # High density = likely digital text
    if text_length > 100 and num_blocks > 5:
        return "digital"
    elif text_length > 50:
        return "mixed"  # Some digital text, might need OCR enhancement
    else:
        return "scanned"  # Needs full OCR
```

### **Phase 3: Stability & Error Handling**

#### 3.1 **Robust Error Recovery**
```python
def process_page_with_retry(args, max_retries=3):
    """Retry failed pages with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return process_page_task(args)
        except Exception as e:
            if attempt == max_retries - 1:
                # Final failure - return error marker
                return (args[1], f"[FAILED after {max_retries} attempts: {str(e)}]")
            time.sleep(2 ** attempt)  # Exponential backoff
```

#### 3.2 **Timeout Protection**
```python
from concurrent.futures import TimeoutError

# In process_pdf_parallel
for future in futures:
    try:
        result = future.result(timeout=60)  # 60 sec per page max
    except TimeoutError:
        result = (page_num, "[TIMEOUT - page too complex]")
```

#### 3.3 **Resource Monitoring**
```python
import psutil

def check_system_resources():
    """Monitor and adjust worker count based on available resources"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_percent = psutil.virtual_memory().percent
    
    if cpu_percent > 90 or memory_percent > 85:
        return max(1, multiprocessing.cpu_count() // 2)  # Throttle
    return max(1, multiprocessing.cpu_count() - 1)
```

### **Phase 4: Advanced Optimizations**

#### 4.1 **Pre-processing Pipeline**
```python
def preprocess_image(img_bytes):
    """Enhance image quality before OCR"""
    import cv2
    import numpy as np
    
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Grayscale conversion
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Adaptive thresholding for better text contrast
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    
    # Denoise
    denoised = cv2.fastNlMeansDenoising(binary)
    
    # Encode back to bytes
    _, encoded = cv2.imencode('.png', denoised)
    return encoded.tobytes()
```

#### 4.2 **Caching Layer**
```python
import hashlib
import pickle

def cache_ocr_result(pdf_path, page_num, result):
    """Cache OCR results to avoid reprocessing"""
    cache_dir = ".ocr_cache"
    os.makedirs(cache_dir, exist_ok=True)
    
    # Create unique hash for this page
    with open(pdf_path, 'rb') as f:
        f.seek(page_num * 1024)  # Approximate page location
        page_hash = hashlib.md5(f.read(1024)).hexdigest()
    
    cache_file = os.path.join(cache_dir, f"{page_hash}.pkl")
    with open(cache_file, 'wb') as f:
        pickle.dump(result, f)

def get_cached_result(pdf_path, page_num):
    """Retrieve cached OCR result if exists"""
    # Similar hashing logic
    # Return cached result or None
    pass
```

#### 4.3 **Async I/O for File Operations**
```python
import asyncio
import aiofiles

async def async_save_result(text, filename):
    """Non-blocking file write"""
    async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
        await f.write(text)
```

---

## 📊 Expected Performance Improvements

| Optimization | Expected Speedup | Stability Impact |
|--------------|------------------|------------------|
| Adaptive scaling | 15-30% | ⭐⭐⭐ |
| Batch processing | 20-40% | ⭐⭐ |
| Memory management | 10-15% | ⭐⭐⭐⭐⭐ |
| Smart chunking | 25-35% | ⭐⭐⭐⭐ |
| Image preprocessing | 10-20% (accuracy) | ⭐⭐⭐ |
| Caching | 50-90% (re-runs) | ⭐⭐ |
| Error handling | N/A | ⭐⭐⭐⭐⭐ |

**Overall Expected Improvement**: **40-60% faster** with **significantly improved stability**

---

## 🎯 Implementation Priority

### **HIGH PRIORITY** (Implement First)
1. ✅ Memory management improvements
2. ✅ Adaptive image scaling
3. ✅ Robust error handling with retries
4. ✅ Remove duplicate code (ocr_engine.py)

### **MEDIUM PRIORITY**
5. ⚠️ Smart text density detection
6. ⚠️ Batch processing for OCR
7. ⚠️ Timeout protection
8. ⚠️ Resource monitoring

### **LOW PRIORITY** (Advanced Features)
9. 🔵 Image preprocessing pipeline
10. 🔵 Caching layer
11. 🔵 Async I/O operations

---

## 🔧 Next Steps

1. **Backup current code**: Create a feature branch
2. **Implement Phase 1 optimizations**: Focus on critical performance
3. **Benchmark**: Test with various PDF types (digital, scanned, mixed)
4. **Iterate**: Measure impact and adjust
5. **Clean up**: Remove unused code (ocr_engine.py)
6. **Document**: Update code comments and user documentation

---

## 📝 Additional Recommendations

### Dependencies Update
Consider adding:
```
pillow>=10.0.0          # Better image handling
psutil>=5.9.0           # Resource monitoring
aiofiles>=23.0.0        # Async file operations (optional)
```

### Configuration File
Create `config.py` for tunable parameters:
```python
# OCR Configuration
MAX_WORKERS = None  # Auto-detect
DPI_THRESHOLD_LOW = 500
DPI_THRESHOLD_HIGH = 1000
TEXT_THRESHOLD = 50
TIMEOUT_PER_PAGE = 60
CACHE_ENABLED = False
PREPROCESSING_ENABLED = True
```

### Testing Strategy
1. **Unit tests**: Test individual functions
2. **Integration tests**: Test full pipeline
3. **Performance benchmarks**: Track improvements
4. **Stress tests**: Large PDFs (100+ pages)

---

**Ready to implement these improvements? Let me know which phase you'd like to start with!**
