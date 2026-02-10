'use client';
import { useState, useEffect } from "react";
import SubmitButton from "./SubmitButton";

export default function HomeworkTable() {
  const [filter, setFilter] = useState('all');
  const [submissions, setSubmissions] = useState<Record<string, boolean>>({});
  const [homeworkList, setHomeworkList] = useState<any[]>([]);

  // 1. Load bài tập (bao gồm cả bài giáo viên mới up) và trạng thái nộp
  useEffect(() => {
    // Lấy bài tập giáo viên đã giao
    const uploadedHW = JSON.parse(localStorage.getItem('vinschool_hw_list') || '[]');
    
    // Bài tập mặc định ban đầu
    const defaultHW = [
      { id: 'unit9_bb', unit: 'Unit 9', title: 'Week 22 fractions math practice.pdf', type: 'Bắt buộc', typeKey: 'mandatory', deadline: 'Jan 9, 2026', fileUrl: '/BaiTapBB_Demo.pdf', color: 'text-red-500' },
      { id: 'unit9_tk', unit: 'Unit 9', title: 'Week 21 HW extension option.pdf', type: 'Tham khảo', typeKey: 'reference', deadline: 'Jan 12, 2026', fileUrl: '/BaiTapThem_Demo.pdf', color: 'text-blue-500' }
    ];

    setHomeworkList([...defaultHW, ...uploadedHW]);

    // Kiểm tra trạng thái nộp bài
    const savedSubmissions = JSON.parse(localStorage.getItem('vinschool_submissions') || '[]');
    const submittedIds = savedSubmissions.map((s: any) => s.id);
    const newSubState: Record<string, boolean> = {};
    [...defaultHW, ...uploadedHW].forEach(hw => {
      newSubState[hw.id] = submittedIds.includes(hw.id);
    });
    setSubmissions(newSubState);

    // Xóa Noti số 1 khi học sinh đã vào xem bảng bài tập
    localStorage.removeItem('new_hw_count');
  }, []);

  const handleSuccess = (key: string, fileName: string) => {
    setSubmissions(prev => ({ ...prev, [key]: true }));
    const current = JSON.parse(localStorage.getItem('vinschool_submissions') || '[]');
    const newSubmission = { 
      id: key, 
      student: "Quang Anh", 
      file: fileName, 
      time: new Date().toLocaleString() 
    };
    localStorage.setItem('vinschool_submissions', JSON.stringify([...current, newSubmission]));
  };

  const handleUnsubmit = (key: string) => {
    setSubmissions(prev => ({ ...prev, [key]: false }));
    const current = JSON.parse(localStorage.getItem('vinschool_submissions') || '[]');
    localStorage.setItem('vinschool_submissions', JSON.stringify(current.filter((s: any) => s.id !== key)));
  };

  const filteredHomework = homeworkList.filter(item => filter === 'all' || item.typeKey === filter);

  return (
    <>
      {/* Giữ nguyên phần Radio Buttons của bạn */}
      <div className="flex space-x-8 mb-6 text-sm font-medium">
        {['all', 'mandatory', 'reference'].map((type) => (
          <label key={type} className="flex items-center space-x-2 cursor-pointer">
            <input type="radio" name="filter" checked={filter === type} onChange={() => setFilter(type)} className="accent-[#4f46e5]"/> 
            <span>{type === 'all' ? 'Tất cả' : type === 'mandatory' ? 'Bài tập bắt buộc' : 'Bài tập tham khảo'}</span>
          </label>
        ))}
      </div>

      <div className="border rounded-lg overflow-hidden shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="bg-[#e0f2fe] text-gray-700">
            <tr className="text-center font-bold">
              <th className="p-4 border-b">Unit</th>
              <th className="p-4 border-b">Bài Tập</th>
              <th className="p-4 border-b">Dạng bài tập</th>
              <th className="p-4 border-b">Deadline</th>
              <th className="p-4 border-b">Chi tiết</th>
              <th className="p-4 border-b">Nộp bài</th>
            </tr>
          </thead>
          <tbody>
            {filteredHomework.map((item) => {
              const isSubmitted = submissions[item.id];
              return (
                <tr key={item.id} className={`border-b text-center transition-all ${isSubmitted ? 'bg-green-50/50' : ''}`}>
                  <td className="p-4 bg-gray-50 font-bold border-r w-24">{item.unit}</td>
                  <td className="p-4 font-medium text-blue-900">{item.title}</td>
                  <td className={`p-4 font-medium ${item.color || (item.type === 'Bắt buộc' ? 'text-red-500' : 'text-blue-500')}`}>{item.type}</td>
                  <td className="p-4 text-gray-500">{item.deadline}</td>
                  <td className="p-4">
                    <a href={item.fileUrl} target="_blank" className="text-blue-600 underline font-medium cursor-pointer hover:text-blue-800">Bấm vào để xem</a>
                  </td>
                  <td className="p-4">
                    {isSubmitted ? (
                      <div className="flex flex-col items-center space-y-1 animate-in zoom-in">
                        <span className="text-green-600 font-bold uppercase text-[11px]">Submitted</span>
                        <button onClick={() => handleUnsubmit(item.id)} className="text-[10px] text-gray-400 underline hover:text-red-500 cursor-pointer">Hủy nộp</button>
                      </div>
                    ) : (
                      <SubmitButton onSuccess={() => handleSuccess(item.id, item.title)} />
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}