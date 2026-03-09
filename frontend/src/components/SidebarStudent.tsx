'use client';

import { User, Home, LayoutGrid, Calendar, Mail, Clock, LogOut } from "lucide-react";
import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function Sidebar() {
  const pathname = usePathname();

  const menuItems = [
    { icon: <User size={30} />, label: "Tài khoản", href: "/student/account" },
    { icon: <Home size={30} />, label: "Trang chủ", href: "/student/home" },
    { icon: <LayoutGrid size={30} />, label: "Các chủ thể", href: "/student/dashboard" },
    { icon: <Calendar size={30} />, label: "Lịch", href: "/student/calendar" },
    { icon: <Mail size={30} />, label: "Hộp thư đến", href: "/student/inbox" },
    { icon: <Clock size={30} />, label: "Lịch sử", href: "/student/history" },
  ];

  const handleLogout = () => {
    document.cookie = "isLoggedIn=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    document.cookie = "userRole=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    document.cookie = "userName=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    window.location.href = '/login';
  };

  return (
    <aside className="w-20 h-screen bg-white border-r flex flex-col items-center py-4 space-y-6 shadow-sm">
      <Link href="/student/home" className="w-18 h-18 -full mb-2 relative overflow-hidden">
        <Image
          src="/logoVinschool.png"
          alt="Vinschool Logo"
          fill
          className="object-contain"
          priority
        />
      </Link>

      <div className="flex flex-col space-y-6 w-full">
        {menuItems.map((item, index) => {
          const isActive = pathname === item.href;
          const isDisabled = item.href === "/student/account" || item.href === "/student/calendar" || item.href === "/student/inbox" || item.href === "/student/history";

          if (isDisabled) {
            return (
              <div key={index} className="flex flex-col items-center w-full cursor-default">
                <div className="p-2 rounded-lg text-slate-500">
                  {item.icon}
                </div>
                <span className="text-[10px] font-medium text-center px-1 text-slate-500">
                  {item.label}
                </span>
              </div>
            );
          }

          return (
            <Link key={index} href={item.href} className="flex flex-col items-center group cursor-pointer w-full">
              <div
                className={`p-2 rounded-lg transition-colors ${isActive
                  ? "bg-yellow-50 text-vinschool-gold"
                  : "text-slate-500 group-hover:bg-blue-50 group-hover:text-blue-700"
                  }`}
              >
                {item.icon}
              </div>
              <span
                className={`text-[10px] font-medium text-center px-1 ${isActive ? "text-vinschool-gold" : "text-slate-500 group-hover:text-blue-700"
                  }`}
              >
                {item.label}
              </span>
            </Link>
          );
        })}
      </div>

      <button
        onClick={handleLogout}
        className="mt-auto flex flex-col items-center group cursor-pointer w-full pb-4"
      >
        <div className="p-2 rounded-lg group-hover:bg-red-50 text-slate-400 group-hover:text-red-600 transition-colors">
          <LogOut size={30} />
        </div>
        <span className="text-[10px] font-medium text-slate-400 group-hover:text-red-600">
          Thoát
        </span>
      </button>
    </aside>
  );
}