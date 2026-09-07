import pandas as pd
import numpy as np
import duckdb
from pathlib import Path

from typing import Any, Optional, List, TypedDict, Dict
from typing import cast
from langchain_core.tools import tool
from pydantic.v1 import BaseModel, Field
from config import PARQUET_DB_DIR, document_vector_store, mail_vector_store
from config import llm
from ingestion_pipeline.operate_database import get_indexed_documents


#définition des schémas attendus pour la sortie structurée du LLM
class MailQueryStructure(BaseModel):
    search_term: Optional[str] = Field(description="Mot-clé issu de la requête utilisateur.")
    subject: Optional[str] = Field(description="Sujet du message.")
    sender: Optional[str] = Field(description="Expéditeur du message.")
    recipient: Optional[str] = Field(description="Destinataire du message.")
    date: Optional[str] = Field(description="Date du message.")

class ParquetQueryStructure(BaseModel):
    search_terms: List[str] = Field(description="Liste des mots-clés extraits de la requête")
    operator: Optional[str] = Field(description="Opérateur logique, 'AND' ou 'OR'")
    doc_type: Optional[str] = Field(description="Type de document ciblé si mentionné (ex: planning, compte-rendu)")
    filename: Optional[str] = Field(description="Nom de fichier précis si mentionné")

class StandardToolResponse(TypedDict):
    message: str
    tables: List[Dict[str, Any]]
    documents: List[Dict[str, Any]]

@tool
def query_documentation(query: str) -> StandardToolResponse:
    """Utile pour chercher des informations dans la documentation générale stockée dans chromadb.
    Ne PAS utiliser pour les tableaux, plannings ou mails. 
    doc_type = texte -> query_documentation


    Args:
        query: str
    """
    try:
        results = document_vector_store.similarity_search(query, k=3)

        if not results:
            return {
                "message": "Aucun document correspondant trouvé.",
                "tables": [],
                "documents": []
            }

        json_dict: StandardToolResponse = {
                "message": "Voici les résultats de votre recherche dans les fichiers :",
                "tables": [],
                "documents": []
            }


        for doc in results:
            filename = doc.metadata.get("filename", "Unknown file")
            page_num = doc.metadata.get("page_number", None)
            total_pages = doc.metadata.get("total_pages", None)
            para_num = doc.metadata.get("paragraph_number")
            total_paragraphs = doc.metadata.get("total_paragraphs")

            source_info = [f"Fichier : {filename}"]
            if page_num and total_pages:
                source_info.append(f"Page : {page_num}/{total_pages}")
            if para_num and total_paragraphs:
                source_info.append(f"Paragraphe : {para_num}/{total_paragraphs}")

            source_label = " | ".join(source_info)
            json_dict["documents"].append({
                "title": f"Source : {source_label}",
                "data": doc.page_content.strip() 
                })

        return json_dict
    
    except Exception as e:
        return {
                "message": f"Erreur lors de la recherche documentaire : {e}",
                "tables": [],
                "documents": []
                }



