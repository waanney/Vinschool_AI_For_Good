"use client";
import { ZaloMobileChat } from '@/components/ZaloMobileChat';

export default function ZaloMobilePage() {
    return (
        <main className="h-screen bg-[#b0b8c4] flex justify-center overflow-hidden p-4">
            <div className="w-full h-full max-w-150 max-h-screen bg-white shadow-2xl rounded-[50px] overflow-hidden relative">
                <ZaloMobileChat />
            </div>
        </main>
    );
}
