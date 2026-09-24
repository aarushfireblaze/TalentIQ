"use client";

import { useRouter } from "next/navigation";
import { CheckCircle2, ChevronRight } from "lucide-react";
import Link from "next/link";

export default function SuccessPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-jbh-lightgray font-sans flex flex-col">
      
      {/* Top Nav */}
      <nav className="w-full bg-white z-50 flex items-center justify-center sm:justify-start px-4 sm:px-6 py-3 sm:py-4 shadow-sm border-b-4 border-jbh-yellow">
        <Link href="/" className="flex items-center gap-2">
          <div className="bg-jbh-yellow text-jbh-black font-heading font-extrabold italic px-2 sm:px-3 py-1 text-lg sm:text-xl tracking-tighter uppercase transform -skew-x-12">
            J.B. HUNT
          </div>
          <span className="text-jbh-black font-heading font-bold tracking-tight text-base sm:text-lg ml-1 sm:ml-2 uppercase">Career Fair</span>
        </Link>
      </nav>

      {/* Main Area */}
      <div className="flex-1 flex items-start sm:items-center justify-center p-0 sm:p-8 mt-6 sm:mt-0">
        <div className="w-full max-w-2xl bg-white sm:border-t-8 border-t-4 border-jbh-yellow shadow-none sm:shadow-2xl ring-0 sm:ring-1 sm:ring-black/5 p-12 sm:p-24 flex flex-col items-center text-center rounded-none sm:rounded-md">
          
          <div className="mb-10 sm:mb-12">
            <CheckCircle2 strokeWidth={2} className="w-20 h-20 sm:w-24 sm:h-24 text-jbh-yellow" />
          </div>

          <h1 className="font-heading text-4xl sm:text-5xl font-extrabold uppercase text-jbh-black tracking-tight mb-6 sm:mb-8">
            Check-In Complete
          </h1>
          
          <p className="text-lg sm:text-xl text-jbh-black/50 leading-relaxed mb-16 sm:mb-20 max-w-lg">
            You are officially registered. Your information has been securely transmitted to our recruitment team.
          </p>

          <button
            onClick={() => router.push("/")}
            className="w-full max-w-sm bg-jbh-black text-white uppercase text-sm sm:text-base font-extrabold px-8 py-4 sm:py-5 rounded-sm hover:bg-jbh-black/90 hover:tracking-wide transition-all flex items-center justify-center gap-2 group shadow-md active:scale-[0.98]"
          >
            Return to Home <ChevronRight strokeWidth={2.5} className="w-4 h-4 sm:w-5 sm:h-5 group-hover:translate-x-1 transition-transform" />
          </button>
        </div>
      </div>
    </div>
  );
}
