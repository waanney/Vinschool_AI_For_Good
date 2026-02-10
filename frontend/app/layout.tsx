import { Inter } from "next/font/google";
import "./globals.css";

// Khai báo font Inter hỗ trợ tiếng Việt
const inter = Inter({ 
  subsets: ["latin", "vietnamese"],
  weight: ['400', '500', '600', '700', '800'] 
});

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi">
      <body className={inter.className}>{children}</body>
    </html>
  );
}