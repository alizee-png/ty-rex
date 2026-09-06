"use client";

import React, { useEffect, useState } from "react";
import {
  Upload,
  Columns3Cog,
  HelpCircle,
  RefreshCcw,
  MinusIcon,
  SendHorizontal,
  Bot,
  X,
  Expand,
} from "lucide-react";

interface FileItem {
  id: string;
  name: string;
  docType: string;
  sheetName: string;
  tableNumber: string;
  template: string;
  file?: File;
  isUploaded: boolean;
  isUploading?: boolean;
}

interface Message {
  sender: "user" | "bot";
  text: string;
  tables?: { title: string; data: any }[];
  documents?: { title: string; data: string }[];
}

interface TableResultItem {
  type?: string;
  filename?: string;
  title?: string;
  data: Record<string, any>[];
}

interface Props {
  results: TableResultItem[];
}

const API_BASE = "http://localhost:8000/api";

export default function RAGInterface() {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [messages, setMessages] = useState<Message[]>([
    {
      sender: "bot",
      text: "Hello ! Charge tes documents, puis pose-moi une question.",
    },
  ]);
  const [inputMessage, setInputMessage] = useState("");
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"upload" | "database">("upload");
  const [dbFiles, setDbFiles] = useState<any[]>([]);
  const [selectedDocType, setSelectedDocType] = useState<string>("tous");
  const [loading, setLoading] = useState(true);
  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [templateText, setTemplateText] = useState("");
  const [templatesList, setTemplatesList] = useState([
    {
      name: "A",
      content: "Noté le, Sujet, Par, Pour le, Fait le",
    },
  ]);
  const [templateName, setTemplateName] = useState(""); // Pour nommer le nouveau template
  const [showHelpModal, setShowHelpModal] = useState(false);
  const [showTableModal, setShowTableModal] = useState<{
    tables?: { title: string; data: any }[];
    documents?: { title: string; data: string }[];
  } | null>(null);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const res = await fetch("http://localhost:8000/api/documents");
      const data = await res.json();

      if (data.status === "success" && data.documents) {
        const loadedFiles: FileItem[] = data.documents.map(
          (doc: any, index: number) => ({
            id: doc.filename || `doc-${index}`,
            name: doc.filename || "Fichier sans nom",
            docType: doc.type || "autre",
            template: doc.template || "",
            isUploaded: true,
          }),
        );

        setDbFiles(loadedFiles);
      }
    } catch (err) {
      console.error("Erreur lors du chargement des documents :", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const filteredDbFiles = dbFiles.filter((item) => {
    if (selectedDocType === "tous") return true;
    return item.docType === selectedDocType;
  });

  //sélection d'un fichier sans upload
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      const newFile: FileItem = {
        id: crypto.randomUUID(),
        name: selectedFile.name,
        docType: "tableau",
        sheetName: "",
        tableNumber: "",
        template: "",
        file: selectedFile,
        isUploaded: false,
      };
      setFiles((prev) => [...prev, newFile]);
    }
  };

  //prend en compte les modifications dans les champs du tableau susceptibles d'être modifié par l'utilisateur
  const updateFileDetail = (
    id: string,
    field: keyof FileItem,
    value: string,
  ) => {
    setFiles((prev) =>
      prev.map((item) => (item.id === id ? { ...item, [field]: value } : item)),
    );
  };

  //upload d'un fichier
  const handleUploadFile = async (item: FileItem) => {
    if (!item.file) return;

    setFiles((prev) =>
      prev.map((f) => (f.id === item.id ? { ...f, isUploading: true } : f)),
    );

    const formData = new FormData();
    formData.append("file", item.file);
    formData.append("doc_type", item.docType);

    if (item.sheetName) formData.append("sheet_name", item.sheetName);
    if (item.tableNumber) formData.append("table_number", item.tableNumber);

    //gestion du template
    if (item.template) {
      const foundTemplate = templatesList.find(
        (t) => t.name === item.template || t.content === item.template,
      );

      const rawTextToSplit = foundTemplate
        ? foundTemplate.content
        : item.template;

      const templateAsListOfStrings = rawTextToSplit
        .split(",")
        .map((s) => s.trim())
        .filter((s) => s.length > 0);

      if (templateAsListOfStrings.length > 0) {
        formData.append("template", JSON.stringify(templateAsListOfStrings));
      }
    }

    try {
      const res = await fetch(`${API_BASE}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        alert(`Erreur: ${errData.detail}`);
        setFiles((prev) =>
          prev.map((f) =>
            f.id === item.id ? { ...f, isUploading: false } : f,
          ),
        );
        return;
      } else {
        await fetchDocuments();
      }

      setFiles((prev) =>
        prev.map((f) =>
          f.id === item.id ? { ...f, isUploaded: true, isUploading: false } : f,
        ),
      );
    } catch (err) {
      console.error("Erreur lors de l'upload:", err);
      alert("Erreur lors de l'envoi du fichier au serveur.");
      setFiles((prev) =>
        prev.map((f) => (f.id === item.id ? { ...f, isUploading: false } : f)),
      );
    }
  };

  //upload de plusieurs fichiers
  const handleUploadAll = async () => {
    const pendingItems = files.filter(
      (item: FileItem) => !item.isUploaded && !item.isUploading,
    );

    if (pendingItems.length === 0) return;

    for (const item of pendingItems) {
      await handleUploadFile(item);
    }
  };

  //suppression d'un document de la base de données
  const handleDeleteFile = async (item: FileItem) => {
    if (item.isUploaded) {
      try {
        const res = await fetch(
          `${API_BASE}/documents/${encodeURIComponent(item.name)}`,
          {
            method: "DELETE",
          },
        );
        if (!res.ok) {
          alert("Erreur lors de la suppression sur le serveur.");
          return;
        }
      } catch (err) {
        console.error("Erreur suppression:", err);
        return;
      }
    }
    setDbFiles((prev) => prev.filter((f) => f.id !== item.id));
  };

  //suppression d'un document de l'interface
  const removeFile = (id: string) => {
    setFiles((prevFiles) => prevFiles.filter((item) => item.id !== id));
  };

  //envoi message utilisateur à l'agent
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || isChatLoading) return;

    const userText = inputMessage;

    const updatedMessages = [{ sender: "user" as const, text: userText }];

    setMessages(updatedMessages);
    setInputMessage("");
    setIsChatLoading(true);

    try {
      const payloadMessages = [
        {
          role: "user",
          content: userText,
        },
      ];

      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: payloadMessages }),
      });

      const data = await res.json();
      const newMessages: Message[] = [];

      // 2. Ajouter la réponse textuelle principale si elle existe
      if (data.message) {
        newMessages.push({ sender: "bot", text: data.message });
      }

      console.log(data.message);

      // 3. Créer un message distinct pour chaque tableau reçu
      if (data.tables && Array.isArray(data.tables)) {
        data.tables.forEach((tableData: any) => {
          newMessages.push({
            sender: "bot",
            text: `Voici le tableau pour : ${tableData.title || "Résultat structuré"}`,
            tables: [tableData], // Un tableau par message
          });
        });
      }

      // 4. Créer un message distinct pour chaque document textuel reçu
      if (data.documents && Array.isArray(data.documents)) {
        data.documents.forEach((docData: any) => {
          newMessages.push({
            sender: "bot",
            text: `Extrait pertinent : ${docData.title || "Document"}`,
            documents: [docData], // Un document par message
          });
        });
      }

      setMessages((prev) => [...prev, ...newMessages]);
    } catch (error) {
      console.error("Erreur lors de la requête chat:", error);
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: "Une erreur est survenue lors du traitement." },
      ]);
    } finally {
      setIsChatLoading(false);
    }
  };

  function TableResult({ results }: Props) {
    if (!results || results.length === 0) return null;

    return (
      <div className="space-y-6 my-4">
        {results.map((item, index) => {
          let rows: Record<string, any>[] = [];
          try {
            const parsed =
              typeof item.data === "string" ? JSON.parse(item.data) : item.data;
            rows = Array.isArray(parsed)
              ? parsed
              : parsed?.data || parsed?.rows || [];
          } catch (e) {
            rows = [];
          }

          const columns = rows.length > 0 ? Object.keys(rows[0]) : [];

          return (
            <div
              key={index}
              className="rounded-lg p-4 shadow-sm border"
              style={{
                backgroundColor: "#BEE9E8",
                borderColor: "#5D5E5D",
                color: "#5D5E5D",
              }}
            >
              {/* Titre du tableau */}
              <div className="mb-3 flex items-center space-x-2">
                <span className="text-xs font-bold">
                  {item.title || `Tableau ${index + 1}`}
                </span>
              </div>

              {/* Tableau HTML responsive */}
              {rows.length === 0 ? (
                <p className="text-xs italic text-gray-500">
                  Aucune donnée à afficher.
                </p>
              ) : (
                <div
                  className="overflow-x-auto rounded border"
                  style={{ borderColor: "#5D5E5D" }}
                >
                  <table
                    className="min-w-full divide-y"
                    style={{ borderColor: "#5D5E5D" }}
                  >
                    <thead>
                      <tr style={{ backgroundColor: "#CAEEFF" }}>
                        {columns.map((col) => (
                          <th
                            key={col}
                            className="px-4 py-2 text-left text-xs font-bold uppercase tracking-wider border-r last:border-r-0"
                            style={{ borderColor: "#5D5E5D", color: "#5D5E5D" }}
                          >
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody
                      className="divide-y"
                      style={{ borderColor: "#5D5E5D" }}
                    >
                      {rows.map(
                        (row: Record<string, any>, rowIndex: number) => (
                          <tr
                            key={rowIndex}
                            className="transition-colors hover:bg-opacity-50"
                            style={{
                              backgroundColor:
                                rowIndex % 2 === 0 ? "#BEE9E8" : "#CAEEFF",
                            }}
                          >
                            {columns.map((col) => (
                              <td
                                key={col}
                                className="px-4 py-2 text-xs border-r last:border-r-0 whitespace-nowrap"
                                style={{
                                  borderColor: "#5D5E5D",
                                  color: "#5D5E5D",
                                }}
                              >
                                {row[col] !== null && row[col] !== undefined
                                  ? String(row[col])
                                  : "-"}
                              </td>
                            ))}
                          </tr>
                        ),
                      )}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  }

  return (
    // CONTENEUR PRINCIPAL
    <div
      className="flex h-screen w-full overflow-hidden"
      style={{ backgroundColor: "#CAEEFF", color: "#5D5E5D" }}
    >
      {/* 1. BARRE LATÉRALE (Sidebar) */}
      <div
        className="w-1/3 flex flex-col h-full shrink-0 border-r"
        style={{ backgroundColor: "#BEE9E8", borderColor: "#5D5E5D" }}
      >
        {/* Boutons d'Onglets */}
        <div
          className="flex border-b"
          style={{ backgroundColor: "#CAEEFF", borderColor: "#5D5E5D" }}
        >
          <button
            onClick={() => setActiveTab("upload")}
            className={`flex-1 py-3 px-4 text-sm font-medium border-b-2 transition-colors ${
              activeTab === "upload"
                ? "border-[#5D5E5D] text-[#5D5E5D] font-bold"
                : "border-transparent text-[#5D5E5D]/70 hover:text-[#5D5E5D]"
            }`}
          >
            Upload
          </button>
          <button
            onClick={() => setActiveTab("database")}
            className={`flex-1 py-3 px-4 text-sm font-medium border-b-2 transition-colors ${
              activeTab === "database"
                ? "border-[#5D5E5D] text-[#5D5E5D] font-bold"
                : "border-transparent text-[#5D5E5D]/70 hover:text-[#5D5E5D]"
            }`}
          >
            View Database
          </button>
        </div>

        {/* Contenu Onglets */}
        <div className="flex-1 overflow-y-auto p-4">
          {activeTab === "upload" ? (
            /* --- ONGLET 1 : UPLOAD & CONFIGURATION --- */
            <div className="flex flex-col gap-4 h-full">
              <div className="flex justify-end items-center mb-3">
                <div className="flex items-center gap-1.5">
                  {/* Bouton sélection du fichier */}
                  <label
                    className="p-1.5 rounded-md cursor-pointer transition border shadow-sm"
                    style={{
                      backgroundColor: "#CAEEFF",
                      borderColor: "#5D5E5D",
                      color: "#5D5E5D",
                    }}
                    title="Sélectionner un fichier"
                  >
                    <Upload className="w-4 h-4" />
                    <input
                      type="file"
                      className="hidden"
                      onChange={handleFileChange}
                      accept=".xlsx,.xls,.pdf,.docx,.msg,.eml"
                    />
                  </label>

                  {/* Bouton template */}
                  <button
                    onClick={() => setShowTemplateModal(true)}
                    className="p-1.5 rounded-md transition border shadow-sm"
                    style={{
                      backgroundColor: "#CAEEFF",
                      borderColor: "#5D5E5D",
                      color: "#5D5E5D",
                    }}
                    title="Saisir un template de texte"
                  >
                    <Columns3Cog className="w-4 h-4" />
                  </button>

                  {/* Bouton consignes utilisateur */}
                  <button
                    onClick={() => setShowHelpModal(true)}
                    className="p-1.5 rounded-md transition border shadow-sm"
                    style={{
                      backgroundColor: "#CAEEFF",
                      borderColor: "#5D5E5D",
                      color: "#5D5E5D",
                    }}
                    title="Aide & Instructions"
                  >
                    <HelpCircle className="w-4 h-4" />
                  </button>
                </div>
              </div>

              <div
                className="max-h-[60vh] overflow-auto rounded-md "
                style={{ backgroundColor: "#BEE9E8", borderColor: "#5D5E5D" }}
              >
                <table className="w-full text-xs text-left">
                  <tbody className="divide-y">
                    {files
                      .filter((item) => !item.isUploaded)
                      .map((item) => (
                        <tr
                          key={item.id}
                          className="hover:bg-[#CAEEFF]/50 transition-colors"
                        >
                          <td
                            className="p-2 font-medium truncate max-w-[200px]"
                            style={{ color: "#5D5E5D" }}
                            title={item.name}
                          >
                            {item.name}
                          </td>
                          <td className="p-1 max-w-[80px]">
                            <select
                              disabled={item.isUploaded}
                              value={item.docType}
                              onChange={(e) =>
                                updateFileDetail(
                                  item.id,
                                  "docType",
                                  e.target.value as FileItem["docType"],
                                )
                              }
                              className="w-full rounded p-1 focus:outline-none disabled:opacity-50 border text-xs"
                              style={{
                                backgroundColor: "#CAEEFF",
                                borderColor: "#5D5E5D",
                                color: "#5D5E5D",
                              }}
                            >
                              <option value="tableau">tableau</option>
                              <option value="planning">planning</option>
                              <option value="texte">texte</option>
                              <option value="mail">mail</option>
                            </select>
                          </td>
                          <td className="p-1 max-w-[80px]">
                            <input
                              type="text"
                              disabled={item.isUploaded}
                              placeholder="Feuil1"
                              value={item.sheetName}
                              onChange={(e) =>
                                updateFileDetail(
                                  item.id,
                                  "sheetName",
                                  e.target.value,
                                )
                              }
                              className="w-full rounded p-1 focus:outline-none disabled:opacity-50 border text-xs"
                              style={{
                                backgroundColor: "#CAEEFF",
                                borderColor: "#5D5E5D",
                                color: "#5D5E5D",
                              }}
                            />
                          </td>
                          <td className="p-1 max-w-[40px]">
                            <input
                              type="text"
                              disabled={item.isUploaded}
                              placeholder="1"
                              value={item.tableNumber}
                              onChange={(e) =>
                                updateFileDetail(
                                  item.id,
                                  "tableNumber",
                                  e.target.value,
                                )
                              }
                              className="w-full rounded p-1 focus:outline-none disabled:opacity-50 border text-xs"
                              style={{
                                backgroundColor: "#CAEEFF",
                                borderColor: "#5D5E5D",
                                color: "#5D5E5D",
                              }}
                            />
                          </td>
                          <td className="p-1 max-w-[40px]">
                            <input
                              type="text"
                              disabled={item.isUploaded}
                              placeholder="A"
                              value={item.template}
                              onChange={(e) =>
                                updateFileDetail(
                                  item.id,
                                  "template",
                                  e.target.value,
                                )
                              }
                              className="w-full rounded p-1 focus:outline-none disabled:opacity-50 border text-xs"
                              style={{
                                backgroundColor: "#CAEEFF",
                                borderColor: "#5D5E5D",
                                color: "#5D5E5D",
                              }}
                            />
                          </td>
                          <td className="p-1 max-w-[40px]">
                            <button
                              onClick={() => removeFile(item.id)}
                              className="p-1 text-white text-xs font-medium rounded-md transition flex items-center gap-1.5 shadow-sm"
                              style={{ backgroundColor: "#5FA8D3" }}
                              title="Retirer le fichier"
                            >
                              <MinusIcon className="w-4 h-4" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    {files.filter((item) => !item.isUploaded).length === 0 && (
                      <tr>
                        <td
                          colSpan={6}
                          className="p-4 text-center"
                          style={{ color: "#5D5E5D" }}
                        >
                          Sélectionne un fichier.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* Bouton pour tout uploader */}
              <div className="flex justify-end mr-1">
                <button
                  onClick={handleUploadAll}
                  className="px-2.5 py-1.5 text-white text-xs font-medium rounded-md transition flex items-center gap-1.5 shadow-sm hover:opacity-90"
                  style={{ backgroundColor: "#5FA8D3" }}
                  title="Charger tout dans la base de données"
                >
                  <RefreshCcw className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ) : (
            /* Onglet Database */
            <div
              className="flex flex-col h-full p-4"
              style={{ color: "#5D5E5D" }}
            >
              <div
                className="flex items-center justify-end mb-4 p-3 rounded-md"
                style={{ backgroundColor: "#BEE9E8" }}
              >
                <div className="flex items-center gap-2">
                  <select
                    value={selectedDocType}
                    onChange={(e) => setSelectedDocType(e.target.value)}
                    className="rounded px-2 py-1 text-xs border focus:outline-none"
                    style={{
                      backgroundColor: "#CAEEFF",
                      borderColor: "#5D5E5D",
                      color: "#5D5E5D",
                    }}
                  >
                    <option value="tous">tous</option>
                    <option value="tableau">compte-rendus tabulaires</option>
                    <option value="planning">plannings</option>
                    <option value="texte">documents texte</option>
                  </select>
                </div>
              </div>

              <div
                className="max-h-[60vh] overflow-auto rounded-lg border"
                style={{ backgroundColor: "#BEE9E8", borderColor: "#5D5E5D" }}
              >
                <table className="w-full text-xs text-left">
                  <tbody
                    className="divide-y"
                    style={{ borderColor: "#5D5E5D" }}
                  >
                    {loading ? (
                      <tr>
                        <td
                          colSpan={3}
                          className="p-6 text-center"
                          style={{ color: "#5D5E5D" }}
                        >
                          Chargement...
                        </td>
                      </tr>
                    ) : filteredDbFiles.length > 0 ? (
                      filteredDbFiles.map((item, index) => (
                        <tr
                          key={`${item.id}-${item.name}-${index}`} // <--- Clé unique garantie
                          className="hover:bg-[#CAEEFF]/50 transition-colors"
                        >
                          <td
                            className="p-2 font-medium truncate max-w-[280px]"
                            style={{ color: "#5D5E5D" }}
                            title={item.name}
                          >
                            {item.name}
                          </td>
                          <td className="p-2">
                            <span
                              className="inline-block px-2 py-0.5 rounded text-[10px]"
                              style={{
                                color: "#5D5E5D",
                              }}
                            >
                              {item.docType}
                            </span>
                          </td>
                          <td
                            className="p-2 rounded text-[10px]"
                            style={{ color: "#5D5E5D" }}
                          >
                            {item.template || "Aucun template"}
                          </td>

                          <td className="p-2 text-right align-middle">
                            <button
                              onClick={() => handleDeleteFile(item)}
                              className="p-1 text-white text-xs font-medium rounded-md transition flex items-center gap-1.5 shadow-sm"
                              title="Supprimer de la base"
                              style={{ backgroundColor: "#5FA8D3" }}
                            >
                              <MinusIcon className="w-4 h-4" />
                            </button>
                          </td>
                        </tr>
                      ))
                    ) : null}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 2. ZONE DE CHAT PRINCIPALE */}
      <div
        className="flex-1 flex flex-col h-full overflow-hidden"
        style={{ backgroundColor: "#CAEEFF" }}
      >
        {/* Liste des Messages */}
        <div className="flex-1 overflow-y-auto p-4 flex flex-col">
          <div className="max-w-xl mx-auto space-y-4 w-full">
            {messages.map((msg, index) => {
              // On vérifie directement si le message embarque des données structurées JSON
              // On vérifie si le message contient un tableau ou un document unique
              const hasTable = msg.sender === "bot" && msg.tables;
              const hasDocument = msg.sender === "bot" && msg.documents;

              return (
                <div
                  key={index}
                  className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start gap-2"}`}
                >
                  {/* Icône affichée uniquement pour l'agent */}
                  {msg.sender !== "user" && (
                    <div
                      className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 border mt-1 shadow-sm"
                      style={{
                        backgroundColor: "#BEE9E8",
                        borderColor: "#5D5E5D",
                        color: "#5D5E5D",
                      }}
                    >
                      <Bot className="w-4 h-4" />
                    </div>
                  )}

                  <div
                    className={`relative max-w-[80%] rounded-lg px-4 py-2 text-[13px] border shadow-sm ${
                      msg.sender === "user"
                        ? "text-white font-medium"
                        : "text-[#5D5E5D]"
                    }`}
                    style={{
                      backgroundColor:
                        msg.sender === "user" ? "#5FA8D3" : "#BEE9E8",
                      borderColor: "#5D5E5D",
                    }}
                  >
                    {/* Bouton "Agrandir" dans le coin si c'est un message avec un tableau */}
                    {hasTable && (
                      <button
                        onClick={() =>
                          setShowTableModal({
                            tables: msg.tables,
                            documents: msg.documents,
                          })
                        }
                        className="absolute top-2 right-2 px-2 py-0.5 flex items-center gap-1 shadow-xs transition z-10 hover:bg-black/5 rounded"
                        title="Afficher en plein écran"
                      >
                        <Expand className="w-4 h-4" />
                      </button>
                    )}

                    {hasTable ? (
                      <div className="overflow-x-auto my-1 pt-5">
                        <TableResult results={msg.tables ?? []} />
                      </div>
                    ) : hasDocument ? (
                      <div className="space-y-1 pt-1">
                        <div className="font-bold">
                          {msg.documents?.[0]?.title}
                        </div>
                        <p className="whitespace-pre-wrap">
                          {msg.documents?.[0]?.data}
                        </p>
                      </div>
                    ) : (
                      <p className="whitespace-pre-wrap">{msg.text}</p>
                    )}
                  </div>
                </div>
              );
            })}
            {/* Indicateur "L'agent réfléchit..." */}
            {isChatLoading && (
              <div className="flex justify-start gap-2">
                <div
                  className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 border mt-1 shadow-sm"
                  style={{
                    backgroundColor: "#BEE9E8",
                    borderColor: "#5D5E5D",
                    color: "#5D5E5D",
                  }}
                >
                  <Bot className="w-4 h-4" />
                </div>
                <div
                  className="text-[13px] rounded-lg px-4 py-2 italic border shadow-sm"
                  style={{
                    backgroundColor: "#BEE9E8",
                    borderColor: "#5D5E5D",
                    color: "#5D5E5D",
                  }}
                >
                  L'agent réfléchit...
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Formulaire d'envoi */}
        <div className="px-4 pb-4" style={{ backgroundColor: "#CAEEFF" }}>
          <form
            onSubmit={handleSendMessage}
            className="max-w-xl mb-2 mx-auto flex gap-2 w-full"
          >
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Posez votre question sur vos documents..."
              className="flex-1 rounded-lg px-4 py-2 text-[13px] focus:outline-none border shadow-inner placeholder-[#5D5E5D]/60"
              style={{
                backgroundColor: "#BEE9E8",
                borderColor: "#5D5E5D",
                color: "#5D5E5D",
              }}
              disabled={isChatLoading}
            />
            <button
              type="submit"
              disabled={isChatLoading || !inputMessage.trim()}
              className="text-white text-[13px] px-4 py-2 rounded-lg transition-colors flex items-center justify-center disabled:opacity-50 shadow-sm hover:opacity-90"
              style={{ backgroundColor: "#5FA8D3" }}
              title="Envoyer"
            >
              <SendHorizontal className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>

      {/* --- MODALE DU TEMPLATE --- */}
      {showTemplateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div
            className="rounded-xl p-6 w-full max-w-md border shadow-xl flex flex-col gap-4 relative"
            style={{
              backgroundColor: "#CAEEFF",
              borderColor: "#5D5E5D",
              color: "#5D5E5D",
            }}
          >
            {/* EN-TÊTE AVEC TITRE ET CROIX DE FERMETURE */}
            <div className="flex justify-between items-center">
              <h3 className="text-sm font-bold">
                Gestion des templates de texte
              </h3>
              <button
                type="button"
                onClick={() => setShowTemplateModal(false)}
                className="p-1 rounded-md hover:bg-[#BEE9E8] transition opacity-70 hover:opacity-100"
                title="Fermer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* 1. LISTE DES TEMPLATES ENREGISTRÉS (EN HAUT) */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[11px] font-semibold opacity-80">
                Templates enregistrés :
              </label>

              <div
                className="max-h-32 overflow-y-auto flex flex-col gap-1 p-2 rounded-lg border shadow-inner"
                style={{ backgroundColor: "#BEE9E8", borderColor: "#5D5E5D" }}
              >
                {templatesList && templatesList.length > 0 ? (
                  templatesList.map((tpl, index) => (
                    <div
                      key={index}
                      onClick={() => setTemplateText(tpl.content)}
                      className="text-xs p-2 rounded hover:bg-[#CAEEFF] transition flex justify-between items-center cursor-pointer group"
                    >
                      <span className="font-medium truncate max-w-[200px]">
                        {tpl.name}
                      </span>

                      <div className="flex items-center gap-2">
                        {/* Bouton de suppression avec l'icône X de Lucide */}
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setTemplatesList(
                              templatesList.filter((_, i) => i !== index),
                            );
                          }}
                          className="p-1 rounded-md hover:bg-[#CAEEFF] transition opacity-60 group-hover:opacity-100"
                          style={{ color: "#5D5E5D" }}
                          title="Supprimer ce template"
                        >
                          <MinusIcon className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))
                ) : (
                  <span className="text-xs italic p-1 opacity-70">
                    Aucun template enregistré pour l'instant.
                  </span>
                )}
              </div>
            </div>

            {/* 2. ESPACE DE TEXTE (EN DESSOUS) */}
            <div className="flex flex-col gap-2">
              <label className="text-[11px] font-semibold opacity-80">
                Rédiger ou modifier :
              </label>

              {/* Nouveau champ pour donner un nom au template */}
              <input
                type="text"
                value={templateName}
                onChange={(e) => setTemplateName(e.target.value)}
                placeholder="Nom du template..."
                className="w-full rounded-lg px-3 py-2 text-xs focus:outline-none border shadow-inner"
                style={{
                  backgroundColor: "#BEE9E8",
                  borderColor: "#5D5E5D",
                  color: "#5D5E5D",
                }}
              />

              <textarea
                rows={4}
                value={templateText}
                onChange={(e) => setTemplateText(e.target.value)}
                placeholder="Écris ou colle ton template ici..."
                className="w-full rounded-lg p-3 text-xs focus:outline-none border shadow-inner resize-none"
                style={{
                  backgroundColor: "#BEE9E8",
                  borderColor: "#5D5E5D",
                  color: "#5D5E5D",
                }}
              />
            </div>

            {/* BOUTONS D'ACTION */}
            <div className="flex justify-end gap-2 mt-2">
              <button
                onClick={() => setShowTemplateModal(false)}
                className="px-3 py-1.5 rounded-md text-xs font-medium border transition hover:opacity-80"
                style={{ borderColor: "#5D5E5D" }}
              >
                Annuler
              </button>
              <button
                onClick={() => {
                  if (!templateText.trim()) return; // Évite d'enregistrer du vide

                  const newTemplateName =
                    templateName.trim() ||
                    `Template ${templatesList.length + 1}`;

                  // Ajoute le nouveau template à la liste
                  setTemplatesList([
                    ...templatesList,
                    { name: newTemplateName, content: templateText },
                  ]);

                  // Réinitialise le champ nom (optionnel)
                  setTemplateName("");
                }}
                className="px-3 py-1.5 rounded-md text-xs font-medium text-white transition hover:opacity-90 shadow-sm"
                style={{ backgroundColor: "#5FA8D3" }}
              >
                Enregistrer
              </button>
            </div>
          </div>
        </div>
      )}

      {/* --- MODALE D'AIDE ET INSTRUCTIONS --- */}
      {showHelpModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div
            className="rounded-xl p-6 w-full max-w-md border shadow-xl flex flex-col gap-4 relative"
            style={{
              backgroundColor: "#CAEEFF",
              borderColor: "#5D5E5D",
              color: "#5D5E5D",
            }}
          >
            {/* EN-TÊTE */}
            <div className="flex justify-between items-center">
              <h3 className="text-sm font-bold flex items-center gap-2">
                <HelpCircle className="w-4 h-4" />
                Aide & Instructions
              </h3>
              <button
                type="button"
                onClick={() => setShowHelpModal(false)}
                className="p-1 rounded-md hover:bg-[#BEE9E8] transition opacity-70 hover:opacity-100"
                style={{ color: "#5D5E5D" }}
                title="Fermer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* CONTENU DES INSTRUCTIONS */}
            <div
              className="flex flex-col gap-3 p-4 rounded-lg border shadow-inner overflow-y-auto max-h-[60vh] text-xs leading-relaxed"
              style={{ backgroundColor: "#BEE9E8", borderColor: "#5D5E5D" }}
            >
              <p className="font-semibold text-[13px]">
                Guide de bonne utilisation
              </p>

              <ul className="list-disc pl-4 flex flex-col gap-2">
                <li>
                  <strong>
                    Avertissement sur le traitement des plannings :
                  </strong>{" "}
                  Cette application ne sait traiter que des plannings
                  préalablement extraits sous format Excel, qui contiennent a
                  minima les colonnes "ID", "Task_Name", "Duration",
                  "Start_Date" et "Finish_Date".
                </li>
                <li>
                  <strong>Type du document :</strong> Dans le traitement et
                  l'enregistrement des fichiers, il est particulièrement
                  important de distinguer entre les compte-rendus et les
                  plannings. Les autres documents (pdf, mails) entrent dans la
                  catégorie "Autre".
                </li>
                <li>
                  <strong>Nom d'onglet :</strong> Le nom d'onglet doit être
                  rempli pour le traitement des CRs sous format Excel.
                </li>
                <li>
                  <strong>Numéro de tableau :</strong> Le numéro de tableau doit
                  être rempli pour le traitement des CRs sous format Word. Il
                  s'agit de la position du tableau dans le document Word :
                  est-il le premier ou le second tableau ? Le troisième ?
                </li>
                <li>
                  <strong>Template :</strong> Le template correspond aux noms
                  qui vont être attribués aux colonnes de votre CR (Excel ou
                  Word) lors du traitement du fichier. Ecrivez chaque nom de
                  colonne séparée par une virgule. Vous pouvez enregistrer des
                  templates récurrents avec le bouton "Template".
                </li>

                <li>
                  <strong>Comparaison de plannings :</strong> Lorsque vous
                  comparez deux plannings entre eux, l'un d'entre eux doit être
                  désigné comme étant la "source" pour le désigner comme objet
                  principal de la comparaison.
                </li>
              </ul>

              <div className="mt-2 p-2 rounded bg-[#CAEEFF]/50 border border-[#5D5E5D]/20">
                <p className="italic opacity-80 text-[11px] text-center">
                  En cas de problème technique, contactez votre administrateur.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MODALE DE PLEIN ÉCRAN POUR LE TABLEAU */}
      {showTableModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs p-4">
          <div
            className="bg-white rounded-lg shadow-xl border border-[#5D5E5D] w-full max-w-4xl max-h-[90vh] flex flex-col p-6 animate-in fade-in zoom-in-95 duration-150"
            style={{ backgroundColor: "#CAEEFF" }}
          >
            {/* En-tête de la modale */}
            <div className="flex justify-between items-center pb-3 border-b border-[#5D5E5D]/30 mb-4">
              <h3
                className="font-semibold text-sm"
                style={{ color: "#5D5E5D" }}
              >
                Visualisation détaillée du tableau
              </h3>
              <button
                onClick={() => setShowTableModal(null)}
                className="p-1 rounded hover:bg-black/5"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 overflow-y-auto space-y-6">
              {/* Rendu des Tables en plein écran */}
              {showTableModal.tables && showTableModal.tables.length > 0 && (
                <div className="space-y-4">
                  {showTableModal.tables.map((tableItem, idx) => (
                    <div key={idx} className="space-y-2">
                      <TableResult results={[tableItem]} />
                    </div>
                  ))}
                </div>
              )}

              {/* Rendu des Documents textuels en plein écran */}
              {showTableModal.documents &&
                showTableModal.documents.length > 0 && (
                  <div className="space-y-4">
                    <h4 className="text-xs font-bold uppercase tracking-wider">
                      Extraits textuels (Documents)
                    </h4>
                    {showTableModal.documents.map((doc, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded border bg-white text-xs space-y-1 shadow-xs"
                        style={{ borderColor: "#5D5E5D" }}
                      >
                        <div className="font-bold text-blue-600">
                          {doc.title}
                        </div>
                        <p className="whitespace-pre-wrap">{doc.data}</p>
                      </div>
                    ))}
                  </div>
                )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
