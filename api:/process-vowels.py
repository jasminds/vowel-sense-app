# api/process-vowels.py

import os
from supabase import create_client, Client
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import uuid
import tempfile # Digunakan untuk membuat file sementara dengan aman

# Inisialisasi Supabase client
# Pastikan SUPABASE_URL dan SUPABASE_KEY telah disetel sebagai Environment Variables di Vercel Dashboard Anda!
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Pastikan URL dan Key tidak kosong
if not SUPABASE_URL or not SUPABASE_KEY:
    # Ini akan menyebabkan deployment gagal atau runtime error jika tidak ada
    print("Error: SUPABASE_URL or SUPABASE_KEY environment variables are not set.")
    # Dalam konteks Vercel, lebih baik membiarkan ini, dan error akan muncul di log Vercel.
    # Anda bisa return error khusus jika ingin, tapi itu akan jadi runtime error.

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"Error initializing Supabase client: {e}")
    # Ini juga akan muncul di log Vercel jika terjadi.

# Ini adalah aplikasi Flask, tapi Vercel akan memanggil fungsi 'handler'
# dan merutekan permintaan ke dalamnya.
app = Flask(__name__)

# Fungsi utama yang akan dipanggil oleh Vercel
# Vercel akan meneruskan HttpRequest object sebagai argumen.
# Kita perlu mengkonversi ke request Flask jika diperlukan.
def handler(event, context): # Vercel memanggil dengan event dan context
    # Konversi event Vercel ke objek request Flask agar kode Flask bisa dipakai
    # Ini adalah cara umum untuk membuat Flask app bekerja di Vercel serverless functions
    with app.test_request_context(
        method=event['method'],
        path=event['path'],
        headers=event['headers'],
        data=event['body'],
        content_type=event['headers'].get('content-type', '')
    ):
        # Sekarang kita bisa menggunakan request Flask
        if request.method == 'POST':
            # Pastikan request adalah multipart/form-data dan ada file 'image'
            if 'image' not in request.files:
                return jsonify({"error": "No image file provided"}), 400

            file = request.files['image']
            if file.filename == '':
                return jsonify({"error": "No selected file"}), 400

            if file:
                try:
                    filename = secure_filename(file.filename)
                    file_extension = os.path.splitext(filename)[1]
                    unique_filename = f"{uuid.uuid4()}{file_extension}"

                    # Gunakan tempfile untuk menyimpan file sementara dengan aman
                    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                        temp_file.write(file.read())
                        temp_file_path = temp_file.name

                    # Unggah ke Supabase Storage
                    with open(temp_file_path, 'rb') as f_read:
                        response_upload = supabase.storage.from_('vowel-sense-images').upload(unique_filename, f_read.read())

                    # Hapus file sementara setelah diunggah
                    os.remove(temp_file_path)

                    if response_upload.data:
                        public_url = supabase.storage.from_('vowel-sense-images').get_public_url(unique_filename)
                        return jsonify({"message": "File uploaded successfully", "url": public_url}), 200
                    else:
                        # Tangani error upload dari Supabase
                        # Supabase client v1.0.0+ biasanya mengembalikan respons error di response_upload.error
                        error_details = response_upload.error.message if response_upload.error else "Unknown upload error"
                        return jsonify({"error": "Failed to upload to Supabase", "details": error_details}), 500

                except Exception as e:
                    # Pastikan Anda punya SUPABASE_URL dan SUPABASE_KEY yang benar
                    return jsonify({"error": f"An unexpected error occurred: {str(e)}", "debug": "Check SUPABASE_URL and SUPABASE_KEY in Vercel environment variables."}), 500
        else:
            return jsonify({"error": "Method Not Allowed", "message": "This endpoint only accepts POST requests with an 'image' file."}), 405
