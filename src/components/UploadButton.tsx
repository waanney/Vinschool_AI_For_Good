// src/components/UploadButton.tsx
'use client';

import { useRef } from 'react';
import { PlusCircle } from 'lucide-react';

export default function UploadButton() {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Giả lập lưu bài tập mới vào hệ thống
      const newHomework = {
        id: Date.now().toString(),
        title: file.name,
        type: 'Bắt buộc',
        deadline: 'Feb 15, 2026',
      };
      
      const currentHW = JSON.parse(localStorage.getItem('vinschool_homework_list') || '[]');
      localStorage.setItem('vinschool_homework_list', JSON.stringify([...currentHW, newHomework]));
      
      // Tạo thông báo cho học sinh (Notify flag)
      localStorage.setItem('has_new_homework_noti', 'true');
      
      alert(`Đã tải lên bài tập: ${file.name}. Học sinh sẽ nhận được thông báo!`);
      window.location.reload(); // Refresh để cập nhật danh sách
    }
  };

  return (
    <div className="mb-6 flex justify-end">
      <input type="file" ref={fileInputRef} className="hidden" onChange={handleUpload} />
      <button 
        onClick={() => fileInputRef.current?.click()}
        className="flex items-center space-x-2 bg-[#1e3a8a] hover:bg-[#152a63] text-white px-6 py-2.5 rounded-xl font-bold transition-all shadow-lg active:scale-95"
      >
        <PlusCircle size={20} />
        <span>Tải lên bài tập mới</span>
      </button>
    </div>
  );
}