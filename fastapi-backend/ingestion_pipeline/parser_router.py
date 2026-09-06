import os
from typing import Any, BinaryIO, Dict, Type

from ingestion_pipeline.parsers.base import BaseParser
from ingestion_pipeline.parsers.text_parser import PDFParser, WordParser
from ingestion_pipeline.parsers.planning_parser import PlanningParser
from ingestion_pipeline.parsers.report_parser import ExcelReportParser, WordReportParser
from ingestion_pipeline.parsers.planning_parser import PlanningParser
from ingestion_pipeline.parsers.mail_parser import OutlookMailParser, GenericMailParser

class ParserRouter:

    def __init__(self):

        #clés parsers
        self._parsers: Dict[tuple[str, str], Type[BaseParser]] = {
            ("texte", "pdf"): PDFParser, 
            ("texte", "docx"): WordParser, 
            ("tableau", "docx"): WordReportParser,
            ("tableau", "xlsx"): ExcelReportParser,
            ("tableau", "xls"): ExcelReportParser,
            ("planning", "xlsx"): PlanningParser,
            ("mail", "msg"): OutlookMailParser,
            ("mail", "eml"): GenericMailParser,
        }

    def parse(self, file_obj: BinaryIO, filename: str, doc_type: str, **kwargs: Any) -> Dict[str, Any]:

        ext = os.path.splitext(filename)[1].lstrip(".").lower()
        route_key = (doc_type, ext)

        if not doc_type or route_key not in self._parsers:
            valid_types = list(set(k[0] for k in self._parsers.keys()))
            raise ValueError(
                f"Combinaison non supportée : type='{doc_type}', extension='{ext}'. " 
                f"Types autorisés : {valid_types}"
            )
        
        #sécurité = rembobine la cassette
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)

        parser_cls = self._parsers[route_key]
        parser_instance = parser_cls()

        #retourne le paser correspondant
        return parser_instance.parse(file_obj, filename, **kwargs)

