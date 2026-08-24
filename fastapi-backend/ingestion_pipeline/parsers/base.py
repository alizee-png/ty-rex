from abc import ABC, abstractmethod
from typing import Dict, Any, BinaryIO

class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_obj: BinaryIO, filename: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Retourne toujours:
        {
            "content": "texte nettoyé...",
            "metadata": {"type": "pdf", "filename": "doc.pdf", ...}
        }
        """
        pass