"""
OfficeMind Vision Module
Dual-layer screen understanding:
  Layer 1: pHash perceptual hashing — fast change detection (no GPU)
  Layer 2: Qwen-VL-Chat semantic understanding — deep visual reasoning (GPU)
"""

from .screen_reader import ScreenReader
from .phash_filter import PHashFilter

__all__ = ["ScreenReader", "PHashFilter"]
