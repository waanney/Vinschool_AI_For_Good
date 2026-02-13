"use client";
import React, { useState, useEffect, useRef, useCallback } from 'react';
import "@/app/globals.css";

// Backend API base URL
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface LessonData {
    subject: string;
    content: string;
    homework?: string;
    homework_link?: string;
    mandatory_assignment?: string;
    mandatory_assignment_deadline?: string;
    mandatory_assignment_link?: string;
    reading_materials_link?: string;
}

interface BackendMessage {
    id: string;
    sender: string;
    greeting: string;
    intro: string;
    lessons: LessonData[];
    closing: string;
    time: string;
    is_ai: boolean;
}

// Định nghĩa cấu trúc tin nhắn
interface Message {
    id: number | string;
    sender: string;
    content: React.ReactNode;
    time: string;
    isAI: boolean;
}

/** Convert a backend message into a styled mobile chat bubble */
function renderBackendMessage(msg: BackendMessage): React.ReactNode {
    return (
        <div className="space-y-2 text-[14px] leading-[1.6]">
            <p className="font-bold text-gray-900">{msg.greeting}</p>
            <p>{msg.intro}</p>

            {msg.lessons.map((lesson, i) => (
                <div key={i}>
                    <strong className="text-blue-700">Môn {lesson.subject}:</strong>
                    <p>{lesson.content}</p>
                    {lesson.homework && <p className="text-[13px] text-gray-600">{lesson.homework}</p>}
                    {lesson.homework_link && (
                        <p className="text-[12px] bg-blue-50 p-2 rounded mt-1 border border-blue-100 italic">
                            📎 {lesson.homework_link}
                        </p>
                    )}
                    {lesson.mandatory_assignment && (
                        <p className="text-[13px] text-gray-600 font-medium">{lesson.mandatory_assignment}</p>
                    )}
                    {lesson.mandatory_assignment_deadline && (
                        <p className="text-[12px] text-orange-600 italic">⏰ {lesson.mandatory_assignment_deadline}</p>
                    )}
                </div>
            ))}

            <p className="font-bold text-[#002d72] pt-2 border-t border-gray-100 text-[12px]">
                {msg.closing}
            </p>
        </div>
    );
}

export const ZaloMobileChat: React.FC = () => {
    const [inputText, setInputText] = useState("");
    const scrollRef = useRef<HTMLDivElement>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const [loading, setLoading] = useState(true);
    const fetchedIds = useRef<Set<string>>(new Set());

    /** Fetch messages from backend and sync (add new + remove deleted) */
    const fetchMessages = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/api/zalo/messages`);
            if (!res.ok) return;
            const data = await res.json();
            const backendMessages = data.messages as BackendMessage[];
            const backendIds = new Set(backendMessages.map(m => m.id));

            // If backend has fewer messages (e.g. after DELETE), reset state
            if (backendMessages.length < fetchedIds.current.size) {
                fetchedIds.current = new Set(backendIds);
                setMessages(
                    backendMessages.map(msg => ({
                        id: msg.id,
                        sender: msg.sender,
                        content: renderBackendMessage(msg),
                        time: msg.time,
                        isAI: msg.is_ai,
                    }))
                );
                return;
            }

            // Otherwise, append only new messages
            const newMessages: Message[] = [];
            for (const msg of backendMessages) {
                if (!fetchedIds.current.has(msg.id)) {
                    fetchedIds.current.add(msg.id);
                    newMessages.push({
                        id: msg.id,
                        sender: msg.sender,
                        content: renderBackendMessage(msg),
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

    const handleSendMessage = () => {
        if (!inputText.trim()) return;

        // Tin nhắn của Phụ huynh
        const userMsg: Message = {
            id: Date.now(),
            sender: "Phụ huynh",
            content: <p className="text-[13.5px]">{inputText}</p>,
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            isAI: false
        };

        setMessages(prev => [...prev, userMsg]);
        setInputText("");

        // AI phản hồi tự động sau 1.2 giây
        setTimeout(() => {
            const aiReply: Message = {
                id: Date.now() + 1,
                sender: "AI Assistant",
                content: <p className="text-[13.5px] italic text-blue-800">Dạ, hệ thống AI đã nhận thông tin từ phụ huynh ạ! ✨</p>,
                time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                isAI: true
            };
            setMessages(prev => [...prev, aiReply]);
        }, 1200);
    };

    return (
        <div className="flex flex-col h-full bg-[#ebeef5]" style={{ fontFamily: "Arial, sans-serif" }}>
            {/* Header Zalo Mobile */}
            <div className="bg-[#0068ff] pt-10 pb-3 px-4 text-white flex items-center gap-3 flex-shrink-0">
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
                    placeholder="Nhập @, tin nhắn đến AI..."
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
