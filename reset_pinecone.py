import os
from dotenv import load_dotenv
import pinecone

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = "risk-policies-index"  # Note: updated to your actual plural index name!

if not PINECONE_API_KEY:
    raise ValueError("PINECONE_API_KEY not found in .env")

pc = pinecone.Pinecone(api_key=PINECONE_API_KEY)

# Check if the index exists
if INDEX_NAME in pc.list_indexes().names():
    print(f"Deleting index: {INDEX_NAME}...")
    pc.delete_index(INDEX_NAME)
    print("Index deleted successfully.")
else:
    print(f"Index '{INDEX_NAME}' does not exist.")
