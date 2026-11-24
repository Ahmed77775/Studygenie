"""Optional third-party packages. Each one is None when it is not installed,
and the features that need it explain what to install instead of crashing."""

try:
    from ollama import chat
except ImportError:
    chat = None

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = ImageDraw = None

try:
    from fpdf import FPDF
except ImportError:
    FPDF = None
