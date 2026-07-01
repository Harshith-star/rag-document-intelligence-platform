import { useState, useEffect, useRef, useCallback } from "react";
import {
  uploadDocument, listDocuments, askQuestion,
  deleteDocument, renameDocument, getDashboardStats,
} from "../api";
import { useAuth } from "../AuthContext";
import {
  BookOpen, LogOut, Upload, Search, Trash2, Edit3,
  Send, Zap, FileText, HardDrive, MessageSquare, Clock,
  ChevronLeft, ChevronRight, Loader2, AlertCircle,
  CheckCircle2, XCircle, Bot, User as UserIcon, BarChart3,
  Files, Plus, X,
} from "lucide-react";

// ── Stat card ──────────────────────────────────────────────────────────────
function StatCard({ icon: Icon, label, value, color = "brand" }) {
  const colors = {
    brand:   "bg-brand-50  text-brand-600  border-brand-100",
    emerald: "bg-emerald-50 text-emerald-600 border-emerald-100",
    amber:   "bg-amber-50  text-amber-600  border-amber-100",
    violet:  "bg-violet-50 text-violet-600 border-violet-100",
  };
  return (
    <div className="card p-5 flex items-center gap-4">
      <div className={`w-11 h-11 rounded-xl flex items-center justify-center border ${colors[color]}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <p className="text-2xl font-bold text-slate-800 leading-none">{value}</p>
        <p className="text-xs text-slate-500 mt-1">{label}</p>
      </div>
    </div>
  );
}

// ── Upload zone ────────────────────────────────────────────────────────────
function UploadZone({ onUpload }) {
  const [dragging, setDragging] = useState(false);
  const [progress, setProgress] = useState(null);
  const [status, setStatus]     = useState(null); // "ok" | "error" | null
  const [message, setMessage]   = useState("");
  const inputRef = useRef();

  const doUpload = async (file) => {
    if (!file) return;
    setProgress(0);
    setStatus(null);
    setMessage("");
    try {
      await uploadDocument(file, setProgress);
      setStatus("ok");
      setMessage(`"${file.name}" processed successfully.`);
      onUpload();
    } catch (err) {
      setStatus("error");
      setMessage(err.response?.data?.detail || "Upload failed.");
    } finally {
      setProgress(null);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => { e.preventDefault(); setDragging(false); doUpload(e.dataTransfer.files[0]); }}
      onClick={() => inputRef.current?.click()}
      className={`relative flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed
        p-8 cursor-pointer transition-all duration-200 select-none
        ${dragging ? "border-brand-500 bg-brand-50" : "border-slate-200 bg-slate-50 hover:border-brand-400 hover:bg-brand-50/50"}`}
    >
      <input ref={inputRef} type="file" accept=".pdf,.txt,.md" className="hidden"
        onChange={(e) => doUpload(e.target.files[0])} />

      {progress !== null ? (
        <>
          <Loader2 className="w-8 h-8 text-brand-500 animate-spin" />
          <p className="text-sm text-slate-600 font-medium">Uploading… {progress}%</p>
          <div className="w-48 h-1.5 rounded-full bg-slate-200">
            <div className="h-1.5 rounded-full bg-brand-500 transition-all" style={{ width: `${progress}%` }} />
          </div>
        </>
      ) : (
        <>
          <div className="w-12 h-12 rounded-xl bg-brand-100 flex items-center justify-center">
            <Upload className="w-6 h-6 text-brand-600" />
          </div>
          <div className="text-center">
            <p className="text-sm font-semibold text-slate-700">Drop a file or click to browse</p>
            <p className="text-xs text-slate-400 mt-1">PDF · TXT · Markdown · max 20 MB</p>
          </div>
        </>
      )}

      {status === "ok" && (
        <div className="absolute inset-x-4 bottom-3 flex items-center gap-2 text-emerald-700 text-xs bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-1.5">
          <CheckCircle2 className="w-3.5 h-3.5 shrink-0" /> {message}
        </div>
      )}
      {status === "error" && (
        <div className="absolute inset-x-4 bottom-3 flex items-center gap-2 text-red-600 text-xs bg-red-50 border border-red-200 rounded-lg px-3 py-1.5">
          <XCircle className="w-3.5 h-3.5 shrink-0" /> {message}
        </div>
      )}
    </div>
  );
}

// ── Document row ───────────────────────────────────────────────────────────
function DocRow({ doc, onRename, onDelete }) {
  const statusColor = {
    completed:  "bg-emerald-100 text-emerald-700",
    processing: "bg-amber-100  text-amber-700",
    failed:     "bg-red-100    text-red-700",
    pending:    "bg-slate-100  text-slate-600",
  }[doc.processing_status] ?? "bg-slate-100 text-slate-600";

  return (
    <div className="flex items-center gap-3 px-4 py-3 hover:bg-slate-50 rounded-xl group transition-colors">
      <div className="w-9 h-9 rounded-lg bg-brand-50 border border-brand-100 flex items-center justify-center shrink-0">
        <FileText className="w-4 h-4 text-brand-600" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-800 truncate">{doc.filename}</p>
        <p className="text-xs text-slate-400 mt-0.5">
          {(doc.file_size / 1024).toFixed(1)} KB · {doc.num_chunks} chunks
          {doc.processing_time ? ` · ${doc.processing_time.toFixed(2)}s` : ""}
        </p>
      </div>
      <span className={`badge ${statusColor} shrink-0`}>{doc.processing_status}</span>
      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button className="btn-ghost py-1 px-2" onClick={() => onRename(doc.id, doc.filename)}
          title="Rename"><Edit3 className="w-3.5 h-3.5" /></button>
        <button className="btn-danger py-1 px-2" onClick={() => onDelete(doc.id)}
          title="Delete"><Trash2 className="w-3.5 h-3.5" /></button>
      </div>
    </div>
  );
}

// ── Chat bubble ────────────────────────────────────────────────────────────
function ChatBubble({ msg }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-white
        ${isUser ? "bg-brand-500" : "bg-slate-700"}`}>
        {isUser ? <UserIcon className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>
      <div className={`max-w-[78%] rounded-2xl px-4 py-3 text-sm leading-relaxed
        ${isUser
          ? "bg-brand-600 text-white rounded-tr-sm"
          : msg.error
            ? "bg-red-50 border border-red-200 text-red-800 rounded-tl-sm"
            : "bg-white border border-slate-200 text-slate-800 rounded-tl-sm shadow-sm"}`}>
        <p className="whitespace-pre-wrap">{msg.text}</p>
        {msg.cached && (
          <span className="inline-flex items-center gap-1 mt-2 text-xs font-medium text-amber-600 bg-amber-50 border border-amber-200 rounded-full px-2 py-0.5">
            <Zap className="w-3 h-3" /> Cached
          </span>
        )}
        {msg.sources?.length > 0 && (
          <div className="mt-2 pt-2 border-t border-slate-100">
            <p className="text-xs text-slate-400 font-medium mb-1">Sources</p>
            <div className="flex flex-wrap gap-1">
              {msg.sources.map((s, i) => (
                <span key={i} className="badge bg-slate-100 text-slate-600">{s}</span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Typing indicator ───────────────────────────────────────────────────────
function TypingIndicator() {
  return (
    <div className="flex gap-3">
      <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center shrink-0">
        <Bot className="w-4 h-4 text-white" />
      </div>
      <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm shadow-sm px-4 py-3">
        <div className="flex gap-1 items-center h-4">
          <div className="typing-dot" />
          <div className="typing-dot" />
          <div className="typing-dot" />
        </div>
      </div>
    </div>
  );
}

// ── Main Dashboard ─────────────────────────────────────────────────────────
export default function Dashboard() {
  const { user, logout } = useAuth();
  const [tab, setTab]           = useState("chat");  // "chat" | "docs" | "analytics"
  const [docs, setDocs]         = useState([]);
  const [total, setTotal]       = useState(0);
  const [page, setPage]         = useState(1);
  const [search, setSearch]     = useState("");
  const [stats, setStats]       = useState(null);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [asking, setAsking]     = useState(false);
  const chatEndRef              = useRef();
  const limit = 8;

  const refreshDocs = useCallback(() => {
    listDocuments(page, limit, search)
      .then((r) => { setDocs(r.data.items); setTotal(r.data.total); })
      .catch(() => {});
  }, [page, search]);

  const refreshStats = useCallback(() => {
    getDashboardStats().then((r) => setStats(r.data)).catch(() => {});
  }, []);

  useEffect(() => { refreshDocs(); }, [refreshDocs]);
  useEffect(() => { refreshStats(); }, [refreshStats]);
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, asking]);

  const handleDelete = async (id) => {
    await deleteDocument(id);
    refreshDocs(); refreshStats();
  };

  const handleRename = async (id, current) => {
    const next = window.prompt("New filename:", current);
    if (!next || next === current) return;
    await renameDocument(id, next);
    refreshDocs();
  };

  const handleAsk = async (e) => {
    e.preventDefault();
    if (!question.trim() || asking) return;
    const q = question.trim();
    setMessages((m) => [...m, { role: "user", text: q }]);
    setQuestion("");
    setAsking(true);
    try {
      const res = await askQuestion(q);
      setMessages((m) => [...m, {
        role: "assistant",
        text: res.data.answer,
        sources: res.data.sources,
        cached: res.data.cached,
      }]);
      refreshStats();
    } catch (err) {
      setMessages((m) => [...m, {
        role: "assistant",
        text: err.response?.data?.detail || "Something went wrong.",
        error: true,
      }]);
    } finally {
      setAsking(false);
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / limit));
  const fmtBytes = (b) => b < 1024 * 1024 ? `${(b / 1024).toFixed(1)} KB` : `${(b / 1024 / 1024).toFixed(2)} MB`;

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Top nav */}
      <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between sticky top-0 z-20 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center">
            <BookOpen className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-slate-800 text-lg">DocuMind</span>
        </div>

        {/* Tab bar */}
        <nav className="flex gap-1 bg-slate-100 rounded-xl p-1">
          {[
            { id: "chat",      label: "Chat",      Icon: MessageSquare },
            { id: "docs",      label: "Documents", Icon: Files         },
            { id: "analytics", label: "Analytics", Icon: BarChart3     },
          ].map(({ id, label, Icon }) => (
            <button key={id} onClick={() => setTab(id)}
              className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-medium transition-all duration-150
                ${tab === id ? "bg-white text-brand-700 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}>
              <Icon className="w-4 h-4" /> {label}
            </button>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <span className="text-sm text-slate-500 hidden md:block">{user?.email}</span>
          <button onClick={logout} className="btn-ghost text-slate-500">
            <LogOut className="w-4 h-4" /> Sign out
          </button>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-4 py-6">

        {/* ── CHAT TAB ── */}
        {tab === "chat" && (
          <div className="flex flex-col h-[calc(100vh-140px)]">
            <div className="flex-1 overflow-y-auto space-y-4 pb-4 pr-1">
              {messages.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-center gap-4 py-16">
                  <div className="w-16 h-16 rounded-2xl bg-brand-100 flex items-center justify-center">
                    <Bot className="w-8 h-8 text-brand-600" />
                  </div>
                  <div>
                    <p className="text-lg font-semibold text-slate-700">Ask anything about your documents</p>
                    <p className="text-sm text-slate-400 mt-1">Upload documents in the Documents tab, then come back here to chat.</p>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2 w-full max-w-md">
                    {["Summarize the main points", "What are the key findings?",
                      "Compare the documents", "List all action items"].map((hint) => (
                      <button key={hint} onClick={() => setQuestion(hint)}
                        className="text-left text-sm text-slate-600 bg-white border border-slate-200 rounded-xl px-4 py-3 hover:border-brand-400 hover:bg-brand-50 transition-all">
                        {hint}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {messages.map((m, i) => <ChatBubble key={i} msg={m} />)}
              {asking && <TypingIndicator />}
              <div ref={chatEndRef} />
            </div>

            <form onSubmit={handleAsk}
              className="flex gap-3 mt-3 bg-white border border-slate-200 rounded-2xl p-2 shadow-sm">
              <input
                className="flex-1 px-3 py-2 text-sm bg-transparent outline-none placeholder-slate-400"
                placeholder="Ask a question about your documents…"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                disabled={asking}
              />
              <button type="submit" className="btn-primary rounded-xl px-4" disabled={asking || !question.trim()}>
                {asking ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              </button>
            </form>
          </div>
        )}

        {/* ── DOCUMENTS TAB ── */}
        {tab === "docs" && (
          <div className="space-y-4">
            <UploadZone onUpload={() => { refreshDocs(); refreshStats(); }} />

            <div className="card">
              {/* Header */}
              <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-3">
                <div className="relative flex-1">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    className="input pl-9 py-1.5 text-sm"
                    placeholder="Search by filename…"
                    value={search}
                    onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                  />
                </div>
                <span className="text-xs text-slate-400 shrink-0">{total} document{total !== 1 ? "s" : ""}</span>
              </div>

              {/* List */}
              <div className="divide-y divide-slate-50 px-2 py-1">
                {docs.length === 0 ? (
                  <div className="text-center py-12 text-slate-400">
                    <Files className="w-10 h-10 mx-auto mb-3 opacity-30" />
                    <p className="text-sm">No documents yet. Upload one above.</p>
                  </div>
                ) : (
                  docs.map((d) => (
                    <DocRow key={d.id} doc={d} onRename={handleRename} onDelete={handleDelete} />
                  ))
                )}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="px-5 py-3 border-t border-slate-100 flex items-center justify-between">
                  <button className="btn-ghost" disabled={page <= 1}
                    onClick={() => setPage((p) => p - 1)}>
                    <ChevronLeft className="w-4 h-4" /> Prev
                  </button>
                  <span className="text-xs text-slate-400">Page {page} of {totalPages}</span>
                  <button className="btn-ghost" disabled={page >= totalPages}
                    onClick={() => setPage((p) => p + 1)}>
                    Next <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── ANALYTICS TAB ── */}
        {tab === "analytics" && (
          <div className="space-y-4">
            {stats ? (
              <>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <StatCard icon={Files}         label="Documents"          value={stats.total_documents}        color="brand"   />
                  <StatCard icon={HardDrive}      label="Storage used"       value={fmtBytes(stats.storage_used_bytes)} color="emerald" />
                  <StatCard icon={MessageSquare}  label="Questions asked"    value={stats.questions_asked}        color="violet"  />
                  <StatCard icon={Clock}          label="Avg response"       value={`${stats.avg_response_time_seconds}s`} color="amber"   />
                </div>

                {/* Cache performance */}
                {stats.questions_asked > 0 && (
                  <div className="card p-5">
                    <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
                      <Zap className="w-4 h-4 text-amber-500" /> Cache performance
                    </h3>
                    <div className="flex items-center gap-4">
                      <div className="flex-1">
                        <div className="flex justify-between text-xs text-slate-500 mb-1.5">
                          <span>Cache hit rate</span>
                          <span className="font-semibold text-amber-600">
                            {Math.round((stats.cache_hits / stats.questions_asked) * 100)}%
                          </span>
                        </div>
                        <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden">
                          <div
                            className="h-2.5 rounded-full bg-gradient-to-r from-amber-400 to-amber-500 transition-all duration-500"
                            style={{ width: `${Math.round((stats.cache_hits / stats.questions_asked) * 100)}%` }}
                          />
                        </div>
                      </div>
                      <div className="text-right shrink-0">
                        <p className="text-xl font-bold text-slate-800">{stats.cache_hits}</p>
                        <p className="text-xs text-slate-400">cache hits</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Recent questions */}
                {stats.recent_questions?.length > 0 && (
                  <div className="card p-5">
                    <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
                      <MessageSquare className="w-4 h-4 text-brand-500" /> Recent questions
                    </h3>
                    <div className="space-y-2">
                      {stats.recent_questions.map((q, i) => (
                        <div key={i} className="flex items-start gap-3 p-3 bg-slate-50 rounded-xl">
                          <MessageSquare className="w-3.5 h-3.5 text-slate-400 mt-0.5 shrink-0" />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-slate-700 truncate">{q.question}</p>
                            <p className="text-xs text-slate-400 mt-0.5">
                              {new Date(q.created_at).toLocaleString()}
                              {q.was_cached && (
                                <span className="ml-2 text-amber-600">⚡ cached</span>
                              )}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="flex items-center justify-center h-40">
                <Loader2 className="w-6 h-6 animate-spin text-slate-300" />
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
