import os
import sys
import pickle
import urllib.request
import fitz  # PyMuPDF
from pathlib import Path

# Add project root to path so we can import app modules
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.services.rag_service import FAISSRetrieverService
import faiss

# A few tiny judgments from the real AWS open data registry for demonstration
AWS_PDFS = [
    "https://indian-high-court-judgments.s3.amazonaws.com/data/pdf/year=1950/court=27_1/bench=newos/HCBM020000011949_1_2006-12-22.pdf",
    "https://indian-high-court-judgments.s3.amazonaws.com/data/pdf/year=1950/court=27_1/bench=newos/HCBM020000011950_1_2006-01-13.pdf",
    "https://indian-high-court-judgments.s3.amazonaws.com/data/pdf/year=1950/court=27_1/bench=newos/HCBM020000041950_1_2006-11-21.pdf"
]

def download_and_extract_text(urls):
    texts = []
    print(f"Downloading and extracting {len(urls)} PDFs from AWS Open Data Registry...")
    for idx, url in enumerate(urls):
        print(f"[{idx+1}/{len(urls)}] Processing {url.split('/')[-1]}...")
        try:
            # Download to memory
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                pdf_data = response.read()
                
            # Extract text using PyMuPDF
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text() + "\n"
            
            # Clean and add header
            text = text.strip()
            if text:
                # Basic chunking if it's too long, but these are small files.
                texts.append(f"Source: {url}\n\n{text}")
                print(f"  -> Extracted {len(text)} characters.")
            else:
                print("  -> Empty text extracted.")
        except Exception as e:
            print(f"  -> Error processing {url}: {e}")
            
    return texts

def main():
    os.makedirs(os.path.join(project_root, "data", "rag_index"), exist_ok=True)
    
    # 1. Get raw texts from AWS PDFs
    texts = download_and_extract_text(AWS_PDFS)
    
    if not texts:
        print("Failed to extract any text. Aborting index build.")
        return
        
    # 2. Initialize the RAG service and build the index
    print("\nInitializing FAISS Index and generating embeddings (this may take a moment)...")
    rag_service = FAISSRetrieverService()
    rag_service.initialize_index_from_texts(texts)
    
    # 3. Save the index and metadata
    index_path = os.path.join(project_root, "data", "rag_index", "index.faiss")
    meta_path = os.path.join(project_root, "data", "rag_index", "metadata.pkl")
    
    print(f"\nSaving index to {index_path}...")
    faiss.write_index(rag_service.faiss_index, index_path)
    
    print(f"Saving metadata to {meta_path}...")
    with open(meta_path, "wb") as f:
        pickle.dump(rag_service.metadata, f)
        
    print("\nDone! The local demo RAG index is now built and ready.")
    print("The backend will automatically load this index on startup.")

if __name__ == "__main__":
    main()
