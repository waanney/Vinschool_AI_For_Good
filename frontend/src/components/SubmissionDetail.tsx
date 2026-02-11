'use client';

import { useState } from "react";
import Image from "next/image";

export default function SubmissionDetail() {
  // Trạng thái lưu danh sách STT các học sinh đã được click xem
  // Mặc định Hải Anh (STT 3) đã trắng từ đầu nên ta cho sẵn vào mảng
  const [viewedIds, setViewedIds] = useState<number[]>([3]);

  const students = [
    {
      stt: 1,
      name: "Cấn Trần Quang Bách",
      time: "Jan 4, 2026",
      comment: "Quang Bách đã nắm khá chắc kiến thức phần cộng trừ phân số. Tuy nhiên còn một số lỗi nằm ở...",
      suggested: "Unit 9: Week 22 fractions math practice and answer key"
    },
    {
      stt: 2,
      name: "Phạm Bách Hợp",
      time: "Apr 4, 2026",
      comment: "Bách Hợp đã nắm chắc kiến thức, tuy nhiên cần chú ý phần sắp xếp thứ tự phân số. Bài tập làm đúng 23/25 câu.",
      suggested: "Unit 9: Week 22 fractions math practice and answer key"
    },
    {
      stt: 3,
      name: "Nguyễn Hải Anh",
      time: "Jan 8, 2026",
      comment: "Hải Anh nắm kiến thức rất chắc. Bài tập làm đúng 100%.",
      suggested: "Blook"
    }
  ];

  const handleRowClick = (stt: number) => {
    if (!viewedIds.includes(stt)) {
      setViewedIds([...viewedIds, stt]);
    }
  };

  return (
    <div className="flex flex-col w-full animate-in fade-in duration-500">
      {/* Header & Nav giữ nguyên UI Vinschool */}
      <header className="bg-[#1e3a8a] text-white p-6 flex justify-between items-center shadow-md">
        <div>
          <h1 className="text-xl font-bold">4B5 - Math - Jem Omer</h1>
          <p className="text-xs text-blue-200 opacity-80 uppercase mt-1">Teacher Management</p>
        </div>
      </header>

      <nav className="bg-white border-b px-8 py-3 flex space-x-8 text-sm font-medium text-gray-600">
        <span>Trang chủ</span>
        <span>Lịch trình</span>
        <span className="bg-[#4f46e5] text-white px-4 py-1 rounded-full cursor-pointer">Bài tập học sinh</span>
        <span>Báo cáo tiến bộ</span>
      </nav>

      <div className="p-6">
        <div className="bg-white rounded-2xl border shadow-sm p-6">
          <h2 className="text-sm font-bold text-slate-800 mb-6">Unit 9: Week 22 fractions math practice - Bài tập bắt buộc - Deadline Jan 9, 2026</h2>

          {/* Bộ lọc */}
          <div className="flex space-x-8 mb-6 text-sm font-medium">
            <label className="flex items-center space-x-2"><input type="radio" defaultChecked name="status" className="accent-blue-900"/> <span>Tất cả</span></label>
            <label className="flex items-center space-x-2"><input type="radio" name="status" className="accent-blue-900"/> <span>Đã nộp bài</span></label>
            <label className="flex items-center space-x-2"><input type="radio" name="status" className="accent-blue-900"/> <span>Chưa nộp bài</span></label>
          </div>

          {/* Bảng chi tiết */}
          <div className="border rounded-lg overflow-hidden">
            <table className="w-full text-left text-[13px]">
              <thead className="bg-[#e0f2fe] text-gray-700 font-bold">
                <tr className="text-center">
                  <th className="p-3 border-b border-r w-12">STT</th>
                  <th className="p-3 border-b border-r w-48">Học sinh</th>
                  <th className="p-3 border-b border-r w-32">Thời gian nộp bài</th>
                  <th className="p-3 border-b border-r">Nhận xét</th>
                  <th className="p-3 border-b border-r w-20">Chi tiết</th>
                  <th className="p-3 border-b w-64">Bài tập được đề xuất thêm</th>
                </tr>
              </thead>
              <tbody>
                {students.map((student) => {
                  const isViewed = viewedIds.includes(student.stt);
                  return (
                    <tr 
                      key={student.stt}
                      onClick={() => handleRowClick(student.stt)}
                      className={`border-b cursor-pointer transition-colors duration-300 ${isViewed ? 'bg-white' : 'bg-[#f3f4f6]'}`}
                    >
                      <td className="p-4 text-center font-bold border-r">{student.stt}</td>
                      <td className="p-4 font-bold text-slate-700 border-r">{student.name}</td>
                      <td className="p-4 text-center text-slate-500 border-r bg-slate-50/50">{student.time}</td>
                      <td className="p-4 text-slate-600 border-r leading-relaxed">{student.comment}</td>
                      <td className="p-4 border-r text-center">
                        <div className="relative w-10 h-12 mx-auto border bg-white shadow-sm">
                           <Image src="/pdf-thumb.png" alt="thumb" fill className="object-cover p-1 opacity-50"/>
                        </div>
                      </td>
                      <td className="p-4 font-medium text-slate-700">{student.suggested}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}