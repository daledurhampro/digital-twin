from pypdf import PdfReader
from pathlib import Path
import json



# Read LinkedIn PDF
try:
    linkedin = ""
    folder = Path("./data")
    for pdf_path in folder.glob("*.pdf"):
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                linkedin += text
except FileNotFoundError:
    linkedin = "Could not locate linkedin or resume PDF's"

# Read other data files
with open("./data/summary.txt", "r", encoding="utf-8") as f:
    summary = f.read()
    
with open("./data/summary.txt", "r", encoding="utf-8") as f:
    summary = f.read()

with open("./data/style.txt", "r", encoding="utf-8") as f:
    style = f.read()

with open("./data/facts.json", "r", encoding="utf-8") as f:
    facts = json.load(f)