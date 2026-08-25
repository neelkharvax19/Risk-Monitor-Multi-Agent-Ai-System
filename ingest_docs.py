import os
import glob
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import pinecone
from pinecone import Pinecone, ServerlessSpec
import time

# Load environment variables
load_dotenv()

# Configuration
DOCS_FOLDER = "docs"
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = "risk-policies-index"  # Matched to tools.py
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Free, local, 384 dimensions

# Ensure docs folder exists
if not os.path.exists(DOCS_FOLDER):
    os.makedirs(DOCS_FOLDER)

# Step 1: Initialize embedding model (runs locally, no API key needed)
print("Loading embedding model...")
embedder = SentenceTransformer(EMBEDDING_MODEL)
print("Embedding model loaded.")

# Step 2: Initialize Pinecone
if not PINECONE_API_KEY or PINECONE_API_KEY == "your_key_here":
    raise ValueError("PINECONE_API_KEY not found or invalid in .env file. Please add your real Pinecone API key.")

pc = Pinecone(api_key=PINECONE_API_KEY)

# Step 3: Check if index exists, create if not
if INDEX_NAME in pc.list_indexes().names():
    print(f"Deleting old Pinecone index: {INDEX_NAME}...")
    pc.delete_index(INDEX_NAME)

print(f"Creating Pinecone index: {INDEX_NAME}...")
pc.create_index(
    name=INDEX_NAME,
    dimension=384,  # Must match the embedding model dimension (all-MiniLM-L6-v2)
    metric="cosine",
    spec=ServerlessSpec(
        cloud="aws",
        region="us-east-1"  # Use any region available in your Pinecone account
    )
)
# Wait for index to be ready
while not pc.describe_index(INDEX_NAME).status['ready']:
    time.sleep(1)
print("Index created and ready.")

# Step 4: Connect to the index
index = pc.Index(INDEX_NAME)

# Step 5: Load all PDFs from /docs folder
pdf_files = glob.glob(os.path.join(DOCS_FOLDER, "*.pdf"))
if not pdf_files:
    print(f"Warning: No PDF files found in '{DOCS_FOLDER}' folder. Please add at least one PDF.")
    exit(1)

print(f"Found {len(pdf_files)} PDF file(s).")

all_chunks = []
for pdf_path in pdf_files:
    print(f"Loading: {pdf_path}")
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()
    
    # Split into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,      # Adjust based on your policy size
        chunk_overlap=50,    # Overlap to preserve context
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = text_splitter.split_documents(documents)
    print(f"  -> Created {len(chunks)} chunks from {os.path.basename(pdf_path)}")
    all_chunks.extend(chunks)

print(f"Total chunks to upsert: {len(all_chunks)}")

# Step 6: Generate embeddings and upsert in batches
batch_size = 50  # Pinecone free tier supports up to 100 per batch
for i in range(0, len(all_chunks), batch_size):
    batch = all_chunks[i:i+batch_size]
    
    # Generate embeddings for this batch
    texts = [chunk.page_content for chunk in batch]
    embeddings = embedder.encode(texts, convert_to_numpy=True).tolist()
    
    # Prepare vectors for upsert
    vectors = []
    for j, chunk in enumerate(batch):
        vector_id = f"chunk_{i+j}_{hash(chunk.page_content)}"
        vectors.append({
            "id": vector_id,
            "values": embeddings[j],
            "metadata": {
                "source": chunk.metadata.get("source", "unknown"),
                "page": chunk.metadata.get("page", 0),
                "text": chunk.page_content  # Store the original text for retrieval
            }
        })
    
    # Upsert to Pinecone
    index.upsert(vectors=vectors)
    print(f"Success: Upserted batch {i//batch_size + 1} / {(len(all_chunks)//batch_size)+1}")

print(f"Done! {len(all_chunks)} chunks successfully upserted to Pinecone index '{INDEX_NAME}'.")
