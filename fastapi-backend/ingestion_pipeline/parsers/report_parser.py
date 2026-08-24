from typing import Dict, Any, BinaryIO
from .base import BaseParser
import docx

import pandas as pd

class ExcelReportParser(BaseParser):

    def parse(self, file_obj: BinaryIO, filename: str, **kwargs: Any) -> Dict[str, Any]:

        sheet_name: str = kwargs.get("sheet_name", "1")
        template: list = kwargs.get("template", ["Noté le", "Sujet", "Par", "Pour le", "Fait le"])

        excel_file = pd.ExcelFile(file_obj)
        df = excel_file.parse(sheet_name=sheet_name)
        #check if this rough cleaning is enough in test
        df = df.dropna(how="all", axis=0)
        df = df.dropna(how="all", axis=1)

        #we apply the template
        df = df.iloc[:, : len(template)]
        df.columns = template

        #conversion des colonnes en mode string pour stockage parquet
        df = df.astype(str)

        return {
            "content": df,
            "metadata": {
                "filename": filename,
                "type": "cr",
                "template" : template,
            }

        }


class WordReportParser(BaseParser):

    def parse(self, file_obj: BinaryIO, filename: str, **kwargs: Any) -> Dict[str, Any]:

        table_number: str = kwargs.get("table_number", "1")
        template: list = kwargs.get("template", ["Noté le", "Sujet", "Par", "Pour le", "Fait le"])

        doc = docx.Document(file_obj)
        index_table = int(table_number) - 1

        if not doc.tables:
            raise ValueError("Aucun tableau trouvé dans ce document Word.")

        if index_table < 0 or index_table >= len(doc.tables):
            raise IndexError("Index hors limite.")

        table = doc.tables[index_table]
        data = [[cell.text.strip() for cell in row.cells] for row in table.rows]
        headers = template
        content = data[0:]
        df = pd.DataFrame(content, columns=headers)

        #nettoyage
        df.dropna(how="all", axis=0).dropna(how="all", axis=1).ffill(axis=0)

        #conversion des colonnes en mode string pour stockage parquet
        df = df.astype(str)

        return {
            "content": df,
            "metadata": {
                "filename": filename,
                "type": "cr",
                "template" : template,
            }
        }

    

