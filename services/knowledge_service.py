from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import os
import pickle

class KnowledgeService:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            
        self.index_path = os.path.join(data_dir, "rules.index")
        self.metadata_path = os.path.join(data_dir, "rules_metadata.pkl")
        
        # Load Model (Lightweight, CPU friendly)
        print("Loading Knowledge Base Model (all-MiniLM-L6-v2)...")
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Load or Create Index
        if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
            print("Loading existing Rules Index...")
            self.index = faiss.read_index(self.index_path)
            with open(self.metadata_path, "rb") as f:
                self.chunks = pickle.load(f)
        else:
            print("Creating new Rules Index...")
            self.dimension = 384 # Dimension of MiniLM
            self.index = faiss.IndexFlatL2(self.dimension)
            self.chunks = []

    def ingest_pdf(self, pdf_path):
        """
        Reads a PDF, chunks it, embeds it, and adds to index.
        """
        try:
            print(f"Ingesting PDF: {pdf_path}")
            reader = PdfReader(pdf_path)
            text = ""
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            
            # Simple chunking by paragraph (approx 500 chars intersection)
            raw_chunks = [t.strip() for t in text.split('\n\n') if len(t.strip()) > 50]
            
            if not raw_chunks:
                return "PDF extracted but contains no usable text (maybe scanned image?)."

            # Create Embeddings
            embeddings = self.embedder.encode(raw_chunks)
            
            # Add to Index
            self.index.add(np.array(embeddings).astype('float32'))
            self.chunks.extend(raw_chunks)
            
            # Save
            self.save_index()
            return f"Successfully ingested {len(raw_chunks)} rule blocks from {os.path.basename(pdf_path)}."
            
        except Exception as e:
            return f"Error ingesting PDF: {e}"

    def query_rules(self, query, k=3):
        """
        Finds top k relevant rule chunks.
        """
        if self.index.ntotal == 0:
            return None
            
        params_emb = self.embedder.encode([query])
        D, I = self.index.search(np.array(params_emb).astype('float32'), k)
        
        results = []
        for i in range(k):
            idx = I[0][i]
            if idx != -1:
                results.append(self.chunks[idx])
        
        return results

    def save_index(self):
        faiss.write_index(self.index, self.index_path)
        with open(self.metadata_path, "wb") as f:
            pickle.dump(self.chunks, f)
