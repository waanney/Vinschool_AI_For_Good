"use client";
import React, { useState, useEffect, useRef } from 'react';
import "../../app/globals.css";

interface Message {
  id: number;
  sender: string;
  content: React.ReactNode; 
  time: string;
  isAI: boolean;
}

export const ZaloDesktopChat: React.FC = () => {
  const [inputText, setInputText] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  
  // 1. Khởi tạo tin nhắn gốc với nội dung Thuyên muốn giữ
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      sender: "AI Assistant",
      content: (
        <div className="space-y-4">
          <p className="font-bold text-[15px] mb-3 text-[#002d72] italic">Bố mẹ các con thân mến,</p>
          <p className="text-[14px] mb-4 text-gray-700">Cô Hana xin gửi nội dung học tập 2 buổi hôm nay của các con ạ:</p>
          
          <div className="pl-3 border-l-[3px] border-[#0068ff]">
            <p className="font-bold text-[#0052cc] text-[14px] underline decoration-blue-200">Môn Science:</p>
            <p className="text-[14px] text-gray-700 mt-1">Tìm hiểu cơ chế hoạt động của hệ tiêu hoá <span className="font-semibold text-blue-600">"digestive system"</span>.</p>
          </div>

          <div className="pl-3 border-l-[3px] border-[#e11d48]">
            <p className="font-bold text-[#be123c] text-[14px] underline decoration-red-200">Môn Toán:</p>
            <p className="text-[14px] text-gray-700 mt-1">Cộng và trừ phân số có cùng mẫu số <span className="italic font-medium">"denominator"</span>. Bắt đầu học khác mẫu số.</p>
          </div>

          <div className="pl-3 border-l-[3px] border-[#10b981]">
            <p className="font-bold text-[#047857] text-[14px] underline decoration-green-200">Môn Tiếng Anh:</p>
            <p className="text-[14px] text-gray-700 mt-1">Ôn tập câu điều kiện loại 0 <span className="italic">"zero conditional"</span> và câu hỏi đuôi.</p>
          </div>

          <p className="mt-6 pt-3 border-t border-gray-100 font-semibold text-[#002d72] text-[13px] tracking-tighter leading-tight">
            Kính mong bố mẹ nhắc nhở các con hoàn thành bài tập đầy đủ giúp cô ạ. Cảm ơn bố mẹ!
          </p>
        </div>
      ),
      time: "21:11",
      isAI: true
    }
  ]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSendMessage = () => {
    if (!inputText.trim()) return;

    const userMsg: Message = {
      id: Date.now(),
      sender: "Phụ huynh Alex",
      content: <p className="text-[14px] text-gray-800">{inputText}</p>,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      isAI: false
    };

    setMessages(prev => [...prev, userMsg]);
    setInputText("");

    // AI phản hồi tự động
    setTimeout(() => {
      const aiReply: Message = {
        id: Date.now() + 1,
        sender: "AI Assistant",
        content: <p className="text-[14px] text-gray-800 italic">Dạ vâng ạ, hệ thống AI đã ghi nhận phản hồi và sẽ cập nhật tình hình học tập của Alex cho phụ huynh thường xuyên ạ! ✨</p>,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isAI: true
      };
      setMessages(prev => [...prev, aiReply]);
    }, 1500);
  };

  return (
    <div className="flex w-full h-full bg-white font-sans text-[#081c36]" style={{ fontFamily: "'Segoe UI', Tahoma, sans-serif" }}>
      {/* 1. Sidebar trái */}
      <div className="w-[64px] bg-[#0052cc] flex flex-col items-center py-6 gap-8 text-white shadow-inner flex-shrink-0">
        <div className="w-10 h-10 bg-[#00a1ff] rounded-full flex items-center justify-center font-bold text-sm border-2 border-white/20">HT</div>
        <div className="text-2xl cursor-pointer hover:opacity-80 transition-opacity">💬</div>
        <div className="text-xl cursor-pointer opacity-60 hover:opacity-100">👤</div>
        <div className="mt-auto mb-4 text-xl cursor-pointer opacity-60 hover:opacity-100">⚙️</div>
      </div>

      {/* 2. Danh sách hội thoại */}
      <div className="w-[280px] border-r border-[#dbdee1] bg-white flex flex-col flex-shrink-0">
        <div className="p-4 border-b border-[#dbdee1] font-bold text-[16px]">Tin nhắn</div>
        <div className="bg-[#e5efff] p-3 flex items-center gap-3 border-l-[4px] border-[#0068ff] cursor-pointer">
          <div className="w-12 h-12 bg-[#0068ff] rounded-full flex items-center justify-center text-white text-[10px] font-bold shadow-sm">AI</div>
          <div className="flex flex-col overflow-hidden">
            <span className="font-bold text-[14px] truncate">Nhóm Zalo của phụ huynh</span>
            <span className="text-[12px] text-[#0068ff] truncate font-medium italic">AI đang trả lời...</span>
          </div>
        </div>
      </div>

      {/* 3. Vùng nội dung chat chính */}
      <div className="flex-1 flex flex-col bg-[#f4f7f9] overflow-hidden">
        {/* Header khung chat */}
        <div className="p-3 bg-white border-b border-[#dbdee1] flex justify-between items-center px-5 flex-shrink-0">
          <div className="flex flex-col">
            <span className="font-bold text-[16px]">Nhóm Zalo của phụ huynh (Alex - 4B5)</span>
            <span className="text-[11px] text-gray-500 font-medium italic">15 thành viên</span>
          </div>
          <div className="flex gap-4 text-gray-400 font-medium text-sm italic">📅 09/02/2026</div>
        </div>

        {/* Vùng tin nhắn cuộn */}
        <div ref={scrollRef} className="flex-1 p-8 overflow-y-auto flex flex-col gap-6 no-scrollbar bg-[#f4f7f9]">
          <div className="text-center"><span className="text-[11px] text-gray-400 font-bold uppercase tracking-widest opacity-60">--- Hôm nay ---</span></div>

          {messages.map((msg) => (
            <div key={msg.id} className={`flex gap-3 ${msg.isAI ? 'self-start' : 'self-end flex-row-reverse'} max-w-[85%]`}>
              <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-white text-[10px] font-bold mt-1 ${msg.isAI ? 'bg-[#0068ff]' : 'bg-green-600'}`}>
                {msg.isAI ? 'AI' : 'PH'}
              </div>
              <div className={`p-4 rounded-xl shadow-[0_1px_2px_rgba(0,0,0,0.1)] border ${msg.isAI ? 'bg-white border-[#dbdee1]' : 'bg-[#e2f2ff] border-[#0068ff]/20'}`}>
                <p className={`text-[11px] font-bold mb-1 ${msg.isAI ? 'text-blue-700' : 'text-green-700'}`}>{msg.sender}</p>
                <div className="leading-relaxed">
                   {msg.content}
                </div>
                <div className="text-[10px] text-gray-400 text-right mt-2 font-bold opacity-70 italic">{msg.time}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Footer soạn thảo chuẩn Desktop */}
        <div className="h-[140px] bg-white border-t border-[#dbdee1] flex flex-col p-3 flex-shrink-0">
          <div className="flex gap-4 mb-2 text-gray-500 text-lg px-2">
            <span className="cursor-pointer hover:text-blue-600">☺</span>
            <span className="cursor-pointer hover:text-blue-600">🖼️</span>
            <span className="cursor-pointer hover:text-blue-600">📎</span>
            <span className="cursor-pointer hover:text-blue-600">📷</span>
          </div>
          <textarea 
            className="w-full h-full bg-transparent border-none focus:outline-none text-[14px] resize-none px-2 text-gray-600 font-medium placeholder:text-gray-300"
            placeholder="Nhập tin nhắn để trả lời cô Hana..."
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