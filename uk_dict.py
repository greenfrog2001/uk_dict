import requests
import tkinter as tk
from tkinter import ttk, messagebox
from deep_translator import GoogleTranslator
import urllib.parse
import time

# ====== CONFIG ======
DICTIONARY_KEY = "e1fd3412-7310-4f5f-a50d-9b0c257660e1"
THESAURUS_KEY = "816b0b3b-c13c-4179-aa49-8c0c98aa26ff"

API_URL_DICT = "https://www.dictionaryapi.com/api/v3/references/collegiate/json/{}?key={}"
API_URL_THES = "https://www.dictionaryapi.com/api/v3/references/thesaurus/json/{}?key={}"

translator = GoogleTranslator(source="en", target="vi")


# ====== TRANSLATE UTILITIES ======
def safe_translate(text):
    """Dịch an toàn, tránh lỗi NoneType."""
    try:
        if not text or not isinstance(text, str):
            return text
        translated = translator.translate(text)
        if not translated or translated.strip() == "":
            return text
        return translated
    except Exception as e:
        print("⚠️ Lỗi dịch:", e)
        return text


def batch_translate(sentences):
    """Dịch danh sách câu — từng câu một, tránh lỗi rate limit."""
    translated = []
    for s in sentences:
        translated.append(safe_translate(s))
        time.sleep(0.5)  # tránh gửi request quá nhanh
    return translated


# ====== COMMON FUNCTION ======
def clear_result():
    result_text.delete(1.0, tk.END)


def fetch_api(word, url_template, key):
    encoded_word = urllib.parse.quote(word)
    url = url_template.format(encoded_word, key)
    res = requests.get(url)
    res.raise_for_status()
    return res.json()


# ====== FEATURE 1 ======
import threading

# cấu hình thời gian (có thể chỉnh)
TRANSLATE_DELAY = 0.25   # giãn giữa các request dịch (giữ an toàn khỏi rate-limit)
TYPING_DELAY_MS = 10     # tốc độ "gõ" từng ký tự (ms) -- 10 = 0.01s

def lookup_meaning():
    word = entry.get().strip()
    if not word:
        messagebox.showwarning("Cảnh báo", "Vui lòng nhập từ hoặc cụm cần tra.")
        return

    clear_result()
    result_text.insert(tk.END, f"🔎 Tra cứu nghĩa của: {word}\n\n")

    def worker():
        try:
            data = fetch_api(word, API_URL_DICT, DICTIONARY_KEY)
            if not data:
                root.after(0, lambda: result_text.insert(tk.END, "❌ Không tìm thấy kết quả.\n"))
                return

            if isinstance(data[0], str):
                def show_suggestions():
                    result_text.insert(tk.END, "❌ Không tìm thấy. Gợi ý:\n")
                    for s in data:
                        result_text.insert(tk.END, f" - {s}\n")
                root.after(0, show_suggestions)
                return

            placeholder_items = []

            def show_english_and_placeholders():
                # Hiển thị tiếng Anh ngay lập tức
                for entry_data in data:
                    hw = entry_data.get("hwi", {}).get("hw", "")
                    fl = entry_data.get("fl", "")
                    defs = entry_data.get("shortdef", [])

                    if hw:
                        result_text.insert(tk.END, f"{hw} ({fl})\n", "word_style")

                    for d in defs:
                        # hiển thị nghĩa tiếng Anh
                        result_text.insert(tk.END, f"   • {d}\n")
                        # hiển thị dòng placeholder
                        placeholder = "Đang dịch..."
                        result_text.insert(tk.END, f"     → {placeholder}\n")
                        placeholder_items.append((placeholder, d))
                    result_text.insert(tk.END, "\n")

            root.after(0, show_english_and_placeholders)

            def translate_thread():
                for placeholder, definition in placeholder_items:
                    vi = safe_translate(definition)
                    time.sleep(TRANSLATE_DELAY)

                    def start_typing(placeholder=placeholder, vi=vi):
                        # Tìm vị trí của dòng "Đang dịch..."
                        idx = result_text.search(placeholder, "1.0", tk.END)
                        if not idx:
                            return

                        # Xóa dòng đó (cả cụm "Đang dịch...")
                        result_text.delete(idx, f"{idx} + {len(placeholder)} chars")

                        # Hiệu ứng gõ từng ký tự
                        def type_char(pos_index, i=0):
                            if i >= len(vi):
                                return
                            result_text.insert(pos_index, vi[i], "vi_style")
                            next_pos = result_text.index(f"{pos_index} + 1 chars")
                            root.after(TYPING_DELAY_MS, lambda: type_char(next_pos, i+1))

                        # Bắt đầu gõ tại vị trí dòng placeholder vừa xóa
                        type_char(idx, 0)

                    root.after(0, start_typing)

            threading.Thread(target=translate_thread, daemon=True).start()

        except Exception as e:
            root.after(0, lambda: result_text.insert(tk.END, f"⚠️ Lỗi: {e}\n"))

    threading.Thread(target=worker, daemon=True).start()




