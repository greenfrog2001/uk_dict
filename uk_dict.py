import requests
import tkinter as tk
from tkinter import ttk, messagebox
from googletrans import Translator
import urllib.parse

# ====== CONFIG ======
DICTIONARY_KEY = "e1fd3412-7310-4f5f-a50d-9b0c257660e1"
THESAURUS_KEY = "816b0b3b-c13c-4179-aa49-8c0c98aa26ff"

API_URL_DICT = "https://www.dictionaryapi.com/api/v3/references/collegiate/json/{}?key={}"
API_URL_THES = "https://www.dictionaryapi.com/api/v3/references/thesaurus/json/{}?key={}"

translator = Translator()


# ====== COMMON FUNCTION ======
def clear_result():
    result_text.delete(1.0, tk.END)


def fetch_api(word, url_template, key):
    """Gọi API và trả về dữ liệu JSON"""
    encoded_word = urllib.parse.quote(word)
    url = url_template.format(encoded_word, key)
    res = requests.get(url)
    res.raise_for_status()
    return res.json()


# ====== FEATURE 1: TRA CỨU NGHĨA ======
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

        shown_defs = 0
        for entry_data in data:
            hw = entry_data.get("hwi", {}).get("hw", "")
            fl = entry_data.get("fl", "")
            defs = entry_data.get("shortdef", [])

            phrase = entry_data.get("meta", {}).get("id", "")
            if ":" in phrase:
                phrase = phrase.split(":")[0]
            display_title = phrase if " " in word else hw

            if display_title:
                result_text.insert(tk.END, f"{display_title} ({fl})\n", "word_style")

            for d in defs:
                shown_defs += 1
                result_text.insert(tk.END, f"   • {d}\n")
                vi = translator.translate(d, src="en", dest="vi").text
                result_text.insert(tk.END, f"     → {vi}\n", "vi_style")
            result_text.insert(tk.END, "\n")

        if shown_defs == 0:
            result_text.insert(tk.END, "Không tìm thấy định nghĩa.\n")

    except Exception as e:
        result_text.insert(tk.END, f"⚠️ Lỗi: {e}\n")


# ====== FEATURE 2: TRA CỨU ĐỒNG NGHĨA & TRÁI NGHĨA ======
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


# ====== FEATURE 3: TRA CỨU PHRASAL VERB ======
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
            if " " in meta_id:  # cụm có dấu cách => phrasal
                found = True
                defs = entry_data.get("shortdef", [])
                result_text.insert(tk.END, f"{meta_id}\n", "word_style")
                for d in defs:
                    result_text.insert(tk.END, f"   • {d}\n")
                    vi = translator.translate(d, src="en", dest="vi").text
                    result_text.insert(tk.END, f"     → {vi}\n", "vi_style")
                result_text.insert(tk.END, "\n")

        if not found:
            result_text.insert(tk.END, "Không tìm thấy phrasal verb.\n")

    except Exception as e:
        result_text.insert(tk.END, f"⚠️ Lỗi: {e}\n")


# ====== UI SETUP ======
root = tk.Tk()
root.title("📘 Smart Minimal Dictionary v3")
root.geometry("700x620")
root.configure(bg="#f6f6f6")

# Title
title_label = ttk.Label(root, text="Smart Minimal Dictionary", font=("Helvetica", 20, "bold"), background="#f6f6f6")
title_label.pack(pady=15)

# Input Frame
frame = ttk.Frame(root)
frame.pack(pady=10)

entry = ttk.Entry(frame, width=45, font=("Helvetica", 13))
entry.pack(side=tk.LEFT, padx=5)
entry.focus()

# --- Buttons Row ---
button_frame = ttk.Frame(root)
button_frame.pack(pady=5)

btn_meaning = ttk.Button(button_frame, text="🔍 Tra nghĩa", command=lookup_meaning)
btn_meaning.grid(row=0, column=0, padx=8)

btn_synant = ttk.Button(button_frame, text="🟢 Đồng / Trái nghĩa", command=lookup_syn_ant)
btn_synant.grid(row=0, column=1, padx=8)

btn_phrasal = ttk.Button(button_frame, text="📘 Phrasal Verb", command=lookup_phrasal)
btn_phrasal.grid(row=0, column=2, padx=8)

# Result Box
result_text = tk.Text(root, wrap="word", font=("Helvetica", 12), height=25, relief="flat", bg="#f9f9f9", padx=10, pady=10)
result_text.pack(fill="both", expand=True, padx=20, pady=10)

# Styles
style = ttk.Style()
style.configure("TButton", font=("Helvetica", 11), padding=6)
style.configure("TEntry", padding=5)
style.configure("TLabel", background="#f6f6f6")

result_text.tag_configure("word_style", font=("Helvetica", 13, "bold"))
result_text.tag_configure("vi_style", foreground="#00897b")
result_text.tag_configure("syn_style", foreground="#1e88e5")
result_text.tag_configure("ant_style", foreground="#d32f2f")

root.mainloop()
