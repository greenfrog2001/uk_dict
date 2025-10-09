import requests
import tkinter as tk
from tkinter import ttk, messagebox
from deep_translator import GoogleTranslator
import urllib.parse
import time
import threading
import json
import os

# ====== GLOBAL FONT CONFIG ======
BASE_FONT = "Segoe UI"  # hoặc "Helvetica" nếu dùng macOS

# ====== AUTO SCALE UI ======
def get_scale_factor(base_width=1366):
    screen_width = root.winfo_screenwidth() if 'root' in globals() else 1366
    raw_scale = screen_width / base_width
    # KHÔI PHỤC hệ số 1.2 để cỡ chữ đủ lớn, và cân chỉnh kích thước cửa sổ chính bên dưới
    return max(0.8, min(1.6, raw_scale * 1.2))  

def scale(value, scale_factor):
    """Scale giá trị (kích thước, font size, padding, ...) theo hệ số"""
    return int(value * scale_factor)

# ====== CONFIG ======
DICTIONARY_KEY = "e1fd3412-7310-4f5f-a50d-9b0c257660e1"
THESAURUS_KEY = "816b0b3b-c13c-4179-aa49-8c0c98aa26ff"

API_URL_DICT = "https://www.dictionaryapi.com/api/v3/references/collegiate/json/{}?key={}"
API_URL_THES = "https://www.dictionaryapi.com/api/v3/references/thesaurus/json/{}?key={}"

translator = GoogleTranslator(source="en", target="vi")

# Global placeholder for the temporary save button frame
save_btn_placeholder_frame = None

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
        # print("⚠️ Lỗi dịch:", e) # Bỏ comment nếu muốn debug
        return text

# ====== COMMON FUNCTION ======
def clear_result():
    result_text.delete(1.0, tk.END)
    clear_save_button() # Clear save button when starting a new search

def fetch_api(word, url_template, key):
    encoded_word = urllib.parse.quote(word)
    url = url_template.format(encoded_word, key)
    res = requests.get(url)
    res.raise_for_status()
    return res.json()

# ====== ESSAY MANAGER & FLASHCARD MANAGER DATA ======
ESSAY_FILE = "essays.json"
essays = {} 

def load_essays():
    global essays
    if not os.path.exists(ESSAY_FILE):
        essays = {}
        return {}
    try:
        with open(ESSAY_FILE, "r", encoding="utf-8") as f:
            essays = json.load(f)
            return essays
    except json.JSONDecodeError:
        essays = {}
        return {}

