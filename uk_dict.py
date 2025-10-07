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
def lookup_meaning():
    word = entry.get().strip()
    if not word:
        messagebox.showwarning("Cảnh báo", "Vui lòng nhập từ hoặc cụm cần tra.")
        return

    clear_result()
    result_text.insert(tk.END, f"🔎 Tra cứu nghĩa của: {word}\n\n")

    try:
        data = fetch_api(word, API_URL_DICT, DICTIONARY_KEY)
        if not data:
            result_text.insert(tk.END, "❌ Không tìm thấy kết quả.\n")
            return

        if isinstance(data[0], str):
            result_text.insert(tk.END, "❌ Không tìm thấy. Gợi ý:\n")
            for s in data:
                result_text.insert(tk.END, f" - {s}\n")
            return

        all_defs = []
        for entry_data in data:
            hw = entry_data.get("hwi", {}).get("hw", "")
            fl = entry_data.get("fl", "")
            defs = entry_data.get("shortdef", [])
            if defs:
                all_defs.extend(defs)

        vi_defs = batch_translate(all_defs)

        for i, entry_data in enumerate(data):
            hw = entry_data.get("hwi", {}).get("hw", "")
            fl = entry_data.get("fl", "")
            defs = entry_data.get("shortdef", [])

            if hw:
                result_text.insert(tk.END, f"{hw} ({fl})\n", "word_style")

            for d in defs:
                vi = safe_translate(d)
                result_text.insert(tk.END, f"   • {d}\n")
                result_text.insert(tk.END, f"     → {vi}\n", "vi_style")
            result_text.insert(tk.END, "\n")

    except Exception as e:
        result_text.insert(tk.END, f"⚠️ Lỗi: {e}\n")


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
root.title("📘 Smart Minimal Dictionary v5")
root.geometry("700x620")
root.configure(bg="#fde4ec")

# Title
title_label = ttk.Label(
    root,
    text="Smart Minimal Dictionary",
    font=("Roboto", 20, "bold"),
    background="#fde4ec",
    foreground="#ad1457",
)
title_label.pack(pady=15)

# Input Frame
frame = ttk.Frame(root, style="Rounded.TFrame")
frame.pack(pady=10)

entry = tk.Entry(
    frame,
    width=45,
    font=("Roboto", 13),
    relief="flat",
    bg="#fff0f6",
    highlightbackground="#f8bbd0",
    highlightcolor="#f48fb1",
    highlightthickness=2,
    bd=0,
)
entry.pack(side=tk.LEFT, padx=5, ipady=6)
entry.focus()

# Buttons
button_frame = ttk.Frame(root)
button_frame.pack(pady=5)

btn_style = ttk.Style()
btn_style.configure(
    "Rounded.TButton",
    font=("Roboto", 11),
    padding=8,
    background="#f8bbd0",
    relief="flat",
)

btn_meaning = ttk.Button(button_frame, text="🔍 Tra nghĩa", command=lookup_meaning, style="Rounded.TButton")
btn_meaning.grid(row=0, column=0, padx=8)

btn_synant = ttk.Button(button_frame, text="🟢 Đồng / Trái nghĩa", command=lookup_syn_ant, style="Rounded.TButton")
btn_synant.grid(row=0, column=1, padx=8)

btn_phrasal = ttk.Button(button_frame, text="📘 Phrasal Verb", command=lookup_phrasal, style="Rounded.TButton")
btn_phrasal.grid(row=0, column=2, padx=8)

# Result Box
result_frame = tk.Frame(root, bg="#fff0f6", highlightbackground="#f8bbd0", highlightthickness=2)
result_frame.pack(fill="both", expand=True, padx=20, pady=10)

result_text = tk.Text(result_frame, wrap="word", font=("Roboto", 12), height=25,
                      relief="flat", bg="#fff0f6", padx=10, pady=10, bd=0)
result_text.pack(fill="both", expand=True)

# Tag Styles
result_text.tag_configure("word_style", font=("Roboto", 13, "bold"), foreground="#880e4f")
result_text.tag_configure("vi_style", foreground="#00897b")
result_text.tag_configure("syn_style", foreground="#1565c0")
result_text.tag_configure("ant_style", foreground="#d84315")

root.mainloop()
