"""Keep the automated suite deterministic and free of model downloads."""

import os


os.environ["WIKI_HAMI_OCR_BACKEND"] = "mock"
os.environ["WIKI_HAMI_FIGURE_TABLE_BACKEND"] = "mock"
os.environ["WIKI_HAMI_STAMP_SIGNATURE_BACKEND"] = "mock"
