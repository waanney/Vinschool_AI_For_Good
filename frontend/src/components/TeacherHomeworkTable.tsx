'use client';

import { useState, useEffect, useRef, useCallback } from "react";
import UploadButton from "./UploadButton";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Submission {
  id: string;
  student_id: string;
  student_name: string;
  assignment_title: string;
  subject: string;
  score: number;
  max_score: number;
  feedback: string;
  attachment_paths: string[];
  details: Record<string, any>;
  graded_at: string;
  is_viewed: boolean;
}

export default function TeacherHomeworkTable({ userName }: { userName: string }) {
  // --- QUẢN LÝ ĐIỀU HỚNG ---
  const [activeMainTab, setActiveMainTab] = useState<'homework' | 'progress' | 'modules'>('homework');
  const [activeSubTab, setActiveSubTab] = useState<'unit' | 'process'>('unit');
  const [reportView, setReportView] = useState<'select' | 'result' | 'detail'>('select');

  // --- TRẠNG THÁI CHO BÁO CÁO TIẾN TRÌNH (TRANG CUỐI) ---
  const [processView, setProcessView] = useState<'select' | 'result'>('select');
  const [isApproved, setIsApproved] = useState(false);
  const [showSuccessToast, setShowSuccessToast] = useState(false); // Trạng thái hiện thông báo

  const [isEditing, setIsEditing] = useState(false);
  const [generalComment, setGeneralComment] = useState(
    "Quang Bách là một học sinh có năng lực Toán học rất tốt, đạt thành tích xuất sắc ở tất cả các Unit trong học kỳ I. Bách thành thạo trong việc phân tích và giải quyết các bài toán giải quyết vấn đề, luôn nhanh chóng xác định được các phép tính. Ở unit Hình Khối, đặc biệt là Bài 6 (3D shape), Bách thể hiện rõ khả năng phân tích và mô tả chính xác các thuộc tính của những hình khối hình học phức tạp. Con luôn làm bài cẩn thận, chính xác và thể hiện tinh thần học tập nghiêm túc, tận tâm."
  );
  const commentRef = useRef<HTMLTextAreaElement>(null);

  // --- BỔ SUNG TRẠNG THÁI CHO MỤC TIÊU HỌC KÌ TIẾP THEO ---
  const [isEditingGoal, setIsEditingGoal] = useState(false);
  const [nextSemesterGoal, setNextSemesterGoal] = useState(
    "Quang Bách cần tiếp tục rèn luyện việc sử dụng chính xác các thuật ngữ Toán học khi trình bày, đặc biệt là trong việc phân biệt và vận dụng các khái niệm liên quan đến các dãy số khác nhau (ví dụ: dãy có hiệu số không đổi và dãy có tỉ số không đổi)."
  );
  const goalRef = useRef<HTMLTextAreaElement>(null);

  // --- QUẢN LÝ VIEW BÀI TẬP ---
  const [view, setView] = useState<'list' | 'detail' | 'images'>('list');
  const [filter, setFilter] = useState('all');
  const [homeworkList, setHomeworkList] = useState<any[]>([]);
  const [selectedStudent, setSelectedStudent] = useState<any>(null);
  const [viewedStudentIds, setViewedStudentIds] = useState<number[]>([4]);
  const [activeHW, setActiveHW] = useState<any>(null);

  // --- API SUBMISSIONS (from /grade Google Chat command) ---
  const [apiSubmissions, setApiSubmissions] = useState<Submission[]>([]);
  const [unviewedCount, setUnviewedCount] = useState(0);
  const [selectedSubmission, setSelectedSubmission] = useState<Submission | null>(null);
  const [selectedStaticStudent, setSelectedStaticStudent] = useState<any>(null);

  // Poll backend for graded submissions every 5 seconds
  const fetchSubmissions = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/teacher/submissions`);
      if (res.ok) {
        const data = await res.json();
        setApiSubmissions(data.submissions || []);
        setUnviewedCount(data.unviewed_count || 0);
      }
    } catch {
      // Backend may not be running — silently ignore
    }
  }, []);

  useEffect(() => {
    fetchSubmissions();
    const interval = setInterval(fetchSubmissions, 5000);
    return () => clearInterval(interval);
  }, [fetchSubmissions]);

  const markSubmissionViewed = async (submissionId: string) => {
    try {
      await fetch(`${API_BASE}/api/teacher/submissions/${submissionId}/view`, {
        method: "POST",
      });
      fetchSubmissions(); // Refresh after marking
    } catch {
      // Silently ignore
    }
  };

  useEffect(() => {
    const defaultHW = [
      { id: 'unit9_bb', unit: 'Unit 9', title: 'Week 22 fractions math practice.pdf', fullTitle: 'Unit 9: Week 22 fractions math practice - Bài tập bắt buộc - Deadline Jan 9, 2026', type: 'Bắt buộc', typeKey: 'mandatory', deadline: 'Jan 9, 2026', color: 'text-red-500' },
      { id: 'unit9_tk', unit: 'Unit 9', title: 'Week 21 HW extension option.pdf', fullTitle: 'Unit 9: Week 21 HW extension option - Bài tập tham khảo - Deadline Jan 12, 2026', type: 'Tham khảo', typeKey: 'reference', deadline: 'Jan 12, 2026', color: 'text-blue-500' }
    ];
    setHomeworkList(defaultHW);
  }, []);

  const students = [
    { stt: 1, name: "Cấn Trần Quang Bách", score: 8.0, maxScore: 10.0, subTimeShort: "Jan 4, 2026", subTime: "15:00:00 4/1/2026", images: ["/BaiTapHS1_Demo.jpg", "/BaiTapHS2_Demo.jpg", "/BaiTapHS3_Demo.jpg"], comment: "Quang Bách đã nắm khá chắc kiến thức phần cộng trừ phân số. Tuy nhiên vẫn còn một số lỗi nằm ở phần cộng trừ và so sánh phân số.", strengths: ["Nắm vững kiến thức phần cộng trừ phân số cùng mẫu", "Biết quy đổi phân số về cùng mẫu số", "Trình bày lời giải rõ ràng, có logic"], improvements: ["Cần cẩn thận hơn ở phần so sánh phân số", "Kiểm tra lại kết quả sau khi làm xong", "Ôn tập thêm phần rút gọn phân số"] },
    { stt: 2, name: "Trần Minh Khôi", score: 7.2, maxScore: 10.0, subTimeShort: "Jan 8, 2026", subTime: "15:00:00 8/1/2026", images: ["/BaiTapHS1_Demo.jpg", "/BaiTapHS2_Demo.jpg", "/BaiTapHS3_Demo.jpg"], comment: "Minh Khôi cần ôn thêm về phần cộng/trừ phân số cùng mẫu. Bài tập làm đúng 18/25 câu.", strengths: ["Hiểu được ý nghĩa cơ bản của phân số", "Làm đúng được phần nhận diện phân số trên sơ đồ", "Có cố gắng hoàn thành đủ các câu"], improvements: ["Cần ôn luyện thêm phần cộng/trừ phân số cùng mẫu", "Chú ý quy tắc tính toán để tránh sai sót", "Rèn luyện kỹ năng rút gọn phân số"] },
    { stt: 3, name: "Phạm Bách Hợp", score: 9.2, maxScore: 10.0, subTimeShort: "Jan 8, 2026", subTime: "15:00:00 8/1/2026", images: ["/BaiTapHS1_Demo.jpg", "/BaiTapHS2_Demo.jpg", "/BaiTapHS3_Demo.jpg"], comment: "Bách Hợp đã nắm chắc kiến thức, tuy nhiên cần chú ý phần sắp xếp thứ tự phân số. Bài tập làm đúng 23/25 câu.", strengths: ["Nắm chắc kiến thức về phân số", "Thực hiện tốt phần cộng trừ phân số", "Bài làm cẩn thận, trình bày rõ ràng"], improvements: ["Cần chú ý hơn ở phần sắp xếp thứ tự phân số", "Kiểm tra lại 2 câu còn sai trước khi nộp bài"] },
    { stt: 4, name: "Nguyễn Hải Anh", score: 10.0, maxScore: 10.0, subTimeShort: "Jan 8, 2026", subTime: "15:00:00 8/1/2026", images: ["/BaiTapHA1_Demo.jpg", "/BaiTapHA2_Demo.jpg", "/BaiTapHA3_Demo.jpg"], comment: "Hải Anh nắm kiến thức rất chắc. Bài tập làm đúng 100%.", strengths: ["Nắm vững toàn bộ kiến thức về phân số", "Làm đúng 100% các câu hỏi", "Trình bày lời giải logic, chính xác", "Thể hiện kỹ năng tư duy toán học xuất sắc"], improvements: ["Có thể thử sức với các bài tập nâng cao về phân số khác mẫu"] }
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

  const handleEditGoalClick = () => {
    setIsEditingGoal(true);
    setTimeout(() => goalRef.current?.focus(), 10);
  };

  return (
    <div className="flex flex-col w-full min-h-screen bg-slate-50/30 font-sans relative">

      {/* --- THÔNG BÁO KHI BẤM DUYỆT --- */}
      {showSuccessToast && (
        <div className="fixed top-10 left-1/2 -translate-x-1/2 z-100 bg-green-600 text-white px-8 py-4 rounded-2xl shadow-2xl font-bold animate-in slide-in-from-top duration-500">
          Báo cáo đã được duyệt và đẩy lên hệ thống để gửi tới tài khoản Phụ huynh
        </div>
      )}

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
        <span
          onClick={() => { setActiveMainTab('modules'); setView('list'); }}
          className={`px-4 py-1.5 rounded-full cursor-pointer transition-all ${activeMainTab === 'modules' ? 'bg-[#4f46e5] text-white shadow-md' : 'hover:bg-slate-100'}`}
        >
          Các học phần
        </span>
        <span onClick={() => { setActiveMainTab('homework'); setView('list'); }} className={`px-4 py-1.5 rounded-full cursor-pointer relative transition-all ${activeMainTab === 'homework' && view !== 'images' ? 'bg-[#4f46e5] text-white shadow-md' : 'hover:bg-slate-100'}`}>
          Bài tập học sinh {(unviewedCount + 2) > 0 && <span className="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] w-4 h-4 flex items-center justify-center rounded-full border border-white">{unviewedCount + 2}</span>}
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
        ) : activeMainTab === 'modules' ? (
          <div className="bg-white rounded-2xl border shadow-sm p-8 animate-in fade-in duration-500">
            <h2 className="bg-[#1e3a8a] text-white text-lg font-bold p-3 mb-6 text-center rounded uppercase tracking-wider">
              {"<4B5> - <Math> - <JEMRO1-TiH.GB>"}
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse border border-slate-400 text-sm">
                <thead className="bg-[#f1f5f9] font-bold">
                  <tr>
                    <th className="border border-slate-400 p-2 text-left w-1/2">Nội dung</th>
                    <th className="border border-slate-400 p-2 text-left">File</th>
                    <th className="border border-slate-400 p-2 text-center w-32">Deadline</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="bg-slate-200 font-bold"><td colSpan={3} className="border border-slate-400 p-2 text-slate-800">Tuần 21</td></tr>
                  <tr className="bg-white font-bold"><td colSpan={3} className="border border-slate-400 p-2">1. Nội dung học tập</td></tr>
                  <tr>
                    <td className="border border-slate-400 p-2 pl-10 text-slate-600 italic">Lesson Plan_ Unit 9</td>
                    <td className="border border-slate-400 p-2 flex items-center gap-2"><span className="text-blue-500 text-base">📄</span> <span className="text-slate-500">Lesson Plan_ Unit 9</span></td>
                    <td className="border border-slate-400 p-2"></td>
                  </tr>
                  <tr>
                    <td className="border border-slate-400 p-2 pl-10 text-slate-600 italic">9.1 addition & subtraction of fractions</td>
                    <td className="border border-slate-400 p-2 flex items-center gap-2"><span className="text-red-500 text-base">📝</span> <span className="text-slate-500">9.1 addition & subtraction of fractions</span></td>
                    <td className="border border-slate-400 p-2"></td>
                  </tr>
                  <tr className="bg-white font-bold"><td colSpan={3} className="border border-slate-400 p-2">2. Bài tập bắt buộc</td></tr>
                  <tr>
                    <td className="border border-slate-400 p-2 text-slate-600">Bài tập bắt buộc_ Week 22 fractions math practice and answer key. Deadline 23/1/2026</td>
                    <td className="border border-slate-400 p-2 text-blue-600 underline">
                      <a href="/BaiTapBB_Demo.pdf" className="hover:text-blue-800">Bài tập bắt buộc_ Week 22 fractions math practice an...</a>
                    </td>
                    <td className="border border-slate-400 p-2 text-center font-medium">28/1/2026</td>
                  </tr>
                  <tr className="bg-white font-bold"><td colSpan={3} className="border border-slate-400 p-2">3. Tài liệu thêm</td></tr>
                  <tr>
                    <td className="border border-slate-400 p-2 text-slate-600 italic">Understanding Fractions, Improper Fractions, and Mixed Numbers</td>
                    <td className="border border-slate-400 p-2 text-blue-600 underline cursor-pointer">Understanding Fractions, Improper Fraction...</td>
                    <td className="border border-slate-400 p-2"></td>
                  </tr>
                  <tr className="bg-white font-bold"><td colSpan={3} className="border border-slate-400 p-2">4. Bài tập tham khảo</td></tr>
                  <tr>
                    <td className="border border-slate-400 p-2 pl-10 text-slate-600 italic">Week 21 HW extension option.pdf</td>
                    <td className="border border-slate-400 p-2 flex items-center gap-2"><span className="text-gray-400 text-base">📎</span> <span className="text-slate-500">Week 21 WS Maths Esl.pdf</span></td>
                    <td className="border border-slate-400 p-2"></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        ) : activeMainTab === 'homework' ? (
          <div className="bg-white rounded-2xl border shadow-sm p-8">
            {view === 'list' ? (
              <>
                <UploadButton />
                <div className="flex space-x-8 mb-6 mt-6 text-sm font-medium">
                  {['all', 'mandatory', 'reference'].map((t) => (<label key={t} className="flex items-center space-x-2 cursor-pointer"><input type="radio" checked={filter === t} onChange={() => setFilter(t)} className="accent-[#4f46e5]" /><span>{t === 'all' ? 'Tất cả' : t === 'mandatory' ? 'Bài tập bắt buộc' : 'Bài tập tham khảo'}</span></label>))}
                </div>
                <div className="border border-slate-200 rounded-xl overflow-hidden shadow-sm"><table className="w-full text-left text-sm"><thead className="bg-[#e0f2fe] text-slate-700 font-bold text-center"><tr><th className="p-4 border-b">Unit</th><th className="p-4 border-b">Bài Tập</th><th className="p-4 border-b">Dạng bài tập</th><th className="p-4 border-b">Deadline</th><th className="p-4 border-b">Chi tiết</th><th className="p-4 border-b">Tình trạng nộp bài</th></tr></thead><tbody>{homeworkList.filter(it => filter === 'all' || it.typeKey === filter).map((item) => { const unviewedStaticCount = students.filter(s => !viewedStudentIds.includes(s.stt)).length; const unviewedApiCount = apiSubmissions.filter(sub => !sub.is_viewed).length; const totalUnviewed = unviewedStaticCount + unviewedApiCount; return (<tr key={item.id} className="border-b border-slate-100 text-center hover:bg-slate-50 transition-colors"><td className="p-4 font-bold border-r border-slate-100 w-24 text-slate-800">{item.unit}</td><td className="p-4 font-medium text-blue-900">{item.title}</td><td className={`p-4 font-bold ${item.color}`}>{item.type}</td><td className="p-4 text-slate-500">{item.deadline}</td><td className="p-4 relative"><button onClick={() => { setActiveHW(item); setView('detail'); }} className="text-blue-600 underline font-medium hover:text-blue-800 cursor-pointer">Bấm vào để xem</button>{totalUnviewed > 0 && <span className="absolute top-2 right-4 bg-red-500 text-white text-[9px] w-4 h-4 flex items-center justify-center rounded-full shadow-sm">{totalUnviewed}</span>}</td><td className="p-4 text-slate-500 font-bold">4/40 Học sinh</td></tr>); })}</tbody></table></div>
              </>
            ) : (
              <>
                <div className="animate-in fade-in duration-500"><button onClick={() => setView('list')} className="mb-4 text-sm text-blue-600 font-medium hover:underline flex items-center">← Quay lại danh sách bài tập</button><h2 className="text-[13px] font-bold text-slate-800 mb-6 leading-relaxed">{activeHW?.fullTitle}</h2><div className="border border-slate-200 rounded-xl overflow-hidden bg-white shadow-sm"><table className="w-full text-left text-[12px]"><thead className="bg-[#e0f2fe] text-gray-700 font-bold text-center"><tr><th className="p-3 border-b border-r border-slate-100 w-12">STT</th><th className="p-3 border-b border-r border-slate-100 w-40">Học sinh</th><th className="p-3 border-b border-r border-slate-100 w-20">Điểm</th><th className="p-3 border-b border-r border-slate-100 w-28">Thời gian nộp bài</th><th className="p-3 border-b border-r border-slate-100">Nhận xét</th><th className="p-3 border-b border-r border-slate-100 w-16 text-center">Chi tiết</th><th className="p-3 border-b border-slate-100 w-56">Bài tập được đề xuất thêm</th></tr></thead><tbody>{/* === AI-graded submissions from /grade Google Chat command — hiển thị TRƯỚC === */}{apiSubmissions.map((sub, idx) => (<tr key={sub.id} onClick={() => { if (!sub.is_viewed) markSubmissionViewed(sub.id); }} className={`border-b border-slate-100 cursor-pointer transition-colors duration-300 ${sub.is_viewed ? 'bg-white' : 'bg-[#f3f4f6]'}`}><td className="p-3 text-center font-bold border-r border-slate-100 text-slate-800">{idx + 1}</td><td className="p-3 font-bold border-r border-slate-100 text-slate-700">{sub.student_name}</td><td className={`p-3 text-center border-r border-slate-100 font-bold ${sub.score < 5 ? 'text-red-500' : sub.score >= 7 ? 'text-green-600' : 'text-orange-500'}`}>{sub.score.toFixed(1)}/{sub.max_score.toFixed(1)}</td><td className="p-3 text-center border-r border-slate-100 text-slate-500 font-medium">{new Date(sub.graded_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</td><td className="p-3 border-r italic text-slate-600 leading-relaxed">{sub.feedback || '-'}</td><td className="p-3 border-r border-slate-100 text-center">{sub.attachment_paths && sub.attachment_paths.length > 0 ? (<div onClick={(e) => { e.stopPropagation(); setSelectedSubmission(sub); }} className="w-8 h-10 mx-auto border border-slate-200 bg-white shadow-sm overflow-hidden cursor-pointer hover:ring-2 hover:ring-blue-400 transition-all"><img src={`${API_BASE}/uploads/${sub.attachment_paths[0].split(/[/\\]/).pop()}`} className="w-full h-full object-cover" onError={(e) => { (e.target as HTMLImageElement).src = '/BaiTapHS1_Demo.jpg'; }} /></div>) : (<button onClick={(e) => { e.stopPropagation(); setSelectedSubmission(sub); }} className="text-blue-600 underline text-[11px] font-medium hover:text-blue-800">Xem bài</button>)}</td><td className="p-3 font-medium text-slate-700">{'-'}</td></tr>))}{students.map((s) => (<tr key={s.stt} onClick={() => !viewedStudentIds.includes(s.stt) && setViewedStudentIds([...viewedStudentIds, s.stt])} className={`border-b border-slate-100 cursor-pointer transition-colors duration-300 ${viewedStudentIds.includes(s.stt) ? 'bg-white' : 'bg-[#f3f4f6]'}`}><td className="p-3 text-center font-bold border-r border-slate-100 text-slate-800">{apiSubmissions.length + s.stt}</td><td className="p-3 font-bold border-r border-slate-100 text-slate-700">{s.name}</td><td className={`p-3 text-center border-r border-slate-100 font-bold ${s.score < 5 ? 'text-red-500' : s.score >= 7 ? 'text-green-600' : 'text-orange-500'}`}>{s.score.toFixed(1)}/{s.maxScore.toFixed(1)}</td><td className="p-3 text-center border-r border-slate-100 text-slate-500 font-medium">{s.subTimeShort}</td><td className="p-3 border-r italic text-slate-600 leading-relaxed">{s.comment}</td><td className="p-3 border-r border-slate-100 text-center"><div onClick={(e) => { e.stopPropagation(); setSelectedStaticStudent(s); }} className="w-8 h-10 mx-auto border border-slate-200 bg-white shadow-sm overflow-hidden cursor-pointer hover:ring-2 hover:ring-blue-400 transition-all"><img src={s.images[0]} className="w-full h-full object-cover" /></div></td><td className="p-3 font-medium text-slate-700">{s.stt === 4 ? "Blook" : activeHW?.fullTitle.replace(".docx", "")}</td></tr>))}</tbody></table></div></div>
                {/* === Submission Detail Modal (API) === */}
                {selectedSubmission && (
                  <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setSelectedSubmission(null)}>
                    <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6" onClick={(e) => e.stopPropagation()}>
                      <div className="flex justify-between items-center mb-4">
                        <h3 className="text-lg font-bold text-slate-800">Chi tiết bài nộp - {selectedSubmission.student_name}</h3>
                        <button onClick={() => setSelectedSubmission(null)} className="text-slate-400 hover:text-slate-600 text-2xl font-light">&times;</button>
                      </div>
                      <div className="grid grid-cols-2 gap-3 mb-4 text-sm">
                        <div className="bg-slate-50 rounded-lg p-3"><span className="text-slate-500">Điểm:</span> <span className={`font-bold ${selectedSubmission.score < 5 ? 'text-red-500' : selectedSubmission.score >= 7 ? 'text-green-600' : 'text-orange-500'}`}>{selectedSubmission.score.toFixed(1)}/{selectedSubmission.max_score.toFixed(1)}</span></div>
                        <div className="bg-slate-50 rounded-lg p-3"><span className="text-slate-500">Thời gian:</span> <span className="font-medium">{new Date(selectedSubmission.graded_at).toLocaleString('vi-VN')}</span></div>
                      </div>
                      {selectedSubmission.feedback && <div className="mb-4"><h4 className="text-sm font-bold text-slate-700 mb-2">Nhận xét:</h4><p className="text-sm text-slate-600 bg-blue-50 rounded-lg p-3 leading-relaxed">{selectedSubmission.feedback}</p></div>}
                      {(selectedSubmission.details?.strengths || []).length > 0 && <div className="mb-4"><h4 className="text-sm font-bold text-green-700 mb-2">Điểm mạnh:</h4><ul className="text-sm text-slate-600 space-y-1">{selectedSubmission.details.strengths.map((s: string, i: number) => <li key={i} className="bg-green-50 rounded-lg px-3 py-2">✓ {s}</li>)}</ul></div>}
                      {(selectedSubmission.details?.improvements || []).length > 0 && <div className="mb-4"><h4 className="text-sm font-bold text-orange-600 mb-2">Cần cải thiện:</h4><ul className="text-sm text-slate-600 space-y-1">{selectedSubmission.details.improvements.map((s: string, i: number) => <li key={i} className="bg-orange-50 rounded-lg px-3 py-2">→ {s}</li>)}</ul></div>}
                      {selectedSubmission.attachment_paths && selectedSubmission.attachment_paths.length > 0 && <div><h4 className="text-sm font-bold text-slate-700 mb-2">Ảnh bài tập đã nộp:</h4><div className="grid grid-cols-3 gap-4">{selectedSubmission.attachment_paths.map((p: string, i: number) => <div key={i} className="w-full aspect-[3/4] border shadow-md bg-white overflow-hidden"><img src={`${API_BASE}/uploads/${p.split(/[/\\]/).pop()}`} className="w-full h-full object-cover" onError={(e) => { (e.target as HTMLImageElement).src = '/BaiTapHS1_Demo.jpg'; }} /></div>)}</div></div>}
                    </div>
                  </div>
                )}
                {/* === Static Student Detail Modal === */}
                {selectedStaticStudent && (
                  <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setSelectedStaticStudent(null)}>
                    <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6" onClick={(e) => e.stopPropagation()}>
                      <div className="flex justify-between items-center mb-4">
                        <h3 className="text-lg font-bold text-slate-800">Chi tiết bài nộp - {selectedStaticStudent.name}</h3>
                        <button onClick={() => setSelectedStaticStudent(null)} className="text-slate-400 hover:text-slate-600 text-2xl font-light">&times;</button>
                      </div>
                      <div className="grid grid-cols-2 gap-3 mb-4 text-sm">
                        <div className="bg-slate-50 rounded-lg p-3"><span className="text-slate-500">Điểm:</span> <span className={`font-bold ${selectedStaticStudent.score < 5 ? 'text-red-500' : selectedStaticStudent.score >= 7 ? 'text-green-600' : 'text-orange-500'}`}>{selectedStaticStudent.score.toFixed(1)}/{selectedStaticStudent.maxScore.toFixed(1)}</span></div>
                        <div className="bg-slate-50 rounded-lg p-3"><span className="text-slate-500">Thời gian:</span> <span className="font-medium">{selectedStaticStudent.subTime}</span></div>
                      </div>
                      <div className="mb-4"><h4 className="text-sm font-bold text-slate-700 mb-2">Nhận xét:</h4><p className="text-sm text-slate-600 bg-blue-50 rounded-lg p-3 leading-relaxed">{selectedStaticStudent.comment}</p></div>
                      {selectedStaticStudent.strengths.length > 0 && <div className="mb-4"><h4 className="text-sm font-bold text-green-700 mb-2">Điểm mạnh:</h4><ul className="text-sm text-slate-600 space-y-1">{selectedStaticStudent.strengths.map((s: string, i: number) => <li key={i} className="bg-green-50 rounded-lg px-3 py-2">✓ {s}</li>)}</ul></div>}
                      {selectedStaticStudent.improvements.length > 0 && <div className="mb-4"><h4 className="text-sm font-bold text-orange-600 mb-2">Cần cải thiện:</h4><ul className="text-sm text-slate-600 space-y-1">{selectedStaticStudent.improvements.map((s: string, i: number) => <li key={i} className="bg-orange-50 rounded-lg px-3 py-2">→ {s}</li>)}</ul></div>}
                      <div><h4 className="text-sm font-bold text-slate-700 mb-2">Ảnh bài tập đã nộp:</h4><div className="grid grid-cols-3 gap-4">{selectedStaticStudent.images.map((img: string, i: number) => <div key={i} className="w-full aspect-[3/4] border shadow-md bg-white overflow-hidden"><img src={img} className="w-full h-full object-cover" /></div>)}</div></div>
                    </div>
                  </div>
                )}
              </>
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
                  <div className="flex-1"><label className="block text-[11px] font-bold mb-2 text-slate-500">🔍 Tên học sinh</label><select className="w-full p-3 border border-slate-200 rounded-xl bg-white text-sm outline-none"><option>Cấn Trần Quang Bách</option></select></div>
                  <div className="flex-1"><label className="block text-[11px] font-bold mb-2 text-slate-500">🔍 Unit</label><select className="w-full p-3 border border-slate-200 rounded-xl bg-white text-sm outline-none"><option>Unit 9 : Addition and subtraction of fractions</option></select></div>
                  <button onClick={() => setReportView('result')} className="bg-[#1e3a8a] text-white px-10 py-3 rounded-xl font-bold hover:bg-blue-900 shadow-md">Progress</button>
                </div>
              ) : reportView === 'result' ? (
                <div className="p-6 animate-in slide-in-from-right duration-500">
                  <div className="flex items-center space-x-4 mb-6"><button onClick={() => setReportView('select')} className="text-2xl font-bold hover:text-blue-700 transition-colors">❮</button><h2 className="text-xl font-bold text-slate-800">Báo cáo Unit 9 - Học sinh Cấn Trần Quang Bách VS081559</h2></div>
                  <div className="border border-slate-300 rounded-xl overflow-hidden bg-white shadow-sm">
                    <table className="w-full text-left text-[12px] border-collapse">
                      <thead className="bg-slate-50 border-b border-slate-300 font-bold"><tr><th className="p-3 border-r border-slate-300 w-20 text-center">UNIT</th><th className="p-3 border-r border-slate-300">NHẬN XÉT TÌNH HÌNH CHUNG</th><th className="p-3">BÀI TẬP</th></tr></thead>
                      <tbody>
                        <tr className="align-top">
                          <td className="p-5 border-r border-slate-300 font-bold text-center text-slate-600">Unit 9</td>
                          <td className="p-5 border-r border-slate-300 space-y-4 text-slate-700 leading-relaxed">
                            <p><strong>1. Nhận diện phân số trên sơ đồ:</strong> Học sinh hiểu tốt ý nghĩa phân số qua hình ảnh minh họa, xác định đúng phần của một tổng thể.</p>
                            <p><strong>2. Tìm phân số tương đương:</strong> Biết cách quy đổi phân số về cùng mẫu số, tuy nhiên đôi lúc còn nhầm lẫn khi kết luận hoặc rút gọn.</p>
                            <p><strong>3. So sánh và sắp xếp thứ tự phân số:</strong> So sánh phân số chính xác, nhận biết được phân số bằng nhau và phân số lớn - bé.</p>
                            <p><strong>4. Cộng/Trừ phân số cùng mẫu:</strong> Thực hiện đúng quy tắc cộng trừ, cần cẩn thận hơn để tránh sai sót ở kết quả cuối.</p>
                            <p><strong>5. Giải toán đố về phân số:</strong> Hiểu đề và lựa chọn đúng phép tính, có khả năng trình bày lời giải nhưng cần kiểm tra lại kết quả.</p>
                            <div className="mt-4 pt-4 border-t border-slate-100">
                              <p><strong>Nhận xét chung:</strong> Hoàn thành tốt yêu cầu bài học. Cần rèn luyện việc kiểm tra lại kết quả sau khi làm xong.</p>
                              <p><strong>Bài tập gợi ý làm thêm:</strong> Dạng cộng trừ phân số khác mẫu số.</p>
                            </div>
                          </td>
                          <td className="p-5">
                            <div className="flex justify-between items-start">
                              <p className="text-slate-600 leading-relaxed italic">Hoàn thành bài tập về nhà. Có 5 lỗi sai nhỏ liên quan tới cộng/trừ và so sánh phân số.</p>
                              <button onClick={() => setReportView('detail')} className="text-blue-600 underline text-[11px] whitespace-nowrap ml-4 font-bold hover:text-blue-800 cursor-pointer">&lt;Chi tiết&gt;</button>
                            </div>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="p-6 animate-in slide-in-from-bottom duration-500"><div className="flex items-center space-x-4 mb-6"><button onClick={() => setReportView('result')} className="text-2xl font-bold">❮</button><h2 className="text-xl font-bold text-slate-800 italic">Chi tiết bài tập Unit 9 - Cấn Trần Quang Bách</h2></div><div className="border border-slate-300 rounded-lg overflow-hidden bg-white shadow-sm"><table className="w-full text-left text-[12px]"><thead className="bg-[#e0f2fe] border-b border-slate-300 font-bold text-gray-700 text-center"><tr><th className="p-3 border-r border-slate-200 w-12">STT</th><th className="p-3 border-r border-slate-200">Bài tập</th><th className="p-3 border-r border-slate-200 w-32">Deadline</th><th className="p-3 border-r border-slate-200 w-32">Thời gian nộp bài</th><th className="p-3 border-r border-slate-300">Nh nhận xét</th><th className="p-3 w-16 text-center">Chi tiết</th></tr></thead><tbody>{progressAssignments.map(pa => (<tr key={pa.stt} className="border-b border-slate-100 hover:bg-slate-50 transition-colors"><td className="p-4 text-center border-r border-slate-200 font-bold text-slate-800">{pa.stt}</td><td className="p-4 border-r border-slate-200 font-medium text-slate-700">{pa.title}</td><td className={`p-4 text-center border-r border-slate-200 font-bold ${pa.status === 'late' ? 'text-red-500' : 'text-green-600'}`}>{pa.deadline || "-"}</td><td className={`p-4 text-center border-r border-slate-200 font-bold ${pa.status === 'late' ? 'text-red-500' : 'text-green-600'}`}>{pa.subTime}</td><td className="p-4 border-r border-slate-200 italic text-slate-500 leading-relaxed">-</td><td className="p-4 text-center"><div onClick={() => { setSelectedStudent(students[0]); setActiveHW({ fullTitle: `Unit 9: ${pa.title}` }); setView('images'); }} className="w-8 h-10 mx-auto border border-slate-200 bg-white overflow-hidden cursor-pointer hover:ring-2 hover:ring-blue-400 transition-all"><img src="/BaiTapHS1_Demo.jpg" className="w-full h-full object-cover opacity-80" /></div></td></tr>))}</tbody></table></div></div>
              )
            ) : (
              /* --- BÁO CÁO TIẾN TRÌNH --- */
              processView === 'select' ? (
                <div className="p-10 flex space-x-6 items-end animate-in fade-in duration-500">
                  <div className="flex-1"><label className="flex text-[11px] font-bold mb-2 text-slate-500 items-center"><span className="mr-1">🔍</span> Tên học sinh</label><select className="w-full p-3 border border-slate-200 rounded-xl bg-white text-sm outline-none focus:ring-2 focus:ring-blue-100 transition-all"><option>Cấn Trần Quang Bách</option></select></div>
                  <div className="flex-1"><label className="flex text-[11px] font-bold mb-2 text-slate-500 items-center"><span className="mr-1">🔍</span> Giai đoạn đánh giá</label><select className="w-full p-3 border border-slate-200 rounded-xl bg-white text-sm outline-none focus:ring-2 focus:ring-blue-100 transition-all"><option>Cuối học kì I</option></select></div>
                  <button onClick={() => setProcessView('result')} className="bg-[#1e3a8a] text-white px-10 py-3 rounded-xl font-bold hover:bg-blue-900 transition-all shadow-md active:scale-95">Progress</button>
                </div>
              ) : (
                /* HIỆN XANH LÁ NHẠT CHO TOÀN BỘ PHẦN KHUNG BÁO CÁO TIẾN TRÌNH KHI ĐÃ DUYỆT */
                <div className={`p-6 animate-in slide-in-from-right duration-500 transition-colors ${isApproved ? 'bg-green-50' : ''}`}>
                  <div className="flex items-center space-x-4 mb-6"><button onClick={() => setProcessView('select')} className="text-2xl font-bold hover:text-blue-700 transition-colors">❮</button><h2 className="text-xl font-bold text-slate-800 italic">Báo cáo cuối học kì I - Học sinh Cấn Trần Quang Bách VS081559</h2></div>

                  {/* BẢNG ĐIỂM UNIT */}
                  <div className="border border-slate-300 rounded-xl overflow-hidden bg-white shadow-sm mb-6">
                    <table className="w-full text-left text-[12px] border-collapse">
                      <thead className="bg-[#e0f2fe] border-b border-slate-300 font-bold text-gray-700 text-center">
                        <tr><th className="p-3 border-r border-slate-300 w-1/3">Unit</th><th className="p-3 border-r border-slate-300">0 - 2</th><th className="p-3 border-r border-slate-300">2 - 4</th><th className="p-3 border-r border-slate-300">4 - 6</th><th className="p-3 border-r border-slate-300">6 - 8</th><th className="p-3">8 - 10</th></tr>
                      </thead>
                      <tbody>
                        <tr className="border-b border-slate-200"><td className="p-4 border-r border-slate-300 font-bold text-slate-700">Unit 7: Fractions, decimals and percentages</td><td className="border-r border-slate-300"></td><td className="border-r border-slate-300"></td><td className="border-r border-slate-300"></td><td className="border-r border-slate-300"></td><td className="p-4 text-center font-bold text-blue-800 bg-blue-50/30">10</td></tr>
                        <tr className="border-b border-slate-200"><td className="p-4 border-r border-slate-300 font-bold text-slate-700">Unit 8: Probability</td><td className="border-r border-slate-300"></td><td className="border-r border-slate-300"></td><td className="border-r border-slate-300"></td><td className="border-r border-slate-300"></td><td className="p-4 text-center font-bold text-blue-800 bg-blue-50/30">10</td></tr>
                        <tr className="bg-slate-50 font-bold"><td className="p-4 border-r border-slate-300 uppercase">Progression Test</td><td colSpan={5} className="p-4 text-center text-blue-900 text-sm">9.8</td></tr>
                      </tbody>
                    </table>
                  </div>

                  {/* NHẬN XÉT CHUNG (Bỏ background màu riêng, luôn giữ nền trắng) */}
                  <div className="border border-slate-300 rounded-xl p-6 shadow-sm bg-white mb-6">
                    <h3 className="font-bold text-slate-800 mb-3 underline">Nhận xét chung:</h3>
                    {isEditing ? (
                      <textarea ref={commentRef} value={generalComment} onChange={(e) => setGeneralComment(e.target.value)} onBlur={() => setIsEditing(false)} className="w-full min-h-25 text-sm text-slate-700 leading-relaxed outline-none border border-blue-200 bg-white rounded p-2 focus:ring-2 focus:ring-blue-100 transition-all" />
                    ) : (
                      <p className="text-sm text-slate-700 leading-relaxed cursor-text" onClick={handleEditClick}>{generalComment}</p>
                    )}
                  </div>

                  {/* --- MỚI: BIỂU ĐỒ ĐÁNH GIÁ NĂNG LỰC HỌC SINH --- */}
                  <div className="border border-slate-300 rounded-xl p-6 shadow-sm bg-white mb-6">
                    <h3 className="font-bold text-slate-800 mb-6 underline">Biểu đồ đánh giá năng lực học sinh:</h3>
                    <div className="flex flex-col lg:flex-row gap-8 items-center lg:items-start">
                      <div className="flex-1 w-full">
                        <table className="w-full text-left text-[11px] border-collapse border border-slate-300">
                          <thead className="bg-slate-50 font-bold text-center">
                            <tr><th className="p-2 border border-slate-300 w-1/4">Năng lực</th><th className="p-2 border border-slate-300 w-1/4">Mức đánh giá</th><th className="p-2 border border-slate-300">Giải thích</th></tr>
                          </thead>
                          <tbody>
                            <tr><td className="p-2 border border-slate-300 font-bold">Số học</td><td className="p-2 border border-slate-300 text-center">5 – Xuất sắc</td><td className="p-2 border border-slate-300">Tính toán nhanh, hiểu tốt về số thập phân...</td></tr>
                            <tr><td className="p-2 border border-slate-300 font-bold">Hình học & Đo lường</td><td className="p-2 border border-slate-300 text-center">5 – Xuất sắc</td><td className="p-2 border border-slate-300">Nhận diện hình 2D, 3D tốt.</td></tr>
                            <tr><td className="p-2 border border-slate-300 font-bold">Thống kê</td><td className="p-2 border border-slate-300 text-center">4.5 – Thành thạo cao</td><td className="p-2 border border-slate-300">Đọc biểu đồ rất tốt...</td></tr>
                            <tr><td className="p-2 border border-slate-300 font-bold">Đại số</td><td className="p-2 border border-slate-300 text-center">5 – Xuất sắc</td><td className="p-2 border border-slate-300">Tìm ra quy luật nhanh chóng...</td></tr>
                            <tr><td className="p-2 border border-slate-300 font-bold">Suy luận TWM</td><td className="p-2 border border-slate-300 text-center">4.5 – Thành thạo cao</td><td className="p-2 border border-slate-300">Thành thạo trong việc phân tích...</td></tr>
                          </tbody>
                        </table>
                      </div>
                      <div className="w-full lg:w-1/3 flex justify-center"><img src="/skills-chart.jpg" alt="Competency Radar" className="max-w-75 h-auto object-contain" /></div>
                    </div>
                  </div>

                  {/* --- MỚI: MỤC TIÊU CHO HỌC KÌ TIẾP THEO (Bỏ background màu riêng, luôn giữ nền trắng) --- */}
                  <div className="border border-slate-300 rounded-xl p-6 shadow-sm bg-white mb-10">
                    <h3 className="font-bold text-slate-800 mb-3 underline">Mục tiêu cho học kì tiếp theo:</h3>
                    {isEditingGoal ? (
                      <textarea ref={goalRef} value={nextSemesterGoal} onChange={(e) => setNextSemesterGoal(e.target.value)} onBlur={() => setIsEditingGoal(false)} className="w-full min-h-25 text-sm text-slate-700 leading-relaxed outline-none border border-blue-200 bg-white rounded p-2 focus:ring-2 focus:ring-blue-100 transition-all" />
                    ) : (
                      <p className="text-sm text-slate-700 leading-relaxed cursor-text" onClick={handleEditGoalClick}>{nextSemesterGoal}</p>
                    )}
                  </div>

                  {/* NÚT DUYỆT TỔNG CUỐI CÙNG */}
                  <div className="flex justify-center pb-8">
                    <button
                      onClick={() => { setIsApproved(true); setShowSuccessToast(true); setTimeout(() => setShowSuccessToast(false), 5000); }}
                      className={`px-20 py-4 rounded-full text-lg font-bold shadow-2xl transition-all ${isApproved ? 'bg-green-600 text-white cursor-default' : 'bg-[#1e3a8a] text-white hover:bg-blue-900 active:scale-95'}`}
                    >
                      {isApproved ? 'BÁO CÁO ĐÃ ĐƯỢC DUYỆT ✓' : 'DUYỆT TOÀN BỘ BÁO CÁO'}
                    </button>
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