@tool
def query_mails(search_term: Optional[str] = None, subject: Optional[str] = None, sender: Optional[str] = None, recipient: Optional[str] = None, date: Optional[str] = None) -> StandardToolResponse:
    """Utile pour chercher des informations dans les mails stockés dans chromadb.
    Ne PAS utiliser pour les documents tableaux ou plannings stockés dans parquet ou les documents textes stockés dans chromadb..
    doc_type = mail -> query_mails

    Args:
        search_term: str - Mot-clé issu de la requête utilisateur.
        subject : str - Filtrer par le sujet du message (optionnel).
        sender: str - Filtrer par l'expéditeur du message (optionnel).
        recipient: str - Filtrer par le destinataire du message (optionnel).
        date: str - Filtrer par la date du message (optionnel).
    """
    try:
        # 1. Si la query est vide, on récupère un lot large via collection.get() sans filtre strict
        if not search_term or not search_term.strip():
            collection = mail_vector_store._collection
            raw_results = collection.get()
            mails = raw_results.get("documents") or []
            metadatas = raw_results.get("metadatas") or []
            
            results = []
            for text, meta in zip(mails, metadatas):
                class DummyDoc:
                    def __init__(self, page_content, metadata):
                        self.page_content = page_content
                        self.metadata = metadata
                results.append(DummyDoc(text, meta))
        else:
            # 2. Si une query textuelle existe, recherche vectorielle large
            results = mail_vector_store.similarity_search(search_term, k=10)

        # 3. Filtrage souple en Python (insensible à la casse, correspondance partielle)
        filtered_results = []
        for doc in results:
            meta = doc.metadata
            match = True
            
            if subject and subject.lower() not in str(meta.get("subject", "")).lower():
                match = False
            if sender and sender.lower() not in str(meta.get("sender", "")).lower():
                match = False
            if recipient and recipient.lower() not in str(meta.get("recipient", "")).lower():
                match = False
            if date and date.lower() not in str(meta.get("date", "")).lower():
                match = False
                
            if match:
                filtered_results.append(doc)

        # On restreint aux k premiers résultats pertinents
        results = filtered_results[:3]

        if not results:
            return {
                "message": "Aucun document correspondant trouvé.",
                "tables": [],
                "documents": []
            }

        json_dict: StandardToolResponse = {
                "message": "Voici les résultats de votre recherche dans les fichiers :",
                "tables": [],
                "documents": []
            }
        
        for doc in results:
            meta = doc.metadata
            filename = meta.get("filename", "Inconnu")
            subject_val = meta.get("subject")
            sender_val = meta.get("sender")
            recipient_val = meta.get("recipient")
            date_val = meta.get("date")

            source_info = [f"Fichier : {filename}"]
            if subject_val:
                source_info.append(f"Sujet : {subject_val}")
            if sender_val:
                source_info.append(f"De : {sender_val}")
            if recipient_val:
                source_info.append(f"À : {recipient_val}")
            if date_val:
                source_info.append(f"Date : {date_val}")

            source_label = " | ".join(source_info)
            json_dict["documents"].append({
                "title": f"Source : {source_label}",
                "data": doc.page_content.strip() 
                })

        return json_dict
    
    except Exception as e:
        return {
                "message": f"Erreur lors de la recherche documentaire : {e}",
                "tables": [],
                "documents": []
                }


