import streamlit as st
import tempfile
import os
import time
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
# Import our new worker module
from ocr_worker import process_page_task, init_worker

st.set_page_config(page_title="Turbo OCR (Multi-Core)", layout="centered")

def save_uploaded_file(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getbuffer())
        return tmp_file.name

def process_pdf_parallel(pdf_path, progress_bar, status_text):
    import fitz # Import here to count pages
    
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()
    
    start_time = time.time()
    
    # Detect available CPU cores (Leave 1 free for the UI to stay responsive)
    max_workers = max(1, multiprocessing.cpu_count() - 1)
    status_text.text(f"Spinning up {max_workers} CPU cores...")
    
    # Prepare arguments for each page: [(path, 0), (path, 1), (path, 2)...]
    tasks = [(pdf_path, i) for i in range(total_pages)]
    results = []
    
    # --- PARALLEL EXECUTION POOL ---
    with ProcessPoolExecutor(max_workers=max_workers, initializer=init_worker) as executor:
        # Submit all tasks
        futures = [executor.submit(process_page_task, task) for task in tasks]
        
        # Monitor completion
        for i, future in enumerate(futures):
            # result() blocks until the specific page is done
            # Note: For better UI responsiveness with huge files, we use as_completed in production,
            # but simple iteration preserves page order easily here.
            page_num, text = future.result()
            results.append((page_num, text))
            
            # Update UI
            progress = (i + 1) / total_pages
            progress_bar.progress(progress)
            status_text.text(f"Processed Page {i+1}/{total_pages}...")

    # Sort results by page number to ensure correct order
    results.sort(key=lambda x: x[0])
    final_text = "".join([r[1] for r in results])
    
    duration = time.time() - start_time
    return final_text, duration

# --- UI LAYOUT ---
st.title("⚡ Turbo OCR (Multi-Core)")
st.markdown("🚀 **Engine:** Hybrid (Digital + OCR) | **Mode:** Parallel Processing")

uploaded_file = st.file_uploader("Upload PDF (Max 100MB)", type=["pdf"])

if uploaded_file:
    file_size_mb = uploaded_file.size / (1024 * 1024)
    st.info(f"File: **{uploaded_file.name}** ({file_size_mb:.2f} MB)")
    
    if st.button("Start Extraction"):
        temp_path = save_uploaded_file(uploaded_file)
        
        if temp_path:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                extracted_text, duration = process_pdf_parallel(temp_path, progress_bar, status_text)
                
                status_text.text("Processing Complete!")
                st.success(f"Done in {duration:.2f} seconds.")
                
                st.download_button(
                    label="Download .txt File",
                    data=extracted_text,
                    file_name=f"{uploaded_file.name}_extracted.txt",
                    mime="text/plain"
                )
                
                with st.expander("Preview Extracted Text"):
                    st.text(extracted_text[:2000] + "...")
                    
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)