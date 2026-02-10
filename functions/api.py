import os
import sys

# Ensure the root directory (parent of 'functions' and 'app') is in the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.insert(0, root_dir)

from mangum import Mangum
from app.main import app

handler = Mangum(app)
