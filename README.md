# ⚡ Turbo OCR Tool

A high-performance OCR tool built with multi-core parallel processing for fast and accurate text extraction from PDF documents.

## 🚀 Features

- **Hybrid Text Extraction**: Intelligent combination of digital text extraction and OCR processing
- **Multi-Core Processing**: Leverages all available CPU cores for maximum speed
- **Smart Detection**: Automatically detects whether pages need OCR or can use faster digital extraction
- **User-Friendly Interface**: Built with Streamlit for easy use
- **Fast & Efficient**: Optimized for processing large PDF files (up to 100MB)

## 🛠️ Technologies

- **PyMuPDF (fitz)**: Fast PDF processing and rendering
- **RapidOCR**: High-performance OCR engine with ONNX runtime
- **Streamlit**: Modern web UI framework
- **Python Multiprocessing**: Parallel processing across CPU cores

## 📦 Installation

1. Clone the repository:
```bash
git clone https://github.com/KayasthaSahil/OCR_Tool.git
cd OCR_Tool
```

2. Create a virtual environment:
```bash
python -m venv venv
```

3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

4. Install dependencies:
```bash
pip install -r requirements.txt
```

## 🎯 Usage

1. Start the application:
```bash
streamlit run app.py
```

2. Open your browser (usually auto-opens to `http://localhost:8501`)

3. Upload a PDF file (max 100MB)

4. Click "Start Extraction" and wait for processing

5. Download the extracted text or preview it in the browser

## 🏗️ Architecture

- **app.py**: Main Streamlit UI with parallel processing orchestration
- **ocr_worker.py**: Worker module for parallel page processing
- **ocr_engine.py**: Legacy serial processor (for reference)

## 📊 Performance

- Processes pages in parallel using all available CPU cores
- Hybrid approach: Fast digital extraction + OCR fallback
- Optimized for speed and accuracy

## 🔄 Current Status

**Active Development**: Performance improvements and optimizations in progress.

See [ANALYSIS_AND_IMPROVEMENTS.md](ANALYSIS_AND_IMPROVEMENTS.md) for planned enhancements.

## 📝 License

MIT License - Feel free to use and modify

## 👤 Author

Sahil Kayastha
- GitHub: [@KayasthaSahil](https://github.com/KayasthaSahil)

---

**Built with ❤️ for fast and efficient document processing**
