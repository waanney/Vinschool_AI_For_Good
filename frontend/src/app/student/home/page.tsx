import Image from 'next/image';

export default function HomePage() {
  return (
    <div className="min-h-full flex flex-col items-center justify-center p-12 space-y-10 animate-in fade-in duration-1000">
      
      <div className="relative w-64 h-32 md:w-80 md:h-40">
        <Image 
          src="/logoVinschool.png"
          alt="Vinschool Logo" 
          fill 
          className="object-contain scale-[1.5]"
          priority
        />
      </div>

      <div className="text-center space-y-4 max-w-2xl">
        <h1 className="text-3xl md:text-4xl font-bold text-[#1e3a8a]">
          Chào mừng bạn đến với Vinschool LMS
        </h1>
        <p className="text-slate-600 text-lg leading-relaxed">
          Nơi ươm mầm tinh hoa, kết nối tri thức và phát triển tương lai. 
          Hệ thống quản lý học tập trực tuyến giúp bạn theo dõi tiến độ, 
          hoàn thành bài tập và tương tác với giáo viên một cách hiệu quả nhất.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-10 w-full max-w-5xl mt-8">
        <div className="aspect-video bg-slate-200 rounded-3xl overflow-hidden relative shadow-md border border-slate-100">
          <Image 
            src="/studyVinschool.webp"
            alt="Học sinh Vinschool 1"
            fill
            className="object-cover"
          />
        </div>

        <div className="aspect-video bg-slate-200 rounded-3xl overflow-hidden relative shadow-md border border-slate-100">
          <Image 
            src="/activityVinschool.webp"
            alt="Học sinh Vinschool 2"
            fill
            className="object-cover"
          />
        </div>
      </div>

      <div className="mt-10 pt-10 text-slate-400 text-sm italic">
        © 2026 Vinschool Education System - Demo Version
      </div>
    </div>
  );
}