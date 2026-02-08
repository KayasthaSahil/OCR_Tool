"""
Configuration file for OCR Tool
Tunable parameters for performance and quality optimization
"""

# Worker Pool Configuration
MAX_WORKERS = None  # None = Auto-detect (CPU count - 1), or set specific number
RESERVE_CORES = 1   # Number of cores to reserve for system/UI

# Image Quality Configuration
DPI_THRESHOLD_LOW = 500    # Below this = low-res scan (needs 3x scaling)
DPI_THRESHOLD_HIGH = 1000  # Above this = high-res digital (needs 1.5x scaling)

# Text Detection Configuration
TEXT_LENGTH_DIGITAL = 100   # Characters needed for "digital" classification
TEXT_LENGTH_MIXED = 50      # Characters needed for "mixed" classification
MIN_TEXT_BLOCKS = 5         # Minimum blocks for digital classification

# Performance Configuration
TIMEOUT_PER_PAGE = 60       # Maximum seconds per page before timeout
MAX_RETRIES = 2             # Number of retry attempts for failed pages
RETRY_BACKOFF_BASE = 0.5    # Base seconds for exponential backoff

# Memory Management
FORCE_GC_AFTER_PAGE = True  # Run garbage collection after each page

# File Limits
MAX_FILE_SIZE_MB = 100      # Maximum allowed PDF file size

# UI Configuration
PREVIEW_LENGTH = 2000       # Characters to show in text preview
SHOW_EMOJIS = True          # Use emoji icons in UI

# Advanced Options (Future Use)
ENABLE_CACHING = False      # Enable result caching (not yet implemented)
ENABLE_PREPROCESSING = True # Enable image preprocessing (not yet implemented)
BATCH_SIZE = 1              # Pages to process per batch (not yet implemented)
