from typing import Any, BinaryIO, Dict, List
from langchain_core.documents import Document
from pypdf import PdfReader
from .base import BaseParser

#dans parser, ajouter code pour gérer un format mail
class PDFParser(BaseParser):
    def parse(self, file_obj: BinaryIO, filename: str, **kwargs: Any) -> Dict[str, Any]:
        reader = PdfReader(file_obj)
        documents: List[Document] = []

        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""

            if not text.strip():
                continue

            doc = Document(
                page_content=text.strip(),
                metadata={
                    "filename": filename,
                    "type": "pdf",
                    "page_number": page_num,
                    "total_pages": len(reader.pages),
                },
            )
            documents.append(doc)

        return {
            "content": documents,
            "metadata": {
                "filename": filename,
                "type": "pdf",
                "total_chunks": len(documents),
            },
        }