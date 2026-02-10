"use client";
import React, { useState, useEffect, useRef } from 'react';
import "../../app/globals.css";

// Định nghĩa cấu trúc tin nhắn
interface Message {
  id: number;
  sender: string;
  content: React.ReactNode;
  time: string;
  isAI: boolean;
}

export const ZaloMobileChat: React.FC = () => {
  const [inputText, setInputText] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  // 1. Khởi tạo danh sách tin nhắn với nội dung bài học từ ảnh mẫu
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      sender: "AI Assistant",
      content: (
        <div className="space-y-2 text-[14px] leading-[1.6]">
          <p className="font-bold text-gray-900">Bố mẹ các con thân mến,</p>
          <p>Cô Hana xin gửi nội dung học tập buổi hôm nay của các con ạ:</p>
          
          <div>
            <strong className="text-blue-700">Môn Science:</strong>
            <p>Tìm hiểu về cơ chế hoạt động của hệ tiêu hoá <span className="italic font-medium">"digestive system"</span>.</p>
          </div>

          <div>
            <strong className="text-blue-700">Môn Toán:</strong>
            <p>Ôn tập phép cộng và trừ phân số có cùng mẫu số <span className="italic">"denominator"</span>.</p>
            <p className="text-[12px] bg-blue-50 p-2 rounded mt-1 border border-blue-100 italic">
              📝 vinschool.edu.vn/math_unit9
            </p>
          </div>

          <div>
            <strong className="text-blue-700">Môn Tiếng Anh:</strong>
            <p>Câu điều kiện loại 0 <span className="italic">"zero conditional"</span>.</p>
          </div>

          <p className="font-bold text-[#002d72] pt-2 border-t border-gray-100 text-[12px]">
            Kính mong bố mẹ nhắc nhở các con hoàn thành bài tập đầy đủ giúp cô ạ. Cảm ơn bố mẹ!
          </p>
        </div>
      ),
      time: "21:11",
      isAI: true
    }
  ]);

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

        {messages.map((msg) => (
          <div key={msg.id} className={`${msg.isAI ? 'self-start max-w-[95%]' : 'self-end max-w-[85%]'}`}>
            <div className={`p-4 rounded-2xl shadow-sm border ${
              msg.isAI 
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