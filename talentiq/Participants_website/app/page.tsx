"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { UploadCloud, FileText, ChevronRight } from "lucide-react";
import Link from "next/link";
import { useDropzone } from "react-dropzone";
import { submitCheckin } from "@/app/actions";

export default function CheckinPage() {
  const router = useRouter();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles && acceptedFiles[0]) {
      setFile(acceptedFiles[0]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
    },
    maxFiles: 1,
    disabled: status === "submitting" || status === "success"
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setStatus("error");
      setErrorMessage("Please upload your resume before submitting.");
      return;
    }
    setStatus("submitting");
    setErrorMessage("");

    try {
      const formData = new FormData();
      formData.append("firstName", firstName);
      formData.append("lastName", lastName);
      formData.append("email", email);
      formData.append("file", file);

      const result = await submitCheckin(formData);

      if (!result.success) {
        throw new Error(result.error);
      }

      setStatus("success");
      setTimeout(() => router.push("/success"), 800);
    } catch (error: any) {
      console.error("Submission error:", error);
      setStatus("error");
      setErrorMessage(error.message || "An error occurred during submission.");
    }
  };

  return (
    <div className="min-h-screen bg-jbh-lightgray font-sans flex flex-col">
      
      {/* Top Nav (Corporate style) */}
      <nav className="w-full bg-white z-50 flex items-center justify-center sm:justify-start px-4 sm:px-6 py-3 sm:py-4 shadow-sm border-b-4 border-jbh-yellow">
        <Link href="/" className="flex items-center gap-2">
          <div className="bg-jbh-yellow text-jbh-black font-heading font-extrabold italic px-2 sm:px-3 py-1 text-lg sm:text-xl tracking-tighter uppercase transform -skew-x-12">
            J.B. HUNT
          </div>
          <span className="text-jbh-black font-heading font-bold tracking-tight text-base sm:text-lg ml-1 sm:ml-2 uppercase">Career Fair</span>
        </Link>
      </nav>

      {/* Main Form Area */}
      <div className="flex-1 flex items-start sm:items-center justify-center p-0 sm:p-6 lg:p-8">
        <div className="w-full max-w-4xl bg-white border-x-0 sm:border border-jbh-gray shadow-none sm:shadow-xl flex flex-col md:flex-row overflow-hidden rounded-none sm:rounded-md">
          
          {/* Side Banner */}
          <div className="bg-jbh-black text-white p-8 sm:p-10 md:p-12 md:w-2/5 flex flex-col justify-start text-center md:text-left">
            <div>
              <h2 className="text-3xl sm:text-4xl md:text-5xl font-heading font-extrabold uppercase mb-4 sm:mb-6 leading-none tracking-tight">
                Join the <br className="hidden md:block" />
                <span className="text-jbh-yellow"> Fleet.</span>
              </h2>
              <div className="w-12 sm:w-16 h-1.5 bg-jbh-yellow mb-6 sm:mb-8 mx-auto md:mx-0"></div>
              <p className="text-sm sm:text-base text-jbh-lightgray/90 font-medium leading-relaxed max-w-sm mx-auto md:mx-0">
                Provide your details to securely check in. Our recruiters will review your information shortly.
              </p>
            </div>
          </div>

          {/* Form */}
          <div className="p-8 sm:p-10 md:p-12 md:w-3/5 overflow-y-auto">
            {/* Added -mt-2 to pull the form UP slightly to perfectly align with the text ascenders of the heading on the left */}
            <form onSubmit={handleSubmit} className="space-y-5 sm:space-y-6 -mt-2">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 sm:gap-6">
                <div className="flex flex-col relative group">
                  <label className="text-[11px] sm:text-xs font-bold text-jbh-black uppercase tracking-wide mb-1 group-focus-within:text-jbh-black transition-colors">First Name</label>
                  <input
                    value={firstName}
                    onChange={e => setFirstName(e.target.value)}
                    disabled={status === "submitting" || status === "success"}
                    required
                    className="w-full bg-[#f9f9f9] border border-[#A0A0A0] rounded-sm px-4 py-3 sm:py-3.5 text-base sm:text-sm text-jbh-black placeholder:text-jbh-gray focus:outline-none focus:border-jbh-black focus:ring-1 focus:ring-jbh-black transition-all peer"
                  />
                </div>
                <div className="flex flex-col relative group">
                  <label className="text-[11px] sm:text-xs font-bold text-jbh-black uppercase tracking-wide mb-1 group-focus-within:text-jbh-black transition-colors">Last Name</label>
                  <input
                    value={lastName}
                    onChange={e => setLastName(e.target.value)}
                    disabled={status === "submitting" || status === "success"}
                    required
                    className="w-full bg-[#f9f9f9] border border-[#A0A0A0] rounded-sm px-4 py-3 sm:py-3.5 text-base sm:text-sm text-jbh-black placeholder:text-jbh-gray focus:outline-none focus:border-jbh-black focus:ring-1 focus:ring-jbh-black transition-all peer"
                  />
                </div>
              </div>

              <div className="flex flex-col relative group">
                <label className="text-[11px] sm:text-xs font-bold text-jbh-black uppercase tracking-wide mb-1 group-focus-within:text-jbh-black transition-colors">Email Address</label>
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  disabled={status === "submitting" || status === "success"}
                  required
                  className="w-full bg-[#f9f9f9] border border-[#A0A0A0] rounded-sm px-4 py-3 sm:py-3.5 text-base sm:text-sm text-jbh-black placeholder:text-jbh-gray focus:outline-none focus:border-jbh-black focus:ring-1 focus:ring-jbh-black transition-all peer"
                />
              </div>

              <div className="flex flex-col relative group pt-4 sm:pt-6">
                <label className="text-[11px] sm:text-xs font-bold text-jbh-black uppercase tracking-wide flex justify-between mb-1">
                  Resume Upload
                  <span className="text-jbh-black font-bold normal-case tracking-normal">Required</span>
                </label>
                
                {!file ? (
                  <div {...getRootProps()} className={`flex flex-col items-center justify-center border-2 border-dashed ${isDragActive ? 'border-jbh-black bg-[#efefef]' : 'border-[#A0A0A0] bg-[#f9f9f9]'} rounded-sm p-6 sm:p-8 hover:bg-[#efefef] hover:border-jbh-black transition-all cursor-pointer group/upload focus-within:ring-2 focus-within:ring-jbh-black focus-within:border-solid focus-within:border-jbh-black`}>
                    <input {...getInputProps()} />
                    <UploadCloud strokeWidth={2.5} className={`w-8 h-8 text-jbh-black mb-3 transition-all ${isDragActive ? 'scale-110 text-jbh-yellow' : 'group-hover/upload:scale-110 group-hover/upload:text-jbh-yellow'}`} />
                    <span className={`inline-block bg-jbh-black text-white px-5 py-2 rounded-full text-xs font-bold mb-2 uppercase transition-colors ${isDragActive ? 'bg-jbh-yellow text-jbh-black' : 'group-hover/upload:bg-jbh-yellow group-hover/upload:text-jbh-black'}`}>
                      {isDragActive ? "Drop File Here" : "Select File"}
                    </span>
                    <span className="text-xs font-medium text-jbh-black/60">PDF or DOCX format. Drag & drop allowed.</span>
                  </div>
                ) : (
                  <div className="flex items-center justify-between p-3 sm:p-4 border-2 border-jbh-black bg-jbh-yellow/5 rounded-sm">
                    <div className="flex items-center gap-3 sm:gap-4 overflow-hidden">
                      <FileText strokeWidth={2.5} className="w-5 h-5 sm:w-6 sm:h-6 text-jbh-black shrink-0" />
                      <div className="min-w-0">
                        <p className="text-sm font-bold text-jbh-black truncate">{file.name}</p>
                        <p className="text-[10px] sm:text-xs text-jbh-black/60 font-medium mt-0.5">
                          {file.name.split('.').pop()?.toUpperCase()} • {(file.size / (1024 * 1024)).toFixed(1)} MB
                        </p>
                      </div>
                    </div>
                    {(status === "idle" || status === "error") && (
                      <button 
                        type="button" 
                        onClick={() => setFile(null)}
                        className="p-2 text-jbh-black/50 hover:text-jbh-black transition-colors font-bold"
                      >
                        ✕
                      </button>
                    )}
                  </div>
                )}
              </div>

              {status === "error" && (
                <div className="text-red-500 text-sm font-medium mt-2">
                  {errorMessage}
                </div>
              )}

              {/* Added pt-10 to increase breathing room above the submit button */}
              <div className="pt-10 pb-2 sm:pb-0">
                <button
                  type="submit"
                  disabled={status === "submitting" || status === "success"}
                  className="w-full bg-jbh-yellow text-jbh-black uppercase text-base font-extrabold px-8 py-4 rounded-sm hover:bg-jbh-black hover:text-jbh-yellow hover:tracking-wide transition-all flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed group/btn shadow-md active:scale-[0.98]"
                >
                  {status === "submitting" ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-2 h-5 w-5 text-current" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Processing...
                    </>
                  ) : status === "success" ? (
                    "Success!"
                  ) : (
                    <>Submit <ChevronRight strokeWidth={2.5} className="w-5 h-5 group-hover/btn:translate-x-1 transition-transform" /></>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
