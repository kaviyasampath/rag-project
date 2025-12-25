import os
import re
import pdfplumber

DATA_DIR = r"C:\Users\KAVYA\OneDrive\Desktop\naac_project\data"
OUTPUT_DIR = r"C:\Users\KAVYA\OneDrive\Desktop\naac_project\cleaned_text"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    text = text.encode("ascii", "ignore").decode()
    text = re.sub(r'Page\s*\d+|\d+/\d+', '', text, flags=re.IGNORECASE)

    return text.strip()


def extract_and_clean_pdf(path):
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    cleaned = clean_text(text)
    return cleaned


def process_all_pdfs():
    for file in os.listdir(DATA_DIR):
        if file.lower().endswith(".pdf"):
            full_path = os.path.join(DATA_DIR, file)
            print(f"\nExtracting + cleaning → {file}")

            cleaned_text = extract_and_clean_pdf(full_path)

            output_path = os.path.join(
                OUTPUT_DIR, file.replace(".pdf", "_cleaned.txt")
            )

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(cleaned_text)

            print(f"Saved cleaned file → {output_path}")


if __name__ == "__main__":
    process_all_pdfs()

