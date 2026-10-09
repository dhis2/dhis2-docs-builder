# Pytest setup for the book builder tests.
# Puts tools/books on the import path, as it is when book_builder.py runs as a script.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
