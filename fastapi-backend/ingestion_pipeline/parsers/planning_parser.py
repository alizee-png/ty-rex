from typing import Dict, Any, BinaryIO
from .base import BaseParser
from config import DEFAULT_DATE

import pandas as pd
import re


class PlanningParser(BaseParser):
    
    def parse(self, file_obj: BinaryIO, filename: str, **kwargs: Any) -> Dict[str, Any]:
        
        cols = ['N° Unique', 'Nom', 'Durée', 'Début', 'Fin']
        df = pd.read_excel(file_obj, usecols=cols, engine="openpyxl")

        df['Début_ISO'] = df['Début'].apply(convert_text_to_date)
        df['Fin_ISO'] = df['Fin'].apply(convert_text_to_date)
        df['Durée_Nb'] = df['Durée'].apply(get_number)

        #conversion des colonnes en mode string pour stockage parquet
        df = df.astype(str)
        
        return {
            "content": df,
            "metadata": {
                "filename": filename,
                "type": "planning"
            }
        }

def month_to_number(month: str) -> str:
    month_map = {
        'janvier': '01', 'février': '02', 'mars': '03', 'avril': '04',
        'mai': '05', 'juin': '06', 'juillet': '07', 'août': '08',
        'septembre': '09', 'octobre': '10', 'novembre': '11', 'décembre': '12'
    }
    return month_map.get(str(month).strip().lower(), '00')

def convert_text_to_date(value : str) -> pd.Timestamp :
    if pd.isna(value) or value != value :
        return DEFAULT_DATE

    text = str(value).strip().lower()
    split_text = text.split(' ')
    cleaned_split_text = split_text[1:-1]
    cleaned_split_text[1] = month_to_number(cleaned_split_text[1])
    cleaned_split_text.reverse()

    date_iso = "-".join(cleaned_split_text)

    return pd.Timestamp(date_iso)

def get_number(value : str) -> float : #ne gère pas les différents cas : semaines, mois, etc. 
    numberlist = re.findall(r'\d+(?:[.,]\d+)?', value)

    if numberlist:
        value_text = numberlist[0].replace(',', '.')
        duration = float(value_text)
    else:
        duration = 0.0

    return duration

