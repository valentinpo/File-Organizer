#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📁 File Organizer GUI v1.5
✅ Меню "Справка": Что нового (из GitHub), Проверить обновления, О программе
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import datetime
import shutil
import urllib.request
import json
import webbrowser
from pathlib import Path

VERSION = "1.5.0"
# 🔗 Ссылки для обновлений
GITHUB_REPO = "valentinpo/File-Organizer"
RAW_VERSION_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/version.json"
RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases"
API_RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

EXT_RULES = {
    'Construct 3': ['.c3p', '.c3t', '.c3addon'],
    '3D Модели': ['.stl', '.obj', '.3mf', '.gltf', '.fbx'],
    'Вектор/Corel': ['.cdr', '.ai', '.eps', '.svg'],
    'Изображения': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.psd'],
    'Документы': ['.pdf', '.doc', '.docx', '.txt', '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.csv'],
    'Архивы': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'],
    'Аудио': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a'],
    'Видео': ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm'],
    'Установщики': ['.exe', '.msi', '.dmg', '.sh', '.pkg', '.deb', '.rpm'],
    'Код': ['.py', '.js', '.html', '.css', '.java', '.cpp', '.go', '.rs', '.php']
}

def build_ext_map():
    mapping = {}
    for folder, exts in EXT_RULES.items():
        for ext in exts:
            mapping[ext.lower()] = folder
    return mapping

def get_target_path(file_path, mode, date_fmt, ext_map):
    ext_target = ext_map.get(file_path.suffix.lower(), 'Разное')
    mtime = datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
    date_target = mtime.strftime("%Y-%m" if date_fmt == "YYYY-MM" else "%Y/%m" if date_fmt == "YYYY/MM" else "%Y")
    if mode == 'ext': return ext_target
    if mode == 'date': return date_target
    return f"{ext_target}/{date_target}"

def run_organizer(path, mode, date_fmt, dry_run, log_q, stop_event):
    downloads = Path(path)
    if not downloads.is_dir():
        log_q.put(("ERROR", f"❌ Папка не найдена: {path}"))
        return
    ext_map = build_ext_map()
    files = [f for f in downloads.iterdir() if f.is_file() and not f.name.startswith('.')]
    if not files:
        log_q.put(("INFO", "📭 Нет файлов для сортировки."))
        return
    log_q.put(("INFO", f"🔍 Найдено файлов: {len(files)}"))
    moved = 0
    for f in files:
        if stop_event.is_set():
            log_q.put(("WARN", "⏹️ Операция остановлена пользователем."))
            break
        try:
            target_folder = get_target_path(f, mode, date_fmt, ext_map)
            target_dir = downloads / target_folder
            target_dir.mkdir(parents=True, exist_ok=True)
            dest = target_dir / f.name
            if dest.exists():
                stem, suffix = f.stem, f.suffix
                counter = 1
                while dest.exists():
                    dest = target_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
            if dry_run:
                log_q.put(("TEST", f"🧪 {f.name} → {target_folder}/"))
            else:
                shutil.move(str(f), str(dest))
                log_q.put(("OK", f"✅ {f.name} → {target_folder}/"))
            moved += 1
        except Exception as e:
            log_q.put(("ERROR", f"❌ Ошибка с {f.name}: {e}"))
    log_q.put(("INFO", f"🎉 Готово! Обработано: {moved}/{len(files)} файлов."))


THEMES = {
    "Dark": {"bg": "#1e1e1e", "fg": "#d4d4d4", "accent": "#0078d7", "frame": "#252526", 
             "ctrl": "#2d2d2d", "border": "#3c3c3c", "text_bg": "#1e1e1e", "text_fg": "#d4d4d4"},
    "Light": {"bg": "#ffffff", "fg": "#1a1a1a", "accent": "#005a9e", "frame": "#f5f5f5", 
              "ctrl": "#e8e8e8", "border": "#cccccc", "text_bg": "#ffffff", "text_fg": "#000000"}
}

class FileOrganizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"📁 File Organizer v{VERSION}")
        self.root.geometry("700x600")
        self.root.minsize(500, 400)
        self.root.resizable(True, True)
        
        self.style = ttk.Style()
        self.stop_event = threading.Event()
        self.log_file = None
        self.current_theme = "Dark"
        self.log_tags = {
            "OK": ("#4caf50", True), "ERROR": ("#f44336", True), "TEST": ("#03a9f4", True), 
            "WARN": ("#ff9800", True), "INFO": ("#e0e0e0", False)
        }

        self._build_menu()
        self._build_ui()
        self._apply_theme("Dark")
        self._setup_defaults()

    def _apply_theme(self, theme_name):
        t = THEMES[theme_name]
        self.current_theme = theme_name
        self.style.theme_use('clam')
        self.root.configure(bg=t["bg"])
        self.style.configure('.', background=t["bg"], foreground=t["fg"], font=('Segoe UI', 10))
        self.style.configure('TFrame', background=t["bg"])
        self.style.configure('TLabelFrame', background=t["ctrl"], bordercolor=t["border"], 
                             lightcolor=t["border"], darkcolor=t["border"])
        self.style.configure('TLabelFrame.Label', background=t["ctrl"], foreground=t["fg"], font=('Segoe UI', 10, 'bold'))
        self.style.configure('TLabel', background=t["bg"], foreground=t["fg"])
        self.style.configure('TButton', background=t["ctrl"], foreground=t["fg"], bordercolor=t["border"])
        self.style.map('TButton', background=[('active', t["accent"]), ('pressed', t["accent"])], 
                       foreground=[('active', '#ffffff')])
        self.style.configure('TCheckbutton', background=t["bg"], foreground=t["fg"])
        self.style.configure('TCombobox', fieldbackground=t["ctrl"], background=t["ctrl"], foreground=t["fg"], bordercolor=t["border"])
        self.style.map('TCombobox', fieldbackground=[('readonly', t["ctrl"])])
        self.style.configure('TEntry', fieldbackground=t["ctrl"], background=t["ctrl"], foreground=t["fg"], bordercolor=t["border"])
        self.style.configure('Horizontal.TProgressbar', troughcolor=t["bg"], background=t["accent"], bordercolor=t["border"])
        self.style.configure('Vertical.TScrollbar', background=t["bg"], troughcolor=t["bg"], bordercolor=t["border"])
        self.style.map('Vertical.TScrollbar', background=[('active', t["border"])])

        if hasattr(self, 'log_text'):
            self.log_text.configure(bg=t["text_bg"], fg=t["text_fg"], insertbackground=t["text_fg"], 
                                    selectbackground=t["accent"], selectforeground='#ffffff')
            info_fg = "#e0e0e0" if theme_name == "Dark" else "#333333"
            self.log_text.tag_config("INFO", foreground=info_fg)
        if hasattr(self, 'menubar'):
            self.menubar.configure(bg=t["ctrl"], fg=t["fg"])
            for menu in self.menubar.winfo_children():
                menu.configure(bg=t["ctrl"], fg=t["fg"], activebackground=t["accent"], activeforeground="#ffffff")
        self.root.update_idletasks()

    def _toggle_theme(self):
        new_theme = "Light" if self.current_theme == "Dark" else "Dark"
        self._apply_theme(new_theme)
        self.theme_btn.config(text=f"🌓 Тема: {new_theme}")

    def _build_menu(self):
        self.menubar = tk.Menu(self.root, tearoff=0)
        
        # 📋 Меню "Справка"
        help_menu = tk.Menu(self.menubar, tearoff=0)
        help_menu.add_command(label="📋 Что нового", command=self.show_whats_new)
        help_menu.add_separator()
        help_menu.add_command(label="🔄 Проверить обновления", command=self.check_updates)
        help_menu.add_separator()
        help_menu.add_command(label="📖 О программе", command=self.show_about)
        
        self.menubar.add_cascade(label="Справка", menu=help_menu)
        self.root.config(menu=self.menubar)

    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(main_frame)
        header.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(header, text="📁 File Organizer", font=('Segoe UI', 14, 'bold')).pack(side=tk.LEFT)
        self.theme_btn = ttk.Button(header, text=f"🌓 Тема: Dark", command=self._toggle_theme)
        self.theme_btn.pack(side=tk.RIGHT)

        path_frame = ttk.LabelFrame(main_frame, text="📂 Папка для сортировки", padding=8)
        path_frame.pack(fill=tk.X, pady=(0, 10))
        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        ttk.Button(path_frame, text="Обзор...", command=self.browse_folder).pack(side=tk.RIGHT)

        opts_frame = ttk.LabelFrame(main_frame, text="⚙️ Настройки", padding=8)
        opts_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(opts_frame, text="Режим:").pack(side=tk.LEFT, padx=(0, 5))
        self.mode_var = tk.StringVar(value="ext")
        self.mode_combo = ttk.Combobox(opts_frame, textvariable=self.mode_var, 
                                       values=["ext (по расширению)", "date (по дате)", "both (расширение + дата)"],
                                       state="readonly", width=25)
        self.mode_combo.pack(side=tk.LEFT, padx=(0, 15))
        self.mode_combo.bind("<<ComboboxSelected>>", self.toggle_date_format)

        ttk.Label(opts_frame, text="Формат даты:").pack(side=tk.LEFT, padx=(0, 5))
        self.date_fmt_var = tk.StringVar(value="YYYY-MM")
        self.date_combo = ttk.Combobox(opts_frame, textvariable=self.date_fmt_var,
                                       values=["YYYY", "YYYY-MM", "YYYY/MM"], state="readonly", width=10)
        self.date_combo.pack(side=tk.LEFT, padx=(0, 15))
        self.toggle_date_format()

        chk_frame = ttk.Frame(main_frame)
        chk_frame.pack(fill=tk.X, pady=(0, 5))
        self.dry_run_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(chk_frame, text="🧪 Тестовый режим", variable=self.dry_run_var).pack(side=tk.LEFT, padx=(0, 15))
        self.save_log_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(chk_frame, text="💾 Сохранять лог в файл", variable=self.save_log_var).pack(side=tk.LEFT)

        ctrl_frame = ttk.Frame(main_frame)
        ctrl_frame.pack(fill=tk.X, pady=(5, 10))
        
        self.run_btn = ttk.Button(ctrl_frame, text="▶️ Начать", command=self.start_organizing)
        self.run_btn.pack(side=tk.LEFT)
        self.stop_btn = ttk.Button(ctrl_frame, text="⏹️ Стоп", command=self.stop_organizing, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(5, 0))
        self.progress = ttk.Progressbar(ctrl_frame, mode='indeterminate', length=200)
        self.progress.pack(side=tk.RIGHT)

        log_frame = ttk.LabelFrame(main_frame, text="📜 Лог", padding=8)
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_text = tk.Text(log_frame, height=14, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        self.status_var = tk.StringVar(value="Готово")
        ttk.Label(main_frame, textvariable=self.status_var, foreground="#888").pack(anchor=tk.E)

    def _setup_defaults(self):
        dl = Path.home() / "Downloads"
        self.path_var.set(str(dl) if dl.exists() else "")

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder: self.path_var.set(folder)

    def toggle_date_format(self, event=None):
        is_date = self.mode_var.get() != "ext (по расширению)"
        self.date_combo.config(state="readonly" if is_date else "disabled")
        if not is_date: self.date_fmt_var.set("YYYY-MM")

    def _log(self, tag, msg):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{msg}]\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        if self.save_log_var.get() and self.log_file and not self.log_file.closed:
            try:
                self.log_file.write(f"[{tag}] {msg}\n")
                self.log_file.flush()
            except Exception: pass

    def start_organizing(self):
        path = self.path_var.get().strip()
        if not path or not Path(path).is_dir():
            messagebox.showwarning("Внимание", "Укажите корректную папку!")
            return
        if self.save_log_var.get():
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            log_path = Path.home() / "Desktop" / f"FO_Log_{ts}.txt"
            try:
                self.log_file = open(log_path, 'w', encoding='utf-8')
                self.log_file.write(f"📁 File Organizer Log | Started: {datetime.datetime.now()}\n")
                self.log_file.flush()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось создать лог-файл: {e}")
                self.save_log_var.set(False)
        self.stop_event.clear()
        self.run_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.progress.start(10)
        self.status_var.set("⏳ Выполняется...")
        self.log_text.config(state=tk.NORMAL); self.log_text.delete(1.0, tk.END)
        self._log("INFO", f"🚀 Запуск: {path}")
        if self.save_log_var.get(): self._log("INFO", f"💾 Лог сохраняется в: {log_path}")
        mode = self.mode_var.get().split(" ")[0]
        self.log_q = queue.Queue()
        thread = threading.Thread(target=run_organizer, 
                                  args=(path, mode, self.date_fmt_var.get(), self.dry_run_var.get(), self.log_q, self.stop_event), 
                                  daemon=True)
        thread.start()
        self.worker_thread = thread
        self.root.after(50, self._process_queue)

    def stop_organizing(self):
        self.stop_event.set()
        self.stop_btn.config(state=tk.DISABLED)
        self._log("WARN", "⏳ Запрос остановки отправлен...")

    def _process_queue(self):
        try:
            while True:
                tag, msg = self.log_q.get_nowait()
                self._log(tag, msg)
        except queue.Empty: pass
        if self.worker_thread.is_alive():
            self.root.after(50, self._process_queue)
        else:
            self._on_finish()

    def _on_finish(self):
        self.progress.stop()
        self.run_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_var.set("✅ Готово")
        self._log("INFO", "─────────────────────────────")
        if self.log_file and not self.log_file.closed:
            self.log_file.close()
            self._log("INFO", "💾 Лог успешно сохранён и закрыт.")

    # 🆕 Показывает "Что нового" из GitHub Releases
    def show_whats_new(self):
        self.status_var.set("📡 Загрузка примечаний...")
        def fetch_notes():
            try:
                with urllib.request.urlopen(API_RELEASES_URL, timeout=5) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    version = data.get('tag_name', 'Unknown')
                    published = data.get('published_at', '')[:10]
                    body = data.get('body', 'Нет описания.')
                    # Форматируем для отображения
                    notes = f"🚀 Версия {version} ({published})\n\n{body}"
                    self.root.after(0, lambda: self._show_notes_popup(notes))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showwarning("Ошибка", "Не удалось загрузить примечания.\nПроверьте интернет-соединение."))
            finally:
                self.root.after(0, lambda: self.status_var.set("✅ Готово"))
        
        threading.Thread(target=fetch_notes, daemon=True).start()

    def _show_notes_popup(self, notes_text):
        popup = tk.Toplevel(self.root)
        popup.title("📋 Что нового")
        popup.geometry("500x400")
        popup.resizable(True, True)
        popup.transient(self.root)
        popup.grab_set()
        
        # Применяем текущую тему к попапу
        t = THEMES[self.current_theme]
        popup.configure(bg=t["bg"])
        
        text = tk.Text(popup, wrap=tk.WORD, bg=t["text_bg"], fg=t["text_fg"], 
                       font=("Consolas", 9), relief=tk.FLAT, padx=10, pady=10)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert(tk.END, notes_text)
        text.config(state=tk.DISABLED)
        
        ttk.Button(popup, text="✅ Закрыть", command=popup.destroy).pack(pady=(0, 10))

    def check_updates(self):
        self.status_var.set("🔄 Проверка обновлений...")
        def check():
            try:
                with urllib.request.urlopen(RAW_VERSION_URL, timeout=5) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    latest = data.get('version', '0.0.0')
                    if self._compare_versions(latest, VERSION) > 0:
                        self.root.after(0, lambda: messagebox.showinfo(
                            "🆕 Обновление доступно", 
                            f"Текущая версия: {VERSION}\nДоступна: {latest}\n\nПерейти в репозиторий для загрузки?",
                            **{"type": "yesno"} if hasattr(messagebox, "showinfo") else {}
                        ))
                        # Открываем релизы в браузере
                        webbrowser.open(RELEASES_URL)
                    else:
                        self.root.after(0, lambda: messagebox.showinfo("Обновления", f"✅ У вас последняя версия ({VERSION})."))
            except Exception:
                self.root.after(0, lambda: messagebox.showwarning("Ошибка сети", "Не удалось проверить обновления."))
            finally:
                self.root.after(0, lambda: self.status_var.set("✅ Готово"))
        threading.Thread(target=check, daemon=True).start()

    def _compare_versions(self, v1, v2):
        """Сравнивает версии в формате 'X.Y.Z'. Возвращает 1 если v1 > v2, -1 если <, 0 если ="""
        def parse(v): return tuple(map(int, v.strip('v').split('.')))
        a, b = parse(v1), parse(v2)
        return (a > b) - (a < b)

    def show_about(self):
        about_text = (f"📁 File Organizer v{VERSION}\n\n"
                      "👨‍💻 Разработчики: Валентин и Михаил Полуяхтовы\n\n"
                      "✨ Функции:\n"
                      "• Сортировка по расширению/дате/гибрид\n"
                      "• Поддержка Construct 3, STL, Corel и др.\n"
                      "• Тестовый режим & безопасные дубликаты\n"
                      "• Светлая/Тёмная тема & изменяемый размер окна\n"
                      "• Экспорт лога операций в файл\n"
                      "• Интеграция с GitHub: релизы и обновления\n\n"
                      "© 2026 | Python 3.6+ | Стандартная библиотека")
        messagebox.showinfo("О программе", about_text)


if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    app = FileOrganizerApp(root)
    root.mainloop()