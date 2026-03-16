'use client';

import { useRef, useState } from 'react';

interface SubmitButtonProps {
  onSuccess: () => void;
}

export default function SubmitButton({ onSuccess }: SubmitButtonProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);

  const handleButtonClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setIsUploading(true);
      
      setTimeout(() => {
        const submission = {
          studentName: "Alex",
          fileName: file.name,
          submitTime: new Date().toLocaleString(),
          unit: "Unit 9"
        };
        localStorage.setItem('unit9_submission', JSON.stringify(submission));
        
        setIsUploading(false);
        onSuccess();
      }, 1500);
    }
  };

  return (
    <div className="flex justify-center">
      <input 
        type="file" 
        ref={fileInputRef} 
        className="hidden" 
        onChange={handleFileChange}
      />
      
      <button 
        onClick={handleButtonClick}
        disabled={isUploading}
        className={`px-6 py-1.5 rounded-full text-xs font-bold transition-all cursor-pointer shadow-sm ${
          isUploading ? "bg-slate-300 cursor-not-allowed" : "bg-blue-600 hover:bg-blue-700 text-white active:scale-95"
        }`}
      >
        {isUploading ? "UPLOADING..." : "SUBMIT"}
      </button>
    </div>
  );
}