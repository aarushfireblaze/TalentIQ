"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardFooter, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

export default function RegisterPage() {
  const router = useRouter();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setTimeout(() => {
      router.push("/resume");
    }, 1000);
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#fafafa] p-4 text-[#111]">
      <div className="w-full max-w-[440px]">
        
        <div className="mb-8 text-center">
          <h1 className="text-xl font-semibold tracking-tight">CAREER FAIR</h1>
          <p className="text-sm text-gray-500 mt-1">Get ready before you arrive</p>
        </div>

        <Card className="border border-gray-200 shadow-sm rounded-xl bg-white overflow-hidden">
          <form onSubmit={handleSubmit}>
            <CardHeader className="pb-4 text-center">
              <CardTitle className="text-lg font-medium">Pre-Register</CardTitle>
              <CardDescription className="text-gray-500 text-sm mt-2">
                Enter your information once and make check-in faster at the fair.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid w-full items-center gap-4">
                <div className="flex flex-col space-y-2">
                  <Label htmlFor="firstName" className="text-gray-600">First name</Label>
                  <Input 
                    id="firstName" 
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    className="h-12 border-gray-200 focus-visible:ring-gray-300"
                    required
                    disabled={loading}
                  />
                </div>
                <div className="flex flex-col space-y-2">
                  <Label htmlFor="lastName" className="text-gray-600">Last name</Label>
                  <Input 
                    id="lastName" 
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    className="h-12 border-gray-200 focus-visible:ring-gray-300"
                    required
                    disabled={loading}
                  />
                </div>
                <div className="flex flex-col space-y-2">
                  <Label htmlFor="email" className="text-gray-600">Email</Label>
                  <Input 
                    id="email" 
                    type="email"
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="h-12 border-gray-200 focus-visible:ring-gray-300"
                    required
                    disabled={loading}
                  />
                </div>
              </div>
            </CardContent>
            <CardFooter>
              <Button className="w-full h-12 bg-[#111] hover:bg-black text-white" disabled={loading}>
                {loading ? "Saving..." : "Continue →"}
              </Button>
            </CardFooter>
          </form>
        </Card>
      </div>
    </main>
  );
}
