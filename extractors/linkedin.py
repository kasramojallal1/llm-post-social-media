import json
from pathlib import Path
from PyPDF2 import PdfReader

def extract_linkedin(pdf_path: str, output_path: str):
    reader = PdfReader(pdf_path)
    text = " ".join(page.extract_text() or "" for page in reader.pages)

    # Simple stub parsing – extend later
    data = {
        "source": "linkedin",
        "raw_text": text.strip()
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    extract_linkedin("data/linkedin.pdf", "processed/linkedin.json")