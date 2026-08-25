import pandas as pd
import numpy as np
from pathlib import Path

from typing import Optional
from langchain_core.tools import tool
from config import PARQUET_DB_DIR, vector_store
from ingestion_pipeline.operate_database import get_indexed_documents

#query rag - main documents
#results wanted : context and page number/filename fed to the agent
@tool
def query_chroma(query: str) -> str:
    """Utile pour chercher des informations dans la documentation générale stockée dans chromadb.
    Ne PAS utiliser pour les documents compte-rendus ou plannings stockés dans parquet. 
    Questions sur des documents généraux (doc_type = pdf) -> 'query_chroma'

    Args:
        query: str
    """
    try:

        results = vector_store.similarity_search(query, k=3)
        if not results:
            return "Aucun document correspondant trouvé."

        formatted_results = []
        for doc in results:
            filename = doc.metadata.get("filename", "Unknown file")
            page_num = doc.metadata.get("page_number", None)
            total_pages = doc.metadata.get("total_pages", None)

            source_label = f"Source : {filename}, page {page_num}/{total_pages}"

            formatted_results.append(f"Source : \n{doc.page_content.strip()}\n({source_label})")

        return "\n\n".join(formatted_results)
    except Exception as e:
        return f"Erreur lors de la recherche documentaire : {e}"


@tool
def query_parquet(parquet_type: str, search_term: Optional[str] = None, filename: Optional[str] = None) -> str:
    """Utile pour chercher des informations dans des compte-rendus ou plannings stockés dans parquet. 
    Ne PAS utiliser pour la documentation générale. 
    A utiliser quand la question contient 'cr', 'compte-rendu', 'compte rendu', 'compte-rendus', 'crs', 'plg', 'plannings'. 
    Mais que l'utilisateur ne veut pas de comparaison ENTRE plannings. 
    doc_type = report ou planning

    Args:
        filename: Nom exact du fichier fourni par l'utilisateur si la recherche vise un seul fichier (optionnel). 
        parquet_type: 'cr'. 
        search_term: Mot-clé ou terme à rechercher dans les colonnes du tableau (optionnel).

        Pour le search_term, tu dois extraire UNIQUEMENT le mot-clé principal ou l'entité clé, sans les mots de liaison ni les verbes.
            Exemples de simplification des termes de recherche :
            - Question : 'Quelles sont les tâches du lot 3 ?' -> Terme de recherche : 'lot 3'
            - Question : 'Peux-tu me donner le compte-rendu du projet Alpha ?' -> Terme de recherche : 'projet Alpha'
            - Question : 'Montre-moi les tâches pour la Phase B' -> Terme de recherche : 'Phase B'
        Règle : N'utilise JAMAIS de mots comme 'tâches' ou 'liste' dans l'argument de recherche.

    """

    target_dir = Path(PARQUET_DB_DIR) / parquet_type

    if not target_dir.exists():
        return f"Aucun dossier trouvé pour le type '{parquet_type}'."

    formatted_results = []

    #recherche dans un seul cr
    if filename:

        #forcer l'extension
        if not filename.endswith(".parquet"):
            filename = f"{filename}.parquet"

        path = target_dir / filename

        try: 
            df = pd.read_parquet(path)
            if search_term:
                mask = (df.astype(str).apply(lambda col: col.str.contains( search_term, case=False, na=False)).any(axis=1))
                filtered_df = df[mask]
            else:
                filtered_df = df

            #nettoyage df
            drop_columns = ["Début", "Fin", "Durée_Nb", "filename", "type"]
            clean_filtered_df = filtered_df.drop(columns=[col for col in drop_columns if col in filtered_df.columns])

            if not filtered_df.empty:
                doc_title = f"### [{parquet_type.upper()}] Source : {filename}"
                table_md = clean_filtered_df.to_markdown(index=False)
                formatted_results.append(f"{doc_title}\n{table_md}")

        except FileNotFoundError:
            print(f"Erreur : Le fichier {path} n'existe pas.")

    #recherche dans tous les crs
    else:
        for parquet_file in target_dir.glob("*.parquet"): #cherche dans tous les crs - code pour un seul cr ?
            try:
                df = pd.read_parquet(parquet_file)
                if search_term:
                    mask = (df.astype(str).apply(lambda col: col.str.contains( search_term, case=False, na=False)).any(axis=1))
                    filtered_df = df[mask]
                else:
                    filtered_df = df

                #nettoyage df
                drop_columns = ["Début", "Fin", "Durée_Nb", "filename", "type"]
                clean_filtered_df = filtered_df.drop(columns=[col for col in drop_columns if col in filtered_df.columns])

                if not filtered_df.empty:
                    doc_title = f"### [{parquet_type.upper()}] Source : {parquet_file.stem}"
                    table_md = clean_filtered_df.to_markdown(index=False)
                    formatted_results.append(f"{doc_title}\n{table_md}")

            except Exception as e:
                print(f"Erreur lors de la lecture du fichier.")

    if not formatted_results:
        return f"Aucun résultat trouvé dans les {parquet_type}."

    return "\n\n".join(formatted_results)


