# Frontend - Vinschool AI For Good

Giao diện người dùng cho hệ thống Vinschool AI For Good, bao gồm các portal cho học sinh, giáo viên, và demo Zalo AI Chat.

## 🎯 Tổng Quan

Frontend này được xây dựng bằng **Next.js 16** với App Router, cung cấp 3 giao diện chính:

- **Student Portal** (`/student`) - Giao diện dành cho học sinh
- **Teacher Portal** (`/teacher`) - Giao diện dành cho giáo viên  
- **Zalo AI Demo** (`/zalo`) - Demo chat AI giữa phụ huynh và giáo viên

## 🛠️ Tech Stack

- **Framework**: Next.js 16.1.6 (App Router)
- **UI Library**: React 19.2.3
- **Styling**: TailwindCSS 4.1.18
- **Icons**: Lucide React
- **Language**: TypeScript 5
- **React Compiler**: Enabled (babel-plugin-react-compiler)

## 📁 Cấu Trúc Thư Mục

```
frontend/
├── src/
│   ├── app/
│   │   ├── (auth)/          # Auth routes (login)
│   │   ├── student/         # Student portal pages
│   │   ├── teacher/         # Teacher portal pages
│   │   ├── zalo/            # Zalo AI demo
│   │   │   ├── desktop/     # Desktop view
│   │   │   ├── mobile/      # Mobile view
│   │   │   └── page.tsx     # Landing page
│   │   ├── layout.tsx       # Root layout
│   │   └── globals.css      # Global styles
│   └── components/          # Reusable components
│       ├── Zalo*.tsx        # Zalo chat components
│       ├── Sidebar*.tsx     # Navigation sidebars
│       └── *Table.tsx       # Data tables
├── public/                  # Static assets
├── next.config.ts           # Next.js configuration
├── tsconfig.json            # TypeScript configuration
└── package.json             # Dependencies

```

## 🚀 Quick Start

### Prerequisites

- Node.js 20+
- npm hoặc yarn

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

Server sẽ chạy tại: **http://localhost:3000**

### Build Production

```bash
npm run build
npm start
```

## 🔗 Routes

| Route | Description |
|-------|-------------|
| `/student` | Portal học sinh - xem bài tập, nộp bài |
| `/teacher` | Portal giáo viên - quản lý bài tập, xem báo cáo |
| `/zalo` | Landing page chọn demo Desktop/Mobile |
| `/zalo/desktop` | Zalo AI chat - Desktop view |
| `/zalo/mobile` | Zalo AI chat - Mobile view |

## 🎨 Features

### Student Portal
- Xem danh sách bài tập
- Nộp bài tập
- Xem feedback từ AI

### Teacher Portal  
- Tạo và quản lý bài tập
- Upload tài liệu
- Xem báo cáo tiến độ học sinh
- Review submissions

### Zalo AI Demo
- **Desktop View**: Giao diện Zalo desktop với sidebar, chat list, và chat window
- **Mobile View**: Giao diện Zalo mobile responsive
- AI tự động phản hồi tin nhắn từ phụ huynh
- Demo real-time communication giữa giáo viên-phụ huynh

## 🔧 Configuration

### TypeScript Paths

Sử dụng alias `@/*` để import từ `src/`:

```typescript
import { ZaloDesktopChat } from '@/components/ZaloDesktopChat';
```

### React Compiler

React Compiler được bật để optimize performance tự động.

## 📝 Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Build production bundle |
| `npm start` | Start production server |
| `npm run lint` | Run ESLint |

## 🎯 Development Notes

- Sử dụng **App Router** (không phải Pages Router)
- Tất cả client components phải có `"use client"` directive
- TailwindCSS 4 với PostCSS plugin
- TypeScript strict mode: disabled (strict: false)
- Font: Inter (hỗ trợ tiếng Việt)

## 🐛 Troubleshooting

### Port đã được sử dụng
```bash
# Change port
PORT=3001 npm run dev
```

### Type errors sau khi update dependencies
```bash
rm -rf .next
npm install
```

## 📦 Dependencies

### Production
- `next`: ^16.1.6
- `react`, `react-dom`: ^19.2.3  
- `lucide-react`: ^0.563.0
- `postcss`: ^8.5.6

### Development
- `typescript`: ^5
- `tailwindcss`: ^4.1.18
- `@tailwindcss/postcss`: ^4.1.18
- `eslint`: ^9
- `babel-plugin-react-compiler`: 1.0.0

## 🤝 Contributing

Khi thêm features mới:
1. Tạo component trong `/src/components`
2. Tạo route trong `/src/app`
3. Follow coding conventions hiện tại
4. Test trên cả desktop và mobile

## 📄 License

Private - Vinschool AI For Good Project
