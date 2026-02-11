'use client';

import { useState, useEffect, useRef } from "react";
import UploadButton from "./UploadButton";

export default function TeacherHomeworkTable({ userName }: { userName: string }) {
  // --- QUẢN LÝ ĐIỀU HƯỚNG ---
  const [activeMainTab, setActiveMainTab] = useState<'homework' | 'progress'>('homework');
  const [activeSubTab, setActiveSubTab] = useState<'unit' | 'process'>('unit');
  const [reportView, setReportView] = useState<'select' | 'result' | 'detail'>('select');

  // --- TRẠNG THÁI CHO BÁO CÁO TIẾN TRÌNH (TRANG CUỐI) ---
  const [processView, setProcessView] = useState<'select' | 'result'>('select');
  const [isApproved, setIsApproved] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [generalComment, setGeneralComment] = useState(
    "Quang Bách là một học sinh có năng lực Toán học rất tốt, đạt thành tích xuất sắc ở tất cả các Unit trong học kỳ I. Bách thành thạo trong việc phân tích và giải quyết các bài toán giải quyết vấn đề, luôn nhanh chóng xác định được các phép tính."
  );
  const commentRef = useRef<HTMLTextAreaElement>(null);

  // --- QUẢN LÝ VIEW BÀI TẬP ---
  const [view, setView] = useState<'list' | 'detail' | 'images'>('list');
  const [filter, setFilter] = useState('all');
  const [homeworkList, setHomeworkList] = useState<any[]>([]);
  const [selectedStudent, setSelectedStudent] = useState<any>(null);
  const [viewedStudentIds, setViewedStudentIds] = useState<number[]>([4]);
  const [activeHW, setActiveHW] = useState<any>(null);

  useEffect(() => {
    const defaultHW = [
      { id: 'unit9_bb', unit: 'Unit 9', title: 'Week 22 fractions math practice.pdf', fullTitle: 'Unit 9: Week 22 fractions math practice - Bài tập bắt buộc - Deadline Jan 9, 2026', type: 'Bắt buộc', typeKey: 'mandatory', deadline: 'Jan 9, 2026', color: 'text-red-500' },
      { id: 'unit9_tk', unit: 'Unit 9', title: 'Week 21 HW extension option.pdf', fullTitle: 'Unit 9: Week 21 HW extension option - Bài tập tham khảo - Deadline Jan 12, 2026', type: 'Tham khảo', typeKey: 'reference', deadline: 'Jan 12, 2026', color: 'text-blue-500' }
    ];
    setHomeworkList(defaultHW);
  }, []);

  const students = [
    { stt: 1, name: "Cấn Trần Quang Bách", images: ["/BaiTapHS1_Demo.jpg", "/BaiTapHS2_Demo.jpg", "/BaiTapHS3_Demo.jpg"], comment: "Quang Bách đã nắm khá chắc kiến thức phần cộng trừ phân số. Tuy nhiên vẫn còn một số lỗi nằm ở phần cộng trừ và so sánh phân số." },
    { stt: 2, name: "Trần Minh Khôi", images: ["/BaiTapHS1_Demo.jpg", "/BaiTapHS2_Demo.jpg", "/BaiTapHS3_Demo.jpg"], comment: "Minh Khôi cần ôn thêm về phần cộng/trừ phân số cùng mẫu. Bài tập làm đúng 18/25 câu." },
    { stt: 3, name: "Phạm Bách Hợp", images: ["/BaiTapHS1_Demo.jpg", "/BaiTapHS2_Demo.jpg", "/BaiTapHS3_Demo.jpg"], comment: "Bách Hợp đã nắm chắc kiến thức, tuy nhiên cần chú ý phần sắp xếp thứ tự phân số. Bài tập làm đúng 23/25 câu." },
    { stt: 4, name: "Nguyễn Hải Anh", images: ["/BaiTapHA1_Demo.jpg", "/BaiTapHA2_Demo.jpg", "/BaiTapHA3_Demo.jpg"], comment: "Hải Anh nắm kiến thức rất chắc. Bài tập làm đúng 100%." }
  ];

  const progressAssignments = [
    { stt: 1, title: "Week 24: Fractions Practice", deadline: "Jan 8, 2026", subTime: "Jan 6, 2026", status: "on-time" },
    { stt: 2, title: "Week 23: Fractions Quiz", deadline: "Jan 7, 2026", subTime: "Jan 8, 2026", status: "late" },
    { stt: 3, title: "Week 22: Math Extension", deadline: "", subTime: "Jan 6, 2026", status: "none" },
    { stt: 4, title: "Week 21: Optional Homework", deadline: "", subTime: "Jan 8, 2026", status: "none" },
  ];

  const openImageGallery = (student: any) => {
    setSelectedStudent(student);
    setView('images');
  };

  const handleEditClick = () => {
    setIsEditing(true);
    setTimeout(() => commentRef.current?.focus(), 10);
  };

  return (
    <div className="flex flex-col w-full min-h-screen bg-slate-50/30">
      <header className="bg-[#1e3a8a] text-white p-6 flex justify-between items-center shadow-md">
        <div>
          <h1 className="text-xl font-bold">4B5 - Math - {userName}</h1>
          <p className="text-xs text-blue-200 opacity-80 uppercase tracking-widest mt-1">Teacher Management</p>
        </div>
        <div className="bg-white/10 px-4 py-2 rounded-lg border border-white/20 text-sm">
          Chào mừng trở lại, <span className="text-yellow-400 font-bold">{userName}</span>! 👋
        </div>
      </header>

      <nav className="bg-white border-b px-8 py-3 flex space-x-8 text-sm font-medium text-gray-600 items-center">
        <span className="cursor-pointer hover:text-blue-600">Trang chủ</span>
        <span className="cursor-pointer hover:text-blue-600">Lịch trình</span>
        <span className="cursor-pointer hover:text-blue-600">Các học phần</span>
        <span onClick={() => { setActiveMainTab('homework'); setView('list'); }} className={`px-4 py-1.5 rounded-full cursor-pointer relative transition-all ${activeMainTab === 'homework' && view !== 'images' ? 'bg-[#4f46e5] text-white shadow-md' : 'hover:bg-slate-100'}`}>
          Bài tập học sinh <span className="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] w-4 h-4 flex items-center justify-center rounded-full border border-white">2</span>
        </span>
        <span onClick={() => { setActiveMainTab('progress'); setReportView('select'); setProcessView('select'); setView('list'); }} className={`px-4 py-1.5 rounded-full cursor-pointer transition-all ${activeMainTab === 'progress' && view !== 'images' ? 'bg-[#4f46e5] text-white shadow-md' : 'hover:bg-slate-100'}`}>
          Báo cáo tiến bộ
        </span>
      </nav>

      <div className="p-6">
        {view === 'images' ? (
          <div className="bg-white rounded-2xl border shadow-sm p-8 text-center animate-in fade-in duration-500">
            <button onClick={() => { if (activeMainTab === 'progress') { setReportView('detail'); setView('list'); } else { setView('detail'); } }} className="mb-4 text-sm text-blue-600 font-medium hover:underline flex items-center">← Quay lại</button>
            <h2 className="text-[14px] font-bold text-slate-800 mb-8 pb-4 border-b text-left">{activeHW?.fullTitle} - <span className="text-blue-700">{selectedStudent?.name}</span></h2>
            <div className="grid grid-cols-3 gap-8">{[0, 1, 2].map((i) => (<div key={i} className="w-full aspect-3/4 border shadow-md bg-white overflow-hidden"><img src={selectedStudent?.images[i] || ""} className="w-full h-full object-cover" /></div>))}</div>
            <p className="mt-8 text-sm text-slate-400 italic font-medium">* Những câu sai AI sẽ gạch chân đỏ để GV dễ dàng theo dõi</p>
          </div>
        ) : activeMainTab === 'homework' ? (
          <div className="bg-white rounded-2xl border shadow-sm p-8">
            {view === 'list' ? (
              <>
                <UploadButton />
                <div className="flex space-x-8 mb-6 mt-6 text-sm font-medium">
                  {['all', 'mandatory', 'reference'].map((t) => (<label key={t} className="flex items-center space-x-2 cursor-pointer"><input type="radio" checked={filter === t} onChange={() => setFilter(t)} className="accent-[#4f46e5]"/><span>{t==='all'?'Tất cả':t==='mandatory'?'Bài tập bắt buộc':'Bài tập tham khảo'}</span></label>))}
                </div>
                <div className="border border-slate-200 rounded-xl overflow-hidden shadow-sm"><table className="w-full text-left text-sm"><thead className="bg-[#e0f2fe] text-slate-700 font-bold text-center"><tr><th className="p-4 border-b">Unit</th><th className="p-4 border-b">Bài Tập</th><th className="p-4 border-b">Dạng bài tập</th><th className="p-4 border-b">Deadline</th><th className="p-4 border-b">Chi tiết</th><th className="p-4 border-b">Tình trạng nộp bài</th></tr></thead><tbody>{homeworkList.filter(it => filter === 'all' || it.typeKey === filter).map((item) => (<tr key={item.id} className="border-b border-slate-100 text-center hover:bg-slate-50 transition-colors"><td className="p-4 font-bold border-r border-slate-100 w-24 text-slate-800">{item.unit}</td><td className="p-4 font-medium text-blue-900">{item.title}</td><td className={`p-4 font-bold ${item.color}`}>{item.type}</td><td className="p-4 text-slate-500">{item.deadline}</td><td className="p-4 relative"><button onClick={() => { setActiveHW(item); setView('detail'); }} className="text-blue-600 underline font-medium hover:text-blue-800 cursor-pointer">Bấm vào để xem</button><span className="absolute top-2 right-4 bg-red-500 text-white text-[9px] w-4 h-4 flex items-center justify-center rounded-full shadow-sm">3</span></td><td className="p-4 text-slate-500 font-bold">4/40 Học sinh</td></tr>))}</tbody></table></div>
              </>
            ) : (
              <div className="animate-in fade-in duration-500"><button onClick={() => setView('list')} className="mb-4 text-sm text-blue-600 font-medium hover:underline flex items-center">← Quay lại danh sách bài tập</button><h2 className="text-[13px] font-bold text-slate-800 mb-6 leading-relaxed">{activeHW?.fullTitle}</h2><div className="border border-slate-200 rounded-xl overflow-hidden bg-white shadow-sm"><table className="w-full text-left text-[12px]"><thead className="bg-[#e0f2fe] text-gray-700 font-bold text-center"><tr><th className="p-3 border-b border-r border-slate-100 w-12">STT</th><th className="p-3 border-b border-r border-slate-100 w-40">Học sinh</th><th className="p-3 border-b border-r border-slate-100 w-28">Thời gian nộp bài</th><th className="p-3 border-b border-r border-slate-100">Nhận xét</th><th className="p-3 border-b border-r border-slate-100 w-16 text-center">Chi tiết</th><th className="p-3 border-b border-slate-100 w-56">Bài tập được đề xuất thêm</th></tr></thead><tbody>{students.map((s) => (<tr key={s.stt} onClick={() => !viewedStudentIds.includes(s.stt) && setViewedStudentIds([...viewedStudentIds, s.stt])} className={`border-b border-slate-100 cursor-pointer transition-colors duration-300 ${viewedStudentIds.includes(s.stt) ? 'bg-white' : 'bg-[#f3f4f6]'}`}><td className="p-3 text-center font-bold border-r border-slate-100 text-slate-800">{s.stt}</td><td className="p-3 font-bold border-r border-slate-100 text-slate-700">{s.name}</td><td className="p-3 text-center border-r border-slate-100 text-slate-500 font-medium">{s.stt === 1 ? 'Jan 4, 2026' : 'Jan 8, 2026'}</td><td className="p-3 border-r italic text-slate-600 leading-relaxed">{s.comment}</td><td className="p-3 border-r border-slate-100 text-center"><div onClick={(e) => { e.stopPropagation(); openImageGallery(s); }} className="w-8 h-10 mx-auto border border-slate-200 bg-white shadow-sm overflow-hidden cursor-pointer hover:ring-2 hover:ring-blue-400 transition-all"><img src={s.images[0]} className="w-full h-full object-cover" /></div></td><td className="p-3 font-medium text-slate-700">{s.stt === 4 ? "Blook" : activeHW?.fullTitle.replace(".docx", "")}</td></tr>))}</tbody></table></div></div>
            )}
          </div>
        ) : (
          <div className="bg-white rounded-2xl border shadow-sm overflow-hidden min-h-137.5">
            <div className="flex justify-center space-x-12 bg-slate-50/50 border-b p-4 border-slate-200">
              <button onClick={() => setActiveSubTab('unit')} className={`pb-2 font-bold text-sm border-b-2 transition-all ${activeSubTab === 'unit' ? 'border-[#4f46e5] text-[#4f46e5]' : 'border-transparent text-slate-400'}`}>Báo cáo Unit</button>
              <button onClick={() => setActiveSubTab('process')} className={`pb-2 font-bold text-sm border-b-2 transition-all ${activeSubTab === 'process' ? 'border-[#4f46e5] text-[#4f46e5]' : 'border-transparent text-slate-400'}`}>Báo cáo tiến trình</button>
            </div>
            
            {activeSubTab === 'unit' ? (
               reportView === 'select' ? (
                <div className="p-10 flex space-x-6 items-end animate-in fade-in duration-500">
                  <div className="flex-1"><label className="block text-[11px] font-bold mb-2 text-slate-500">🔍 Tên học sinh</label><select className="w-full p-3 border border-slate-200 rounded-xl bg-white text-sm"><option>Cấn Trần Quang Bách</option></select></div>
                  <div className="flex-1"><label className="block text-[11px] font-bold mb-2 text-slate-500">🔍 Unit</label><select className="w-full p-3 border border-slate-200 rounded-xl bg-white text-sm"><option>Unit 9 : Addition and subtraction of fractions</option></select></div>
                  <button onClick={() => setReportView('result')} className="bg-[#1e3a8a] text-white px-10 py-3 rounded-xl font-bold hover:bg-blue-900 shadow-md">Progress</button>
                </div>
              ) : reportView === 'result' ? (
                <div className="p-6 animate-in slide-in-from-right duration-500">
                  <div className="flex items-center space-x-4 mb-6"><button onClick={() => setReportView('select')} className="text-2xl font-bold">❮</button><h2 className="text-xl font-bold text-slate-800">Báo cáo Unit 9 - Học sinh Cấn Trần Quang Bách VS081559</h2></div>
                  <div className="border border-slate-300 rounded-xl overflow-hidden bg-white shadow-sm"><table className="w-full text-left text-[12px] border-collapse"><thead className="bg-slate-50 border-b border-slate-300 font-bold"><tr><th className="p-3 border-r border-slate-300 w-20 text-center">UNIT</th><th className="p-3 border-r border-slate-300">NHẬN XÉT TÌNH HÌNH CHUNG</th><th className="p-3">BÀI TẬP</th></tr></thead>
                    <tbody><tr className="align-top"><td className="p-5 border-r border-slate-300 font-bold text-center text-slate-600">Unit 9</td>
                        <td className="p-5 border-r border-slate-300 space-y-4 text-slate-700 leading-relaxed">
                          <p><strong>1. Nhận diện phân số trên sơ đồ:</strong> Học sinh hiểu tốt ý nghĩa phân số qua hình ảnh minh họa, xác định đúng phần của một tổng thể.</p>
                          <p><strong>2. Tìm phân số tương đương:</strong> Biết cách quy đổi phân số về cùng mẫu số, tuy nhiên đôi lúc còn nhầm lẫn khi kết luận hoặc rút gọn.</p>
                          <p><strong>3. So sánh và sắp xếp thứ tự phân số:</strong> So sánh phân số chính xác, nhận biết được phân số bằng nhau và phân số lớn - bé.</p>
                          <p><strong>4. Cộng/Trừ phân số cùng mẫu:</strong> Thực hiện đúng quy tắc cộng trừ, cần cẩn thận hơn để tránh sai sót ở kết quả cuối.</p>
                          <p><strong>5. Giải toán đố về phân số:</strong> Hiểu đề và lựa chọn đúng phép tính, có khả năng trình bày lời giải nhưng cần kiểm tra lại kết quả.</p>
                          <div className="mt-4 pt-4 border-t border-slate-100"><p><strong>Nhận xét chung:</strong> Hoàn thành tốt yêu cầu bài học. Cần rèn luyện việc kiểm tra lại kết quả sau khi làm xong.</p><p><strong>Bài tập gợi ý làm thêm:</strong> Dạng cộng trừ phân số khác mẫu số.</p></div>
                        </td><td className="p-5"><div className="flex justify-between items-start"><p className="text-slate-600">Hoàn thành bài tập về nhà. Có 5 lỗi sai nhỏ liên quan tới cộng/trừ và so sánh phân số.</p><button onClick={() => setReportView('detail')} className="text-blue-600 underline text-[11px] whitespace-nowrap ml-4 font-bold cursor-pointer">&lt;Chi tiết&gt;</button></div></td></tr></tbody></table></div>
                </div>
              ) : (
                <div className="p-6 animate-in slide-in-from-bottom duration-500"><div className="flex items-center space-x-4 mb-6"><button onClick={() => setReportView('result')} className="text-2xl font-bold">❮</button><h2 className="text-xl font-bold text-slate-800">Chi tiết bài tập Unit 9 - Cấn Trần Quang Bách</h2></div>
                  <div className="border border-slate-300 rounded-lg overflow-hidden bg-white shadow-sm"><table className="w-full text-left text-[12px]"><thead className="bg-[#e0f2fe] border-b border-slate-300 font-bold text-gray-700 text-center"><tr><th className="p-3 border-r border-slate-200 w-12">STT</th><th className="p-3 border-r border-slate-200">Bài tập</th><th className="p-3 border-r border-slate-200 w-32">Deadline</th><th className="p-3 border-r border-slate-200 w-32">Thời gian nộp bài</th><th className="p-3 border-r border-slate-200">Nhận xét</th><th className="p-3 w-16 text-center">Chi tiết</th></tr></thead><tbody>{progressAssignments.map((pa) => (<tr key={pa.stt} className="border-b border-slate-100 hover:bg-slate-50 transition-colors"><td className="p-4 text-center border-r border-slate-200 font-bold">{pa.stt}</td><td className="p-4 border-r border-slate-200 font-medium">{pa.title}</td><td className={`p-4 text-center border-r border-slate-200 font-bold ${pa.status==='late'?'text-red-500':'text-green-600'}`}>{pa.deadline||"-"}</td><td className={`p-4 text-center border-r border-slate-200 font-bold ${pa.status==='late'?'text-red-500':'text-green-600'}`}>{pa.subTime}</td><td className="p-4 border-r border-slate-200 italic text-slate-500">-</td><td className="p-4 text-center"><div onClick={() => { setSelectedStudent(students[0]); setActiveHW({ fullTitle: `Unit 9: ${pa.title}` }); setView('images'); }} className="w-8 h-10 mx-auto border border-slate-200 bg-white shadow-sm overflow-hidden flex items-center justify-center cursor-pointer hover:ring-2 hover:ring-blue-400 transition-all"><img src="/BaiTapHS1_Demo.jpg" className="w-full h-full object-cover" /></div></td></tr>))}</tbody></table></div>
                </div>
              )
            ) : (
              /* --- PHẦN BÁO CÁO TIẾN TRÌNH (ẢNH 1 & ẢNH 2) --- */
              processView === 'select' ? (
                <div className="p-10 flex space-x-6 items-end animate-in fade-in duration-500">
                  <div className="flex-1"><label className="text-[11px] font-bold mb-2 text-slate-500 flex items-center"><span className="mr-1">🔍</span> Tên học sinh</label><select className="w-full p-3 border border-slate-200 rounded-xl bg-white text-sm outline-none"><option>Cấn Trần Quang Bách</option><option>Phạm Liên Hoa</option></select></div>
                  <div className="flex-1"><label className="text-[11px] font-bold mb-2 text-slate-500 flex items-center"><span className="mr-1">🔍</span> Giai đoạn đánh giá</label><select className="w-full p-3 border border-slate-200 rounded-xl bg-white text-sm outline-none"><option>Giữa học kì I</option><option>Cuối học kì I</option></select></div>
                  <button onClick={() => setProcessView('result')} className="bg-[#1e3a8a] text-white px-10 py-3 rounded-xl font-bold hover:bg-blue-900 transition-all shadow-md active:scale-95">Progress</button>
                </div>
              ) : (
                <div className="p-6 animate-in slide-in-from-right duration-500">
                  <div className="flex items-center space-x-4 mb-6"><button onClick={() => setProcessView('select')} className="text-2xl font-bold">❮</button><h2 className="text-xl font-bold text-slate-800 italic">Báo cáo cuối học kì I - Học sinh Cấn Trần Quang Bách VS081559</h2></div>
                  <div className="border border-slate-300 rounded-xl overflow-hidden bg-white shadow-sm mb-6"><table className="w-full text-left text-[12px] border-collapse"><thead className="bg-[#e0f2fe] border-b border-slate-300 font-bold text-gray-700 text-center"><tr><th className="p-3 border-r border-slate-300 w-1/3">Unit</th><th className="p-3 border-r border-slate-300">0 - 2</th><th className="p-3 border-r border-slate-300">2 - 4</th><th className="p-3 border-r border-slate-300">4 - 6</th><th className="p-3 border-r border-slate-300">6 - 8</th><th className="p-3">8 - 10</th></tr></thead><tbody><tr className="border-b border-slate-200"><td className="p-4 border-r border-slate-300 font-bold text-slate-700">Unit 7: Fractions, decimals and percentages</td><td className="border-r border-slate-300"></td><td className="border-r border-slate-300"></td><td className="border-r border-slate-300"></td><td className="border-r border-slate-300"></td><td className="p-4 text-center font-bold text-blue-800 bg-blue-50/30">10</td></tr><tr className="border-b border-slate-200"><td className="p-4 border-r border-slate-300 font-bold text-slate-700">Unit 8: Probability</td><td className="border-r border-slate-300"></td><td className="border-r border-slate-300"></td><td className="border-r border-slate-300"></td><td className="border-r border-slate-300"></td><td className="p-4 text-center font-bold text-blue-800 bg-blue-50/30">10</td></tr><tr className="bg-slate-50 font-bold"><td className="p-4 border-r border-slate-300 uppercase">Progression Test</td><td colSpan={5} className="p-4 text-center text-blue-900 text-sm">9.8</td></tr></tbody></table></div>
                  
                  {/* VÙNG NHẬN XÉT: CHỈNH SỬA & DUYỆT (ẢNH 2) */}
                  <div className={`border border-slate-300 rounded-xl p-6 shadow-sm transition-colors duration-500 ${isApproved ? 'bg-green-50 border-green-200' : 'bg-white'}`}>
                    <h3 className="font-bold text-slate-800 mb-3 underline">Nhận xét chung:</h3>
                    {isEditing ? (
                      <textarea ref={commentRef} value={generalComment} onChange={(e) => setGeneralComment(e.target.value)} onBlur={() => setIsEditing(false)} className="w-full min-h-25 text-sm text-slate-700 leading-relaxed outline-none border border-blue-200 bg-white rounded p-2 focus:ring-2 focus:ring-blue-100 transition-all" />
                    ) : (
                      <p className="text-sm text-slate-700 leading-relaxed cursor-text" onClick={handleEditClick}>{generalComment}</p>
                    )}
                    <div className="flex justify-end space-x-4 mt-6">
                      <button onClick={handleEditClick} className="bg-[#1e3a8a] text-white px-8 py-2 rounded-full text-sm font-bold shadow-md hover:bg-blue-900 transition-all">Chỉnh sửa</button>
                      <button onClick={() => { setIsApproved(true); setIsEditing(false); }} className={`px-10 py-2 rounded-full text-sm font-bold shadow-md transition-all ${isApproved ? 'bg-green-600 text-white border-none' : 'bg-[#1e3a8a] text-white hover:bg-blue-900'}`}>
                        {isApproved ? 'Đã duyệt ✓' : 'Duyệt'}
                      </button>
                    </div>
                  </div>
                </div>
              )
            )}
          </div>
        )}
      </div>
    </div>
  );
}