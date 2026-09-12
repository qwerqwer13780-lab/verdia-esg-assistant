import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import faiss
import numpy as np
import pymupdf4llm
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

from app.config import CHUNKS_PATH, EMBEDDING_MODEL, INDEX_PATH, MARKDOWN_DIR, PDF_DIR, STORAGE_DIR

headers_to_split_on = [('#', 'h1'), ('##', 'h2'), ('###', 'h3'), ('####', 'h4')]
header_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on, strip_headers=False)
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1200,
    chunk_overlap=180,
    separators=['\n\n', '\n', '. ', ' ', ''],
)


def main():
    pdf_files = sorted(PDF_DIR.glob('*.pdf'))
    if not pdf_files:
        raise ValueError(f'No PDFs found in {PDF_DIR}. Add the approved ESG source PDFs first.')

    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)
    markdown_documents = []

    for pdf_path in pdf_files:
        print(f'Extracting: {pdf_path.name}')
        pages = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True)
        full_markdown = []

        for page_number, page in enumerate(pages, start=1):
            page_text = page.get('text', '').strip()
            if not page_text:
                continue
            full_markdown.append(page_text)
            markdown_documents.append({
                'source': pdf_path.name,
                'page': page_number,
                'text': page_text,
            })

        (MARKDOWN_DIR / f'{pdf_path.stem}.md').write_text(
            '\n\n'.join(full_markdown),
            encoding='utf-8',
        )

    chunks = []
    for doc in markdown_documents:
        sections = header_splitter.split_text(doc['text'])
        for section in sections:
            heading_path = ' > '.join(
                section.metadata[key]
                for key in ['h1', 'h2', 'h3', 'h4']
                if section.metadata.get(key)
            )
            for chunk_text in text_splitter.split_text(section.page_content):
                text = chunk_text.strip()
                if text:
                    chunks.append({
                        'text': text,
                        'source': doc['source'],
                        'page': doc['page'],
                        'heading': heading_path,
                    })

    if not chunks:
        raise ValueError('No chunks were created from the ESG source PDFs.')

    print(f'Loading embedding model: {EMBEDDING_MODEL}')
    embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    chunk_texts = [f'passage: {chunk["text"]}' for chunk in chunks]
    embeddings = embedding_model.encode(
        chunk_texts,
        batch_size=32,
        normalize_embeddings=True,
        show_progress_bar=True,
        convert_to_numpy=True,
    )
    embeddings = np.asarray(embeddings, dtype='float32')

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    faiss.write_index(index, str(INDEX_PATH))

    with CHUNKS_PATH.open('w', encoding='utf-8') as file:
        json.dump(chunks, file, ensure_ascii=False)

    print(f'PDFs: {len(pdf_files)}')
    print(f'Chunks: {len(chunks)}')
    print(f'Index vectors: {index.ntotal}')
    print(f'Saved: {INDEX_PATH}')
    print(f'Saved: {CHUNKS_PATH}')


if __name__ == '__main__':
    main()
