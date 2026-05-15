import sys
from unittest.mock import MagicMock

# Mock external SDK modules before any the_curator imports during collection.
# VertexClient and PodcastGeneration are instantiated at module level in main.py,
# so these must be in sys.modules before test files are imported.
for _mod in [
    "google.genai",
    "google.genai.types",
    "google.cloud",
    "google.cloud.storage",
    "anthropic",
]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()
