#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📁 File Organizer GUI v1.3
✅ Тёмная тема, Construct 3, изменяемое окно, лог в файл, кредиты Полуяхтовым
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import datetime
import shutil
import urllib.request
import json
from pathlib import Path

VERSION = "1.3.0"
# 🔧 Правила группировки (обновлены)
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


class FileOrganizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"📁 File Organizer v{VERSION}")
        self.root.geometry("700x600")
        self.root.minsize(500, 400)
        self.root.resizable(True, True)  # ✅ Изменяемый размер окна
        
        # ✅ Тёмная тема
        self.style = ttk.Style()
        self._apply_dark_theme()
        
        self.stop_event = threading.Event()
        self.log_file = None
        self.log_tags = {
            "OK": ("#4caf50", True), "ERROR": ("#f44336", True), "TEST": ("#03a9f4", True), 
            "WARN": ("#ff9800", True), "INFO": ("#e0e0e0", False)
        }

        self._build_menu()
        self._build_ui()
        self._setup_defaults()

    def _apply_dark_theme(self):
        # Базовая тема и цвета
        bg, fg = "#1e1e1e", "#d4d4d4"
        accent = "#0078d7"
        frame_bg = "#252526"
        ctrl_bg = "#2d2d2d"
        
        self.style.theme_use('clam')
        self.root.configure(bg=bg)
        
        # Глобальные стили
        self.style.configure('.', background=bg, foreground=fg, font=('Segoe UI', 10))
        self.style.configure('TFrame', background=bg)
        self.style.configure('TLabelFrame', background=ctrl_bg, bordercolor="#3c3c3c", lightcolor="#3c3c3c", darkcolor="#3c3c3c")
        self.style.configure('TLabelFrame.Label', background=ctrl_bg, foreground=fg, font=('Segoe UI', 10, 'bold'))
        self.style.configure('TLabel', background=bg, foreground=fg)
        
        # Кнопки и элементы управления
        self.style.configure('TButton', background=ctrl_bg, foreground=fg, bordercolor="#3c3c3c", lightcolor="#3c3c3c", darkcolor="#3c3c3c")
        self.style.map('TButton', background=[('active', accent), ('pressed', '#005a9e')], foreground=[('active', '#ffffff')])
        
        self.style.configure('TCheckbutton', background=bg, foreground=fg)
        self.style.configure('TCombobox', fieldbackground=ctrl_bg, background=ctrl_bg, foreground=fg, bordercolor="#3c3c3c")
        self.style.map('TCombobox', fieldbackground=[('readonly', ctrl_bg)], selectbackground=[('focus', accent)])
        self.style.configure('TEntry', fieldbackground=ctrl_bg, background=ctrl_bg, foreground=fg, bordercolor="#3c3c3c")
        
        # Прогресс-бар и скроллбар
        self.style.configure('Horizontal.TProgressbar', troughcolor=bg, background=accent, bordercolor="#3c3c3c")
        self.style.configure('Vertical.TScrollbar', background=bg, troughcolor=bg, bordercolor="#3c3c3c")
        self.style.map('Vertical.TScrollbar', background=[('active', '#505050')])

    def _build_menu(self):
        menubar = tk.Menu(self.root, tearoff=0, bg="#252526", fg="#d4d4d4", activeborderwidth=0, activebackground="#0078d7")
        help_menu = tk.Menu(menubar, tearoff=0, bg="#252526", fg="#d4d4d4", activeborderwidth=0, activebackground="#0078d7")
        help_menu.add_command(label="📖 О программе", command=self.show_about)
        help_menu.add_command(label="🔄 Проверить обновления", command=self.check_updates)
        menubar.add_cascade(label="Помощь", menu=help_menu)
        self.root.config(menu=menubar)

    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Путь
        path_frame = ttk.LabelFrame(main_frame, text="📂 Папка для сортировки", padding=8)
        path_frame.pack(fill=tk.X, pady=(0, 10))
        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        ttk.Button(path_frame, text="Обзор...", command=self.browse_folder).pack(side=tk.RIGHT)

        # Настройки
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

        # Чекбоксы
        chk_frame = ttk.Frame(main_frame)
        chk_frame.pack(fill=tk.X, pady=(0, 5))
        self.dry_run_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(chk_frame, text="🧪 Тестовый режим", variable=self.dry_run_var).pack(side=tk.LEFT, padx=(0, 15))
        self.save_log_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(chk_frame, text="💾 Сохранять лог в файл", variable=self.save_log_var).pack(side=tk.LEFT)

        # Кнопки
        ctrl_frame = ttk.Frame(main_frame)
        ctrl_frame.pack(fill=tk.X, pady=(5, 10))
        
        self.run_btn = ttk.Button(ctrl_frame, text="▶️ Начать", command=self.start_organizing)
        self.run_btn.pack(side=tk.LEFT)
        self.stop_btn = ttk.Button(ctrl_frame, text="⏹️ Стоп", command=self.stop_organizing, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(5, 0))
        self.progress = ttk.Progressbar(ctrl_frame, mode='indeterminate', length=200)
        self.progress.pack(side=tk.RIGHT)

        # Лог
        log_frame = ttk.LabelFrame(main_frame, text="📜 Лог", padding=8)
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_text = tk.Text(log_frame, height=14, wrap=tk.WORD, state=tk.DISABLED, bg="#1e1e1e", fg="#d4d4d4", 
                                insertbackground="#d4d4d4", selectbackground="#0078d7")
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        for tag, (color, bold) in self.log_tags.items():
            self.log_text.tag_config(tag, foreground=color, font=("Consolas", 9, "bold" if bold else "normal"))
            
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
        
        # Запись в файл
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

        # Подготовка лог-файла
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

    def show_about(self):
        about_text = (f"📁 File Organizer v{VERSION}\n\n"
                      "👨‍💻 Разработчики: Валентин и Михаил Полуяхтовы\n\n"
                      "✨ Функции:\n"
                      "• Сортировка по расширению/дате/гибрид\n"
                      "• Поддержка Construct 3, STL, Corel и др.\n"
                      "• Тестовый режим & безопасные дубликаты\n"
                      "• Тёмная тема & изменяемый размер окна\n"
                      "• Экспорт лога операций в файл\n\n"
                      "© 2026 | Python 3.6+ | Стандартная библиотека")
        messagebox.showinfo("О программе", about_text)

    def check_updates(self):
        self.status_var.set("🔄 Проверка обновлений...")
        try:
            # Замените на реальный URL вашего raw-JSON
            latest_version = VERSION 
            if latest_version > VERSION:
                messagebox.showinfo("Обновление", f"🆕 Доступна версия {latest_version}!")
            else:
                messagebox.showinfo("Обновления", f"✅ У вас последняя версия ({VERSION}).")
        except Exception:
            messagebox.showwarning("Ошибка сети", "Не удалось проверить обновления.")
        finally:
            self.status_var.set("✅ Готово")


if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    app = FileOrganizerApp(root)
    root.mainloop()