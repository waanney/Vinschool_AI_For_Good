// src/app/teacher/page.tsx
import { cookies } from "next/headers";
import TeacherHomeworkTable from "@/components/TeacherHomeworkTable";

export default async function TeacherPage() {
  const cookieStore = await cookies();
  const userName = cookieStore.get('userName')?.value || 'Thầy Jem Omer';

  return (
    <div className="flex flex-col w-full animate-in fade-in duration-700">
      <TeacherHomeworkTable userName={decodeURIComponent(userName)} />
    </div>
  );
}