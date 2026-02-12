"use client";
import { ZaloMobileChat } from '../components/ZaloMobileChat';

export default function MobilePage() {
  return (
    <main className="min-h-screen bg-[#b0b8c4] flex items-center justify-center p-4">
      <div className="w-full max-w-[350px] h-[600px] bg-white shadow-2xl rounded-[50px] overflow-hidden relative">
        <ZaloMobileChat />
      </div>
    </main>
  );
}