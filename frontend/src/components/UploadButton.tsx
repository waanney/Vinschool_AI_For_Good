// src/components/UploadButton.tsx
'use client';

import { useRef, useState } from 'react';
import { PlusCircle, Loader2 } from 'lucide-react';

export default function UploadButton() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  const isImageFile = (file: File) =>
    ['image/jpeg', 'image/png'].includes(file.type) ||
    /\.(jpe?g|png)$/i.test(file.name);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);

    // Save to localStorage (existing behaviour)
    const newHomework = {
      id: Date.now().toString(),
      title: file.name,
      type: 'Bắt buộc',
      deadline: 'Feb 15, 2026',
    };
    const currentHW = JSON.parse(localStorage.getItem('vinschool_homework_list') || '[]');
    localStorage.setItem('vinschool_homework_list', JSON.stringify([...currentHW, newHomework]));
    localStorage.setItem('has_new_homework_noti', 'true');

    // If image, send to Gemini vision API for parsing + Milvus storage
    if (isImageFile(file)) {
      try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('date', new Date().toISOString().slice(0, 10));
        formData.append('subject', '');

        const res = await fetch(`/api/teacher/daily-lesson/parse-image`, {
          method: 'POST',
          body: formData,
        });

        if (res.ok) {
          const data = await res.json();
          alert(`Đã tải lên và phân tích: ${data.title} (${data.subject}). Nội dung đã lưu vào hệ thống!`);
        } else {
          alert(`Đã tải lên bài tập: ${file.name}. (Lưu ý: phân tích AI không thành công)`);
        }
      } catch {
        alert(`Đã tải lên bài tập: ${file.name}. Học sinh sẽ nhận được thông báo!`);
      }
    } else {
      alert(`Đã tải lên bài tập: ${file.name}. Học sinh sẽ nhận được thông báo!`);
    }

    setUploading(false);
    window.location.reload();
  };

  return (
    <div className="mb-6 flex justify-end">
      <input type="file" ref={fileInputRef} className="hidden" accept=".jpg,.jpeg,.png,.pdf,.docx,.pptx" onChange={handleUpload} />
      <button
        onClick={() => fileInputRef.current?.click()}
        disabled={uploading}
        className="flex items-center space-x-2 bg-[#1e3a8a] hover:bg-[#152a63] text-white px-6 py-2.5 rounded-xl font-bold transition-all shadow-lg active:scale-95 disabled:opacity-60"
      >
        {uploading ? <Loader2 size={20} className="animate-spin" /> : <PlusCircle size={20} />}
        <span>{uploading ? 'Đang xử lý...' : 'Tải lên bài tập mới'}</span>
      </button>
    </div>
  );
}
