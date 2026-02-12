import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const isLoggedIn = request.cookies.get('isLoggedIn')?.value;
  const userRole = request.cookies.get('userRole')?.value;
  const { pathname } = request.nextUrl;

  // 1. Khi người dùng vào trang gốc '/'
  if (pathname === '/') {
    if (!isLoggedIn) {
      // Nếu chưa đăng nhập, bắt buộc đẩy sang /login
      return NextResponse.redirect(new URL('/login', request.url));
    } else {
      // Nếu đã đăng nhập, đẩy về trang Home theo đúng Role
      const target = userRole === 'teacher' ? '/teacher/home' : '/student/home';
      return NextResponse.redirect(new URL(target, request.url));
    }
  }

  // 2. Nếu đã đăng nhập mà cố quay lại trang /login
  if (isLoggedIn && pathname === '/login') {
    const target = userRole === 'teacher' ? '/teacher/home' : '/student/home';
    return NextResponse.redirect(new URL(target, request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/', '/login', '/student/:path*', '/teacher/:path*'],
};