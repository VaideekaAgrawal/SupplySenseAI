"use client";
import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, ChatResponse } from "@/lib/api";

interface Message {
  role: "user" | "ai";
  text: string;
  suggestions?: string[];
  functionCalled?: string;
}

const SCENARIO_CHIPS = [
  "What if Mumbai Port closes for 2 days?",
  "Show alternative routes for SH001",
  "How resilient is our network?",
  "Which shipments will be delayed?",
  "Analyze NH-48 weather disruption",
];

export default function ChatPage() {
  return (
    <Suspense>
      <ChatPageInner />
    </Suspense>
  );
}

function ChatPageInner() {
  const searchParams = useSearchParams();
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "ai",
      text: "Hello! I'm SupplySense AI — your supply chain resilience assistant.\n\nI have real-time access to all 50 active shipments, 2 disruptions, and 8 carriers.\n\nTry asking me about disruptions, alternative routes, or network resilience.",
      suggestions: SCENARIO_CHIPS.slice(0, 3),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(`session-${Date.now()}`);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Pre-fill from URL ?q= param
  useEffect(() => {
    const q = searchParams.get("q");
    if (q) setInput(decodeURIComponent(q));
  }, [searchParams]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (text: string) => {
    if (!text.trim() || loading) return;
    const userMsg = text.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: userMsg }]);
    setLoading(true);

    try {
      const res: ChatResponse = await api.chat(userMsg, sessionId);
      setMessages((prev) => [
        ...prev,
        {
          role: "ai",
          text: res.message,
          suggestions: res.suggestions,
          functionCalled: res.function_called || undefined,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "ai", text: "Sorry, I couldn't reach the AI backend. Make sure it's running on port 8000." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-6 flex flex-col h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="mb-4">
        <h1 className="text-xl font-bold text-white">SupplySense AI Chat</h1>
        <p className="text-slate-400 text-sm">Gemini 2.0 Flash · Supply chain expert mode</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[85%] rounded-2xl px-4 py-3 ${
              msg.role === "user"
                ? "bg-blue-600 text-white rounded-br-sm"
                : "bg-navy-800 border border-slate-700 text-slate-100 rounded-bl-sm"
            }`}>
              {msg.functionCalled && (
                <div className="text-xs text-blue-400 mb-1 font-mono">
                  🔧 {msg.functionCalled}
                </div>
              )}
              <div className="whitespace-pre-wrap text-sm leading-relaxed">{msg.text}</div>
              {msg.suggestions && msg.suggestions.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {msg.suggestions.map((s) => (
                    <button
                      key={s}
                      onClick={() => send(s)}
                      className="text-xs bg-slate-700 hover:bg-slate-600 text-slate-300 px-2.5 py-1 rounded-full transition-colors"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-navy-800 border border-slate-700 rounded-2xl rounded-bl-sm px-4 py-3">
              <div className="flex gap-1 items-center">
                <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Scenario chips */}
      <div className="flex flex-wrap gap-2 mb-3">
        {SCENARIO_CHIPS.map((chip) => (
          <button
            key={chip}
            onClick={() => send(chip)}
            className="text-xs bg-slate-800 hover:bg-slate-700 border border-slate-600 text-slate-300 px-3 py-1.5 rounded-full transition-colors"
          >
            {chip}
          </button>
        ))}
      </div>

      {/* Input */}
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send(input)}
          placeholder="Ask about disruptions, routes, or resilience…"
          className="flex-1 bg-navy-800 border border-slate-700 text-white placeholder-slate-500 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500"
          disabled={loading}
        />
        <button
          onClick={() => send(input)}
          disabled={!input.trim() || loading}
          className="px-4 py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white rounded-xl text-sm font-medium transition-colors"
        >
          Send
        </button>
      </div>
    </div>
  );
}
