import requests
import tkinter as tk
from tkinter import ttk, messagebox
from deep_translator import GoogleTranslator
import urllib.parse
import time
import threading
import json
import os

# ====== AUTO SCALE UI ======
def get_scale_factor(base_width=1366):
    screen_width = root.winfo_screenwidth() if 'root' in globals() else 1366
    raw_scale = screen_width / base_width
    return max(0.8, min(1.6, raw_scale * 1.2))  # 👈 nhân thêm 1.2 để to hơn

def scale(value, scale_factor):
    """Scale giá trị (kích thước, font size, padding, ...) theo hệ số"""
    return int(value * scale_factor)

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
        time.sleep(0.5)
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

# ====== FEATURE 1: TỪ ĐIỂN NGHĨA ======
TRANSLATE_DELAY = 0.25
TYPING_DELAY_MS = 10

def lookup_meaning():
    word = entry.get().strip()
    if not word or word == placeholder_text:
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
                for entry_data in data:
                    hw = entry_data.get("hwi", {}).get("hw", "")
                    fl = entry_data.get("fl", "")
                    defs = entry_data.get("shortdef", [])
                    if hw:
                        result_text.insert(tk.END, f"{hw} ({fl})\n", "word_style")
                    for d in defs:
                        result_text.insert(tk.END, f"   • {d}\n")
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
                        idx = result_text.search(placeholder, "1.0", tk.END)
                        if not idx:
                            return
                        result_text.delete(idx, f"{idx} + {len(placeholder)} chars")

                        def type_char(pos_index, i=0):
                            if i >= len(vi):
                                return
                            result_text.insert(pos_index, vi[i], "vi_style")
                            next_pos = result_text.index(f"{pos_index} + 1 chars")
                            root.after(TYPING_DELAY_MS, lambda: type_char(next_pos, i+1))

                        type_char(idx, 0)

                    root.after(0, start_typing)

            threading.Thread(target=translate_thread, daemon=True).start()

        except Exception as e:
            root.after(0, lambda: result_text.insert(tk.END, f"⚠️ Lỗi: {e}\n"))

    threading.Thread(target=worker, daemon=True).start()

# ====== FEATURE 2: ĐỒNG/TRÁI NGHĨA ======
def lookup_syn_ant():
    word = entry.get().strip()
    if not word or word == placeholder_text:
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

# ====== FEATURE 3: PHRASAL VERB ======
def lookup_phrasal():
    word = entry.get().strip()
    if not word or word == placeholder_text:
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
            if " " in meta_id:
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

# ====== ESSAY MANAGER ======
ESSAY_FILE = "essays.json"

