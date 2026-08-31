"""
PythonAnywhere WSGI Configuration
Allows running the 24/7 FB Messenger Bot directly as a Web App on PythonAnywhere.
"""

import sys
import os

# Add current project directory to sys.path
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# Import Flask app
from server import app as application
