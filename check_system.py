import sys
import os
import shutil
import subprocess

print("--- XIAO SISTEM TARAMASI BAŞLIYOR ---\n")

# 1. PYTHON SÜRÜMÜ
print(f"[1] Python: {sys.version}")

# 2. FFMPEG KONTROLÜ (En Kritik Kısım)
ffmpeg_path = shutil.which("ffmpeg")
print(f"[2] FFmpeg Yolu: {ffmpeg_path}")

if not ffmpeg_path:
    print("    ❌ HATA: FFmpeg sistemde bulunamadı!")
    print("    ÇÖZÜM: 'ffmpeg.exe' indirip bu klasöre atman gerek.")
else:
    try:
        # Versiyon kontrolü yap
        result = subprocess.run([ffmpeg_path, "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print("    ✅ FFmpeg çalışıyor.")
    except Exception as e:
        print(f"    ❌ FFmpeg var ama çalışmıyor: {e}")

# 3. KÜTÜPHANE KONTROLLERİ
libraries = ["torch", "torchaudio", "demucs", "soundfile"]
print("\n[3] Kütüphane Kontrolleri:")
for lib in libraries:
    try:
        __import__(lib)
        print(f"    ✅ {lib} yüklü.")
    except ImportError:
        print(f"    ❌ {lib} EKSİK! (pip install {lib} yapmalısın)")
    except Exception as e:
        print(f"    ⚠️ {lib} yüklenirken hata: {e}")

# 4. SIMULASYON (Demucs Testi)
print("\n[4] Demucs Ayrıştırma Testi:")
# Test için uploads klasöründe bir dosya var mı bak
upload_dir = os.path.join(os.getcwd(), "uploads")
test_file = None

if os.path.exists(upload_dir):
    files = [f for f in os.listdir(upload_dir) if f.endswith(('.mp3', '.wav'))]
    if files:
        test_file = os.path.join(upload_dir, files[0])
        print(f"    Test dosyası bulundu: {files[0]}")
    else:
        print("    ⚠️ Uploads klasöründe test edilecek ses dosyası yok.")
else:
    print("    ⚠️ Uploads klasörü yok.")

if test_file:
    print("    🚀 Demucs manuel olarak çalıştırılıyor (Lütfen bekleyin)...")
    try:
        # Flask olmadan direkt komut satırı testi
        cmd = [sys.executable, "-m", "demucs", "-n", "htdemucs", "--out", "separated_test", test_file]
        process = subprocess.run(cmd, capture_output=True, text=True)

        if process.returncode == 0:
            print("\n    ✅ BAŞARILI! Demucs dosyayı ayırdı.")
            print("    Sorun Flask/App.py kodunda olabilir.")
        else:
            print("\n    ❌ BAŞARISIZ! İşte hatanın asıl sebebi:")
            print("    ------------------------------------------------")
            print(process.stderr)
            print("    ------------------------------------------------")
    except Exception as e:
        print(f"    ❌ Komut hatası: {e}")
else:
    print("    ℹ️ Testi tamamlamak için 'uploads' klasörüne bir şarkı atıp tekrar çalıştır.")

print("\n--- TARAMA BİTTİ ---")
input("Kapatmak için Enter'a bas...")