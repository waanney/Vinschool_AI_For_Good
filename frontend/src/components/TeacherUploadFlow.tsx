'use client';

import { useState, useRef } from 'react';
import { PlusCircle, Check, Loader2 } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

interface ParsedLesson {
  subject: string;
  title: string;
  content: string;
  homework: string;
  notes: string;
}

export default function TeacherUploadFlow() {
  // Steps: 1 → File, 2 → Type, 3 → Deadline, 4 → Uploading, 5 → Done, 6 → Error
  const [step, setStep] = useState(1);
  const [newHW, setNewHW] = useState({ title: '', type: 'Bắt buộc', deadline: '' });
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [parsedLesson, setParsedLesson] = useState<ParsedLesson | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isImageFile = (file: File) =>
    ['image/jpeg', 'image/png'].includes(file.type) ||
    /\.(jpe?g|png)$/i.test(file.name);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setNewHW({ ...newHW, title: file.name });
      setStep(2);
    }
  };

  const handleFinish = async () => {
    setStep(4); // uploading state

    // Save to localStorage list (keep existing behaviour for non-image files)
    const currentList = JSON.parse(localStorage.getItem('vinschool_hw_list') || '[]');
    const hwItem = {
      id: Date.now().toString(),
      unit: 'Unit 9',
      ...newHW,
      typeKey: newHW.type === 'Bắt buộc' ? 'mandatory' : 'reference',
    };
    localStorage.setItem('vinschool_hw_list', JSON.stringify([...currentList, hwItem]));
    localStorage.setItem('new_hw_count', '1');

    // If the file is an image, send it to Gemini vision for parsing + Milvus storage
    if (selectedFile && isImageFile(selectedFile)) {
      try {
        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('date', newHW.deadline || new Date().toISOString().slice(0, 10));
        formData.append('subject', '');

        const res = await fetch(`${API_BASE}/api/teacher/daily-lesson/parse-image`, {
          method: 'POST',
          body: formData,
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: res.statusText }));
          throw new Error(err.detail || 'Upload failed');
        }

        const data = await res.json();
        setParsedLesson({
          subject: data.subject,
          title: data.title,
          content: data.content,
          homework: data.homework,
          notes: data.notes,
        });
      } catch (err: any) {
        setErrorMsg(err.message || 'Lỗi khi phân tích hình ảnh');
        setStep(6);
        return;
      }
    }

    setStep(5); // done
    setTimeout(() => {
      setStep(1);
      setSelectedFile(null);
      setParsedLesson(null);
      window.location.reload();
    }, 3000);
  };

  return (
    <div className="mb-8 p-6 bg-blue-50/50 rounded-3xl border border-blue-100">
      {step === 1 && (
        <button onClick={() => fileInputRef.current?.click()} className="flex items-center space-x-2 bg-[#1e3a8a] text-white px-6 py-3 rounded-xl font-bold hover:bg-blue-800 transition-all">
          <PlusCircle size={20} /> <span>Tải lên bài tập mới</span>
          <input type="file" ref={fileInputRef} className="hidden" accept=".jpg,.jpeg,.png,.pdf,.docx,.pptx" onChange={handleFileSelect} />
        </button>
      )}

      {step === 2 && (
        <div className="flex flex-col space-y-4 animate-in slide-in-from-left duration-300">
          <p className="font-bold text-[#1e3a8a]">Bước 2: Chọn loại bài tập cho &quot;{newHW.title}&quot;</p>
          <div className="flex space-x-4">
            {['Bắt buộc', 'Tham khảo'].map(t => (
              <button key={t} onClick={() => { setNewHW({...newHW, type: t}); setStep(3); }} className="px-6 py-2 border-2 border-blue-200 rounded-xl hover:bg-blue-600 hover:text-white font-medium transition-all">
                {t}
              </button>
            ))}
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="flex flex-col space-y-4 animate-in slide-in-from-left duration-300">
          <p className="font-bold text-[#1e3a8a]">Bước 3: Thiết lập Deadline</p>
          <div className="flex items-center space-x-4">
            <input type="date" className="p-2 border rounded-xl" onChange={(e) => setNewHW({...newHW, deadline: e.target.value})} />
            <button onClick={handleFinish} className="bg-green-600 text-white px-8 py-2 rounded-xl font-bold">Hoàn tất Upload</button>
          </div>
        </div>
      )}

      {step === 4 && (
        <div className="flex items-center space-x-3 text-blue-700 font-bold animate-in fade-in">
          <Loader2 size={20} className="animate-spin" />
          <span>Đang phân tích bài tập bằng AI và lưu vào hệ thống...</span>
        </div>
      )}

      {step === 5 && (
        <div className="flex flex-col space-y-3 animate-in zoom-in">
          <div className="flex items-center space-x-2 text-green-600 font-bold">
            <div className="bg-green-100 p-2 rounded-full"><Check size={20}/></div>
            <span>Đã giao bài tập thành công cho học sinh!</span>
          </div>
          {parsedLesson && (
            <div className="bg-white rounded-xl border border-green-200 p-4 text-sm text-slate-700 space-y-1">
              <p><span className="font-semibold">Môn:</span> {parsedLesson.subject}</p>
              <p><span className="font-semibold">Chủ đề:</span> {parsedLesson.title}</p>
              {parsedLesson.homework && <p><span className="font-semibold">Bài tập:</span> {parsedLesson.homework}</p>}
              <p className="text-xs text-slate-400 mt-1">Nội dung đã được AI trích xuất và lưu vào hệ thống.</p>
            </div>
          )}
        </div>
      )}

      {step === 6 && (
        <div className="flex flex-col space-y-3 animate-in fade-in">
          <div className="flex items-center space-x-2 text-red-600 font-bold">
            <span>Lỗi: {errorMsg}</span>
          </div>
          <button onClick={() => { setStep(1); setErrorMsg(''); }} className="text-sm text-blue-600 underline self-start">Thử lại</button>
        </div>
      )}
    </div>
  );
}