#comparing_analysis - pour l'instant que deux tableaux, coder version où plus d'un versus
@tool
def compare_plannings(parquet_type: str, filename_source: str, filename_versus: str) -> str:

    """Utile pour comparer deux plannings stockés sous format parquet. 
    Ne PAS utiliser pour les pdfs ou les compte-rendus. 
    A utiliser quand la question contient 'planning', 'plannings' avec le mot clé 'source'. 
    Analyse comparative de deux plannings (doc_type = planning) -> 'compare_plannings'

    Args:
            filename_versus: Nom exact du fichier fourni par l'utilisateur. 
            parquet_type: 'planning'. 
            filename_source: Nom exact du fichier fourni par l'utilisateur qu'il désigne comme la source. 
        
    """
    #ajouter analyse durée

    target_dir = Path(PARQUET_DB_DIR) / parquet_type

    if not target_dir.exists():
        return f"Aucun dossier trouvé pour le type '{parquet_type}'."

    formatted_results = []

    #forcer l'extension
    if not filename_source.endswith(".parquet"):
        filename_source = f"{filename_source}.parquet"

    if not filename_versus.endswith(".parquet"):
            filename_versus = f"{filename_versus}.parquet"

    path_source = target_dir / filename_source #exception si filename n'existe pas
    path_versus = target_dir / filename_versus #exception si filename n'existe pas

    source_df = pd.read_parquet(path_source)
    versus_df = pd.read_parquet(path_versus)

    #df qui va contenir l'analyse
    analysis_df = source_df.copy()

    analysis_col_id = next(c for c in analysis_df.columns if 'id' in str(c).lower())
    versus_col_id = next(c for c in versus_df.columns if 'id' in str(c).lower())
    cols_to_copy = [versus_col_id, "Début_ISO", "Fin_ISO", "Durée"]
    versus_ids = set(versus_df[versus_col_id].dropna())

    #stem of filename
    clean_filename_versus = Path(filename_versus).stem

    #merge colonnes de date de l'ancien planning vers le nouveau
    analysis_df = analysis_df.merge(versus_df[cols_to_copy].rename(columns={
        "Début_ISO": f"Début_ISO_{clean_filename_versus}", 
        "Fin_ISO": f"Fin_ISO_{clean_filename_versus}",
        "Durée": f"Durée_{clean_filename_versus}",
    }), on=analysis_col_id, how="left")

    #calcul retard en jours ouvrés
    col_duration_versus = f"Durée_{clean_filename_versus}"
    col_start_versus = f"Début_ISO_{clean_filename_versus}"
    col_source = "Fin_ISO"
    col_versus = f"Fin_ISO_{clean_filename_versus}"

    s_source = pd.to_datetime(analysis_df[col_source], errors="coerce")
    s_versus = pd.to_datetime(analysis_df[col_versus], errors="coerce")

    mask_valid = s_source.notna() & s_versus.notna()

    dates_source = np.array(s_source[mask_valid].dt.date.tolist(), dtype="datetime64[D]")
    dates_versus = np.array(s_versus[mask_valid].dt.date.tolist(), dtype="datetime64[D]")

    analysis_df["Analyse"] = np.nan

    if len(dates_source) > 0 :
        analysis_df.loc[mask_valid, "Analyse"] = np.busday_count(dates_versus, dates_source)

    print(analysis_df["Analyse"])

    #identification des nouvelles lignes
    analysis_df["Analyse"] = analysis_df["Analyse"].astype("string")
    is_new_line = analysis_df[analysis_col_id].isin(versus_ids) == False
    analysis_df.loc[is_new_line, "Analyse"] = "Ligne ajoutée"    #print(analysis_df)

    print(analysis_df["Analyse"])

    #lignes supprimées
    deleted_lines_ids = set(versus_df[versus_col_id]) - set(analysis_df[analysis_col_id])
    deleted_lines_df = versus_df[versus_df[versus_col_id].isin(deleted_lines_ids)]

    print(deleted_lines_df)

    #nettoyer le tableau final
    drop_columns = ["Début", "Fin", "Durée_Nb", "filename", "type"]
    clean_analysis_df = analysis_df.drop(columns=[col for col in drop_columns if col in analysis_df.columns])
    clean_deleted_lines_df = deleted_lines_df.drop(columns=[col for col in drop_columns if col in deleted_lines_df.columns])

    print(clean_analysis_df)

    #passage en markdown
    analysis_table_md = clean_analysis_df.to_markdown(index=False)
    deleted_lines_md = clean_deleted_lines_df.to_markdown(index=False)
    formatted_results.append(f"{analysis_table_md}\n{deleted_lines_md}")

    if not formatted_results:
        return f"Aucun résultat trouvé dans les {parquet_type}."

    return "\n\n".join(formatted_results)


@tool
def search_documents() -> str:
    """
    Récupère la liste de tous les documents indexés. 
    À utiliser pour trouver le nom exact d'un fichier à partir d'une demande approximative.
    """
    docs = get_indexed_documents()
    
    if not docs:
        return "Aucun document n'est actuellement indexé."
        
    formatted_list = "\n".join([f"- {doc}" for doc in docs])
    return f"Voici la liste des documents disponibles :\n{formatted_list}"



