@tool
def query_parquet(search_terms: List[str], operator: Optional[str] = None, doc_type: Optional[str] = None, filename: Optional[str] = None) -> StandardToolResponse:
    """Utile pour chercher des informations dans des compte-rendus ou plannings stockés dans parquet. 
    Ne PAS utiliser pour la documentation générale. 
    A utiliser quand la question contient 'cr', 'compte-rendu', 'compte rendu', 'compte-rendus', 'crs', 'plg', 'plannings'. 
    Mais que l'utilisateur ne veut pas de comparaison ENTRE plannings. 

    Règle d'inférence à RESPECTER pour le doc_type :
    'cr', 'compte-rendu', 'compte rendu', 'compte-rendus', 'crs', => doc_type = tableau
    'plg', 'plannings' => doc_type = planning

    Args:
        search_terms: Liste de mots-clés ou termes à rechercher dans les colonnes du dataframe.
        operator: "AND" ou "OR" pour combiner les termes de recherche (optionnel, par défaut "AND").
        doc_type: Type de document dans lequel chercher : doc_type = tableau | doc_type = planning. 
        filename: Nom exact du fichier fourni par l'utilisateur si la recherche vise un seul fichier (optionnel). 
        

    Pour les search_terms, tu dois extraire UNIQUEMENT les mots-clés principaux ou les entités clés, sans les mots de liaison ni les verbes.
        Exemples de simplification des termes de recherche :
        - Question : 'Quelles sont les tâches du lot 3 ?' -> Terme de recherche : 'lot 3'
        - Question : 'Peux-tu me donner le compte-rendu du projet Alpha ?' -> Terme de recherche : 'projet Alpha'
        - Question : 'Montre-moi les tâches pour la Phase B' -> Terme de recherche : 'Phase B'
        - Question : 'Quelles sont les tâches du lot 1 pour le mur de soutènement ?' -> Terme de recherche : 'lot 1', 'mur de soutènement'; Opérateur : 'AND'
        - Question : 'Quelles sont les tâches du lot 2 et 4 ?' -> Terme de recherche : 'lot 2', 'lot 4'; Opérateur : 'OR'
    Règle : N'utilise JAMAIS de mots comme 'tâches' ou 'liste' dans l'argument de recherche.

    """
    operator = operator or "AND"
    parquet_type = doc_type or None 

    if parquet_type is not None:
        target_dir = Path(PARQUET_DB_DIR) / parquet_type
    else: 
        target_dir = Path(PARQUET_DB_DIR)

    json_dict: StandardToolResponse = {
        "message": "Voici les résultats de votre recherche dans les fichiers :",
        "tables": [],
        "documents": []
    }

    drop_columns = ["Début", "Fin", "Durée_Nb", "filename", "type", "template"]

    
    def process_and_format_df(df):
        """Filtre le dataframe selon les search_terms et produit un json flat pour l'agent."""
        mask = None
        if search_terms:
            for st in search_terms:

                current_mask = df.astype(str).apply(lambda col: col.str.contains(st, case=False, na=False)).any(axis=1)
                if mask is None:
                    mask = current_mask
                else:
                    if operator.upper() == "AND":
                        mask = mask & current_mask
                    else:
                        mask = mask | current_mask
            filtered_df = df[mask] if mask is not None else df
        else:
            filtered_df = df

        # Nettoyage df
        clean_filtered_df = filtered_df.drop(columns=[col for col in drop_columns if col in filtered_df.columns])

        if not clean_filtered_df.empty:
            df_flat = clean_filtered_df.astype(object).where(pd.notna(clean_filtered_df), None)
            json_flat = df_flat.to_dict(orient="records") 

            return json_flat
        
        return None

    def find_file_in_parquet(base_dir: str, filename: str) -> pd.DataFrame:
        """Recherche un fichier spécifique dans une arborescence de fichiers Parquet."""

        query = f"""
            SELECT * 
            FROM read_parquet('{base_dir}/**/*.parquet', hive_partitioning=true)
            WHERE filename = ?"""

        return duckdb.sql(query, params=[filename]).df()

    #filename mentionné
    if filename:
        
        try: 
            df = find_file_in_parquet(PARQUET_DB_DIR, filename)
            print(df)
            result = process_and_format_df(df)
            print(f"Résultat pour le fichier {filename} : {result}")

            if result:
                json_dict["tables"].append({
                "title": f"Source : {filename}",
                "data": result
                })
        except FileNotFoundError:
            print(f"Erreur : Le fichier {filename} n'existe pas.")

    #recherche élargie
    else:
        for parquet_file in target_dir.glob("*.parquet"): 
            try:
                df = pd.read_parquet(parquet_file)
                filename = df["filename"].iloc[0] if "filename" in df.columns else parquet_file.name
                result = process_and_format_df(df)
                if result:
                    json_dict["tables"].append({
                        "title": f"Source : {filename}",
                        "data": result
                    })
            except Exception as e:
                print(f"Erreur lors de la lecture du fichier {filename} : {e}")

    if not json_dict["tables"]:
        return {
            "message": f"Aucun résultat trouvé dans les {parquet_type or 'documents'}.",
            "tables": [],
            "documents": []
        }

    return json_dict


