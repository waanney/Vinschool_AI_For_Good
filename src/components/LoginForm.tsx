'use client';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { Globe } from 'lucide-react';

export default function LoginForm() {
  const router = useRouter();

// Hàm xử lý chung cho việc lưu Cookie và chuyển hướng
  const login = (role: string, name: string) => {
    document.cookie = `isLoggedIn=true; path=/; max-age=3600`;
    document.cookie = `userRole=${role}; path=/; max-age=3600`;
    document.cookie = `userName=${encodeURIComponent(name)}; path=/; max-age=3600`;

    if (role === 'student') {
      router.push('/student/home'); 
    } 
    else {
      router.push('/teacher/home'); 
    }

    router.refresh();
  };
  
  return (
    <div className="w-full max-w-120 p-10 md:p-12 bg-white/10 backdrop-blur-xl rounded-[20px] shadow-2xl flex flex-col items-center">
      
      <div className="w-40 h-26 relative mb-10">
        <Image
          src="/logoVinschool.png"
          alt="Vinschool Logo"
          fill
          className="object-contain scale-[1.6]"
          priority
        />
      </div>

      <div className="w-full space-y-4">
        <button 
          onClick={() => login('student', 'Alex')}
          className="w-full py-4 bg-vinschool-gold hover:bg-[#eab308] text-white font-extrabold rounded-xl shadow-lg transition-all active:scale-[0.98] uppercase tracking-wider text-[15px]"
        >
          STUDENT LOGIN
        </button>
        <button 
          onClick={() => login('teacher', 'Thầy Jem Omer')}
          className="w-full py-4 bg-[#10066a] hover:bg-[#120462] text-white font-extrabold rounded-xl shadow-lg transition-all active:scale-[0.98] uppercase tracking-wider text-[15px]">
          PRESCHOOL – TEACHERS & STAFF
        </button>
        <button 
          onClick={() => login('admin', 'Cô Lily')}
          className="w-full py-4 bg-[#10066a] hover:bg-[#120462] text-white font-extrabold rounded-xl shadow-lg transition-all active:scale-[0.98] uppercase tracking-wider text-[15px]">
          K–12 – TEACHERS & ADMINISTRATORS
        </button>
      </div>

      <div className="mt-6 flex flex-col items-center space-y-6">
        <button className="text-white/80 hover:text-white hover:underline text-s transition-colors">
          Forgot your password?
        </button>

        <div className="flex space-x-16">
          <button className="px-5 py-2 border border-white/40 text-white rounded-lg hover:bg-white/10 text-s transition-all">
            Entrance test
          </button>
          <button className="px-5 py-2 border border-white/40 text-white rounded-lg hover:bg-white/10 text-s transition-all">
            Sample Test
          </button>
        </div>

        <button className="flex items-center space-x-2 text-white border border-white/20 px-3 py-1.5 rounded-lg hover:bg-white/5 text-s">
           <Globe size={16} />
           <span>English</span>
           <span className="text-[10px]">▼</span>
        </button>
      </div>
    </div>
  );
}