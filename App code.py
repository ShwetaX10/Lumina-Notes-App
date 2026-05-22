import React, { useState, useEffect, useMemo, useTransition } from "react";
import {
  Search,
  Plus,
  Edit3,
  Trash2,
  Bookmark,
  Sparkles,
  Download,
  Sun,
  Moon,
  RotateCcw,
  Check,
  X,
  FileText,
  FileJson,
  Info,
  Calendar,
  Layers,
  Tag,
  Smile,
  AlertCircle,
  Mic,
  MicOff,
  Wifi,
  WifiOff,
  Cloud,
  CloudOff
} from "lucide-react";
import { useSpeechRecognition } from "./hooks/useSpeechRecognition";
import { 
  isFirebaseEnabled, 
  auth, 
  db, 
  loginWithGoogle, 
  logoutUser, 
  handleFirestoreError, 
  OperationType 
} from "./firebase";
import { 
  collection, 
  doc, 
  setDoc, 
  deleteDoc, 
  query, 
  where, 
  onSnapshot 
} from "firebase/firestore";

interface Note {
  id: string;
  title: string;
  content: string;
  pinned: boolean;
  trashed: boolean;
  createdAt: number;
  updatedAt: number;
  summary?: string;
  tags?: string[];
  mood?: string;
  isAnalyzing?: boolean;
}

// Initial placeholder notes to give users an elegant workspace out of the box
const DEFAULT_NOTES: Note[] = [
  {
    id: "note-1",
    title: "Project Logic Refactor",
    content: "Finalize the transition to **React Hooks** for better state `logic` management. Need to audit the auth provider...\n\n- Write custom hook for localStorage.\n- Test performance under high note load.\n- Replace old contextual providers.",
    pinned: true,
    trashed: false,
    createdAt: Date.now() - 1000 * 60 * 10,
    updatedAt: Date.now() - 1000 * 60 * 10,
    summary: "Refactoring authentication flow with React hooks to optimize state.",
    tags: ["dev", "architecture"],
    mood: "Focused 🎯"
  },
  {
    id: "note-2",
    title: "Weekly Team Sync",
    content: "Weekly team agenda and feedback sync notes.\n\n* \"The logic is sound, we just need more testing.\"\n* Focus on **ux details** and styling contrast.\n* Release beta build next Thursday.",
    pinned: false,
    trashed: false,
    createdAt: Date.now() - 1000 * 60 * 60 * 2,
    updatedAt: Date.now() - 1000 * 60 * 60 * 2,
    summary: "Discussed system architecture and confirmed core business logics.",
    tags: ["meeting", "sync"],
    mood: "Collaborative 🤝"
  },
  {
    id: "note-3",
    title: "API Endpoints Design",
    content: "We need clean and standard endpoint structures:\n\n`GET /api/v1/notes`\n`POST /api/v1/notes/analyze`\n`DELETE /api/v1/notes/:id`",
    pinned: false,
    trashed: false,
    createdAt: Date.now() - 1000 * 60 * 60 * 4,
    updatedAt: Date.now() - 1000 * 60 * 60 * 4,
    summary: "Proposed restful endpoints for note operations.",
    tags: ["backend", "api"],
    mood: "Analytical 📊"
  }
];

