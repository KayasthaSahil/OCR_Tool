"""
Enhanced OCR Worker Module with Performance Optimizations
- Adaptive image scaling based on document quality
- Improved memory management
- Robust error handling with retry logic
- Explicit resource cleanup
"""

import fitz  # PyMuPDF
from rapidocr_onnxruntime import RapidOCR
import time
import gc
import config

# Global variable to hold the model in each worker process
# This ensures we load the model ONLY ONCE per CPU core, not per page.
ocr_engine = None


def init_worker():
    """
    This runs once when a new CPU core starts working.
    It loads the AI model into that core's memory.
    """
    global ocr_engine
    if ocr_engine is None:
        ocr_engine = RapidOCR()


def get_optimal_scale(page):
    """
    Dynamically determine optimal scaling factor based on page resolution.
    
    Args:
        page: PyMuPDF page object
        
    Returns:
        float: Optimal scaling factor (1.5 to 3.0)
    """
    rect = page.rect
    # Use the smaller dimension as reference for DPI estimation
    page_dimension = min(rect.width, rect.height)
    
    # Adaptive scaling based on estimated quality (configurable thresholds)
    if page_dimension < config.DPI_THRESHOLD_LOW:
        # Low-resolution scan - needs more upscaling for better OCR
        return 3.0
    elif page_dimension < config.DPI_THRESHOLD_HIGH:
        # Medium quality - standard upscaling
        return 2.0
    else:
        # High-resolution digital document - minimal upscaling needed
        return 1.5


def estimate_text_density(page):
    """
    More sophisticated text detection than simple character count.
    
    Args:
        page: PyMuPDF page object
        
    Returns:
        str: "digital", "mixed", or "scanned"
    """
    text = page.get_text()
    text_length = len(text.strip())
    
    try:
        # Get text blocks for better analysis
        blocks = page.get_text("blocks")
        num_blocks = len(blocks) if blocks else 0
        
        # High density = likely digital text (configurable thresholds)
        if text_length > config.TEXT_LENGTH_DIGITAL and num_blocks > config.MIN_TEXT_BLOCKS:
            return "digital"
        elif text_length > config.TEXT_LENGTH_MIXED:
            return "mixed"  # Some text, might benefit from OCR enhancement
        else:
            return "scanned"  # Needs full OCR
    except:
        # Fallback to simple threshold if block detection fails
        return "digital" if text_length > config.TEXT_LENGTH_MIXED else "scanned"


def process_page_task(args, max_retries=2):
    """
    Enhanced page processing with retry logic and better error handling.
    
    Args:
        args: Tuple of (pdf_path, page_number)
        max_retries: Maximum number of retry attempts on failure
        
    Returns:
        Tuple of (page_num, extracted_text)
    """
    pdf_path, page_num = args
    
    # Retry logic for robustness
    for attempt in range(max_retries + 1):
        try:
            return _process_single_page(pdf_path, page_num)
        except Exception as e:
            if attempt == max_retries:
                # Final failure - return error marker with details
                error_msg = f"[FAILED after {max_retries + 1} attempts: {str(e)[:100]}]"
                return (page_num, f"--- Page {page_num + 1} (Error) ---\n{error_msg}\n")
            
            # Wait before retry (exponential backoff from config)
            time.sleep(config.RETRY_BACKOFF_BASE * (2 ** attempt))
            
            # Force garbage collection before retry
            gc.collect()


def _process_single_page(pdf_path, page_num):
    """
    Internal function to process a single page.
    
    Args:
        pdf_path: Path to PDF file
        page_num: Page number to process
        
    Returns:
        Tuple of (page_num, extracted_text)
    """
    doc = None
    pix = None
    
    try:
        # Open PDF for this page (lazy loading)
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_num)
        
        # Estimate text density for smarter processing
        density = estimate_text_density(page)
        
        # --- STRATEGY 1: Digital Extraction (FAST) ---
        if density == "digital":
            text = page.get_text()
            return (page_num, f"--- Page {page_num + 1} (Digital) ---\n{text}\n")
        
        # --- STRATEGY 2: Hybrid (Digital + OCR Enhancement) ---
        if density == "mixed":
            digital_text = page.get_text()
            # For mixed content, we could enhance with OCR in the future
            # For now, trust the digital extraction
            return (page_num, f"--- Page {page_num + 1} (Digital-Mixed) ---\n{digital_text}\n")
        
        # --- STRATEGY 3: Full OCR (SLOW but Robust) ---
        # Get optimal scaling for this page
        scale_factor = get_optimal_scale(page)
        
        # Render page as image with adaptive scaling
        pix = page.get_pixmap(matrix=fitz.Matrix(scale_factor, scale_factor))
        img_bytes = pix.tobytes("png")
        
        # Explicitly free pixmap memory before OCR
        del pix
        pix = None
        
        # Run RapidOCR on the image bytes
        result, _ = ocr_engine(img_bytes)
        
        # Free image bytes
        del img_bytes
        
        # Extract text from OCR result
        if result:
            extracted = "\n".join([line[1] for line in result])
        else:
            extracted = "[No text detected]"
        
        return (page_num, f"--- Page {page_num + 1} (OCR@{scale_factor}x) ---\n{extracted}\n")
    
    finally:
        # Explicit cleanup to prevent memory leaks
        if pix is not None:
            try:
                del pix
            except:
                pass
        
        if doc is not None:
            try:
                doc.close()
            except:
                pass
        
        # Suggest garbage collection for large objects
        gc.collect()


# Backward compatibility - keep the original function signature
def process_page_with_retry(args, max_retries=2):
    """
    Wrapper for backward compatibility.
    """
    return process_page_task(args, max_retries)