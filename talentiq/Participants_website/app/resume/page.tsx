"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { UploadCloud, FileText, CheckCircle2 } from "lucide-react";

export default function ResumePage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<"idle" | "uploading" | "success">("idle");
  const [progress, setProgress] = useState(0);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = () => {
    if (!file) return;
    setStatus("uploading");
    
    // Simulate upload progress
    let p = 0;
    const interval = setInterval(() => {
      p += 10;
      setProgress(p);
      if (p >= 100) {
        clearInterval(interval);
        setStatus("success");
        setTimeout(() => {
          router.push("/success");
        }, 1000);
      }
    }, 150);
  };

  const handleSkip = () => {
    router.push("/success");
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#fafafa] p-4 text-[#111]">
      <div className="w-full max-w-[440px]">
        
        <div className="mb-8 text-center">
          <h1 className="text-xl font-semibold tracking-tight">CAREER FAIR</h1>
        </div>

        <Card className="border border-gray-200 shadow-sm rounded-xl bg-white overflow-hidden">
          <CardHeader className="pb-4 text-center">
            <CardTitle className="text-lg font-medium">Add your resume</CardTitle>
            <CardDescription className="text-gray-500 text-sm mt-2">
              Upload your resume now so employers can easily access it at the career fair.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {status === "idle" && (
              <>
                {!file ? (
                  <div className="relative border-2 border-dashed border-gray-200 hover:border-gray-300 rounded-xl p-8 flex flex-col items-center justify-center transition-colors cursor-pointer bg-gray-50/50">
                    <input 
                      type="file" 
                      accept=".pdf,.docx" 
                      className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                      onChange={handleFileChange}
                    />
                    <UploadCloud className="w-8 h-8 text-gray-400 mb-3" />
                    <p className="text-sm font-medium text-gray-700">Upload your resume</p>
                    <p className="text-xs text-gray-500 mt-1">Drag and drop or choose a file</p>
                    <div className="mt-4 px-3 py-1 bg-white border border-gray-200 rounded-md text-[10px] font-medium text-gray-500 uppercase tracking-wider">
                      PDF or DOCX
                    </div>
                  </div>
                ) : (
                  <div className="border border-gray-200 rounded-xl p-4 flex items-center justify-between bg-white">
                    <div className="flex items-center gap-3 overflow-hidden">
                      <div className="p-2 bg-gray-50 rounded-lg flex-shrink-0 border border-gray-100">
                        <FileText className="w-5 h-5 text-gray-600" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">{file.name}</p>
                        <p className="text-xs text-gray-500 mt-0.5">
                          {file.name.split('.').pop()?.toUpperCase()} • {(file.size / (1024 * 1024)).toFixed(1)} MB
                        </p>
                      </div>
                    </div>
                    <button 
                      onClick={() => setFile(null)}
                      className="text-gray-400 hover:text-gray-600 p-2"
                    >
                      ✕
                    </button>
                  </div>
                )}
              </>
            )}

            {status === "uploading" && (
              <div className="py-6 flex flex-col items-center justify-center text-center animate-in fade-in">
                <p className="text-sm font-medium text-gray-900 mb-4">Uploading resume...</p>
                <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-[#111] transition-all duration-150 ease-out"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-2">{progress}%</p>
              </div>
            )}

            {status === "success" && (
              <div className="py-8 flex flex-col items-center justify-center text-center animate-in fade-in">
                <CheckCircle2 className="w-12 h-12 text-green-500 mb-3" />
                <p className="text-sm font-medium text-gray-900">Resume uploaded ✓</p>
              </div>
            )}
          </CardContent>
          
          {status === "idle" && (
            <CardFooter className="flex flex-col gap-3">
              <Button 
                onClick={handleUpload}
                disabled={!file}
                className="w-full h-12 bg-[#111] hover:bg-black text-white disabled:opacity-50 disabled:bg-gray-200 disabled:text-gray-500"
              >
                Upload Resume →
              </Button>
              <Button 
                variant="ghost"
                onClick={handleSkip}
                className="w-full h-12 text-gray-500 hover:text-gray-900 hover:bg-gray-50"
              >
                Skip for now
              </Button>
            </CardFooter>
          )}
        </Card>
      </div>
    </main>
  );
}
