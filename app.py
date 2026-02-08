import streamlit as st
import tempfile
import os
import time
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
# Import our new worker module
from ocr_worker import process_page_task, init_worker
import config

st.set_page_config(page_title="Turbo OCR (Multi-Core)", layout="centered")

def save_uploaded_file(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getbuffer())
        return tmp_file.name

def process_pdf_parallel(pdf_path, progress_bar, status_text):
    """
    Enhanced parallel PDF processing with timeout protection and better error handling.
    """
    import fitz # Import here to count pages
    from concurrent.futures import TimeoutError
    
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()
    
    start_time = time.time()
    
    # Detect available CPU cores (configurable via config.py)
    if config.MAX_WORKERS is None:
        max_workers = max(1, multiprocessing.cpu_count() - config.RESERVE_CORES)
    else:
        max_workers = config.MAX_WORKERS
    status_text.text(f"🚀 Spinning up {max_workers} CPU cores...")
    
    # Prepare arguments for each page: [(path, 0), (path, 1), (path, 2)...]
    tasks = [(pdf_path, i) for i in range(total_pages)]
    results = []
    failed_pages = []
    
    # Timeout per page (configurable via config.py)
    TIMEOUT_PER_PAGE = config.TIMEOUT_PER_PAGE
    
    # --- PARALLEL EXECUTION POOL ---
    with ProcessPoolExecutor(max_workers=max_workers, initializer=init_worker) as executor:
        # Submit all tasks
        futures = [executor.submit(process_page_task, task) for task in tasks]
        
        # Monitor completion with timeout protection
        for i, future in enumerate(futures):
            try:
                # Wait for page with timeout protection
                page_num, text = future.result(timeout=TIMEOUT_PER_PAGE)
                results.append((page_num, text))
                
            except TimeoutError:
                # Page took too long - mark as timeout
                page_num = i
                timeout_text = f"--- Page {page_num + 1} (Timeout) ---\n[Processing exceeded {TIMEOUT_PER_PAGE}s limit]\n"
                results.append((page_num, timeout_text))
                failed_pages.append(page_num + 1)
                
            except Exception as e:
                # Unexpected error during processing
                page_num = i
                error_text = f"--- Page {page_num + 1} (Error) ---\n[{str(e)[:200]}]\n"
                results.append((page_num, error_text))
                failed_pages.append(page_num + 1)
            
            # Update UI with more informative status
            progress = (i + 1) / total_pages
            progress_bar.progress(progress)
            
            if failed_pages:
                status_text.text(f"📄 Processed {i+1}/{total_pages} pages ({len(failed_pages)} issues)...")
            else:
                status_text.text(f"📄 Processed {i+1}/{total_pages} pages...")

    # Sort results by page number to ensure correct order
    results.sort(key=lambda x: x[0])
    final_text = "".join([r[1] for r in results])
    
    duration = time.time() - start_time
    
    # Return results with diagnostic info
    return final_text, duration, failed_pages

# --- UI LAYOUT ---
st.title("⚡ Turbo OCR (Multi-Core)")
st.markdown("🚀 **Engine:** Hybrid (Digital + OCR) | **Mode:** Parallel Processing")

uploaded_file = st.file_uploader(f"Upload PDF (Max {config.MAX_FILE_SIZE_MB}MB)", type=["pdf"])

if uploaded_file:
    file_size_mb = uploaded_file.size / (1024 * 1024)
    st.info(f"📄 File: **{uploaded_file.name}** ({file_size_mb:.2f} MB)")
    
    if st.button("▶️ Start Extraction"):
        temp_path = save_uploaded_file(uploaded_file)
        
        if temp_path:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                extracted_text, duration, failed_pages = process_pdf_parallel(temp_path, progress_bar, status_text)
                
                status_text.text("✅ Processing Complete!")
                
                # Show success message with timing and diagnostics
                if failed_pages:
                    st.warning(f"⚠️ Completed in {duration:.2f} seconds with {len(failed_pages)} page(s) having issues: {', '.join(map(str, failed_pages))}")
                else:
                    st.success(f"✨ Done in {duration:.2f} seconds - All pages processed successfully!")
                
                # Calculate statistics
                total_chars = len(extracted_text)
                st.metric("Extracted Characters", f"{total_chars:,}")
                
                st.download_button(
                    label="⬇️ Download .txt File",
                    data=extracted_text,
                    file_name=f"{uploaded_file.name}_extracted.txt",
                    mime="text/plain"
                )
                
                with st.expander("👁️ Preview Extracted Text"):
                    preview_length = min(config.PREVIEW_LENGTH, len(extracted_text))
                    st.text(extracted_text[:preview_length] + ("..." if len(extracted_text) > preview_length else ""))
                    
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)