@tool
def query_production(query: str) -> StandardToolResponse:
    """Si l'utilisateur te demande de chercher dans tous les documents produits, utilise query_production. 
    A utiliser pour des requêtes qui concernent les documents produits (plannings, mails, compte-rendus).
    Ne PAS utiliser pour la documentation générale.
    
    Args:
        query: Requête utilisateur à analyser.
    """
    prompt = f"Analyse cette requête utilisateur et extrait les paramètres pour interroger une base parquet : '{query}'"

    json_dict: StandardToolResponse = {
        "message": "Recherche globale dans les bases de données et documents.",
        "tables": [],
        "documents": []
    }

    #--- interroger chromaDB
    structured_llm_chroma = llm.with_structured_output(MailQueryStructure)
    args_chroma: MailQueryStructure = cast(MailQueryStructure, structured_llm_chroma.invoke(prompt))
    mails_results = query_mails.invoke({
        "search_term": args_chroma.search_term,
        "subject": args_chroma.subject,
        "sender": args_chroma.sender,
        "recipient": args_chroma.recipient,
        "date": args_chroma.date,
        })

    if isinstance(mails_results, dict):
        json_dict["tables"].extend(mails_results.get("tables", []))
        json_dict["documents"].extend(mails_results.get("documents", []))
    
    #--- interroger parquet
    structured_llm_parquet = llm.with_structured_output(ParquetQueryStructure)
    args_parquet: ParquetQueryStructure = cast(ParquetQueryStructure, structured_llm_parquet.invoke(prompt))
    
    parquet_results = query_parquet.invoke({
            "search_terms": args_parquet.search_terms,
            "doc_type": getattr(args_parquet, "doc_type", None),
            "filename": getattr(args_parquet, "filename", None),
            "operator": getattr(args_parquet, "operator", None),
        })

    if isinstance(parquet_results, dict):
        json_dict["tables"].extend(parquet_results.get("tables", []))
        json_dict["documents"].extend(parquet_results.get("documents", []))
    
    return json_dict


