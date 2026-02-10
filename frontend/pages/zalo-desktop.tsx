"use client";
import { ZaloDesktopChat } from '../components/ai-demo/ZaloDesktopChat';

export default function DesktopPage() {
  return (
    <main className="min-h-screen bg-[#dfe2e7] flex items-center justify-center p-8">
      <div className="w-full max-w-[900px] h-[600px] bg-white shadow-2xl rounded-lg overflow-hidden flex ">
        <ZaloDesktopChat />
      </div>
    </main>
  );
}