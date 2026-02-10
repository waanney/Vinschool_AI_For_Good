'use client';

import { useState, useRef } from 'react';
import { PlusCircle, Check } from 'lucide-react';

export default function TeacherUploadFlow() {
  const [step, setStep] = useState(1); // 1: File, 2: Type, 3: Deadline, 4: Finish
  const [newHW, setNewHW] = useState({ title: '', type: 'Bắt buộc', deadline: '' });
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      setNewHW({ ...newHW, title: e.target.files[0].name });
      setStep(2);
    }
  };

  const handleFinish = () => {
    // Lưu vào danh sách bài tập chung
    const currentList = JSON.parse(localStorage.getItem('vinschool_hw_list') || '[]');
    const hwItem = {
      id: Date.now().toString(),
      unit: 'Unit 9',
      ...newHW,
      typeKey: newHW.type === 'Bắt buộc' ? 'mandatory' : 'reference'
    };
    localStorage.setItem('vinschool_hw_list', JSON.stringify([...currentList, hwItem]));
    
    // Gửi thông báo cho học sinh
    localStorage.setItem('new_hw_count', '1');
    
    setStep(4);
    setTimeout(() => {
        setStep(1);
        window.location.reload();
    }, 2000);
  };

  return (
    <div className="mb-8 p-6 bg-blue-50/50 rounded-3xl border border-blue-100">
      {step === 1 && (
        <button onClick={() => fileInputRef.current?.click()} className="flex items-center space-x-2 bg-[#1e3a8a] text-white px-6 py-3 rounded-xl font-bold hover:bg-blue-800 transition-all">
          <PlusCircle size={20} /> <span>Tải lên bài tập mới</span>
          <input type="file" ref={fileInputRef} className="hidden" onChange={handleFileSelect} />
        </button>
      )}

      {step === 2 && (
        <div className="flex flex-col space-y-4 animate-in slide-in-from-left duration-300">
          <p className="font-bold text-[#1e3a8a]">Bước 2: Chọn loại bài tập cho "{newHW.title}"</p>
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
        <div className="flex items-center space-x-2 text-green-600 font-bold animate-in zoom-in">
          <div className="bg-green-100 p-2 rounded-full"><Check size={20}/></div>
          <span>Đã giao bài tập thành công cho học sinh!</span>
        </div>
      )}
    </div>
  );
}