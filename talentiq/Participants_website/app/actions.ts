"use server";

import { supabaseAdmin } from "@/lib/supabaseAdmin";

export async function submitCheckin(formData: FormData) {
  const firstName = formData.get("firstName") as string;
  const lastName = formData.get("lastName") as string;
  const email = formData.get("email") as string;
  const file = formData.get("file") as File | null;

  if (!file) {
    throw new Error("Resume file is required");
  }

  try {
    // 1. Upload the file using the admin client (bypasses storage RLS)
    const fileExt = file.name.split('.').pop();
    const fileName = `${Date.now()}-${Math.random().toString(36).substring(2, 15)}.${fileExt}`;
    
    const { data: uploadData, error: uploadError } = await supabaseAdmin.storage
      .from("resumes")
      .upload(fileName, file);

    if (uploadError) {
      console.error("Upload error details:", uploadError);
      throw new Error("Failed to upload resume: " + uploadError.message);
    }

    const resumeUrl = uploadData.path;

    // 2. Insert the response using the admin client (bypasses database RLS)
    const { error: insertError } = await supabaseAdmin
      .from("responses")
      .insert([
        {
          first_name: firstName,
          last_name: lastName,
          email: email,
          resume_url: resumeUrl,
        }
      ]);

    if (insertError) {
      console.error("Insert error details:", insertError);
      throw new Error("Failed to save response: " + insertError.message);
    }

    return { success: true };
  } catch (error: any) {
    console.error("Server Action Error:", error);
    return { success: false, error: error.message || "An unexpected error occurred." };
  }
}
