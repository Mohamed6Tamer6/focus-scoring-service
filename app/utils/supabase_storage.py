from supabase import create_client, Client
from config import settings
from uuid import UUID

supabase = None
try:
    supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    print("SUCCESS: Supabase client initialized and ready.")
except Exception as e:
    print(f"WARNING: Supabase client could not be initialized: {e}")
    print("PDF Uploads to bucket will be disabled until a valid SUPABASE_KEY is provided.")

BUCKET_NAME = "focus_servising"


def upload_pdf_report(pdf_bytes: bytes, user_id: UUID, session_id: UUID) -> str | None:

    if supabase is None:
        print("Supabase client not initialized. Skipping upload.")
        return None

    file_path = f"{str(user_id)}/{str(session_id)}.pdf"

    print(f"[UPLOAD] Starting upload: bucket='{BUCKET_NAME}', path='{file_path}', size={len(pdf_bytes)} bytes")

    try:
        upload_response = supabase.storage.from_(BUCKET_NAME).upload(
            path=file_path,
            file=pdf_bytes,
            file_options={"content-type": "application/pdf"}
        )
        print(f"[UPLOAD] Upload response: {upload_response}")
        print(f"[UPLOAD] Stored path: {file_path}")

        return file_path

    except Exception as e:
        error_str = str(e)
        print(f"[UPLOAD] CRITICAL FAIL for user {user_id}, session {session_id}: {error_str}")
        if "Bucket not found" in error_str:
            print(f"[UPLOAD] HINT: Bucket '{BUCKET_NAME}' does not exist. Create it in Storage > New Bucket.")
        elif "Invalid API key" in error_str or "invalid" in error_str.lower():
            print("[UPLOAD] HINT: Check SUPABASE_KEY in .env — use the anon key from Project Settings > API.")
        elif "violates" in error_str or "security" in error_str.lower():
            print("[UPLOAD] HINT: Check RLS policies on the bucket.")
        return None


def get_signed_url(file_path: str, expires_in: int = 3600) -> str | None:

    if supabase is None:
        print("Supabase client not initialized. Cannot generate signed URL.")
        return None

    try:
        response = supabase.storage.from_(BUCKET_NAME).create_signed_url(
            path=file_path,
            expires_in=expires_in
        )
        return response.get("signedURL")
    except Exception as e:
        print(f"[SIGNED_URL] Failed to generate signed URL for path '{file_path}': {e}")
        return None