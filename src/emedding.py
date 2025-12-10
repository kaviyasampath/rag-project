import os
from sentence_transformers import SentenceTransformer
import chromadb

CHUNKS_DIR = r"C:\Users\KAVYA\OneDrive\Desktop\naac_project\chunks"

# Initialize ChromaDB client
client = chromadb.Client()

# Create or load a collection
collection = client.create_collection(name="naac_chunks")

# Load embedding model (offline)
model = SentenceTransformer("all-MiniLM-L6-v2")


def embed_text(text):
    return model.encode(text).tolist()


def process_all_chunks():
    for folder in os.listdir(CHUNKS_DIR):
        folder_path = os.path.join(CHUNKS_DIR, folder)

        if os.path.isdir(folder_path):
            print(f"\nEmbedding chunks from → {folder}")

            for file in os.listdir(folder_path):
                if file.endswith(".txt"):

                    chunk_path = os.path.join(folder_path, file)

                    with open(chunk_path, "r", encoding="utf-8") as f:
                        chunk_text = f.read()

                    embedding = embed_text(chunk_text)

                    # Use unique ID for each chunk
                    chunk_id = f"{folder}_{file}"

                    # Add to vector DB
                    collection.add(
                        ids=[chunk_id],
                        embeddings=[embedding],
                        metadatas=[{
                            "source_file": folder,
                            "chunk_name": file
                        }],
                        documents=[chunk_text]
                    )

                    print(f"Embedded {file}")


if __name__ == "__main__":
    process_all_chunks()
