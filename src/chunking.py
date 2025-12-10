import os
import re

INPUT_DIR = r"C:\Users\KAVYA\OneDrive\Desktop\naac_project\cleaned_text"
OUTPUT_DIR = r"C:\Users\KAVYA\OneDrive\Desktop\naac_project\chunks"

os.makedirs(OUTPUT_DIR, exist_ok=True)

CHUNK_SIZE = 500  # ~500 words per chunk


def chunk_text(text, chunk_size=CHUNK_SIZE):
    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)

    return chunks


def process_all_cleaned_files():
    for file in os.listdir(INPUT_DIR):
        if file.lower().endswith(".txt"):

            input_path = os.path.join(INPUT_DIR, file)
            
            print(f"\nChunking → {file}")

            with open(input_path, "r", encoding="utf-8") as f:
                text = f.read()

            chunks = chunk_text(text)

            # Create a folder for chunk output
            base_name = file.replace(".txt", "")
            chunk_folder = os.path.join(OUTPUT_DIR, base_name)
            os.makedirs(chunk_folder, exist_ok=True)

            # Save each chunk
            for idx, chunk in enumerate(chunks):
                chunk_path = os.path.join(chunk_folder, f"chunk_{idx}.txt")

                with open(chunk_path, "w", encoding="utf-8") as cf:
                    cf.write(chunk)

            print(f"Saved {len(chunks)} chunks → {chunk_folder}")


if __name__ == "__main__":
    process_all_cleaned_files()
