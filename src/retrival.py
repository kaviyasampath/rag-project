import chromadb
from sentence_transformers import SentenceTransformer

# Load Chroma client
client = chromadb.Client()

# Load the collection created earlier
collection = client.get_collection(name="naac_chunks")

# Load the same embedding model used during indexing
model = SentenceTransformer("all-MiniLM-L6-v2")


def embed_query(query):
    return model.encode(query).tolist()


def search(query, k=5):
    print(f"\nSearching for → {query}\n")

    query_embedding = embed_query(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k
    )

    return results


if __name__ == "__main__":
    # Example usage
    query = "Details about teaching learning process for criterion 2"
    results = search(query, k=5)

    for i in range(len(results["documents"][0])):
        print(f"Result {i+1}:")
        print("Chunk Text:", results["documents"][0][i][:300], "...")
        print("File:", results["metadatas"][0][i]["source_file"])
        print("Chunk Name:", results["metadatas"][0][i]["chunk_name"])
        print("------")