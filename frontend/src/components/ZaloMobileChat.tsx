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

// Định nghĩa cấu trúc tin nhắn
interface Message {
    id: number | string;
    sender: string;
    content: React.ReactNode;
    text?: string;          // raw text for preview or other purposes
    time: string;
    isAI: boolean;
}

/** Convert a backend plain-text message into a styled mobile chat bubble */
function renderBackendMessage(msg: BackendMessage): React.ReactNode {
    const lines = msg.text.split('\n');

    return (
        <div className="space-y-1 text-[14px] leading-[1.6]">
            {lines.map((line, i) => {
                if (line.trim() === '') {
                    return <div key={i} className="h-2" />;
                }
                return (
                    <p key={i} className="whitespace-pre-wrap">
                        {line}
                    </p>
                );
            })}
        </div>
    );
}

export const ZaloMobileChat: React.FC = () => {
    const [inputText, setInputText] = useState("");
    const scrollRef = useRef<HTMLDivElement>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const [loading, setLoading] = useState(true);
    const fetchedIds = useRef<Set<string>>(new Set());
    // Tracks only backend-originated IDs for the reset-on-DELETE check.
    const backendFetchedIds = useRef<Set<string>>(new Set());

    /** Fetch messages from backend and sync (add new + remove deleted) */
    const fetchMessages = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/api/zalo/messages`);
            if (!res.ok) return;
            const data = await res.json();
            const backendMessages = data.messages as BackendMessage[];
            const backendIds = new Set(backendMessages.map(m => m.id));

            // If backend has fewer messages than we've seen from it (e.g. DELETE),
            // reset state. Compare against backendFetchedIds not fetchedIds so
            // local user messages don't falsely trigger this.
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

    // Tự động cuộn xuống dưới cùng khi có tin nhắn mới
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    // const [isTyping, setIsTyping] = useState(false); // unused for now

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
                sender: "Phụ huynh",
                content: <p className="text-[13.5px]">{text}</p>,
                time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }),
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

                    // Replace temp ID with the real backend ID so the poller won't re-add it
                    if (data.user_msg_id) {
                        fetchedIds.current.delete(tempId);
                        fetchedIds.current.add(data.user_msg_id);
                        setMessages(prev => prev.map(m =>
                            m.id === tempId ? { ...m, id: data.user_msg_id } : m
                        ));
                    }

                    // Add AI reply with backend ID
                    if (data.reply && data.ai_msg_id) {
                        const aiReply: Message = {
                            id: data.ai_msg_id,
                            sender: "Cô Hana (AI)",
                            content: (
                                <div className="space-y-1 text-[14px] leading-[1.6]">
                                    {data.reply.split('\n').map((line: string, i: number) =>
                                        line.trim() === '' ? <div key={i} className="h-2" /> :
                                        <p key={i} className="whitespace-pre-wrap">{line}</p>
                                    )}
                                </div>
                            ),
                            text: data.reply,
                            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }),
                            isAI: true
                        };
                        setMessages(prev => [...prev, aiReply]);
                        fetchedIds.current.add(data.ai_msg_id);
                    }
                }
            } catch {
                const errorReply: Message = {
                    id: Date.now() + 1,
                    sender: "Cô Hana (AI)",
                    content: <p className="text-[13.5px] text-red-600 italic">Không thể kết nối đến AI. Thử lại sau ạ.</p>,
                    text: "Không thể kết nối đến AI. Thử lại sau ạ.",
                    time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }),
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
            sender: "Phụ huynh",
            content: <p className="text-[13.5px]">{text}</p>,
            text,
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }),
            isAI: false
        };

        setMessages(prev => [...prev, userMsg]);
        setInputText("");
    };

    return (
        <div className="flex flex-col h-full bg-[#ebeef5]" style={{ fontFamily: "Arial, sans-serif" }}>
            {/* Header Zalo Mobile */}
            <div className="bg-[#0068ff] pt-10 pb-3 px-4 text-white flex items-center gap-3 shrink-0">
                <div className="w-10 h-10 bg-blue-200 rounded-full flex items-center justify-center text-[#0068ff] font-bold shadow-sm">AI</div>
                <div className="flex flex-col">
                    <span className="font-bold text-[15px]">Nhóm Zalo của phụ huynh</span>
                    <span className="text-[11px] opacity-90">Hoạt động vừa xong</span>
                </div>
            </div>

            {/* Vùng hiển thị tin nhắn */}
            <div ref={scrollRef} className="flex-1 p-3 overflow-y-auto flex flex-col gap-4 no-scrollbar">
                <div className="text-center my-2">
                    <span className="text-[10px] bg-gray-300/50 px-2 py-0.5 rounded-full text-gray-500 font-bold uppercase">Hôm nay</span>
                </div>

                {loading && messages.length === 0 && (
                    <div className="text-center text-gray-400 text-sm mt-4">Đang tải...</div>
                )}

                {!loading && messages.length === 0 && (
                    <div className="text-center text-gray-400 text-xs mt-4">Chưa có tin nhắn</div>
                )}

                {messages.map((msg) => (
                    <div key={msg.id} className={`${msg.isAI ? 'self-start max-w-[95%]' : 'self-end max-w-[85%]'}`}>
                        <div className={`p-4 rounded-2xl shadow-sm border ${msg.isAI
                                ? 'bg-white rounded-tl-none border-gray-100'
                                : 'bg-[#e2f2ff] rounded-tr-none border-blue-100'
                            }`}>
                            <div className="text-gray-800">
                                {msg.content}
                            </div>
                            <div className={`text-[10px] mt-2 font-medium ${msg.isAI ? 'text-gray-400 text-right' : 'text-gray-400 text-right font-bold italic'}`}>
                                {msg.time} {!msg.isAI && "· Đã xem"}
                            </div>
                        </div>
                    </div>
                ))}


            </div>

            {/* Input Mobile */}
            <div className="p-3 bg-white border-t flex items-center gap-3 pb-8">
                <input
                    className="flex-1 bg-gray-100 rounded-full px-4 py-2 text-sm focus:outline-none placeholder: text-black"
                    placeholder="/dailysum"
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                />
                <button
                    onClick={handleSendMessage}
                    className="text-[#0068ff] font-bold text-sm"
                >
                    GỬI
                </button>
            </div>
        </div>
    );
};
