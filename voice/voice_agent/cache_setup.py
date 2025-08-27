"""
HuggingFace cache setup - must be imported first before any HF-related imports.
"""

import os
from pathlib import Path
from loguru import logger


def setup_hf_cache():
    """Set up HuggingFace cache directory globally."""
    # Get the project root directory (voice/)
    project_root = Path(__file__).parent.parent
    cache_dir = project_root / ".hf_cache"
    cache_dir.mkdir(exist_ok=True)
    cache_dir_str = str(cache_dir.absolute())
    
    # Set all HuggingFace cache environment variables
    os.environ['HF_HOME'] = cache_dir_str
    os.environ['HF_HUB_CACHE'] = cache_dir_str
    os.environ['TRANSFORMERS_CACHE'] = cache_dir_str
    os.environ['HF_DATASETS_CACHE'] = cache_dir_str
    os.environ['HUGGINGFACE_HUB_CACHE'] = cache_dir_str
    
    logger.info(f"🗂️ HuggingFace cache directory set to: {cache_dir_str}")
    return cache_dir_str


# Set up cache immediately when this module is imported
setup_hf_cache()