export default function App() {
  // Cloud Auth & Synchronization states
  const [user, setUser] = useState<any | null>(null);
  const [isSyncingWithCloud, setIsSyncingWithCloud] = useState(false);
  const [firebaseStatus, setFirebaseStatus] = useState<"disabled" | "ready" | "error">(() => {
    return isFirebaseEnabled ? "ready" : "disabled";
  });

  // Load notes from localStorage or initialize with defaults
  const [notes, setNotes] = useState<Note[]>(() => {
    const saved = localStorage.getItem("lumina_notes");
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        console.error("Failed to parse saved notes, using default templates", e);
      }
    }
    return DEFAULT_NOTES;
  });

  // Theme support
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    const saved = localStorage.getItem("lumina_theme");
    return saved === "light" ? "light" : "dark";
  });

  // Sidebar navigation settings
  const [currentTab, setCurrentTab] = useState<"all" | "pinned" | "trash">("all");
  
  // Search state
  const [searchQuery, setSearchQuery] = useState("");
  
  // Sorting setting (newest or oldest)
  const [sortBy, setSortBy] = useState<"newest" | "oldest">("newest");
  
  // Modal editor state
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [editingNote, setEditingNote] = useState<Partial<Note> | null>(null);
  const [editorTitle, setEditorTitle] = useState("");
  const [editorContent, setEditorContent] = useState("");
  const [editorTabs, setEditorTabs] = useState<"write" | "preview">("write");

  // Speech Recognition hook and states
  const { 
    isListening, 
    transcript, 
    startListening, 
    stopListening, 
    clearTranscript, 
    error: speechError, 
    supported: isSpeechSupported 
  } = useSpeechRecognition();
  
  const [dictationTarget, setDictationTarget] = useState<"title" | "content">("content");

  // Listen to Auth State Changes
  useEffect(() => {
    if (isFirebaseEnabled && auth) {
      const unsubscribe = auth.onAuthStateChanged(
        (u) => {
          setUser(u);
          if (u) {
            setFirebaseStatus("ready");
          } else {
            setFirebaseStatus(isFirebaseEnabled ? "ready" : "disabled");
          }
        },
        (error) => {
          console.error("Auth state change listener error:", error);
          setFirebaseStatus("error");
        }
      );
      return () => unsubscribe();
    }
  }, []);

  // Live listener to Firestore note streams when user is logged in
  useEffect(() => {
    if (!isFirebaseEnabled || !db || !user) {
      return;
    }
    
    setIsSyncingWithCloud(true);
    const notesQuery = query(
      collection(db, "notes"),
      where("userId", "==", user.uid)
    );
    
    const unsubscribe = onSnapshot(
      notesQuery,
      (snapshot) => {
        const cloudNotes: Note[] = [];
        snapshot.forEach((docSnap) => {
          cloudNotes.push(docSnap.data() as Note);
        });
        
        // Match cloud notes or keep custom template if they haven't synced yet
        if (cloudNotes.length > 0) {
          setNotes(cloudNotes);
        }
        setIsSyncingWithCloud(false);
      },
      (error) => {
        setIsSyncingWithCloud(false);
        setFirebaseStatus("error");
        handleFirestoreError(error, OperationType.LIST, "notes");
      }
    );
    
    return () => unsubscribe();
  }, [user]);

  // Migrate local notes upwards when user registers/logs in to prevent lost offline progress
  useEffect(() => {
    if (!isFirebaseEnabled || !db || !user || notes.length === 0) return;
    
    const migrateNotes = async () => {
      try {
        const unmigratedLocalNotes = notes.filter(n => !n.id.startsWith("cloud_"));
        if (unmigratedLocalNotes.length === 0) return;
        
        for (const localNote of unmigratedLocalNotes) {
          const cloudNoteId = "cloud_" + localNote.id.replace("note-", "");
          const noteData = {
            ...localNote,
            id: cloudNoteId,
            userId: user.uid,
            updatedAt: Date.now()
          };
          
          await setDoc(doc(db!, "notes", cloudNoteId), noteData);
        }
        console.log("Successfully migrated local workspace to Cloud Sync");
      } catch (err) {
        console.error("Local workspace cloud migration failed:", err);
      }
    };
    
    migrateNotes();
  }, [user]);

  // Sync state changes to localStorage only when offline (not authenticated in the cloud)
  useEffect(() => {
    if (!user) {
      localStorage.setItem("lumina_notes", JSON.stringify(notes));
    }
  }, [notes, user]);

  useEffect(() => {
    localStorage.setItem("lumina_theme", theme);
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  // Append transcript to editor matching selected target in real-time
  useEffect(() => {
    if (transcript) {
      if (dictationTarget === "title") {
        setEditorTitle(prev => {
          const base = prev.trim();
          return base ? `${base} ${transcript}` : transcript;
        });
      } else {
        setEditorContent(prev => {
          const base = prev.trim();
          return base ? `${base}\n${transcript}` : transcript;
        });
      }
      clearTranscript();
    }
  }, [transcript, dictationTarget]);

  // Local fallback analyze helper matching server-side heuristics
  const analyzeLocally = (title: string, content: string) => {
    const text = `${title} ${content}`.toLowerCase();
    const tagsSet = new Set<string>();
    
    // Extract basic tags based on simple content heuristics
    if (text.includes("react") || text.includes("code") || text.includes("typescript") || text.includes("dev") || text.includes("api") || text.includes("bug")) {
      tagsSet.add("dev");
    }
    if (text.includes("meet") || text.includes("sync") || text.includes("team") || text.includes("call") || text.includes("weekly")) {
      tagsSet.add("meeting");
    }
    if (text.includes("idea") || text.includes("brainstorm") || text.includes("creative")) {
      tagsSet.add("brainstorm");
    }
    if (tagsSet.size === 0) {
      tagsSet.add("personal");
    }
    
    let mood = "Focused 🎯";
    if (text.includes("happy") || text.includes("great") || text.includes("awesome") || text.includes("won") || text.includes("yay") || text.includes("excited")) {
      mood = "Excited 🎉";
    } else if (text.includes("meeting") || text.includes("sync") || text.includes("discuss") || text.includes("team")) {
      mood = "Collaborative 🤝";
    } else if (text.includes("sad") || text.includes("bad") || text.includes("fail") || text.includes("issue") || text.includes("error")) {
      mood = "Concerned ⚠️";
    } else if (text.includes("learn") || text.includes("read") || text.includes("research") || text.includes("books")) {
      mood = "Mindful 🧘";
    } else if (text.includes("idea") || text.includes("design") || text.includes("drawing")) {
      mood = "Creative 🧠";
    }
    
    const clean = content.replace(/[#*`_-]/g, "").trim();
    const summary = clean.length > 70 ? clean.substring(0, 67) + "..." : clean || "Empty note content.";
    
    return {
      summary,
      tags: Array.from(tagsSet),
      mood
    };
  };

  // Unified Note Save logic (Cloud Firestore sync vs Local Offline cache)
  const saveNoteCloudOrLocal = async (noteItem: Note) => {
    if (isFirebaseEnabled && db && user) {
      try {
        const secureNote = {
          ...noteItem,
          userId: user.uid
        };
        await setDoc(doc(db, "notes", noteItem.id), secureNote);
      } catch (error) {
        handleFirestoreError(error, OperationType.WRITE, `notes/${noteItem.id}`);
      }
    } else {
      setNotes(prev => {
        const exists = prev.some(n => n.id === noteItem.id);
        if (exists) {
          return prev.map(n => n.id === noteItem.id ? noteItem : n);
        }
        return [noteItem, ...prev];
      });
    }
  };

  // Unified delete action
  const deleteNoteCloudOrLocal = async (noteId: string) => {
    if (isFirebaseEnabled && db && user) {
      try {
        await deleteDoc(doc(db, "notes", noteId));
      } catch (error) {
        handleFirestoreError(error, OperationType.DELETE, `notes/${noteId}`);
      }
    } else {
      setNotes(prev => prev.filter(n => n.id !== noteId));
    }
  };

  // Triggers server-side AI summary estimation with optimistic updating
  const triggerAIAnalysis = async (noteId: string, title: string, content: string) => {
    // Optimistic set isAnalyzing locally or in Firestore
    if (isFirebaseEnabled && db && user) {
      try {
        const origNote = notes.find(n => n.id === noteId);
        if (origNote) {
          const updatedNote = { ...origNote, isAnalyzing: true };
          await setDoc(doc(db, "notes", noteId), { ...updatedNote, userId: user.uid });
        }
      } catch (err) {
        console.error("AI Analysis Firebase state sync failed", err);
      }
    } else {
      setNotes(prev => prev.map(n => n.id === noteId ? { ...n, isAnalyzing: true } : n));
    }
    
    try {
      const response = await fetch("/api/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ title, content })
      });
      
      if (!response.ok) {
        throw new Error("Analysis request failed");
      }
      
      const data = await response.json();
      
      if (isFirebaseEnabled && db && user) {
        const origNote = notes.find(n => n.id === noteId);
        if (origNote) {
          const updatedNote = {
            ...origNote,
            summary: data.summary,
            tags: data.tags,
            mood: data.mood,
            isAnalyzing: false,
            userId: user.uid
          };
          await setDoc(doc(db, "notes", noteId), updatedNote);
        }
      } else {
        setNotes(prev => prev.map(n => 
          n.id === noteId 
            ? { 
                ...n, 
                summary: data.summary, 
                tags: data.tags, 
                mood: data.mood, 
                isAnalyzing: false 
              } 
            : n
        ));
      }
    } catch (e) {
      console.warn("Server AI is not accessible or failed. Falling back to local analysis Heuristics.", e);
      const localResult = analyzeLocally(title, content);
      
      if (isFirebaseEnabled && db && user) {
        const origNote = notes.find(n => n.id === noteId);
        if (origNote) {
          const updatedNote = {
            ...origNote,
            summary: localResult.summary,
            tags: localResult.tags,
            mood: localResult.mood,
            isAnalyzing: false,
            userId: user.uid
          };
          await setDoc(doc(db, "notes", noteId), updatedNote);
        }
      } else {
        setNotes(prev => prev.map(n => 
          n.id === noteId 
            ? { 
                ...n, 
                summary: localResult.summary, 
                tags: localResult.tags, 
                mood: localResult.mood, 
                isAnalyzing: false 
              } 
            : n
        ));
      }
    }
  };

  // Handler to open editor for creating a new note
  const handleNewNoteClick = () => {
    setEditingNote(null);
    setEditorTitle("");
    setEditorContent("");
    setEditorTabs("write");
    setIsEditorOpen(true);
  };

  // Handler to open editor for editing existing note
  const handleEditNoteClick = (note: Note) => {
    setEditingNote(note);
    setEditorTitle(note.title);
    setEditorContent(note.content);
    setEditorTabs("write");
    setIsEditorOpen(true);
  };

  // Quick pin toggle handler
  const handleTogglePin = async (noteId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const noteToModify = notes.find(n => n.id === noteId);
    if (!noteToModify) return;
    const updatedNote = { ...noteToModify, pinned: !noteToModify.pinned, updatedAt: Date.now() };
    await saveNoteCloudOrLocal(updatedNote);
  };

  // Quick move to Trash handler
  const handleMoveToTrash = async (noteId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const noteToModify = notes.find(n => n.id === noteId);
    if (!noteToModify) return;
    const updatedNote = { ...noteToModify, trashed: true, pinned: false, updatedAt: Date.now() };
    await saveNoteCloudOrLocal(updatedNote);
  };

  // Restore logic
  const handleRestoreFromTrash = async (noteId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const noteToModify = notes.find(n => n.id === noteId);
    if (!noteToModify) return;
    const updatedNote = { ...noteToModify, trashed: false, updatedAt: Date.now() };
    await saveNoteCloudOrLocal(updatedNote);
  };

  // Permanent Delete
  const handlePermanentDelete = async (noteId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm("Are you sure you want to permanently delete this note? This action cannot be undone.")) {
      await deleteNoteCloudOrLocal(noteId);
    }
  };

  // Core Save Action (handles both Create and Update)
  const handleSaveNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editorTitle.trim() && !editorContent.trim()) {
      alert("Please enter a title or write some content before saving.");
      return;
    }

    const currentTitle = editorTitle.trim() || "Untitled Note";
    const currentContent = editorContent;

    if (editingNote && editingNote.id) {
      // Editing existing note
      const updatedId = editingNote.id;
      const isContentChanged = 
        editingNote.title !== currentTitle || 
        editingNote.content !== currentContent;
        
      const origNote = notes.find(n => n.id === updatedId);
      const updatedNote: Note = {
        ...origNote!,
        id: updatedId,
        title: currentTitle,
        content: currentContent,
        updatedAt: Date.now()
      };
      
      await saveNoteCloudOrLocal(updatedNote);
      setIsEditorOpen(false);
      
      // If content changed, re-analyze to keep AI insights fresh!
      if (isContentChanged) {
        triggerAIAnalysis(updatedId, currentTitle, currentContent);
      }
    } else {
      // Create new note
      const newId = user ? "cloud_" + Math.random().toString(36).substring(2, 11) : "note-" + Math.random().toString(36).substring(2, 11);
      const newNote: Note = {
        id: newId,
        title: currentTitle,
        content: currentContent,
        pinned: false,
        trashed: false,
        createdAt: Date.now(),
        updatedAt: Date.now(),
        isAnalyzing: true // initial analyzing state
      };
      
      await saveNoteCloudOrLocal(newNote);
      setIsEditorOpen(false);
      
      // Trigger AI analysis server-side call
      triggerAIAnalysis(newId, currentTitle, currentContent);
    }
  };

  // Markdown compiler logic for formatting notes
  const renderMarkdown = (text: string, searchHighlightQuery?: string): React.ReactNode => {
    if (!text) return <span className="text-zinc-500 italic">No notes body context entered.</span>;
    
    // Safety escape HTML first
    let compiled = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
      
    // 1. Double asterisks bold formatting
    compiled = compiled.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    
    // 2. Single asterisk italic formatting
    compiled = compiled.replace(/\*(.*?)\*/g, "<em>$1</em>");
    
    // 3. Simple strikethroughs
    compiled = compiled.replace(/~~(.*?)~~/g, "<del>$1</del>");
    
    // 4. Highlight inline backtick styles code
    compiled = compiled.replace(
      /`(.*?)`/g, 
      '<code class="mono px-1 py-0.5 rounded bg-zinc-950/80 text-indigo-400 dark:text-indigo-300">$1</code>'
    );
    
    // 5. Blockquotes line-wise
    compiled = compiled.replace(/^&gt;\s+(.*)$/gm, '<blockquote class="border-l-2 border-indigo-500 pl-3 text-zinc-500 italic my-1">$1</blockquote>');
    
    // 6. Bullet lines translation
    compiled = compiled.replace(/^[*-]\s+(.*)$/gm, '<li class="list-disc list-inside ml-2 py-0.5">$1</li>');

    // Case-insensitive highlighted query wrapping
    if (searchHighlightQuery && searchHighlightQuery.trim().length > 0) {
      const escapedQuery = searchHighlightQuery.replace(/[-\/\\^$*+?.()|[\]{}]/g, "\\$&");
      const highlightRegex = new RegExp(`(${escapedQuery})`, "gi");
      
      // Split safely by HTML tags so we don't pollute code labels or structures
      const tagFragments = compiled.split(/(<[^>]+>)/);
      const outputFragments = tagFragments.map(fragment => {
        if (fragment.startsWith("<") && fragment.endsWith(">")) {
          return fragment;
        }
        return fragment.replace(
          highlightRegex, 
          '<span class="highlight bg-indigo-500/40 text-white rounded px-0.5 font-medium">$1</span>'
        );
      });
      compiled = outputFragments.join("");
    }
    
    return (
      <div 
        dangerouslySetInnerHTML={{ __html: compiled }} 
        className="text-zinc-400 dark:text-zinc-400 text-[13px] leading-relaxed space-y-1 break-words" 
      />
    );
  };

  // Title highlighters
  const renderHighlightedTitle = (titleText: string, searchHighlightQuery: string) => {
    if (!searchHighlightQuery || !searchHighlightQuery.trim()) {
      return <>{titleText}</>;
    }
    const escapedQuery = searchHighlightQuery.replace(/[-\/\\^$*+?.()|[\]{}]/g, "\\$&");
    const highlightRegex = new RegExp(`(${escapedQuery})`, "gi");
    const titleParts = titleText.split(highlightRegex);
    return (
      <>
        {titleParts.map((part, index) => 
          highlightRegex.test(part) ? (
            <span key={index} className="highlight bg-indigo-500/40 text-white rounded px-0.5 font-semibold">
              {part}
            </span>
          ) : (
            part
          )
        )}
      </>
    );
  };

  // Core Filtering & Searching logic
  const filteredNotes = useMemo(() => {
    // Stage 1: Filter active tab view category
    let notesSet = notes;
    if (currentTab === "trash") {
      notesSet = notes.filter(n => n.trashed === true);
    } else if (currentTab === "pinned") {
      notesSet = notes.filter(n => n.pinned === true && n.trashed === false);
    } else {
      notesSet = notes.filter(n => n.trashed === false);
    }

    // Stage 2: Parse search filter query case-insensitive
    if (searchQuery.trim().length > 0) {
      const parsedQuery = searchQuery.toLowerCase();
      notesSet = notesSet.filter(n => {
        return (
          n.title.toLowerCase().includes(parsedQuery) ||
          n.content.toLowerCase().includes(parsedQuery) ||
          (n.summary && n.summary.toLowerCase().includes(parsedQuery)) ||
          (n.tags && n.tags.some(t => t.toLowerCase().includes(parsedQuery))) ||
          (n.mood && n.mood.toLowerCase().includes(parsedQuery))
        );
      });
    }

    // Stage 3: Organize items by sort state (pinned notes always sit topmost if in dashboard)
    const sorted = [...notesSet].sort((a, b) => {
      if (sortBy === "newest") {
        return b.createdAt - a.createdAt;
      } else {
        return a.createdAt - b.createdAt;
      }
    });

    if (currentTab === "all") {
      // Split pinned out on dashboard
      const pinnedList = sorted.filter(n => n.pinned);
      const regularList = sorted.filter(n => !n.pinned);
      return [...pinnedList, ...regularList];
    }

    return sorted;
  }, [notes, currentTab, searchQuery, sortBy]);

  // Extract list of all unique tags to display beautiful stats in sidebar
  const activeTags = useMemo(() => {
    const counts: { [key: string]: number } = {};
    notes
      .filter(n => !n.trashed)
      .forEach(n => {
        if (n.tags) {
          n.tags.forEach(t => {
            const cleanTag = t.trim().toLowerCase();
            if (cleanTag) {
              counts[cleanTag] = (counts[cleanTag] || 0) + 1;
            }
          });
        }
      });
    return Object.entries(counts).map(([name, count]) => ({ name, count })).slice(0, 5);
  }, [notes]);

  // Download logic handlers
  const downloadJSONBackup = () => {
    const backupData = notes.filter(n => !n.trashed);
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(backupData, null, 2));
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `lumina_notes_backup_${new Date().toISOString().split('T')[0]}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const downloadTXTBackup = () => {
    const rawNotes = notes.filter(n => !n.trashed);
    let outputString = "=== LUMINA NOTES EXPORT ===\n\n";
    
    rawNotes.forEach((n, idx) => {
      outputString += `NOTE #${idx + 1}\n`;
      outputString += `Title   : ${n.title}\n`;
      outputString += `Created : ${new Date(n.createdAt).toLocaleString()}\n`;
      if (n.mood) outputString += `Mood    : ${n.mood}\n`;
      if (n.tags && n.tags.length > 0) outputString += `Tags    : #${n.tags.join(" #")}\n`;
      if (n.summary) outputString += `Summary : ${n.summary}\n`;
      outputString += `Content :\n----------------------------------------\n`;
      outputString += `${n.content}\n`;
      outputString += `----------------------------------------\n\n\n`;
    });

    const dataStr = "data:text/plain;charset=utf-8," + encodeURIComponent(outputString);
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `lumina_notes_summary_${new Date().toISOString().split('T')[0]}.txt`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  // Helper theme toggler
  const toggleThemeMode = () => {
    setTheme(prev => prev === "dark" ? "light" : "dark");
  };

  return (
    <div id="lumina-app" className={`flex h-screen w-screen overflow-hidden transition-colors duration-300 font-sans ${theme === "dark" ? "bg-zinc-950 text-zinc-100" : "bg-zinc-50 text-zinc-900"}`}>
      
      {/* Sidebar Navigation */}
      <aside id="lumina-sidebar" className={`w-64 flex flex-col justify-between py-6 border-r shrink-0 transition-colors ${theme === "dark" ? "bg-zinc-950 border-zinc-900" : "bg-zinc-100 border-zinc-200"}`}>
        <div className="px-6 flex-1 flex flex-col overflow-y-auto">
          {/* Brand Logo Header */}
          <div className="flex items-center justify-between mb-8 text-indigo-500 dark:text-indigo-400">
            <div className="flex items-center gap-3">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="animate-pulse">
                <path d="M15.5 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V8.5L15.5 3Z"/>
                <path d="M15 3v6h6"/>
                <path d="M9 18h6"/>
                <path d="M9 14h6"/>
                <path d="M9 10h1"/>
              </svg>
              <span className="font-bold text-xl tracking-tight dark:text-white text-zinc-900">LUMINA</span>
            </div>
            
            {/* Quick Dark Mode Switch Badge */}
            <button 
              id="theme-toggler"
              onClick={toggleThemeMode} 
              className={`p-2 rounded-lg transition-colors border ${theme === "dark" ? "bg-zinc-900 border-zinc-800 text-amber-400 hover:bg-zinc-800" : "bg-white border-zinc-300 text-indigo-600 hover:bg-zinc-50"}`}
              title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
            >
              {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
            </button>
          </div>

          {/* Navigation Items */}
          <nav className="space-y-1">
            <button
              id="tab-all"
              onClick={() => { setCurrentTab("all"); setSearchQuery(""); }}
              className={`w-full flex items-center justify-between px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${currentTab === "all" ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/10" : "text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200 hover:bg-zinc-200/50 dark:hover:bg-zinc-900/40"}`}
            >
              <span className="flex items-center gap-3">
                <Layers size={17} />
                All Notes
              </span>
              <span className={`text-[11px] px-2 py-0.5 rounded-full ${currentTab === "all" ? "bg-indigo-700 text-white" : "bg-zinc-200 dark:bg-zinc-900 text-zinc-500"}`}>
                {notes.filter(n => !n.trashed).length}
              </span>
            </button>

            <button
              id="tab-pinned"
              onClick={() => { setCurrentTab("pinned"); setSearchQuery(""); }}
              className={`w-full flex items-center justify-between px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${currentTab === "pinned" ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/10" : "text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200 hover:bg-zinc-200/50 dark:hover:bg-zinc-900/40"}`}
            >
              <span className="flex items-center gap-3">
                <Bookmark size={17} />
                Pinned
              </span>
              <span className={`text-[11px] px-2 py-0.5 rounded-full ${currentTab === "pinned" ? "bg-indigo-700 text-white" : "bg-zinc-200 dark:bg-zinc-900 text-zinc-500"}`}>
                {notes.filter(n => n.pinned && !n.trashed).length}
              </span>
            </button>

            <button
              id="tab-trash"
              onClick={() => { setCurrentTab("trash"); setSearchQuery(""); }}
              className={`w-full flex items-center justify-between px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${currentTab === "trash" ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/10" : "text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200 hover:bg-zinc-200/50 dark:hover:bg-zinc-900/40"}`}
            >
              <span className="flex items-center gap-3">
                <Trash2 size={17} />
                Trash
              </span>
              <span className={`text-[11px] px-2 py-0.5 rounded-full ${currentTab === "trash" ? "bg-indigo-700 text-white" : "bg-zinc-200 dark:bg-zinc-900 text-zinc-500"}`}>
                {notes.filter(n => n.trashed).length}
              </span>
            </button>
          </nav>

          {/* Dynamic Recent Tags Section */}
          <div className="mt-8 mb-3 text-xs font-semibold uppercase tracking-widest text-zinc-400 dark:text-zinc-600">
            Active Tags
          </div>
          
          <div className="space-y-2 flex-1 overflow-y-auto max-h-[160px] pr-2">
            {activeTags.length > 0 ? (
              activeTags.map((tag, i) => (
                <button
                  key={tag.name}
                  onClick={() => setSearchQuery(tag.name)}
                  className="w-full flex items-center justify-between text-xs py-1 px-2 rounded hover:bg-zinc-200/60 dark:hover:bg-zinc-900/60 text-zinc-600 dark:text-zinc-400 hover:text-indigo-500 text-left transition-all"
                >
                  <span className="flex items-center gap-2 truncate">
                    <span className={`w-1.5 h-1.5 rounded-full ${i % 3 === 0 ? "bg-indigo-500" : i % 3 === 1 ? "bg-emerald-500" : "bg-amber-500"}`} />
                    #{tag.name}
                  </span>
                  <span className="text-[10px] text-zinc-400 shrink-0">({tag.count})</span>
                </button>
              ))
            ) : (
              <div className="text-xs text-zinc-500 italic px-2 py-1">No active tags.</div>
            )}
          </div>
        </div>

        {/* Cloud Auth & Status Container */}
        <div id="firebase-profile-panel" className="mx-6 mb-4 p-4 rounded-xl border border-dashed flex flex-col gap-3 shrink-0 dark:border-zinc-800 border-zinc-200 bg-zinc-200/5 dark:bg-zinc-950/25 bg-zinc-200/5 dark:bg-zinc-950/25">
          <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-widest text-zinc-400 dark:text-zinc-500">
            <span>Cloud Sync</span>
            {isSyncingWithCloud ? (
              <span className="flex items-center gap-1.5 text-indigo-500 lowercase">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-ping" /> syncing
              </span>
            ) : user ? (
              <span className="flex items-center gap-1.5 text-emerald-500 lowercase">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> connected
              </span>
            ) : firebaseStatus === "disabled" ? (
              <span className="flex items-center gap-1.5 text-amber-500 lowercase animate-pulse">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500" /> offline mode
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-zinc-500 lowercase">
                <span className="w-1.5 h-1.5 rounded-full bg-zinc-500" /> unconfigured
              </span>
            )}
          </div>

          {user ? (
            <div className="flex items-center justify-between gap-1.5 bg-zinc-200/50 dark:bg-zinc-900/40 p-2 rounded-lg">
              <div className="flex items-center gap-2 truncate min-w-0">
                {user.photoURL ? (
                  <img src={user.photoURL} alt={user.displayName || "User"} className="w-6 h-6 rounded-full shrink-0" referrerPolicy="no-referrer" />
                ) : (
                  <div className="w-6 h-6 rounded-full bg-indigo-600 text-white flex items-center justify-center text-[10px] font-bold uppercase shrink-0">
                    {(user.displayName || "U").substring(0, 1)}
                  </div>
                )}
                <div className="flex flex-col min-w-0">
                  <span className="text-[11px] font-bold truncate dark:text-zinc-200 text-zinc-800 leading-tight">{user.displayName || "Lumina User"}</span>
                  <span className="text-[9px] text-zinc-500 truncate leading-none">{user.email}</span>
                </div>
              </div>
              <button
                id="firebase-signout-btn"
                onClick={async () => {
                  await logoutUser();
                  setUser(null);
                  setNotes(DEFAULT_NOTES); // load standard defaults back to screen safely
                }}
                className="px-2 py-1 hover:bg-zinc-200 dark:hover:bg-zinc-800 text-red-500 hover:text-red-600 rounded transition-colors text-[9px] font-bold cursor-pointer shrink-0"
                title="Sign Out"
              >
                Logout
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-[10px] text-zinc-500 leading-normal">
                Sync all summaries, tag indices, and markdown notes in real-time across devices securely.
              </p>
              <button
                id="firebase-signin-btn"
                disabled={!isFirebaseEnabled}
                onClick={async () => {
                  try {
                    const u = await loginWithGoogle();
                    setUser(u);
                  } catch (e) {
                    setFirebaseStatus("error");
                    alert("Authentication error: Please ensure Firebase console has Google provider active.");
                  }
                }}
                className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-xs font-bold bg-indigo-600 hover:bg-indigo-500 active:scale-95 transition-all text-white shadow shadow-indigo-600/10 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
              >
                <Sparkles size={11} className="animate-pulse" />
                <span>Sign In with Google</span>
              </button>
              {!isFirebaseEnabled && (
                <p className="text-[9px] text-zinc-500 italic leading-snug">
                  * Admin: terms are pending initialization. Click 'Accept' to connect.
                </p>
              )}
            </div>
          )}
        </div>

        {/* Actions Bottom Bar (Export options) */}
        <div id="export-panel" className="px-6 pt-4 border-t border-zinc-200 dark:border-zinc-900 space-y-2 shrink-0">
          <button
            id="export-txt-btn"
            onClick={downloadTXTBackup}
            disabled={notes.length === 0}
            className="w-full flex items-center justify-center gap-2 py-2 text-xs font-semibold border rounded-lg transition-all dark:border-zinc-800 dark:text-zinc-400 hover:bg-zinc-200/50 dark:hover:bg-zinc-900 text-zinc-600 hover:text-zinc-900 dark:hover:text-zinc-200 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            <FileText size={14} />
            <span>Export ALL .TXT</span>
          </button>
          <button
            id="export-json-btn"
            onClick={downloadJSONBackup}
            disabled={notes.length === 0}
            className="w-full flex items-center justify-center gap-2 py-2 text-xs font-semibold border rounded-lg transition-all dark:border-zinc-800 dark:text-zinc-400 hover:bg-zinc-200/50 dark:hover:bg-zinc-900 text-zinc-600 hover:text-zinc-900 dark:hover:text-zinc-200 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            <FileJson size={14} />
            <span>Export ALL .JSON</span>
          </button>
        </div>
      </aside>

      {/* Main Workspace Frame */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        
        {/* Workspace Top Header (Search, Filters, New Note Button) */}
        <header className={`h-20 px-8 flex items-center justify-between border-b transition-colors shrink-0 ${theme === "dark" ? "bg-zinc-950 border-zinc-900" : "bg-white border-zinc-200"}`}>
          
          {/* Search Box */}
          <div className="flex-1 max-w-xl relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-400 dark:text-zinc-500" size={17} />
            <input
              id="search-input"
              type="text"
              placeholder="Search note headers, tag words, summaries..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className={`w-full border rounded-full py-2.5 pl-12 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all ${
                theme === "dark" 
                  ? "bg-zinc-900/60 border-zinc-800 text-zinc-200 placeholder-zinc-500 focus:border-zinc-700" 
                  : "bg-zinc-100 border-zinc-200 text-zinc-800 placeholder-zinc-400 focus:border-zinc-300"
              }`}
            />
            {searchQuery && (
              <button 
                onClick={() => setSearchQuery("")} 
                className="absolute right-4 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600"
                title="Clear Search"
              >
                <X size={15} />
              </button>
            )}
          </div>

          {/* Header Action Items (Newest vs Oldest sorts & New Note Trigger button) */}
          <div className="flex items-center gap-4 ml-6 shrink-0">
            <div className={`flex rounded-lg p-1 border ${theme === "dark" ? "bg-zinc-900 border-zinc-800" : "bg-zinc-100 border-zinc-200"}`}>
              <button
                id="sort-newest"
                onClick={() => setSortBy("newest")}
                className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${sortBy === "newest" ? "bg-indigo-600 text-white shadow-sm" : "text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200"}`}
              >
                Newest
              </button>
              <button
                id="sort-oldest"
                onClick={() => setSortBy("oldest")}
                className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${sortBy === "oldest" ? "bg-indigo-600 text-white shadow-sm" : "text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200"}`}
              >
                Oldest
              </button>
            </div>

            {/* Main Creative Trigger CTA */}
            <button
              id="new-note-btn"
              onClick={handleNewNoteClick}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-full text-sm font-semibold transition-all shadow-md hover:shadow-lg shadow-indigo-600/10 cursor-pointer"
            >
              <Plus size={16} strokeWidth={2.5} />
              New Note
            </button>
          </div>
        </header>

        {/* Notes Cards Display Grid */}
        <div id="notes-grid-container" className="flex-1 p-8 overflow-y-auto">
          {filteredNotes.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              
              {filteredNotes.map((note) => (
                <div
                  key={note.id}
                  id={`note-card-${note.id}`}
                  className={`relative p-6 rounded-2xl border flex flex-col justify-between transition-all duration-300 shadow-sm ${
                    note.pinned 
                      ? theme === "dark"
                        ? "bg-indigo-950/20 border-indigo-500/40 hover:border-indigo-500/60 shadow-indigo-950/10"
                        : "bg-indigo-50/50 border-indigo-200 hover:border-indigo-300 shadow-indigo-200/10"
                      : theme === "dark"
                        ? "bg-zinc-900/50 border-zinc-800/80 hover:border-zinc-700/80"
                        : "bg-white border-zinc-200/80 hover:border-indigo-200/80 hover:shadow-md"
                  }`}
                >
                  {/* Card Operations Header */}
                  <div className="flex items-start justify-between mb-3 gap-2">
                    <h3 className="font-bold text-base leading-tight dark:text-white text-zinc-900 break-words flex-1">
                      {renderHighlightedTitle(note.title, searchQuery)}
                    </h3>
                    
                    {/* Action controls */}
                    <div className="flex items-center gap-1.5 shrink-0 opacity-70 hover:opacity-100 transition-opacity">
                      {!note.trashed && (
                        <button
                          onClick={(e) => handleTogglePin(note.id, e)}
                          className={`p-1.5 rounded-md hover:bg-zinc-200 dark:hover:bg-zinc-800 transition-colors ${
                            note.pinned ? "text-indigo-400 dark:text-indigo-400" : "text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300"
                          }`}
                          title={note.pinned ? "Unpin Note" : "Pin Note"}
                        >
                          <Bookmark size={15} fill={note.pinned ? "currentColor" : "none"} />
                        </button>
                      )}

                      {!note.trashed ? (
                        <>
                          <button
                            onClick={() => handleEditNoteClick(note)}
                            className="p-1.5 rounded-md text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-200 dark:hover:bg-zinc-800 transition-colors"
                            title="Edit Note"
                          >
                            <Edit3 size={15} />
                          </button>
                          <button
                            onClick={(e) => handleMoveToTrash(note.id, e)}
                            className="p-1.5 rounded-md text-zinc-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
                            title="Move to Trash"
                          >
                            <Trash2 size={15} />
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            onClick={(e) => handleRestoreFromTrash(note.id, e)}
                            className="p-1.5 rounded-md text-zinc-400 hover:text-indigo-500 dark:hover:text-indigo-400 hover:bg-zinc-200 dark:hover:bg-zinc-800 transition-colors"
                            title="Restore note"
                          >
                            <RotateCcw size={15} />
                          </button>
                          <button
                            onClick={(e) => handlePermanentDelete(note.id, e)}
                            className="p-1.5 rounded-md text-zinc-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
                            title="Delete Permanently"
                          >
                            <X size={15} />
                          </button>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Render Compiled Markdown Content */}
                  <div className="mb-4 flex-1">
                    {renderMarkdown(note.content, searchQuery)}
                  </div>

                  {/* AI smart blocks summary & dynamic indicators */}
                  {(note.isAnalyzing || note.summary || note.tags || note.mood) && (
                    <div className={`mt-4 p-3.5 rounded-xl border ${
                      theme === "dark" 
                        ? "bg-zinc-950/60 border-zinc-800/60" 
                        : "bg-zinc-50 border-zinc-200"
                    }`}>
                      {note.isAnalyzing ? (
                        <div className="flex items-center gap-2.5 py-1 text-xs text-indigo-500 dark:text-indigo-400 font-medium">
                          <Sparkles size={13} className="animate-spin text-indigo-500" />
                          <span className="animate-pulse">AI summarizing and tag indexing...</span>
                        </div>
                      ) : (
                        <div className="space-y-2">
                          <div className="flex justify-between items-center text-[10px] uppercase font-bold tracking-wider">
                            <span className="text-indigo-500 dark:text-indigo-400 flex items-center gap-1">
                              <Sparkles size={10} /> Smart AI Info
                            </span>
                            {note.mood && (
                              <span className="text-zinc-500 dark:text-zinc-400 lowercase first-letter:uppercase">
                                mood: <strong className="text-zinc-700 dark:text-zinc-200">{note.mood}</strong>
                              </span>
                            )}
                          </div>
                          
                          {note.summary && (
                            <p className="text-[11px] font-normal leading-normal italic text-zinc-500 dark:text-zinc-500">
                              "{note.summary}"
                            </p>
                          )}
                          
                          {note.tags && note.tags.length > 0 && (
                            <div className="flex flex-wrap gap-1 pt-0.5">
                              {note.tags.map((t) => (
                                <span
                                  key={t}
                                  className="px-1.5 py-0.5 bg-indigo-500/10 dark:bg-indigo-500/15 text-indigo-600 dark:text-indigo-300 rounded text-[9px] font-semibold tracking-wider uppercase"
                                >
                                  #{t}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Simple timestamp log */}
                  <div className="mt-4 pt-3 border-t border-zinc-200/50 dark:border-zinc-800/30 flex items-center justify-between text-[10px] text-zinc-400">
                    <span className="flex items-center gap-1 select-none">
                      <Calendar size={10} />
                      {new Date(note.createdAt).toLocaleDateString(undefined, {
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit"
                      })}
                    </span>
                    
                    {note.pinned && (
                      <span className="text-indigo-500 dark:text-indigo-400 font-bold uppercase tracking-tight text-[9px]">
                        Pinned
                      </span>
                    )}
                  </div>

                </div>
              ))}

            </div>
          ) : (
            /* Dashboard Empty State Frame */
            <div className="flex flex-col items-center justify-center py-20 text-center max-w-md mx-auto">
              <div className={`p-4 rounded-full mb-4 border ${theme === "dark" ? "bg-zinc-900 border-zinc-800" : "bg-zinc-100 border-zinc-200"}`}>
                <Info size={32} className="text-zinc-400" />
              </div>
              <h3 className="font-bold text-lg mb-1 leading-tight dark:text-white">
                {searchQuery ? "No matching notes found" : currentTab === "trash" ? "Trash is completely empty" : "No notes yet"}
              </h3>
              <p className="text-sm text-zinc-500 leading-normal mb-6">
                {searchQuery 
                  ? "We couldn't match any note title, markdown content, smart summary tags, or mood identifiers with that query."
                  : currentTab === "trash" 
                    ? "Notes you discard are held in Trash temporarily. Permanent deletions are non-reversible." 
                    : "Create elegant notes with Markdown formatting. Our integrated Server AI will automatically summarize them and group topics!"}
              </p>
              {!searchQuery && currentTab !== "trash" && (
                <button
                  onClick={handleNewNoteClick}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-full text-sm font-semibold transition-all shadow-md cursor-pointer"
                >
                  Create Your First Note
                </button>
              )}
            </div>
          )}
        </div>

        {/* Global Floating Utility Stats Footer */}
        <footer className={`h-10 px-8 flex items-center justify-between border-t transition-colors text-[10px] text-zinc-500 uppercase tracking-wider shrink-0 select-none ${theme === "dark" ? "bg-zinc-950 border-zinc-900" : "bg-zinc-100 border-zinc-200"}`}>
          <div className="flex items-center gap-2 font-semibold">
            <span className="w-2 h-2 rounded-full bg-emerald-500 shadow shadow-emerald-500/50 animate-pulse" />
            Storage Authenticated & Saved Locally
          </div>
          <div>
            Notes Count: {notes.length} Active System Threads
          </div>
        </footer>

      </main>

      {/* Elegant sliding Note Editor overlay modal */}
      {isEditorOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-zinc-950/70 backdrop-blur-sm animate-fade-in">
          
          <div 
            id="editor-modal-frame"
            className={`w-full max-w-2xl rounded-2xl border flex flex-col overflow-hidden max-h-[85vh] shadow-2xl transition-all duration-300 ${
              theme === "dark" ? "bg-zinc-900 border-zinc-800" : "bg-white border-zinc-200"
            }`}
          >
            {/* Modal Header bar */}
            <div className={`px-6 py-4 border-b flex items-center justify-between ${theme === "dark" ? "border-zinc-800" : "border-zinc-100"}`}>
              <div className="flex items-center gap-3">
                <Sparkles size={16} className="text-indigo-500 dark:text-indigo-400" />
                <span className="font-bold text-sm tracking-tight">
                  {editingNote ? "✏️ Edit Lumina Note" : "✨ Write Lumina Note"}
                </span>
              </div>
              
              {/* Write vs Preview Toggle badge */}
              <div className="flex bg-zinc-100 dark:bg-zinc-950 rounded-lg p-0.5 border border-zinc-200/50 dark:border-zinc-800">
                <button
                  type="button"
                  onClick={() => setEditorTabs("write")}
                  className={`px-2.5 py-1 text-[11px] font-semibold rounded-md transition-colors ${editorTabs === "write" ? "bg-indigo-600 text-white" : "text-zinc-500"}`}
                >
                  Write Content
                </button>
                <button
                  type="button"
                  onClick={() => setEditorTabs("preview")}
                  className={`px-2.5 py-1 text-[11px] font-semibold rounded-md transition-colors ${editorTabs === "preview" ? "bg-indigo-600 text-white" : "text-zinc-500"}`}
                >
                  Preview MD
                </button>
              </div>
            </div>

            {/* Modal Input Editor fields */}
            <form onSubmit={handleSaveNote} className="flex-1 flex flex-col min-h-0">
              
              <div className="p-6 space-y-4 flex-1 overflow-y-auto">
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-zinc-400 dark:text-zinc-500 mb-1.5">
                    Note Header Title
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="Enter short, elegant title identifier..."
                    value={editorTitle}
                    onChange={(e) => setEditorTitle(e.target.value)}
                    className={`w-full px-4 py-2.5 text-sm font-semibold rounded-xl border focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all ${
                      theme === "dark" 
                        ? "bg-zinc-950 border-zinc-800 text-zinc-100 placeholder-zinc-600" 
                        : "bg-zinc-50 border-zinc-200 text-zinc-800 placeholder-zinc-400"
                    }`}
                  />
                </div>

                {/* Voice Dictation Accessory Bar */}
                <div id="dictation-panel" className={`p-4 rounded-xl border flex flex-col gap-2 transition-all duration-300 ${
                  isListening 
                    ? "border-red-500/40 bg-red-500/5 shadow-md shadow-red-500/10 animate-pulse" 
                    : theme === "dark"
                      ? "border-zinc-800 bg-zinc-950/20"
                      : "border-zinc-200/60 bg-zinc-50/40"
                }`}>
                  <div className="flex items-center justify-between gap-4 flex-wrap">
                    <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-400 dark:text-zinc-500 flex items-center gap-1.5 select-none">
                      <Mic size={12} className={isListening ? "text-red-500 animate-bounce" : "text-zinc-400"} />
                      Voice Transcribing Tools
                    </span>
                    
                    {/* Dictation Destination Selectors & Microphone Action */}
                    <div className="flex items-center gap-2.5 ml-auto">
                      <div className="flex bg-zinc-200/50 dark:bg-zinc-950 rounded-lg p-0.5 border dark:border-zinc-800 border-zinc-200">
                        <button
                          type="button"
                          onClick={() => setDictationTarget("title")}
                          className={`px-2 py-0.5 text-[9px] font-bold rounded transition-colors ${dictationTarget === "title" ? "bg-indigo-600 text-white" : "text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200"}`}
                        >
                          Target Title
                        </button>
                        <button
                          type="button"
                          onClick={() => setDictationTarget("content")}
                          className={`px-2 py-0.5 text-[9px] font-bold rounded transition-colors ${dictationTarget === "content" ? "bg-indigo-600 text-white" : "text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200"}`}
                        >
                          Target Content
                        </button>
                      </div>

                      {isSpeechSupported ? (
                        <button
                          id="dictation-trigger-btn"
                          type="button"
                          onClick={isListening ? stopListening : startListening}
                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[10px] font-bold cursor-pointer transition-all active:scale-95 shadow ${
                            isListening 
                              ? "bg-red-500 hover:bg-red-600 text-white shadow-red-500/25" 
                              : "bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/10"
                          }`}
                        >
                          {isListening ? (
                            <>
                              <MicOff size={11} />
                              <span>Stop Dictating</span>
                            </>
                          ) : (
                            <>
                              <Mic size={11} />
                              <span>Start Dictating</span>
                            </>
                          )}
                        </button>
                      ) : (
                        <span className="text-[10px] text-amber-500 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/25 flex items-center gap-1 select-none">
                          <AlertCircle size={10} /> Speech API Unsupported
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Audio feedback soundwave placeholder when dictating */}
                  {isListening && (
                    <div className="flex items-center gap-3 py-1.5 px-2.5 bg-red-500/10 rounded-lg border border-red-500/20">
                      <div className="flex gap-0.5 shrink-0 items-center justify-center">
                        <span className="w-0.5 h-3 bg-red-500 rounded animate-[bounce_1s_infinite_100ms]" />
                        <span className="w-0.5 h-4.5 bg-red-500 rounded animate-[bounce_1s_infinite_200ms]" />
                        <span className="w-0.5 h-6 bg-red-500 rounded animate-[bounce_1s_infinite_300ms]" />
                        <span className="w-0.5 h-2.5 bg-red-500 rounded animate-[bounce_1s_infinite_400ms]" />
                        <span className="w-0.5 h-4.5 bg-red-500 rounded animate-[bounce_1s_infinite_500ms]" />
                      </div>
                      <span className="text-[10px] text-red-500 dark:text-red-400 font-medium italic animate-pulse">
                        Listening continuously... Dictating directly into your selected text target field!
                      </span>
                    </div>
                  )}

                  {speechError && (
                    <p className="text-[10px] text-red-500 bg-red-500/10 px-2.5 py-1 rounded border border-red-500/25 flex items-center gap-1.5">
                      <AlertCircle size={11} className="shrink-0" /> Error message: {speechError}
                    </p>
                  )}
                </div>

                <div className="flex-1 flex flex-col min-h-[220px]">
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-zinc-400 dark:text-zinc-500 mb-1.5">
                    Notes content (Supports simple markdown like **bold**, *italic*, list bullet loops, blockquotes)
                  </label>
                  
                  {editorTabs === "write" ? (
                    <textarea
                      placeholder="Write layout details, schedules, code bits or instructions..."
                      value={editorContent}
                      onChange={(e) => setEditorContent(e.target.value)}
                      className={`w-full flex-1 min-h-[220px] px-4 py-3 text-sm rounded-xl border focus:outline-none focus:ring-2 focus:ring-indigo-500/50 font-sans leading-relaxed resize-none transition-all ${
                        theme === "dark" 
                          ? "bg-zinc-950 border-zinc-800 text-zinc-200 placeholder-zinc-600" 
                          : "bg-zinc-50 border-zinc-200 text-zinc-700 placeholder-zinc-400"
                      }`}
                    />
                  ) : (
                    <div className={`w-full flex-1 min-h-[220px] px-4 py-3 rounded-xl border overflow-y-auto ${
                      theme === "dark" 
                        ? "bg-zinc-950 border-zinc-800" 
                        : "bg-zinc-50 border-zinc-200"
                    }`}>
                      {renderMarkdown(editorContent)}
                    </div>
                  )}
                </div>

                <div className="flex items-start gap-2 text-[11px] text-zinc-500">
                  <Info size={11} className="mt-0.5 text-indigo-500 dark:text-indigo-400 shrink-0" />
                  <span>
                    When you save, our smart servers analyze your notes context locally or via Gemini, generating a Smart 1-sentence summary, tags list, and mood indicators automatically.
                  </span>
                </div>
              </div>

              {/* Modal controls and handlers */}
              <div className={`px-6 py-4 border-t flex items-center justify-end gap-3 shrink-0 ${theme === "dark" ? "border-zinc-800" : "border-zinc-100"}`}>
                <button
                  type="button"
                  onClick={() => setIsEditorOpen(false)}
                  className="px-4 py-2 text-xs font-semibold rounded-lg text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 transition-colors cursor-pointer"
                >
                  Discard
                </button>
                <button
                  type="submit"
                  className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2 rounded-lg text-xs font-semibold transition-all shadow-md cursor-pointer"
                >
                  <Check size={13} />
                  Save Note
                </button>
              </div>

            </form>

          </div>

        </div>
      )}

    </div>
  );
}
