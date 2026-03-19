"use client";
import React, { useState, useEffect, useRef, useCallback } from 'react';
import "@/app/globals.css";

// Backend API base URL
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

interface BackendMessage {
    id: string;
    sender: string;
    text: string;
    time: string;
    is_ai: boolean;
}

// format a timestamp (ms) relative to now, similar to Zalo conversation list
function formatRelativeTime(ts: number): string {
    const diff = Date.now() - ts;
    const sec = Math.floor(diff / 1000);
    if (sec < 60) return `Few sec`;
    const min = Math.floor(diff / 60000);
    if (min < 60) return `${min}m`;
    const hour = Math.floor(diff / 3600000);
    if (hour < 24) return `${hour}h`;
    const d = new Date(ts);
    return d.toLocaleDateString();
}

interface Message {
    id: number | string;
    sender: string;
    content: React.ReactNode;
    text: string;            // raw text for previews
    time: string;            // formatted hour:minute
    ts: number;              // concrete timestamp for relative calculations
    isAI: boolean;
}

/** Convert a backend plain-text message into a styled React chat bubble */
function renderBackendMessage(msg: BackendMessage): React.ReactNode {
    // Split the text by newlines and render each line, preserving blank lines as spacing
    const lines = msg.text.split('\n');

    return (
        <div className="space-y-1">
            {lines.map((line, i) => {
                if (line.trim() === '') {
                    return <div key={i} className="h-2" />;
                }
                return (
                    <p key={i} className="text-[14px] text-gray-700 leading-relaxed whitespace-pre-wrap">
                        {line}
                    </p>
                );
            })}
        </div>
    );
}

