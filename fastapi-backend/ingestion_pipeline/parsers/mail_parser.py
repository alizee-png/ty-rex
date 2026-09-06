from typing import Dict, Any, BinaryIO
from .base import BaseParser
from langchain_core.documents import Document
from bs4 import BeautifulSoup

import extract_msg
import email
from email import policy

#parcours utilisateur : dépôt mail -> traitement texte + pj
#pas de gestion des pièces jointes pour l'instant
class OutlookMailParser(BaseParser):
    
    def parse(self, file_obj: BinaryIO, filename: str, **kwargs: Any) -> Dict[str, Any]:
        msg_any: Any = extract_msg.openMsg(file_obj)

        sujet = msg_any.subject
        expéditeur = msg_any.sender
        destinataire = msg_any.to
        date = msg_any.date

        raw_html = msg_any.htmlBody
        if raw_html:
            soup = BeautifulSoup(raw_html, "html.parser")
            corps_brut = soup.get_text(separator="\n")
            lignes = [ligne.strip() for ligne in corps_brut.splitlines() if ligne.strip()]
            corps = "\n".join(lignes)
        else:
            corps = msg_any.body or ""

        chunks = [Document(
                page_content=corps,
                metadata={
                    "filename": filename,
                    "type": "mail",
                    "subject": sujet,
                    "sender": expéditeur,
                    "recipient": destinataire,
                    "date": str(date),
                }
            )
        ]

        return {
        "content": chunks,
        "metadata": {
            "filename": filename,
            "type": "mail",
            "subject": sujet,
            "sender": expéditeur,
            "recipient": destinataire,
            "date": str(date),
        },
    }


#pas de gestion des pièces jointes pour l'instant
class GenericMailParser(BaseParser):
    
    def parse(self, file_obj: BinaryIO, filename: str, **kwargs: Any) -> Dict[str, Any]:

        msg = email.message_from_binary_file(file_obj, policy=policy.default)

        sujet = msg["subject"]
        expéditeur = msg["from"]
        destinataire = msg["to"]
        date = msg["date"]

        corps = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()

                if content_type == "text/plain" or content_type == "text/html":
                    corps = part.get_content()
                    break

        chunks = [Document(
                page_content=corps,
                metadata={
                    "filename": filename,
                    "type": "mail",
                    "subject": sujet,
                    "sender": expéditeur,
                    "recipient": destinataire,
                    "date": str(date),
                }
            )
        ]
        
        return {
        "content": chunks,
        "metadata": {
            "filename": filename,
            "type": "mail",
            "subject": sujet,
            "sender": expéditeur,
            "recipient": destinataire,
            "date": str(date),
        },
    }
