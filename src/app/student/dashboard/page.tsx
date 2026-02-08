import { cookies } from "next/headers";
import HomeworkTable from "@/components/HomeworkTable";

export default async function HomeworkPage() {
  const cookieStore = await cookies();
  const userName = cookieStore.get('userName')?.value || 'Người dùng';
  const userRole = cookieStore.get('userRole')?.value;

  return (
    <div className="flex flex-col w-full">
      <header className="bg-[#1e3a8a] text-white p-6 flex justify-between items-center shadow-md">
        <div>
          <h1 className="text-xl font-bold">4B5 - Math - {userName}</h1>
          <p className="text-xs text-blue-200 opacity-80 uppercase tracking-widest mt-1">
            {'Student Dashboard'}
          </p>
        </div>
        <div className="bg-white/10 px-4 py-2 rounded-lg border border-white/20 backdrop-blur-sm">
          <span className="text-sm font-medium">Chào mừng trở lại, <span className="text-yellow-400 font-bold">{decodeURIComponent(userName)}</span>! 👋</span>
        </div>
      </header>

      <nav className="bg-white border-b px-8 py-3 flex space-x-8 text-sm font-medium text-gray-600">
        <span className="cursor-pointer">Trang chủ</span>
        <span className="cursor-pointer">Lịch trình</span>
        <span className="cursor-pointer">Các học phần</span>
        <span className="bg-[#4f46e5] text-white px-4 py-1 rounded-full cursor-pointer relative">
          Bài tập học sinh
          <span className="absolute -top-1 -right-1 bg-red-500 text-[10px] w-4 h-4 flex items-center justify-center rounded-full">2</span>
        </span>
        <span className="cursor-pointer">Báo cáo tiến bộ</span>
      </nav>

      <div className="p-6">
        <div className="bg-white rounded-2xl border shadow-sm p-6">
          <HomeworkTable />
        </div>
      </div>
    </div>
  );
}