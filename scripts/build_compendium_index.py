import fitz  # PyMuPDF
import json
import os
import re
from pathlib import Path

# The PDFs to index on the Desktop
PDF_FILES = [
    "StarsWithoutNumberRevised-DeluxeEdition-011418.pdf",
    "WorldsWithoutNumber_DeluxePDF_040221.pdf",
    "CitiesWithoutNumber_Deluxe_083023.pdf",
    "WolvesOfGod_042020.pdf"
]

def clean_text(text: str) -> str:
    """Removes excessive whitespace and unprintable characters from PDF text."""
    # Replace multiple spaces/newlines with a single space
    text = re.sub(r'\s+', ' ', text)
    # Remove non-ascii characters that might break json or discord
    text = text.encode('ascii', 'ignore').decode('ascii')
    return text.strip()

def extract_pdf_rules(desktop_path: str, data_dir: str):
    """
    Extracts text from each page of the PDFs and saves them into a searchable JSON format.
    """
    output_index = []
    
    for filename in PDF_FILES:
        pdf_path = os.path.join(desktop_path, filename)
        
        if not os.path.exists(pdf_path):
            print(f"Warning: PDF not found: {pdf_path}")
            continue
            
        print(f"Indexing {filename}...")
        
        # Determine a shorter book name for the embed
        book_name = filename.split('_')[0].replace("WithoutNumber", " WN").replace("Revised-DeluxeEdition-011418", "").replace("DeluxePDF", "")
        book_name = book_name.replace(".pdf", "")

        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                # Keep text block structure if possible instead of just raw text
                text = page.get_text()
                cleaned = clean_text(text)
                
                # We skip completely blank pages or pages with almost no text
                if len(cleaned) > 50:
                    output_index.append({
                        "book": book_name,
                        # PyMuPDF page numbers are 0-indexed, and physical books usually have 
                        # cover pages, so +1 is a good rough estimate for the PDF page number.
                        "page": page_num + 1,
                        "content": cleaned
                    })
            doc.close()
        except Exception as e:
            print(f"Error processing {filename}: {e}")

    output_path = os.path.join(data_dir, 'rules_index.json')
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_index, f, indent=2)
        print(f"\nSuccessfully built rule index with {len(output_index)} pages indexed.")
        print(f"Saved to: {output_path}")
    except Exception as e:
         print(f"Failed to save index: {e}")

if __name__ == "__main__":
    desktop_dir = r"C:\Users\John Morris\Desktop"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    data_directory = os.path.join(project_dir, 'data')
    
    # Ensure data dir exists
    os.makedirs(data_directory, exist_ok=True)
    
    extract_pdf_rules(desktop_dir, data_directory)
