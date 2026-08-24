import os
from typing import Any, BinaryIO, Dict, Type

from ingestion_pipeline.parsers.base import BaseParser
from ingestion_pipeline.parsers.pdf_parser import PDFParser
from ingestion_pipeline.parsers.planning_parser import PlanningParser
from ingestion_pipeline.parsers.report_parser import ExcelReportParser, WordReportParser

class ParserRouter:

    def __init__(self):

        #clés parsers
        self._parsers: Dict[tuple[str, str], Type[BaseParser]] = {
            ("pdf", "pdf"): PDFParser, #ajouter mails ?
            ("cr", "docx"): WordReportParser,
            ("cr", "xlsx"): ExcelReportParser,
            ("cr", "xls"): ExcelReportParser,
            ("planning", "xlsx"): PlanningParser,
        }

    def parse(self, file_obj: BinaryIO, filename: str, doc_type: str, **kwargs: Any) -> Dict[str, Any]:

        ext = os.path.splitext(filename)[1].lstrip(".").lower()
        route_key = (doc_type, ext)

        if not doc_type or route_key not in self._parsers:
            valid_types = list(set(k[0] for k in self._parsers.keys()))
            raise ValueError(
                f"Combinaison non supportée : type='{doc_type}', extension='{ext}'. " #à envoyer dans l'interface
                f"Types autorisés : {valid_types}"
            )
        #sécurité = rembobine la cassette
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)

        parser_cls = self._parsers[route_key]
        parser_instance = parser_cls()

        #retourne le paser correspondant
        return parser_instance.parse(file_obj, filename, **kwargs)