def load_essays():
    if not os.path.exists(ESSAY_FILE):
        return {}
    with open(ESSAY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_essays(data):
    with open(ESSAY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

essays = load_essays()

def open_essay_window():
    essay_win = tk.Toplevel(root)
    essay_win.title("📚 Bài văn mẫu")
    essay_win.geometry("700x600")
    essay_win.configure(bg="#fde4ec")

    title = tk.Label(
        essay_win,
        text="📚 Danh sách bài văn mẫu",
        font=("Roboto", scale(18, scale_factor), "bold"),
        bg="#fde4ec",
        fg="#ad1457"
    )
    title.pack(pady=scale(15, scale_factor))

    # ====== Nút quay lại màn hình chính ======
    back_main_btn = tk.Button(
        essay_win,
        text="⬅ Về màn hình chính",
        command=essay_win.destroy,
        font=("Roboto", scale(11, scale_factor), "bold"),
        bg="#f8bbd0",
        fg="#880e4f",
        activebackground="#f48fb1",
        activeforeground="white",
        relief="flat",
        padx=scale(15, scale_factor),
        pady=scale(6, scale_factor),
        cursor="hand2"
    )
    back_main_btn.pack(pady=scale(5, scale_factor))

    # ====== Frame chứa danh sách bài ======
    container = tk.Frame(essay_win, bg="#fde4ec")
    container.pack(fill="both", expand=True, padx=scale(20, scale_factor), pady=10)

    def refresh_list():
        for widget in container.winfo_children():
            widget.destroy()

        for name in essays.keys():
            frame_item = tk.Frame(container, bg="#fff0f6", bd=0, relief="flat",
                                  highlightbackground="#f8bbd0", highlightthickness=2)
            frame_item.pack(fill="x", pady=scale(6, scale_factor))

            btn = tk.Button(
                frame_item,
                text=name,
                font=("Roboto", scale(12, scale_factor), "bold"),
                bg="#f8bbd0",
                fg="#880e4f",
                relief="flat",
                bd=0,
                cursor="hand2",
                activebackground="#f48fb1",
                activeforeground="white",
                command=lambda n=name: open_essay_detail(n)
            )
            btn.pack(fill="x", ipadx=scale(5, scale_factor), ipady=scale(8, scale_factor))

    def open_essay_detail(name):
        detail_win = tk.Toplevel(essay_win)
        detail_win.title(name)
        detail_win.geometry("700x600")
        detail_win.configure(bg="#fde4ec")

        lbl_title = tk.Label(detail_win, text=name, font=("Roboto", scale(18, scale_factor), "bold"),
                             bg="#fde4ec", fg="#ad1457")
        lbl_title.pack(pady=scale(10, scale_factor))

        txt = tk.Text(
            detail_win,
            wrap="word",
            font=("Roboto", scale(12, scale_factor)),
            bg="#fff0f6",
            fg="#212121",
            padx=scale(10, scale_factor),
            pady=scale(10, scale_factor),
            relief="flat",
            height=25,
            highlightthickness=2,
            highlightbackground="#f8bbd0"
        )
        txt.pack(fill="both", expand=True, padx=scale(20, scale_factor), pady=scale(10, scale_factor))
        txt.insert(tk.END, essays[name])
        txt.config(state="disabled")  # chỉ cho đọc

        back_btn = tk.Button(
            detail_win,
            text="🔙 Quay lại danh sách",
            command=detail_win.destroy,
            font=("Roboto", scale(11, scale_factor), "bold"),
            bg="#f8bbd0",
            fg="#880e4f",
            activebackground="#f48fb1",
            activeforeground="white",
            relief="flat",
            padx=scale(15, scale_factor),
            pady=scale(6, scale_factor),
            cursor="hand2"
        )
        back_btn.pack(pady=scale(10, scale_factor))

    def add_new_essay_popup():
        popup = tk.Toplevel(essay_win)
        popup.title("➕ Thêm bài mới")
        popup.geometry("500x400")
        popup.configure(bg="#fde4ec")

        tk.Label(popup, text="Tiêu đề bài:", bg="#fde4ec", fg="#880e4f",
                 font=("Roboto", scale(12, scale_factor), "bold")).pack(pady=scale(5, scale_factor))
        title_entry = tk.Entry(popup, font=("Roboto", scale(12, scale_factor)), width=40, relief="flat",
                               bg="#fff0f6", highlightthickness=2, highlightbackground="#f8bbd0")
        title_entry.pack(pady=scale(5, scale_factor))

        tk.Label(popup, text="Nội dung:", bg="#fde4ec", fg="#880e4f",
                 font=("Roboto", scale(12, scale_factor), "bold")).pack(pady=scale(5, scale_factor))
        content_text = tk.Text(popup, wrap="word", font=("Roboto", scale(11, scale_factor)), height=10,
                               relief="flat", bg="#fff0f6", highlightthickness=2,
                               highlightbackground="#f8bbd0")
        content_text.pack(pady=scale(5, scale_factor), padx=scale(10, scale_factor), fill="both", expand=True)

        def save_new():
            title = title_entry.get().strip()
            content = content_text.get("1.0", tk.END).strip()
            if not title or not content:
                messagebox.showwarning("Cảnh báo", "Vui lòng nhập đủ tiêu đề và nội dung.")
                return
            essays[title] = content
            save_essays(essays)
            messagebox.showinfo("Thành công", f"Đã thêm bài: {title}")
            popup.destroy()
            refresh_list()

        save_btn = tk.Button(
            popup,
            text="💾 Lưu bài mới",
            command=save_new,
            font=("Roboto", scale(11, scale_factor), "bold"),
            bg="#f8bbd0",
            fg="#880e4f",
            activebackground="#f48fb1",
            activeforeground="white",
            relief="flat",
            padx=scale(15, scale_factor),
            pady=scale(6, scale_factor),
            cursor="hand2"
        )
        save_btn.pack(pady=scale(10, scale_factor))

    # ====== Nút thêm bài mới ======
    add_btn = tk.Button(
        essay_win,
        text="➕ Thêm bài mới",
        command=add_new_essay_popup,
        font=("Roboto", scale(11, scale_factor), "bold"),
        bg="#f8bbd0",
        fg="#880e4f",
        activebackground="#f48fb1",
        activeforeground="white",
        relief="flat",
        padx=scale(15, scale_factor),
        pady=scale(6, scale_factor),
        cursor="hand2"
    )
    add_btn.pack(pady=scale(10, scale_factor))

    refresh_list()

# ====== UI SETUP ======
# ====== INITIALIZE ROOT FIRST TO DETECT SCREEN SIZE ======
root = tk.Tk()
scale_factor = get_scale_factor()

# Cập nhật hệ số DPI (Windows thường mặc định là 1.0, nhưng có thể khác)
root.tk.call('tk', 'scaling', scale_factor)

root.title("📘 Smart Minimal Dictionary v6")
root.geometry(f"{scale(700, scale_factor)}x{scale(500, scale_factor)}")
root.configure(bg="#fde4ec")

title_label = tk.Label(root, text="Smart Minimal Dictionary", font=("Roboto", scale(20, scale_factor), "bold"), bg="#fde4ec", fg="#ad1457")
title_label.pack(pady=scale(15, scale_factor))

frame = tk.Frame(root, bg="#fde4ec")
frame.pack(pady=scale(10, scale_factor))

entry = tk.Entry(frame, width=45, font=("Roboto", scale(13, scale_factor)), relief="flat", bg="#fff0f6",
                 highlightthickness=2, highlightbackground="#f8bbd0", highlightcolor="#f48fb1")
entry.pack(side=tk.LEFT, padx=scale(5, scale_factor), ipady=scale(6, scale_factor))

# Placeholder setup
placeholder_text = "Nhập từ hoặc cụm từ tiếng Anh..."
placeholder_color = "#b5b5b5"
default_text_color = "#880e4f"

def set_placeholder():
    entry.insert(0, placeholder_text)
    entry.config(fg=placeholder_color)

def clear_placeholder(event=None):
    if entry.get() == placeholder_text:
        entry.delete(0, tk.END)
        entry.config(fg=default_text_color)

def restore_placeholder(event=None):
    if entry.get() == "":
        set_placeholder()

entry.bind("<FocusIn>", clear_placeholder)
entry.bind("<FocusOut>", restore_placeholder)
set_placeholder()

# Buttons
button_frame = tk.Frame(root, bg="#fde4ec")
button_frame.pack(pady=scale(5, scale_factor))

def create_pink_button(text, command):
    btn = tk.Button(button_frame, text=text, command=command,
                    font=("Roboto", scale(11, scale_factor), "bold"), bg="#f8bbd0", fg="#880e4f",
                    activebackground="#f48fb1", activeforeground="white",
                    relief="flat", bd=0, padx=scale(15, scale_factor), pady=scale(6, scale_factor), cursor="hand2")

    def on_enter(e): btn.config(bg="#f06292", fg="white")
    def on_leave(e): btn.config(bg="#f8bbd0", fg="#880e4f")
    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)
    return btn

btn_meaning = create_pink_button("🔍 Tra nghĩa", lookup_meaning)
btn_meaning.grid(row=0, column=0, padx=scale(8, scale_factor))

btn_synant = create_pink_button("🟢 Đồng / Trái nghĩa", lookup_syn_ant)
btn_synant.grid(row=0, column=1, padx=scale(8, scale_factor))

btn_phrasal = create_pink_button("📘 Phrasal Verb", lookup_phrasal)
btn_phrasal.grid(row=0, column=2, padx=scale(8, scale_factor))

btn_essays = create_pink_button("📚 Bài văn mẫu", open_essay_window)
btn_essays.grid(row=0, column=3, padx=scale(8, scale_factor))

# Result text
result_frame = tk.Frame(root, bg="#fde4ec")
result_frame.pack(fill="both", expand=True, padx=scale(20, scale_factor), pady=scale(10, scale_factor))

result_text = tk.Text(result_frame, wrap="word", font=("Roboto", scale(12, scale_factor)), height=25, relief="flat",
                      bg="#fff0f6", fg="#212121", insertbackground="#ad1457", padx=scale(10, scale_factor), pady=scale(10, scale_factor),
                      bd=0, highlightthickness=2, highlightbackground="#f8bbd0")
result_text.pack(fill="both", expand=True)

result_text.tag_configure("word_style", font=("Roboto", scale(13, scale_factor), "bold"), foreground="#880e4f")
result_text.tag_configure("vi_style", foreground="#00897b")
result_text.tag_configure("syn_style", foreground="#1565c0")
result_text.tag_configure("ant_style", foreground="#d84315")

root.mainloop()