@tool
def compare_plannings(filename: str, filename_reference: str) -> StandardToolResponse:
    """Utile pour comparer deux plannings stockés sous format parquet. 
    Ne PAS utiliser pour les pdfs ou les compte-rendus. 
    A utiliser quand la question contient 'planning', 'plannings' avec le mot clé 'source'. 
    Analyse comparative de deux plannings (doc_type = planning) -> 'compare_plannings'

    Args:
            filename: Nom du fichier fourni par l'utilisateur.
            filename_reference: Nom du fichier fourni par l'utilisateur qu'il désigne comme la référence. 
        
    """
    target_dir = Path(PARQUET_DB_DIR) / "planning"

    if not target_dir.exists():
        return {
            "message":"Aucun dossier trouvé pour le type 'planning'.",
            "tables": [],
            "documents": []
        }

    json_dict: StandardToolResponse = {
            "message": "Voici les résultats de votre recherche dans les fichiers :",
            "tables": [],
            "documents": []
        }

    #--- ouverture des deux fichiers parquet
    filename = f"{Path(filename).stem}.parquet"
    filename_reference = f"{Path(filename_reference).stem}.parquet"

    path_source = target_dir / filename 
    path_reference = target_dir / filename_reference 

    source_df = pd.read_parquet(path_source)
    reference_df = pd.read_parquet(path_reference)

    #--- création de la df qui va contenir l'analyse
    analysis_df = source_df.copy()

    analysis_col_id = next(c for c in analysis_df.columns if 'unique' in str(c).lower())
    reference_col_id = next(c for c in reference_df.columns if 'unique' in str(c).lower())
    cols_to_copy = [reference_col_id, "Début_ISO", "Fin_ISO", "Durée_Nb"]
    reference_ids = set(reference_df[reference_col_id].dropna())

    #stem of filename
    clean_filename_reference = Path(filename_reference).stem

    #--- merge colonnes de date de l'ancien planning vers le nouveau
    analysis_df = analysis_df.merge(reference_df[cols_to_copy].rename(columns={
        "Début_ISO": f"Début_ISO_{clean_filename_reference}", 
        "Fin_ISO": f"Fin_ISO_{clean_filename_reference}",
        "Durée_Nb": f"Durée_Nb_{clean_filename_reference}",
    }), on=analysis_col_id, how="left")

    #--- calcul retard sur dates de fin
    col_source = "Fin_ISO"
    col_reference = f"Fin_ISO_{clean_filename_reference}"

    s_source = pd.to_datetime(analysis_df[col_source], errors="coerce")
    s_reference = pd.to_datetime(analysis_df[col_reference], errors="coerce")

    mask_valid = s_source.notna() & s_reference.notna()

    dates_source = np.array(s_source[mask_valid].dt.date.tolist(), dtype="datetime64[D]")
    dates_reference = np.array(s_reference[mask_valid].dt.date.tolist(), dtype="datetime64[D]")

    analysis_df["Analyse_Fin"] = np.nan

    if len(dates_source) > 0 :
        analysis_df.loc[mask_valid, "Analyse_Fin"] = np.busday_count(dates_reference, dates_source)

    print(analysis_df["Analyse_Fin"])

    #--- calcul écarts de durées
    col_duration_source = "Durée_Nb"
    col_duration_reference = f"Durée_Nb_{clean_filename_reference}"

    d_source = pd.to_numeric(analysis_df[col_duration_source], errors='coerce')
    d_reference = pd.to_numeric(analysis_df[col_duration_reference], errors='coerce')

    mask_valid_duration = d_source.notna() & d_reference.notna()
    analysis_df["Analyse_Durée"] = np.nan
    analysis_df.loc[mask_valid_duration, "Analyse_Durée"] = d_source - d_reference

    #--- identification des nouvelles lignes
    is_new_line = ~analysis_df[analysis_col_id].isin(reference_ids)
    analysis_df.loc[is_new_line, "Nouvelles_lignes"] = "Ligne ajoutée"    #print(analysis_df)

    #--- identification des lignes supprimées
    deleted_lines_ids = set(reference_df[reference_col_id]) - set(analysis_df[analysis_col_id])
    deleted_lines_df = reference_df[reference_df[reference_col_id].isin(deleted_lines_ids)].copy()
    deleted_lines_df["Lignes_supprimées"] = "Ligne supprimée"

    print(deleted_lines_df)

    #--- nettoyer le tableau final
    drop_columns = ["Début", "Fin", col_duration_source, col_duration_reference, "filename", "type"]
    clean_analysis_df = analysis_df.drop(columns=[col for col in drop_columns if col in analysis_df.columns])
    clean_deleted_lines_df = deleted_lines_df.drop(columns=[col for col in drop_columns if col in deleted_lines_df.columns])

    print(clean_analysis_df)

    #json
    if not clean_analysis_df.empty:
        df_flat = clean_analysis_df.astype(object).where(pd.notna(clean_analysis_df), None)
        json_flat = df_flat.to_dict(orient="records") 
        json_dict["tables"].append({
            "title": f"Source : {path_source.stem}_analysis",
            "data": json_flat
            })

    if not clean_deleted_lines_df.empty:
        deleted_lines_df_flat = clean_deleted_lines_df.astype(object).where(pd.notna(clean_deleted_lines_df), None)
        deleted_lines_json_flat = deleted_lines_df_flat.to_dict(orient="records") 
        json_dict["tables"].append({
            "title": f"Source : {path_reference.stem}_analysis",
            "data": deleted_lines_json_flat
            })

    if not json_dict["tables"]:
        return {
                "message":"Erreur lors de l'analyse.",
                "tables": [],
                "documents": []
            }

    return json_dict

@tool
def search_documents() -> str:
    """
    Récupère la liste de tous les documents indexés. 
    À utiliser pour trouver le nom exact d'un fichier à partir d'une demande approximative.
    """
    docs = get_indexed_documents(include_mails=True, include_documents=True, include_parquet=True)
    
    if not docs:
        return "Aucun document n'est actuellement indexé."
        
    formatted_list = "\n".join([f"- {doc}" for doc in docs])
    return f"Voici la liste des documents disponibles :\n{formatted_list}"




















