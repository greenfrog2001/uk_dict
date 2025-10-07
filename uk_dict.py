import requests
import tkinter as tk
from tkinter import ttk, messagebox
from googletrans import Translator
# from playsound import playsound
import tempfile
import os
import urllib.parse

# ========== CONFIG ==========
# These two keys need to be put in a file.
DICTIONARY_KEY = "e1fd3412-7310-4f5f-a50d-9b0c257660e1"
THESAURUS_KEY = "816b0b3b-c13c-4179-aa49-8c0c98aa26ff"
API_KEY = DICTIONARY_KEY  # Merriam-Webster Collegiate API key
API_URL = "https://www.dictionaryapi.com/api/v3/references/collegiate/json/{}?key={}"

translator = Translator()

# ========== FUNCTIONS ==========
def lookup_word():
    word = entry.get().strip()
    if not word:
        messagebox.showwarning("Warning", "Vui lòng nhập từ hoặc cụm cần tra.")
        return

    result_text.delete(1.0, tk.END)
    result_text.insert(tk.END, f"🔎 Tra cứu: {word}\n\n")

    encoded_word = urllib.parse.quote(word)  # xử lý phrasal verb có dấu cách
    url = API_URL.format(encoded_word, API_KEY)

    try:
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()

        if isinstance(data, list) and len(data) == 0:
            result_text.insert(tk.END, "❌ Không tìm thấy kết quả.\n")
            return

        if isinstance(data[0], str):
            result_text.insert(tk.END, "❌ Không tìm thấy. Gợi ý:\n")
            for s in data:
                result_text.insert(tk.END, f" - {s}\n")
            return

        all_synonyms = set()
        audio_link = None
        shown_defs = 0

        for entry_data in data:
            hw = entry_data.get("hwi", {}).get("hw", "")
            fl = entry_data.get("fl", "")
            defs = entry_data.get("shortdef", [])
            syns = entry_data.get("meta", {}).get("syns", [])

            # Nếu có phần "phrase"
            phrase = entry_data.get("meta", {}).get("id", "")
            if ":" in phrase:  # ví dụ: "take off:1"
                phrase = phrase.split(":")[0]

            # Hiển thị tiêu đề từ hoặc cụm
            display_title = phrase if " " in word else hw
            if display_title:
                result_text.insert(tk.END, f"{display_title} ({fl})\n", "word_style")

            for d in defs:
                shown_defs += 1
                result_text.insert(tk.END, f"   • {d}\n")
                translated = translator.translate(d, src="en", dest="vi").text
                result_text.insert(tk.END, f"     → {translated}\n", "vi_style")

            for group in syns:
                for s in group:
                    all_synonyms.add(s)

            # Lấy link phát âm (nếu có)
            # if not audio_link:
            #     sound_data = entry_data.get("hwi", {}).get("prs", [])
            #     if sound_data:
            #         audio = sound_data[0].get("sound", {}).get("audio")
            #         if audio:
            #             subdir = "gg" if audio.startswith("gg") else audio[0]
            #             audio_link = f"https://media.merriam-webster.com/audio/prons/en/us/mp3/{subdir}/{audio}.mp3"

            result_text.insert(tk.END, "\n")

        if shown_defs == 0:
            result_text.insert(tk.END, "Không tìm thấy định nghĩa cho từ này.\n")

        # Từ đồng nghĩa
        if all_synonyms:
            result_text.insert(tk.END, "🟢 Từ đồng nghĩa:\n", "word_style")
            result_text.insert(tk.END, ", ".join(sorted(all_synonyms)) + "\n\n")

        # Nút phát âm
        # if audio_link:
        #     play_button.config(state="normal")
        #     play_button.audio_link = audio_link
        # else:
        #     play_button.config(state="disabled")

    except Exception as e:
        result_text.insert(tk.END, f"⚠️ Lỗi: {e}")

# def play_audio():
#     link = getattr(play_button, "audio_link", None)
#     if not link:
#         messagebox.showinfo("Thông báo", "Không có âm thanh cho từ này.")
#         return
#     try:
#         audio_data = requests.get(link)
#         audio_data.raise_for_status()
#         with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
#             tmp.write(audio_data.content)
#             tmp_path = tmp.name
#         playsound(tmp_path)
#         os.remove(tmp_path)
#     except Exception as e:
#         messagebox.showerror("Lỗi phát âm", str(e))

# ========== UI SETUP ==========
root = tk.Tk()
root.title("📘 Smart Minimal Dictionary v2")
root.geometry("650x580")
root.configure(bg="#f6f6f6")

# Title
title_label = ttk.Label(root, text="Smart Minimal Dictionary", font=("Helvetica", 20, "bold"), background="#f6f6f6")
title_label.pack(pady=10)

# Input Frame
frame = ttk.Frame(root)
frame.pack(pady=10)

entry = ttk.Entry(frame, width=45, font=("Helvetica", 13))
entry.pack(side=tk.LEFT, padx=5)
entry.focus()

search_btn = ttk.Button(frame, text="Tra cứu", command=lookup_word)
search_btn.pack(side=tk.LEFT, padx=5)

# play_button = ttk.Button(frame, text="🔊 Phát âm", command=play_audio, state="disabled")
# play_button.pack(side=tk.LEFT, padx=5)

# Result Text
result_text = tk.Text(root, wrap="word", font=("Helvetica", 12), height=22, relief="flat", bg="#f9f9f9", padx=10, pady=10)
result_text.pack(fill="both", expand=True, padx=20, pady=10)

# Style
style = ttk.Style()
style.configure("TButton", font=("Helvetica", 11), padding=6)
style.configure("TEntry", padding=5)
style.configure("TLabel", background="#f6f6f6")

# Text tag for styling
result_text.tag_configure("word_style", font=("Helvetica", 13, "bold"))
result_text.tag_configure("vi_style", foreground="#00897b")

root.mainloop()
