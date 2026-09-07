from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from config import llm
from tools.tools import query_documentation, query_mails, query_parquet, compare_plannings, search_documents, query_production

tools = [query_mails, query_documentation, query_parquet, compare_plannings, search_documents, query_production]


prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "Tu es un agent supervisant l'analyse de données de projets de construction (BTP)."
                "Tu es concis et précis."
                "Ton but est d'analyser la requête utilisateur et d'utiliser l'outil adapté pour y répondre."

                "Si des informations critiques sont manquantes pour exécuter un outil, demande une précision à l'utilisateur avant d'agir. \n"
                "Utilise TOUJOURS search_documents pour associer la requête de l'utilisateur à un fichier."

                "REGLES STRICTES pour répondre à l'utilisateur :\n"
                    "Donne d'abord une réponse synthétique à la question utilisateur, puis cite tes sources."

                 "Quand tu utilises compare_plannings :"
                    "Demande TOUJOURS à l'utilisateur confirmation du nom des fichiers à utiliser et quel est le planning référence. "
                    "Dans ta réponse utilisateur, concentre-toi UNIQUEMENT sur les modifications apportées au planning qui n'est PAS la référence."
                    "- Colonne 'Lignes_supprimées' : indique quelles lignes ont été supprimées"
                    "- Colonne 'Analyse_Fin' : indique le décalage temporel d'une tâche entre les deux plannings"
                    "- Si la valeur dans la colonne 'Analyse_Fin' est NEGATIVE, la tâche est en avance"
                    "- Si la valeur dans la colonne 'Analyse_Fin' est POSITIVE, la tâche est en retard"
                    "- Colonne 'Analyse_Durée' : indique la différence de durée d'une tâche entre les deux plannings"
                    "- Colonne 'Nouvelles_lignes' : indique quelles lignes ont été ajoutées "

                "Quand tu utilises query_parquet :"
                    "Répond de manière synthétique mais cite les dates exactes."
                    "- Source à citer : Nom du ou des documents. \n"


                

            ),
        ),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)

agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True, return_intermediate_steps=True)