export const ZaloDesktopChat: React.FC = () => {
    const [inputText, setInputText] = useState("");
    const scrollRef = useRef<HTMLDivElement>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const [loading, setLoading] = useState(true);
    const [showList, setShowList] = useState(false); // mobile: whether conversation list is visible
    const [activeChatId, setActiveChatId] = useState<string>('parent'); // which conversation is open (default selected)

    const chatTitle = "Nhóm Zalo của phụ huynh"; // hardcoded for now; replace with real data later
    // fetchedIds tracks ALL IDs we have locally (backend + local-only user messages).
    const fetchedIds = useRef<Set<string>>(new Set());
    // backendFetchedIds tracks only IDs that actually came from the backend.
    // Used for the reset-on-DELETE check so local user messages don't trigger a false reset.
    const backendFetchedIds = useRef<Set<string>>(new Set());

    /** Fetch messages from backend and sync (add new + remove deleted) */
    const fetchMessages = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/api/zalo/messages`);
            if (!res.ok) return;
            const data = await res.json();
            const backendMessages = data.messages as BackendMessage[];
            const backendIds = new Set(backendMessages.map(m => m.id));

            // If the backend has fewer messages than we know about from the backend
            // (e.g. after a DELETE /messages call), reset state entirely.
            // We intentionally compare against backendFetchedIds (not fetchedIds) so
            // that locally-added user messages don't falsely trigger this branch.
            if (backendMessages.length < backendFetchedIds.current.size) {
                fetchedIds.current = new Set(backendIds);
                backendFetchedIds.current = new Set(backendIds);
                setMessages(
                    backendMessages.map(msg => ({
                        id: msg.id,
                        sender: msg.sender,
                        content: renderBackendMessage(msg),
                        text: msg.text,
                        time: msg.time,
                        ts: Date.now(),
                        isAI: msg.is_ai,
                    }))
                );
                return;
            }

            // Otherwise, append only new messages
            const newMessages: Message[] = [];
            for (const msg of backendMessages) {
                backendFetchedIds.current.add(msg.id);
                if (!fetchedIds.current.has(msg.id)) {
                    fetchedIds.current.add(msg.id);
                    newMessages.push({
                        id: msg.id,
                        sender: msg.sender,
                        content: renderBackendMessage(msg),
                        text: msg.text,
                        time: msg.time,
                        ts: Date.now(),
                        isAI: msg.is_ai,
                    });
                }
            }

            if (newMessages.length > 0) {
                setMessages(prev => [...prev, ...newMessages]);
            }
        } catch {
            // Backend not available — silent fail for demo
        } finally {
            setLoading(false);
        }
    }, []);

    // Initial fetch + poll every 3 seconds
    useEffect(() => {
        fetchMessages();
        const interval = setInterval(fetchMessages, 3000);
        return () => clearInterval(interval);
    }, [fetchMessages]);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    // const [isTyping, setIsTyping] = useState(false); // unused, kept for future typing indicator

    const handleSendMessage = async () => {
        if (!inputText.trim()) return;

        const text = inputText.trim();

        // If message starts with /, it's a command — send to backend
        if (text.startsWith("/")) {
            setInputText("");

            // Show the user's message immediately — don't wait for the round-trip
            const tempId = `user-temp-${Date.now()}`;
            const userMsg: Message = {
                id: tempId,
                sender: "Phụ huynh Alex",
                content: <p className="text-[14px] text-gray-800">{text}</p>,
                text,
                time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }),
                ts: Date.now(),
                isAI: false
            };
            setMessages(prev => [...prev, userMsg]);
            fetchedIds.current.add(tempId);

            try {
                const res = await fetch(`${API_BASE}/api/zalo/chat`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ sender: "Phụ huynh Alex", text }),
                });
                if (res.ok) {
                    const data = await res.json();

                    // Add AI reply using a local ID — the backend no longer writes
                    // chat replies to the store, so the poller will never see this
                    // message and there is no risk of duplication.
                    if (data.reply) {
                        const aiReply: Message = {
                            id: `ai-local-${Date.now()}`,
                            sender: "Cô Hana (AI)",
                            content: (
                                <div className="space-y-1">
                                    {data.reply.split('\n').map((line: string, i: number) =>
                                        line.trim() === '' ? <div key={i} className="h-2" /> :
                                        <p key={i} className="text-[14px] text-gray-700 leading-relaxed whitespace-pre-wrap">{line}</p>
                                    )}
                                </div>
                            ),
                            text: data.reply,
                            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }),
                            ts: Date.now(),
                            isAI: true
                        };
                        setMessages(prev => [...prev, aiReply]);
                    }
                }
            } catch {
                const errorReply: Message = {
                    id: Date.now() + 1,
                    sender: "Cô Hana (AI)",
                    content: <p className="text-[14px] text-red-600 italic">Không thể kết nối đến hệ thống AI. Vui lòng thử lại sau ạ.</p>,
                    text: "Không thể kết nối đến hệ thống AI. Vui lòng thử lại sau ạ.",
                    time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }),
                    ts: Date.now(),
                    isAI: true
                };
                setMessages(prev => [...prev, errorReply]);
            } finally {
            }
            return;
        }

        // Regular message (not /ask) - add immediately
        const userMsg: Message = {
            id: Date.now(),
            sender: "Phụ huynh Alex",
            content: <p className="text-[14px] text-gray-800">{text}</p>,
            text,
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }),
            ts: Date.now(),
            isAI: false
        };

        setMessages(prev => [...prev, userMsg]);
        setInputText("");
    };

    return (
        <div className="flex w-full h-full bg-white font-sans text-[#081c36]" style={{ fontFamily: "'Segoe UI', Tahoma, sans-serif" }}>
            {/* 1. Sidebar trái */}
            {/* always show a thin icon column; keep fixed width */}
            <div className="w-16 bg-[#0052cc] flex flex-col items-center py-6 gap-8 text-white shadow-inner shrink-0">
                <div className="w-10 h-10 bg-[#00a1ff] rounded-full flex items-center justify-center font-bold text-sm border-2 border-white/20">HT</div>
                <div className="text-2xl cursor-pointer hover:opacity-80 transition-opacity">💬</div>
                <div className="text-xl cursor-pointer opacity-60 hover:opacity-100">👤</div>
                <div className="mt-auto mb-4 text-xl cursor-pointer opacity-60 hover:opacity-100">⚙️</div>
            </div>

            {/* 2. Danh sách hội thoại */}
            {/* slide-in list on mobile, static on md+ */}
            {/* backdrop layered below this when open */}
            {showList && (
                <div
                    className="fixed inset-0 bg-black/30 z-10 md:hidden"
                    onClick={() => setShowList(false)}
                />
            )}
            <div
                className={
                    `fixed inset-y-0 left-0 z-20 w-[320px] bg-white border-r border-[#dbdee1] flex flex-col shrink-0 h-full overflow-y-auto no-scrollbar transform transition-transform duration-200 ease-in-out ` +
                    `${showList ? 'translate-x-0' : '-translate-x-full'} md:relative md:translate-x-0 md:flex`
                }
            >
                <div className="p-4 border-b border-[#dbdee1] font-bold text-[16px]">Tin nhắn</div>
                <div
                    className={
                        `p-3 flex items-center gap-3 cursor-pointer transition-colors ` +
                        (activeChatId === 'parent'
                            ? 'bg-[#e5efff] border-[#0068ff]'
                            : 'hover:bg-[#e5efff] border-l-4 border-transparent hover:border-[#0068ff]')
                    }
                    onClick={() => {
                        setActiveChatId('parent');
                        setShowList(false);
                    }}
                >
                    <div className="w-12 h-12 bg-[#0068ff] rounded-full shrink-0 flex items-center justify-center text-white text-[14px] font-bold shadow-sm">AI</div>
                    <div className="flex flex-col overflow-hidden flex-1">
                        <div className="flex justify-between items-center">
                            <span className="font-medium text-[16px] truncate">{chatTitle}</span>
                            <span className="text-[12px] text-gray-500 shrink-0 ml-2">
                                {messages.length > 0 ? formatRelativeTime(messages[messages.length-1].ts) : ''}
                            </span>
                        </div>
                        <span className="text-[15px] text-[#9d9d9d] overflow-hidden whitespace-nowrap truncate">
                            {(() => {
                                if (messages.length === 0) return '';
                                const last = messages[messages.length - 1];
                                let prefix = '';
                                if (last.isAI) {
                                    prefix = last.sender ? `${last.sender}: ` : '';
                                } else {
                                    prefix = 'Bạn: ';
                                }
                                return prefix + last.text;
                            })()}
                        </span>
                    </div>
                </div>
            </div>

            {/* 3. Vùng nội dung chat chính */}
            <div className="flex-1 flex flex-col bg-[#f4f7f9] overflow-hidden">
                {/* Header */}
                <div className="p-3 bg-white border-b border-[#dbdee1] flex justify-between items-center px-5 shrink-0">
                    <div className="flex items-center gap-2">
                        {/* show back/hamburger on small screens */}
                        <button
                            className="md:hidden text-xl mr-2"
                            onClick={() => setShowList(prev => !prev)}
                        >
                            {showList ? '←' : '☰'}
                        </button>
                        <div className="w-12 h-12 bg-[#0068ff] rounded-full shrink-0 flex items-center justify-center text-white text-[14px] font-bold shadow-sm">AI</div>
                        <div className="flex flex-col">
                            <span className="font-medium text-[18px]">Nhóm Zalo của phụ huynh</span>
                            <span className="text-[14px] text-gray-500">15 thành viên</span>
                        </div>
                    </div>
                </div>

                {/* Vùng tin nhắn cuộn */}
                <div ref={scrollRef} className="flex-1 min-h-0 p-8 overflow-y-auto flex flex-col gap-6 no-scrollbar bg-[#f4f7f9]">
                    <div className="text-center my-2"><span className="text-[10px] bg-gray-400/60 px-7 py-1 rounded-xl text-white uppercase">Hôm nay</span></div>

                    {loading && messages.length === 0 && (
                        <div className="text-center text-gray-400 text-sm mt-8">Đang tải tin nhắn...</div>
                    )}

                    {!loading && messages.length === 0 && (
                        <div className="text-center text-gray-400 text-sm mt-8">
                            Chưa có tin nhắn. Gửi thông báo từ backend bằng POST /api/zalo/send-demo
                        </div>
                    )}

                    {messages.map((msg) => (
                        <div key={msg.id} className={`flex gap-3 ${msg.isAI ? 'self-start' : 'self-end flex-row-reverse'} max-w-[85%] md:max-w-[60%]`}>
                            <div className={`w-8 h-8 rounded-full shrink-0 flex items-center justify-center text-white text-[10px] font-bold mt-1 ${msg.isAI ? 'bg-[#0068ff]' : 'bg-green-600'}`}>
                                {msg.isAI ? 'AI' : 'PH'}
                            </div>
                            <div className={`p-4 rounded-xl shadow-[0_1px_2px_rgba(0,0,0,0.1)] border ${msg.isAI ? 'bg-white border-[#dbdee1]' : 'bg-[#e2f2ff] border-[#0068ff]/20'}`}>
                                <p className={`text-[11px] font-bold mb-1 ${msg.isAI ? 'text-blue-700' : 'text-green-700'}`}>{msg.sender}</p>
                                <div className="leading-relaxed">
                                    {msg.content}
                                </div>
                                <div className="text-[10px] text-gray-400 text-left mt-2 font-bold opacity-70">{msg.time}</div>
                            </div>
                        </div>
                    ))}


                </div>

                {/* Footer */}
                <div className="h-auto md:h-35 bg-white border-t border-[#dbdee1] flex flex-col p-3 shrink-0">
                    <div className="flex gap-4 mb-2 text-gray-500 text-lg px-2">
                        <span className="cursor-pointer hover:text-blue-600">☺</span>
                        <span className="cursor-pointer hover:text-blue-600">🖼️</span>
                        <span className="cursor-pointer hover:text-blue-600">📎</span>
                        <span className="cursor-pointer hover:text-blue-600">📷</span>
                    </div>
                    <textarea
                        className="w-full h-full bg-transparent border-none focus:outline-none text-[14px] resize-none px-2 text-gray-600 font-medium placeholder:text-gray-300"
                        placeholder="/dailysum"
                        value={inputText}
                        onChange={(e) => setInputText(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSendMessage())}
                    />
                    <div className="flex justify-end pr-2 pb-1">
                        <button
                            onClick={handleSendMessage}
                            className="bg-[#0068ff] text-white px-5 py-1.5 rounded text-xs font-bold hover:bg-blue-700 shadow-sm transition-all"
                        >
                            GỬI
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};