# ====== FEATURE 2 ======
def lookup_syn_ant():
    word = entry.get().strip()
    if not word:
        messagebox.showwarning("Cảnh báo", "Vui lòng nhập từ cần tra.")
        return

    clear_result()
    result_text.insert(tk.END, f"🟢 Tra cứu từ đồng nghĩa / trái nghĩa của: {word}\n\n")

    try:
        data = fetch_api(word, API_URL_THES, THESAURUS_KEY)
        if not data:
            result_text.insert(tk.END, "❌ Không tìm thấy dữ liệu.\n")
            return

        if isinstance(data[0], str):
            result_text.insert(tk.END, "❌ Không tìm thấy. Gợi ý:\n")
            for s in data:
                result_text.insert(tk.END, f" - {s}\n")
            return

        for entry_data in data:
            meta = entry_data.get("meta", {})
            syns = meta.get("syns", [])
            ants = meta.get("ants", [])
            defs = entry_data.get("shortdef", [])
            hw = entry_data.get("hwi", {}).get("hw", "")

            if hw:
                result_text.insert(tk.END, f"{hw}\n", "word_style")

            if defs:
                result_text.insert(tk.END, f"→ {defs[0]}\n\n")

            if syns:
                result_text.insert(tk.END, "🔹 Từ đồng nghĩa:\n", "syn_style")
                result_text.insert(tk.END, ", ".join(syns[0]) + "\n\n")

            if ants:
                result_text.insert(tk.END, "🔸 Từ trái nghĩa:\n", "ant_style")
                result_text.insert(tk.END, ", ".join(ants[0]) + "\n\n")

    except Exception as e:
        result_text.insert(tk.END, f"⚠️ Lỗi: {e}\n")


# ====== FEATURE 3 ======
def lookup_phrasal():
    word = entry.get().strip()
    if not word:
        messagebox.showwarning("Cảnh báo", "Vui lòng nhập cụm động từ cần tra.")
        return

    clear_result()
    result_text.insert(tk.END, f"📘 Tra cứu phrasal verb: {word}\n\n")

    try:
        data = fetch_api(word, API_URL_DICT, DICTIONARY_KEY)
        if not data:
            result_text.insert(tk.END, "❌ Không tìm thấy cụm này.\n")
            return

        if isinstance(data[0], str):
            result_text.insert(tk.END, "❌ Không tìm thấy. Gợi ý:\n")
            for s in data:
                result_text.insert(tk.END, f" - {s}\n")
            return

        found = False
        for entry_data in data:
            meta_id = entry_data.get("meta", {}).get("id", "")
            if " " in meta_id:  # chỉ lấy cụm động từ
                found = True
                defs = entry_data.get("shortdef", [])
                result_text.insert(tk.END, f"{meta_id}\n", "word_style")
                for d in defs:
                    vi = safe_translate(d)
                    result_text.insert(tk.END, f"   • {d}\n")
                    result_text.insert(tk.END, f"     → {vi}\n", "vi_style")
                result_text.insert(tk.END, "\n")

        if not found:
            result_text.insert(tk.END, "Không tìm thấy phrasal verb.\n")

    except Exception as e:
        result_text.insert(tk.END, f"⚠️ Lỗi: {e}\n")


# ====== UI SETUP ======
root = tk.Tk()
root.title("📘 Smart Minimal Dictionary v6")
root.geometry("700x620")
root.configure(bg="#fde4ec")  # nền hồng nhạt

# Title
title_label = tk.Label(
    root,
    text="Smart Minimal Dictionary",
    font=("Roboto", 20, "bold"),
    bg="#fde4ec",
    fg="#ad1457",
)
title_label.pack(pady=15)

# Input Frame
frame = tk.Frame(root, bg="#fde4ec", highlightthickness=0, bd=0)
frame.pack(pady=10)

entry = tk.Entry(
    frame,
    width=45,
    font=("Roboto", 13),
    relief="flat",
    bg="#fff0f6",
    highlightthickness=2,
    highlightbackground="#f8bbd0",
    highlightcolor="#f48fb1",
    bd=0,
)
entry.pack(side=tk.LEFT, padx=5, ipady=6)
entry.focus()

# Button Frame
button_frame = tk.Frame(root, bg="#fde4ec")
button_frame.pack(pady=5)

def create_pink_button(text, command):
    return tk.Button(
        button_frame,
        text=text,
        command=command,
        font=("Roboto", 11, "bold"),
        bg="#f8bbd0",
        fg="#880e4f",
        activebackground="#f48fb1",
        activeforeground="white",
        relief="flat",
        bd=0,
        padx=15,
        pady=6,
        cursor="hand2",
        highlightthickness=0,
    )

btn_meaning = create_pink_button("🔍 Tra nghĩa", lookup_meaning)
btn_meaning.grid(row=0, column=0, padx=8)

btn_synant = create_pink_button("🟢 Đồng / Trái nghĩa", lookup_syn_ant)
btn_synant.grid(row=0, column=1, padx=8)

btn_phrasal = create_pink_button("📘 Phrasal Verb", lookup_phrasal)
btn_phrasal.grid(row=0, column=2, padx=8)

# Result Box
result_frame = tk.Frame(root, bg="#fde4ec", highlightthickness=0)
result_frame.pack(fill="both", expand=True, padx=20, pady=10)

result_text = tk.Text(
    result_frame,
    wrap="word",
    font=("Roboto", 12),
    height=25,
    relief="flat",
    bg="#fff0f6",
    fg="#212121",
    insertbackground="#ad1457",
    padx=10,
    pady=10,
    bd=0,
    highlightthickness=2,
    highlightbackground="#f8bbd0",
)
result_text.pack(fill="both", expand=True)

# Tag Styles
result_text.tag_configure("word_style", font=("Roboto", 13, "bold"), foreground="#880e4f")
result_text.tag_configure("vi_style", foreground="#00897b")
result_text.tag_configure("syn_style", foreground="#1565c0")
result_text.tag_configure("ant_style", foreground="#d84315")


root.mainloop()
