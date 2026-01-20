import os
import chromadb
from sentence_transformers import SentenceTransformer
import google.generativeai as genai


# ----------------------------
# CONFIG
# ----------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

CHROMA_PATH = r"C:/Users/KAVYA/OneDrive/Desktop/naac_project/chromadb"
COLLECTION_NAME = "naac_chunks"

EMBED_MODEL_NAME = "all-MiniLM-L6-v2"


# ----------------------------
# SETUP CHECKS
# ----------------------------
if not GEMINI_API_KEY:
    raise ValueError(
        "❌ GEMINI_API_KEY not found.\n\n"
        "✅ Set it in PowerShell like this:\n"
        "$env:GEMINI_API_KEY='your_key_here'\n"
    )


# ----------------------------
# GEMINI SETUP
# ----------------------------
genai.configure(api_key=GEMINI_API_KEY)

print("\n==============================")
print("✅ AVAILABLE GEMINI MODELS FOR YOUR API KEY")
print("==============================\n")

available_models = []
for m in genai.list_models():
    # Print all model names and their supported methods
    print(m.name, "->", m.supported_generation_methods)

    # Store models that support generateContent
    if "generateContent" in m.supported_generation_methods:
        available_models.append(m.name)

# If no model supports generateContent, we cannot proceed
if not available_models:
    raise ValueError(
        "\n❌ No available Gemini models support generateContent for your API key.\n"
        "✅ Please check your API key permissions in Google AI Studio.\n"
    )

# Pick the first working model automatically
WORKING_MODEL = available_models[0]
print("\n✅ Auto-selected model for generation:", WORKING_MODEL)

gemini_model = genai.GenerativeModel(WORKING_MODEL)


# ----------------------------
# CHROMADB SETUP
# ----------------------------
client_chroma = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client_chroma.get_or_create_collection(name=COLLECTION_NAME)

embedder = SentenceTransformer(EMBED_MODEL_NAME)


# ----------------------------
# RETRIEVAL
# ----------------------------
def retrieve_chunks(query: str, k: int = 5):
    query_vec = embedder.encode(query).tolist()
    results = collection.query(query_embeddings=[query_vec], n_results=k)
    return results


def build_context(results, max_chars: int = 6000):
    docs = results["documents"][0]
    metas = results["metadatas"][0]

    blocks = []
    size = 0

    for doc, meta in zip(docs, metas):
        block = f"[SOURCE: {meta.get('source_file')} | {meta.get('chunk_name')}]\n{doc}\n"
        if size + len(block) > max_chars:
            break
        blocks.append(block)
        size += len(block)

    return "\n\n".join(blocks)


# ----------------------------
# GENERATION
# ----------------------------
def generate_naac_response(query: str, context: str):
    prompt = f"""
You are an expert NAAC SSR report writer.

STRICT RULES:
1) Use ONLY the provided context.
2) Do NOT invent numbers, departments, events, or dates.
3) If data is missing, say: "Data not available in provided documents".
4) Keep a formal academic NAAC SSR tone.
5) Use headings and structured paragraphs.
6) At the end, include an "Evidence Used" list referencing sources.

CONTEXT:
{context}

TASK:
Write a NAAC-ready response for:
{query}

OUTPUT FORMAT:
1) Overview
2) Key Practices / Activities
3) Outcomes / Impact
4) Evidence Used (source_file + chunk_name)
"""

    response = gemini_model.generate_content(prompt)
    return response.text


def run_rag(query: str, k: int = 5):
    results = retrieve_chunks(query, k=k)
    context = build_context(results)
    answer = generate_naac_response(query, context)
    return answer


# ----------------------------
# MAIN
# ----------------------------
if __name__ == "__main__":
    user_query = "Generate NAAC Criterion 2: Teaching Learning and Evaluation summary"
    output = run_rag(user_query, k=5)

    print("\n==============================")
    print("✅ NAAC GENERATED OUTPUT")
    print("==============================\n")
    print(output)

    # Save output to file
    with open("naac_generated_output.txt", "w", encoding="utf-8") as f:
        f.write(output)

    print("\n✅ Saved output to naac_generated_output.txt")

