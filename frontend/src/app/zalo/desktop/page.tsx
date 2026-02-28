"use client";
import { ZaloDesktopChat } from '@/components/ZaloDesktopChat';

export default function ZaloDesktopPage() {
    return (
        <main className="h-screen bg-[#dfe2e7] flex justify-center overflow-hidden">
            <div className="w-full h-screen bg-white shadow-2xl rounded-lg overflow-hidden flex">
                <ZaloDesktopChat />
            </div>
        </main>
    );
}
