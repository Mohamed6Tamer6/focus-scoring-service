from supabase import create_client, Client
from config import settings
import uuid

supabase = None
try:
    supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    print("SUCCESS: Supabase client initialized and ready.")
except Exception as e:
    print(f"WARNING: Supabase client could not be initialized: {e}")
    print("PDF Uploads to bucket will be disabled until a valid SUPABASE_KEY is provided.")

def upload_pdf_report(pdf_bytes: bytes, user_id: str, session_id: str) -> str | None:

    if supabase is None:
        print("Supabase client not initialized. Skipping upload.")
        return None
        
    bucket_name = "focus_servising"
    file_path = f"{user_id}/{session_id}.pdf"
    
    print(f"[UPLOAD] Starting upload: bucket='{bucket_name}', path='{file_path}', size={len(pdf_bytes)} bytes")
    
    try:
        upload_response = supabase.storage.from_(bucket_name).upload(
            path=file_path,
            file=pdf_bytes,
            file_options={"content-type": "application/pdf"}
        )
        print(f"[UPLOAD] Upload response: {upload_response}")
        
        public_url = supabase.storage.from_(bucket_name).get_public_url(file_path)
        print(f"[UPLOAD] Public URL: {public_url}")
        return public_url
    except Exception as e:
        error_str = str(e)
        print(f"[UPLOAD] CRITICAL FAIL for user {user_id}, session {session_id}: {error_str}")
        if "Bucket not found" in error_str:
            print("[UPLOAD] HINT: The bucket 'session-reports' does not exist in your Supabase project. Please create it in Storage > New Bucket.")
        elif "Invalid API key" in error_str or "invalid" in error_str.lower():
            print("[UPLOAD] HINT: The SUPABASE_KEY may be wrong. Use the anon key from Project Settings > API.")
        elif "violates" in error_str or "security" in error_str.lower():
            print("[UPLOAD] HINT: Check your Supabase Storage RLS policies. You may need to allow inserts on the bucket.")
        return None
