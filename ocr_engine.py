import fitz  # PyMuPDF
from rapidocr_onnxruntime import RapidOCR
import time

class OCRProcessor:
    def __init__(self):
        # Initialize the OCR model once to save time
        # We limit the number of threads to prevent CPU choking on large files
        print("Loading OCR Engine...")
        self.ocr_engine = RapidOCR()
        print("OCR Engine Ready.")

    def extract_text(self, pdf_path):
        """
        Main function to process the PDF.
        Returns: A string containing all extracted text.
        """
        full_text = []
        start_time = time.time()
        
        # Open the PDF file
        # 'fitz.open' is lazy; it doesn't load the whole 100MB into RAM at once.
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        print(f"Processing {pdf_path} ({total_pages} pages)...")

        for page_num, page in enumerate(doc):
            print(f"Processing Page {page_num + 1}/{total_pages}...", end="\r")
            
            # --- STRATEGY 1: Digital Extraction (FAST) ---
            # Try to grab text directly from the PDF layer
            text = page.get_text()
            
            # Heuristic: If we found substantial text (>50 chars), assume it's digital.
            # This skips the expensive OCR process.
            if len(text.strip()) > 50:
                full_text.append(f"--- Page {page_num + 1} (Digital) ---\n{text}")
                continue

            # --- STRATEGY 2: OCR Extraction (SLOW but Robust) ---
            # If text was empty or too short, render the page as an image.
            
            # zoom=2 creates a higher resolution image (essential for accuracy)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_bytes = pix.tobytes("png")
            
            # Run RapidOCR on the image bytes
            result, _ = self.ocr_engine(img_bytes)
            
            extracted_ocr = ""
            if result:
                # RapidOCR returns a list of [box, text, score]
                extracted_ocr = "\n".join([line[1] for line in result])
            
            full_text.append(f"--- Page {page_num + 1} (OCR) ---\n{extracted_ocr}")

        doc.close()
        
        end_time = time.time()
        duration = end_time - start_time
        print(f"\nCompleted in {duration:.2f} seconds.")
        
        return "\n".join(full_text)

# This block allows us to test this file directly without the UI
if __name__ == "__main__":
    import sys
    
    # Create a dummy file named 'test.pdf' in your folder to test this!
    # Or pass a path as an argument: python ocr_engine.py my_document.pdf
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = "test.pdf" 

    try:
        processor = OCRProcessor()
        text = processor.extract_text(path)
        
        # Save to a debug file
        with open("debug_output.txt", "w", encoding="utf-8") as f:
            f.write(text)
            
        print("Extraction saved to debug_output.txt")
        
    except Exception as e:
        print(f"Error: {e}")
        print("Did you forget to put a PDF file in the folder?")