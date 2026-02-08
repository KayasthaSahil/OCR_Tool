import fitz  # PyMuPDF
from rapidocr_onnxruntime import RapidOCR

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

def process_page_task(args):
    """
    The independent task running on a separate CPU core.
    Args: (pdf_path, page_number)
    """
    pdf_path, page_num = args
    
    # Open PDF strictly for this page (Lazy Loading)
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_num)
        
        # --- STRATEGY 1: Digital Extraction ---
        text = page.get_text()
        if len(text.strip()) > 50:
            doc.close()
            return (page_num, f"--- Page {page_num + 1} (Digital) ---\n{text}\n")
            
        # --- STRATEGY 2: OCR Extraction ---
        # Use the pre-loaded global engine
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_bytes = pix.tobytes("png")
        
        result, _ = ocr_engine(img_bytes)
        
        extracted = ""
        if result:
            extracted = "\n".join([line[1] for line in result])
        else:
            extracted = "[No text found]"
            
        doc.close()
        return (page_num, f"--- Page {page_num + 1} (OCR) ---\n{extracted}\n")

    except Exception as e:
        return (page_num, f"--- Page {page_num + 1} (Error) ---\n{str(e)}\n")