def save_essays(data):
    with open(ESSAY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

load_essays()

FLASHCARD_FILE = "flashcards.json"
flashcards = {}

def load_flashcards():
    global flashcards
    if not os.path.exists(FLASHCARD_FILE):
        flashcards = {}
        return {}
    try:
        with open(FLASHCARD_FILE, "r", encoding="utf-8") as f:
            flashcards = json.load(f)
            return flashcards
    except json.JSONDecodeError:
        flashcards = {}
        return {}

def save_flashcards_to_file(data):
    with open(FLASHCARD_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
load_flashcards()

def clear_save_button():
    global save_btn_placeholder_frame
    # Kiểm tra xem frame có tồn tại và chưa bị hủy không
    if save_btn_placeholder_frame and save_btn_placeholder_frame.winfo_exists():
        save_btn_placeholder_frame.destroy()
        save_btn_placeholder_frame = None

def save_word_to_flashcards(word, definition_vi, btn_widget):
    global flashcards
    
    # Simple definition cleanup
    if definition_vi.startswith("→ "):
        definition_vi = definition_vi[2:].strip()
        
    if word in flashcards:
        messagebox.showinfo("Thông báo", f"Từ '{word}' đã có trong Flashcards!")
        return
        
    flashcards[word] = definition_vi
    save_flashcards_to_file(flashcards)
    
    # Update the button state to 'Saved' and disable the hover effect
    btn_widget.config(
        text="⭐ Đã lưu", 
        command=lambda: None, # Vô hiệu hóa nút
        bg="#a5d6a7", 
        fg="#1b5e20", 
        activebackground="#a5d6a7", 
        activeforeground="#1b5e20"
    )
    btn_widget.unbind("<Enter>")
    btn_widget.unbind("<Leave>")
    
    messagebox.showinfo("Thành công", f"Đã thêm từ '{word}' vào Flashcards!")

# ====== FEATURE 1: TỪ ĐIỂN NGHĨA - Đã FIX lỗi UnboundLocalError ======
TRANSLATE_DELAY = 0.25
TYPING_DELAY_MS = 10

def lookup_meaning():
    word = entry.get().strip()
    if not word or word == placeholder_text:
        messagebox.showwarning("Cảnh báo", "Vui lòng nhập từ hoặc cụm cần tra.")
        return

    clear_result() # Gọi clear_save_button() ở đây
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

            # 1. Lấy nghĩa tiếng Việt đầu tiên để lưu Flashcard (chạy trong worker thread)
            first_definition_vi = None
            if not isinstance(data[0], str):
                first_entry = data[0]
                if first_entry.get("shortdef"):
                    first_definition_en = first_entry["shortdef"][0]
                    first_definition_vi = safe_translate(first_definition_en)
            
            # 2. Hiển thị kết quả tiếng Anh và placeholder (chạy trong main thread)
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

            # 3. Thêm nút Lưu Từ (chạy trong main thread)
            def add_save_button_to_ui(word, definition):
                global save_btn_placeholder_frame
                if not definition: return 
                
                is_saved = word in flashcards
                
                clear_save_button() # Đảm bảo nút cũ bị xóa
                
                save_btn_placeholder_frame = tk.Frame(root, bg="#fde4ec")
                save_btn_placeholder_frame.pack(before=result_frame, pady=scale(10, scale_factor)) 
                
                save_text = "⭐ Lưu từ" if not is_saved else "⭐ Đã lưu"
                save_bg = "#f8bbd0" if not is_saved else "#a5d6a7"
                save_fg = "#880e4f" if not is_saved else "#1b5e20"
                
                # BƯỚC 1: Tạo nút trước với command rỗng
                btn_save = tk.Button(
                    save_btn_placeholder_frame, 
                    text=save_text, 
                    command=lambda: None, # Gán lệnh rỗng ban đầu để tránh lỗi
                    font=(BASE_FONT, scale(11, scale_factor), "bold"),
                    bg=save_bg, 
                    fg=save_fg,
                    activebackground=save_bg, 
                    activeforeground=save_fg,
                    relief="flat", bd=0, 
                    padx=scale(15, scale_factor), 
                    pady=scale(6, scale_factor), 
                    cursor="hand2"
                )

                # BƯỚC 2: Gán lệnh thực tế sau khi nút đã được tạo
                if not is_saved:
                    # Gán command gọi hàm save_word_to_flashcards, truyền button object
                    cmd = lambda w=word, d=definition, b=btn_save: save_word_to_flashcards(w, d, b)
                    btn_save.config(command=cmd)
                    add_hover_effect(btn_save, save_bg, "#f48fb1")
                else:
                    # Nếu đã lưu, command vẫn là lambda: None, và loại bỏ hover
                    btn_save.unbind("<Enter>")
                    btn_save.unbind("<Leave>")
                    
                # BƯỚC 3: Hiển thị nút
                btn_save.pack()
                
            if first_definition_vi:
                root.after(0, lambda: add_save_button_to_ui(word, first_definition_vi))

            # 4. Hiệu ứng dịch và gõ chữ (chạy trong translate thread)
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

# ====== FEATURE 2: ĐỒNG/TRÁI NGHĨA (Giữ nguyên) ======
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

# ====== FEATURE 3: PHRASAL VERB (Giữ nguyên) ======
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

# ====== UI UTILITIES (Hover, Animate) ======
def hex_to_rgb(hex_color):
    """Chuyển mã hex (#rrggbb) sang tuple RGB (r,g,b)."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb):
    """Chuyển tuple RGB (r,g,b) sang mã hex."""
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

def smooth_color_transition(widget, from_color, to_color, steps=15, delay=15):
    """Hiệu ứng chuyển màu mượt mà (có hủy animation cũ tránh giật)."""
    if hasattr(widget, "_hover_job") and widget._hover_job:
        widget.after_cancel(widget._hover_job)

    from_rgb = hex_to_rgb(from_color)
    to_rgb = hex_to_rgb(to_color)

    def step(i=0):
        if i > steps:
            widget._hover_job = None
            return
        ratio = i / steps
        new_rgb = tuple(int(from_rgb[j] + (to_rgb[j] - from_rgb[j]) * ratio) for j in range(3))
        new_color = rgb_to_hex(new_rgb)
        widget.config(bg=new_color, activebackground=new_color)
        widget._hover_job = widget.after(delay, step, i + 1)

    step()

def add_hover_effect(widget, normal_color, hover_color):
    """Thêm hiệu ứng hover mượt mà, tránh giật."""
    widget._hover_job = None
    widget.bind("<Enter>", lambda e: smooth_color_transition(widget, normal_color, hover_color))
    widget.bind("<Leave>", lambda e: smooth_color_transition(widget, hover_color, normal_color))

# Thêm hiệu ứng phóng to và fade-in khi mở cửa sổ con
def animate_zoom_fade_in(window, duration=250, steps=15, scale_start=0.9, alpha_start=0.0):
    window.update_idletasks()
    step_delay = duration // steps

    w = window.winfo_width()
    h = window.winfo_height()
    x = window.winfo_x()
    y = window.winfo_y()

    if w <= 1 or h <= 1:
        try:
            geometry = window.geometry().split('+')[0]
            w, h = [int(v) for v in geometry.split('x')]
        except ValueError:
            # Fallback if geometry is not set properly
            w, h = 700, 600

    window.attributes("-alpha", alpha_start)

    def animate(step=0):
        ratio = scale_start + (1 - scale_start) * (step / steps)
        alpha = alpha_start + (1 - alpha_start) * (step / steps)

        new_w = int(w * ratio)
        new_h = int(h * ratio)
        new_x = x + (w - new_w) // 2
        new_y = y + (h - new_h) // 2

        window.geometry(f"{new_w}x{new_h}+{new_x}+{new_y}")
        window.attributes("-alpha", alpha)

        if step < steps:
            window.after(step_delay, animate, step + 1)
        else:
            window.geometry(f"{w}x{h}+{x}+{y}")
            window.attributes("-alpha", 1.0)

    animate()

# Hiệu ứng thu nhỏ và fade-out khi đóng cửa sổ con
def animate_zoom_fade_out(window, duration=250, steps=15, scale_end=0.9, alpha_end=0.0, on_complete=None):
    window.update_idletasks()
    step_delay = duration // steps

    w = window.winfo_width()
    h = window.winfo_height()
    x = window.winfo_x()
    y = window.winfo_y()

    def animate(step=0):
        ratio = 1 - (1 - scale_end) * (step / steps)
        alpha = 1 - (1 - alpha_end) * (step / steps)

        new_w = int(w * ratio)
        new_h = int(h * ratio)
        new_x = x + (w - new_w) // 2
        new_y = y + (h - new_h) // 2

        window.geometry(f"{new_w}x{new_h}+{new_x}+{new_y}")
        window.attributes("-alpha", alpha)

        if step < steps:
            window.after(step_delay, animate, step + 1)
        else:
            if on_complete:
                on_complete()

    animate()

def close_with_animation(win):
    animate_zoom_fade_out(win, on_complete=win.destroy)


# ====== FEATURE 4: FLASHCARDS MANAGER (Re-added) ======
CARD_FRONT_COLOR = "#f48fb1"
CARD_BACK_COLOR = "#880e4f"
CARD_TEXT_COLOR = "white"

def open_flashcard_manager():
    load_flashcards() 
    
    manager_win = tk.Toplevel(root)
    manager_win.title("🃏 Hệ thống Flashcards")
    # Đã giảm kích thước cơ sở
    manager_win.geometry(f"{scale(650, scale_factor)}x{scale(550, scale_factor)}") 
    manager_win.configure(bg="#fde4ec")
    manager_win.protocol("WM_DELETE_WINDOW", lambda: close_with_animation(manager_win))
    animate_zoom_fade_in(manager_win)
    
    # Title
    tk.Label(
        manager_win,
        text="🃏 Flashcards của bạn",
        font=(BASE_FONT, scale(18, scale_factor), "bold"),
        bg="#fde4ec",
        fg="#ad1457"
    ).pack(pady=scale(15, scale_factor))

    # Scrollable Container
    container = tk.Frame(manager_win, bg="#fde4ec")
    container.pack(fill="both", expand=True, padx=scale(20, scale_factor), pady=10)

    canvas = tk.Canvas(container, bg="#fde4ec", highlightthickness=0)
    scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg="#fde4ec")

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

    def resize_scroll_region(event):
        canvas.itemconfig(canvas_window, width=event.width)

    canvas.bind("<Configure>", resize_scroll_region)
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    list_frame = scrollable_frame
    
    # Card Flipping Logic
    def flip_card(card_label, english_word, vietnamese_meaning):
        """Lật thẻ giữa tiếng Anh và tiếng Việt"""
        current_text = card_label.cget("text")
        
        if current_text == english_word:
            # Flip to Back (VI)
            card_label.config(
                text=vietnamese_meaning, 
                bg=CARD_BACK_COLOR, 
                fg=CARD_TEXT_COLOR,
                font=(BASE_FONT, scale(14, scale_factor), "normal")
            )
        else:
            # Flip to Front (EN)
            card_label.config(
                text=english_word, 
                bg=CARD_FRONT_COLOR, 
                fg=CARD_TEXT_COLOR,
                font=(BASE_FONT, scale(16, scale_factor), "bold")
            )
        
    # Delete Logic
    def delete_flashcard(word, callback):
        global flashcards
        if messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn xóa từ '{word}' khỏi Flashcards?"):
            if word in flashcards:
                del flashcards[word]
                save_flashcards_to_file(flashcards)
                messagebox.showinfo("Đã xóa", f"Đã xóa từ '{word}'.")
                callback()

    # Refresh Card List
    def refresh_cards():
        # Xóa các widget cũ
        for widget in list_frame.winfo_children():
            widget.destroy()
            
        if not flashcards:
            tk.Label(
                list_frame, 
                text="Chưa có Flashcards nào được lưu. \nBạn hãy tra từ và nhấn '⭐ Lưu từ' để bắt đầu! 😥", 
                bg="#fde4ec", 
                fg="#ad1457",
                font=(BASE_FONT, scale(14, scale_factor), "bold"),
                pady=scale(50, scale_factor)
            ).pack(fill="x")
            return
            
        # Layout: Grid 2 columns for better space usage
        for i, (en_word, vi_meaning) in enumerate(flashcards.items()):
            row = i // 2
            col = i % 2
            
            # Flashcard container
            card_frame = tk.Frame(list_frame, bg=CARD_FRONT_COLOR, bd=2, relief="raised")
            card_frame.grid(row=row, column=col, padx=scale(10, scale_factor), pady=scale(10, scale_factor), sticky="nsew")
            list_frame.grid_columnconfigure(col, weight=1)

            # Label (the card itself)
            card_label = tk.Label(
                card_frame,
                text=en_word,
                font=(BASE_FONT, scale(16, scale_factor), "bold"),
                bg=CARD_FRONT_COLOR,
                fg=CARD_TEXT_COLOR,
                height=scale(4, scale_factor),
                width=scale(20, scale_factor),
                wraplength=scale(200, scale_factor) 
            )
            card_label.pack(fill="both", expand=True, padx=scale(10, scale_factor), pady=scale(10, scale_factor))
            
            # Bind click event
            card_label.bind("<Button-1>", lambda e, l=card_label, en=en_word, vi=vi_meaning: flip_card(l, en, vi))
            
            # --- Delete Button ---
            delete_btn = tk.Button(
                card_frame, 
                text="Xóa", 
                command=lambda w=en_word: delete_flashcard(w, refresh_cards),
                font=(BASE_FONT, scale(8, scale_factor)), 
                bg="#e57373", 
                fg="white", 
                relief="flat", 
                bd=0,
                cursor="hand2"
            )
            add_hover_effect(delete_btn, "#e57373", "#f06292")
            delete_btn.pack(side="bottom", fill="x")
            
    # --- Control Buttons ---
    control_frame = tk.Frame(manager_win, bg="#fde4ec")
    control_frame.pack(pady=scale(10, scale_factor))
    
    # Vì create_pink_button nằm ngoài scope, ta phải định nghĩa lại nút với add_hover_effect
    def create_small_pink_button(master, text, command):
        btn = tk.Button(master, text=text, command=command,
                        font=(BASE_FONT, scale(11, scale_factor), "bold"), bg="#f8bbd0", fg="#880e4f",
                        activebackground="#f48fb1", activeforeground="white",
                        relief="flat", padx=scale(15, scale_factor), pady=scale(6, scale_factor), cursor="hand2")
        add_hover_effect(btn, "#f8bbd0", "#f48fb1")
        return btn

    btn_back = create_small_pink_button(control_frame, "🔙 Quay lại", lambda: close_with_animation(manager_win))
    btn_back.pack(side="left", padx=scale(10, scale_factor))
    
    btn_refresh = create_small_pink_button(control_frame, "🔄 Tải lại", refresh_cards)
    btn_refresh.pack(side="left", padx=scale(10, scale_factor))
    
    refresh_cards()
    
# ====== ESSAY MANAGER (Đã giữ nguyên logic) ======

def open_essay_window():
    essay_win = tk.Toplevel(root)
    essay_win.title("📚 Bài văn mẫu")
    # Đã giảm kích thước cơ sở
    essay_win.geometry(f"{scale(650, scale_factor)}x{scale(550, scale_factor)}") 
    essay_win.configure(bg="#fde4ec")

    essay_win.protocol("WM_DELETE_WINDOW", lambda: close_with_animation(essay_win))

    animate_zoom_fade_in(essay_win)

    title = tk.Label(
        essay_win,
        text="📚 Danh sách bài văn mẫu",
        font=(BASE_FONT, scale(18, scale_factor), "bold"),
        bg="#fde4ec",
        fg="#ad1457"
    )
    title.pack(pady=scale(15, scale_factor))

    # ====== Nút quay lại màn hình chính ======
    back_main_btn = tk.Button(
        essay_win,
        text="⬅ Về màn hình chính",
        command=lambda: close_with_animation(essay_win),
        font=(BASE_FONT, scale(11, scale_factor), "bold"),
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
    add_hover_effect(back_main_btn, "#f8bbd0", "#f48fb1")

    # ====== Frame chứa danh sách bài có thanh cuộn ======
    container = tk.Frame(essay_win, bg="#fde4ec")
    container.pack(fill="both", expand=True, padx=scale(20, scale_factor), pady=10)

    canvas = tk.Canvas(container, bg="#fde4ec", highlightthickness=0)
    scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg="#fde4ec")

    # Gắn frame cuộn vào canvas
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

    def resize_scroll_region(event):
        canvas.itemconfig(canvas_window, width=event.width)

    canvas.bind("<Configure>", resize_scroll_region)
    canvas.configure(yscrollcommand=scrollbar.set)

    # ====== Hiệu ứng cuộn mượt có quán tính ======
    scroll_speed = 0
    momentum_active = False

    def on_mousewheel(event):
        """Xử lý cuộn có quán tính."""
        nonlocal scroll_speed, momentum_active

        delta = event.delta
        if event.num == 5 or delta < 0:
            delta = -1
        elif event.num == 4 or delta > 0:
            delta = 1

        scroll_speed += delta * 3 
        if not momentum_active:
            momentum_active = True
            apply_momentum_scroll()

    def apply_momentum_scroll():
        """Giảm dần tốc độ cuộn, mô phỏng quán tính."""
        nonlocal scroll_speed, momentum_active
        if abs(scroll_speed) < 0.1:
            momentum_active = False
            scroll_speed = 0
            return

        canvas.yview_scroll(int(-scroll_speed), "units")
        scroll_speed *= 0.85 
        canvas.after(16, apply_momentum_scroll) 

    canvas.bind_all("<MouseWheel>", on_mousewheel)      
    canvas.bind_all("<Button-4>", on_mousewheel)        
    canvas.bind_all("<Button-5>", on_mousewheel)        

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    list_frame = scrollable_frame


    def refresh_list():
        for widget in list_frame.winfo_children():
            widget.destroy()

        for name in essays.keys():
            # ====== Thẻ chứa từng bài ======
            frame_item = tk.Frame(
                list_frame,
                bg="#fff0f6",
                bd=0,
                relief="flat",
                highlightbackground="#f8bbd0",
                highlightthickness=2
            )
            frame_item.pack(
                fill="x",
                padx=scale(40, scale_factor),
                pady=scale(6, scale_factor),
                expand=True
            )

            # ====== Nút mở bài ======
            btn = tk.Button(
                frame_item,
                text=name,
                font=(BASE_FONT, scale(12, scale_factor), "bold"),
                bg="#f8bbd0",
                fg="#880e4f",
                relief="flat",
                bd=0,
                cursor="hand2",
                activebackground="#f48fb1",
                activeforeground="white",
                padx=scale(15, scale_factor),
                pady=scale(8, scale_factor),
                command=lambda n=name: open_essay_detail(n)
            )
            btn.pack(fill="x", expand=True, ipadx=scale(5, scale_factor), ipady=scale(8, scale_factor))

            add_hover_effect(btn, "#f8bbd0", "#f48fb1")

    def open_essay_detail(name):
        detail_win = tk.Toplevel(essay_win)
        detail_win.title(name)
        detail_win.geometry(f"{scale(650, scale_factor)}x{scale(550, scale_factor)}")
        detail_win.configure(bg="#fde4ec")

        detail_win.protocol("WM_DELETE_WINDOW", lambda: close_with_animation(detail_win))

        animate_zoom_fade_in(detail_win)

        lbl_title = tk.Label(detail_win, text=name, font=(BASE_FONT, scale(18, scale_factor), "bold"),
                            bg="#fde4ec", fg="#ad1457")
        lbl_title.pack(pady=scale(10, scale_factor))

        txt = tk.Text(
            detail_win,
            wrap="word",
            font=(BASE_FONT, scale(12, scale_factor)),
            bg="#fff0f6",
            fg="#212121",
            padx=scale(10, scale_factor),
            pady=scale(10, scale_factor),
            relief="flat",
            height=25,
            highlightthickness=2,
            highlightbackground="#f8bbd0"
        )
        # ====== Khung nút chức năng ======
        btn_frame = tk.Frame(detail_win, bg="#fde4ec")
        btn_frame.pack(pady=scale(10, scale_factor))
        
        txt.pack(fill="both", expand=True, padx=scale(20, scale_factor), pady=scale(10, scale_factor))
        txt.insert(tk.END, essays[name])
        txt.config(state="disabled")

        def enable_edit():
            txt.config(state="normal")
            edit_btn.pack_forget()
            delete_btn.pack_forget()
            save_btn.pack(side="left", padx=scale(8, scale_factor))
            cancel_btn.pack(side="left", padx=scale(8, scale_factor))

        def save_changes():
            essays[name] = txt.get("1.0", tk.END).strip()
            save_essays(essays)
            txt.config(state="disabled")
            save_btn.pack_forget()
            cancel_btn.pack_forget()
            edit_btn.pack(side="left", padx=scale(8, scale_factor))
            delete_btn.pack(side="left", padx=scale(8, scale_factor))
            messagebox.showinfo("✅ Đã lưu", f"Đã cập nhật bài: {name}")

        def cancel_edit():
            txt.delete("1.0", tk.END)
            txt.insert(tk.END, essays[name])
            txt.config(state="disabled")    
            save_btn.pack_forget()
            cancel_btn.pack_forget()
            edit_btn.pack(side="left", padx=scale(8, scale_factor))
            delete_btn.pack(side="left", padx=scale(8, scale_factor))

        def delete_essay():
            if messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn xóa bài '{name}' không?"):
                del essays[name]
                save_essays(essays)
                close_with_animation(detail_win)
                messagebox.showinfo("🗑 Đã xóa", f"Đã xóa bài '{name}'.")
                refresh_list()

        edit_btn = tk.Button(btn_frame, text="✏ Chỉnh sửa", command=enable_edit,
                            font=(BASE_FONT, scale(11, scale_factor), "bold"),
                            bg="#f8bbd0", fg="#880e4f",
                            activebackground="#f48fb1", activeforeground="white",
                            relief="flat", padx=scale(15, scale_factor), pady=scale(6, scale_factor), cursor="hand2")
        add_hover_effect(edit_btn, "#f8bbd0", "#f48fb1")
        edit_btn.pack(side="left", padx=scale(8, scale_factor))

        delete_btn = tk.Button(btn_frame, text="🗑 Xóa bài", command=delete_essay,
                            font=(BASE_FONT, scale(11, scale_factor), "bold"),
                            bg="#f8bbd0", fg="#880e4f",
                            activebackground="#f48fb1", activeforeground="white",
                            relief="flat", padx=scale(15, scale_factor), pady=scale(6, scale_factor), cursor="hand2")
        add_hover_effect(delete_btn, "#f8bbd0", "#f48fb1")
        delete_btn.pack(side="left", padx=scale(8, scale_factor))

        save_btn = tk.Button(btn_frame, text="💾 Lưu bài", command=save_changes,
                            font=(BASE_FONT, scale(11, scale_factor), "bold"),
                            bg="#f8bbd0", fg="#880e4f",
                            activebackground="#f48fb1", activeforeground="white",
                            relief="flat", padx=scale(15, scale_factor), pady=scale(6, scale_factor), cursor="hand2")
        add_hover_effect(save_btn, "#f8bbd0", "#f48fb1")

        cancel_btn = tk.Button(btn_frame, text="❌ Hủy", command=cancel_edit,
                            font=(BASE_FONT, scale(11, scale_factor), "bold"),
                            bg="#f8bbd0", fg="#880e4f",
                            activebackground="#f48fb1", activeforeground="white",
                            relief="flat", padx=scale(15, scale_factor), pady=scale(6, scale_factor), cursor="hand2")
        add_hover_effect(cancel_btn, "#f8bbd0", "#f48fb1")

        back_btn = tk.Button(detail_win, text="🔙 Quay lại danh sách", command=lambda: close_with_animation(detail_win),
                            font=(BASE_FONT, scale(11, scale_factor), "bold"),
                            bg="#f8bbd0", fg="#880e4f",
                            activebackground="#f48fb1", activeforeground="white",
                            relief="flat", padx=scale(15, scale_factor), pady=scale(6, scale_factor), cursor="hand2")
        back_btn.pack(pady=scale(10, scale_factor))
        add_hover_effect(back_btn, "#f8bbd0", "#f48fb1")


    def add_new_essay_popup():
        popup = tk.Toplevel(essay_win)
        popup.title("➕ Thêm bài mới")
        # Đã giảm kích thước cơ sở
        popup.geometry(f"{scale(450, scale_factor)}x{scale(350, scale_factor)}")
        popup.configure(bg="#fde4ec")

        popup.protocol("WM_DELETE_WINDOW", lambda: close_with_animation(popup))

        animate_zoom_fade_in(popup)

        tk.Label(popup, text="Tiêu đề bài:", bg="#fde4ec", fg="#880e4f",
                 font=(BASE_FONT, scale(12, scale_factor), "bold")).pack(pady=scale(5, scale_factor))
        title_entry = tk.Entry(popup, font=(BASE_FONT, scale(12, scale_factor)), width=40, relief="flat",
                               bg="#fff0f6", highlightthickness=2, highlightbackground="#f8bbd0")
        title_entry.pack(pady=scale(5, scale_factor))

        tk.Label(popup, text="Nội dung:", bg="#fde4ec", fg="#880e4f",
                 font=(BASE_FONT, scale(12, scale_factor), "bold")).pack(pady=scale(5, scale_factor))
        content_text = tk.Text(popup, wrap="word", font=(BASE_FONT, scale(11, scale_factor)), height=10,
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
            close_with_animation(popup)
            refresh_list()

        save_btn = tk.Button(
            popup,
            text="💾 Lưu bài mới",
            command=save_new,
            font=(BASE_FONT, scale(11, scale_factor), "bold"),
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
        add_hover_effect(save_btn, "#f8bbd0", "#f48fb1")

    # ====== Nút thêm bài mới ======
    add_btn = tk.Button(
        essay_win,
        text="➕ Thêm bài mới",
        command=add_new_essay_popup,
        font=(BASE_FONT, scale(11, scale_factor), "bold"),
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
    add_hover_effect(add_btn, "#f8bbd0", "#f48fb1")

    refresh_list()


# ====== UI SETUP ======
# ====== INITIALIZE ROOT FIRST TO DETECT SCREEN SIZE ======
root = tk.Tk()
scale_factor = get_scale_factor()

# Cập nhật hệ số DPI
root.tk.call('tk', 'scaling', scale_factor)

root.title("📘 Sổ tay hướng dẫn mạo hiểm Toeic của Uyển Khanh")
# Đã GIẢM kích thước cơ sở để cân đối với font to hơn
root.geometry(f"{scale(800, scale_factor)}x{scale(500, scale_factor)}") 
root.configure(bg="#fde4ec")

title_label = tk.Label(root, text="SỔ TAY HƯỚNG DẪN MẠO HIỂM TOEIC", font=(BASE_FONT, scale(20, scale_factor), "bold"), bg="#fde4ec", fg="#ad1457")
title_label.pack(pady=scale(15, scale_factor))

frame = tk.Frame(root, bg="#fde4ec")
frame.pack(pady=scale(10, scale_factor))

entry = tk.Entry(frame, width=45, font=(BASE_FONT, scale(13, scale_factor)), relief="flat", bg="#fff0f6",
                 highlightthickness=2, highlightbackground="#f8bbd0", highlightcolor="#f48fb1")
entry.pack(side=tk.LEFT, padx=scale(5, scale_factor), ipady=scale(6, scale_factor))
entry.bind("<Return>", lambda event: lookup_meaning())


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
    # Đã loại bỏ logic hover cũ trong hàm này, dùng add_hover_effect bên dưới
    btn = tk.Button(button_frame, text=text, command=command,
                    font=(BASE_FONT, scale(11, scale_factor), "bold"), bg="#f8bbd0", fg="#880e4f",
                    activebackground="#f48fb1", activeforeground="white",
                    relief="flat", bd=0, padx=scale(15, scale_factor), pady=scale(6, scale_factor), cursor="hand2")
    return btn

btn_meaning = create_pink_button("🔍 Tra nghĩa", lookup_meaning)
btn_meaning.grid(row=0, column=0, padx=scale(8, scale_factor))

btn_synant = create_pink_button("🟢 Đồng / Trái nghĩa", lookup_syn_ant)
btn_synant.grid(row=0, column=1, padx=scale(8, scale_factor))

btn_phrasal = create_pink_button("📘 Phrasal Verb", lookup_phrasal)
btn_phrasal.grid(row=0, column=2, padx=scale(8, scale_factor))

btn_essays = create_pink_button("📚 Bài văn mẫu", open_essay_window)
btn_essays.grid(row=0, column=3, padx=scale(8, scale_factor))

# ====== Nút Flashcards Mới ======
btn_flashcards = create_pink_button("🃏 Flashcards", open_flashcard_manager)
btn_flashcards.grid(row=0, column=4, padx=scale(8, scale_factor))


# Thêm hiệu ứng hover mượt cho tất cả nút
for btn in [btn_meaning, btn_synant, btn_phrasal, btn_essays, btn_flashcards]:
    add_hover_effect(btn, "#f8bbd0", "#f48fb1")


# Result text
result_frame = tk.Frame(root, bg="#fde4ec")
result_frame.pack(fill="both", expand=True, padx=scale(20, scale_factor), pady=scale(10, scale_factor))

result_text = tk.Text(result_frame, wrap="word", font=(BASE_FONT, scale(12, scale_factor)), height=25, relief="flat",
                      bg="#fff0f6", fg="#212121", insertbackground="#ad1457", padx=scale(10, scale_factor), pady=scale(10, scale_factor),
                      bd=0, highlightthickness=2, highlightbackground="#f8bbd0")
result_text.pack(fill="both", expand=True)

result_text.tag_configure("word_style", font=(BASE_FONT, scale(13, scale_factor), "bold"), foreground="#880e4f")
result_text.tag_configure("vi_style", foreground="#00897b")
result_text.tag_configure("syn_style", foreground="#1565c0")
result_text.tag_configure("ant_style", foreground="#d84315")

root.mainloop()
