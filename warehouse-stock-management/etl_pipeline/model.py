# model.py
import os
import logging
from openai import OpenAI

# Impor dan muat variabel dari file .env
from dotenv import load_dotenv
load_dotenv()

# Konfigurasi logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# --- Konfigurasi Pemotongan Narasi ---
MAX_NARRATIVE_WORDS = 120 

# --- Konfigurasi Klien OpenAI ---
# Menggunakan API resmi OpenAI
try:
    client = OpenAI(
      # Tidak perlu base_url, library openai akan menggunakan endpoint default
      api_key=os.environ.get("OPENAI_API_KEY") # Membaca dari .env
    )
except Exception as e:
    log.error(f"Gagal menginisialisasi klien OpenAI: {e}")
    client = None

def truncate_text(text: str, max_words: int) -> str:
    """Memotong teks agar tidak melebihi jumlah kata maksimum."""
    if not text: return ""
    words = text.split()
    if len(words) <= max_words: return text
    truncated = " ".join(words[:max_words])
    return truncated + "..."

def generate_narrative_analysis(inventory_summary: dict, financial_summary: dict, total_items: int) -> str:
    """
    Menghasilkan narasi analitik dari data gudang menggunakan model GPT-4o-mini dari OpenAI.
    """
    if not client:
        log.error("Klien OpenAI tidak tersedia. Tidak dapat membuat narasi.")
        return "<p><b>Error:</b> Klien OpenAI tidak dapat diinisialisasi. Periksa API Key di file .env.</p>"

    log.info("Memulai pembuatan narasi analitik dengan AI (GPT-4o-mini)...")

    total_inventory_value = financial_summary.get('total_inventory_value', 0)
    stock_turnover_ratio = inventory_summary.get('stock_turnover_ratio', 0)
    days_of_inventory_on_hand = inventory_summary.get('days_of_inventory_on_hand', 0)
    total_dead_stock_items = inventory_summary.get('total_dead_stock_items', 0)
    total_dead_stock_value = inventory_summary.get('total_dead_stock_value', 0)
    
    if total_items == 0: total_items = 1
    dead_stock_percentage = (total_dead_stock_items / total_items) * 100

    prompt = f"""
    Anda adalah seorang analis bisnis ahli. Buatlah narasi analitik yang SANGAT RINGKAS dan BERDAMPAK dalam Bahasa Indonesia berdasarkan data gudang berikut.

    Data:
    - Total Nilai Inventori: Rp {total_inventory_value:,.0f}
    - Rasio Perputaran Stok: {stock_turnover_ratio:.2f}
    - Hari Persediaan: {days_of_inventory_on_hand:.1f} hari
    - Jumlah Item Dead Stock: {total_dead_stock_items} SKU ({dead_stock_percentage:.1f}%)
    - Nilai Dead Stock: Rp {total_dead_stock_value:,.0f}

    Instruksi KRUSIAL:
    1.  Jawaban harus RINGKAS, tidak lebih dari 2 paragraf.
    2.  Jangan melebihi {MAX_NARRATIVE_WORDS} kata.
    3.  Fokus hanya pada SATU temuan kritis dan SATU rekomendasi utama.
    4.  Gunakan tag HTML seperti <b> untuk teks tebal dan <br><br> untuk paragraf baru.
    5.  Langsung ke intinya, tidak perpa kata pengantar.
    """

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini", # Menggunakan model GPT-4o-mini
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        narrative = completion.choices[0].message.content
        log.info(f"AI (GPT-4o-mini)  narasi dengan {len(narrative.split())} kata.")
        
        final_narrative = truncate_text(narrative, MAX_NARRATIVE_WORDS)
        
        if len(final_narrative.split()) < len(narrative.split()):
            log.warning(f"Narasi AI terlalu panjang dan telah dipotong menjadi {len(final_narrative.split())} kata.")
        
        log.info("Narasi akhir siap digunakan.")
        return final_narrative

    except Exception as e:
        log.error(f"Gagal narasi analitik: {e}")
        return "<p><b>Error:</b> Gagal narasi analitik. Periksa log untuk detailnya (misal: kuota API key habis atau koneksi bermasalah).</p>"


# --- Blok untuk Testing ---
if __name__ == "__main__":
    dummy_inventory_summary = {'stock_turnover_ratio': 2.5, 'days_of_inventory_on_hand': 146.0, 'total_dead_stock_items': 450, 'total_dead_stock_value': 2_500_000_000}
    dummy_financial_summary = {'total_inventory_value': 5_100_000_000}
    dummy_total_items = 1000

    print("--- Memulai Pembuatan Narasi Analitik (dengan OpenAI GPT-4o-mini) ---")
    hasil_narasi = generate_narrative_analysis(inventory_summary=dummy_inventory_summary, financial_summary=dummy_financial_summary, total_items=dummy_total_items)
    print("\n--- Hasil Narasi Akhir ---")
    print(hasil_narasi)
    print(f"\nJumlah kata akhir: {len(hasil_narasi.split())}")
    print("\n--- Selesai ---")