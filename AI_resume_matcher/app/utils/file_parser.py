from pypdf import PdfReader

def extract_text_from_pdf(file_path: str) -> str:
    reader = PdfReader(file_path)
    texts = []

    for page in reader.pages:
        page_text = page.extract_text() or ""
        texts.append(page_text)

    return "\n".join(texts).strip()