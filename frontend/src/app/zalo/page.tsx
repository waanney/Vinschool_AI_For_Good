import Link from 'next/link';

export default function ZaloPage() {
    return (
        <main className="min-h-screen bg-gradient-to-br from-blue-50 to-blue-100 flex items-center justify-center p-8">
            <div className="bg-white rounded-2xl shadow-2xl p-12 max-w-md w-full">
                <div className="text-center mb-8">
                    <div className="w-20 h-20 bg-[#0068ff] rounded-full flex items-center justify-center text-white font-bold text-2xl mx-auto mb-4 shadow-lg">
                        AI
                    </div>
                    <h1 className="text-3xl font-bold text-gray-800 mb-2">Zalo AI Chat Demo</h1>
                    <p className="text-gray-600">Chọn giao diện để xem demo</p>
                </div>

                <div className="space-y-4">
                    <Link
                        href="/zalo/desktop"
                        className="block w-full bg-[#0068ff] hover:bg-blue-700 text-white font-bold py-4 px-6 rounded-xl transition-all text-center shadow-md hover:shadow-lg"
                    >
                        🖥️ Desktop View
                    </Link>

                    <Link
                        href="/zalo/mobile"
                        className="block w-full bg-[#0068ff] hover:bg-blue-700 text-white font-bold py-4 px-6 rounded-xl transition-all text-center shadow-md hover:shadow-lg"
                    >
                        📱 Mobile View
                    </Link>
                </div>

                <div className="mt-8 pt-6 border-t border-gray-200 text-center text-sm text-gray-500">
                    <p>AI-powered parent-teacher communication demo</p>
                </div>
            </div>
        </main>
    );
}
