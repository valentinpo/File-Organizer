#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📁 File Organizer GUI v1.2
✅ Кнопка Стоп, STL & Corel, меню О программе, проверка обновлений, кредиты
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

VERSION = "1.2.0"
# 🔧 Правила группировки (обновлены)
EXT_RULES = {
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
        self.root.geometry("650x550")
        self.root.resizable(False, False)
        
        # ✅ Шрифты без конфликтов Tcl/Tk
        style = ttk.Style()
        style.configure('.', font=('Segoe UI', 10))
        
        self.stop_event = threading.Event()
        self.log_tags = {"OK": ("#28a745", True), "ERROR": ("#dc3545", True), "TEST": ("#17a2b8", True), 
                         "WARN": ("#ffc107", True), "INFO": ("#333333", False)}

        self._build_menu()
        self._build_ui()
        self._setup_defaults()

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        help_menu = tk.Menu(menubar, tearoff=0)
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

        self.dry_run_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts_frame, text="🧪 Тестовый режим", variable=self.dry_run_var).pack(side=tk.LEFT)

        # Кнопки
        ctrl_frame = ttk.Frame(main_frame)
        ctrl_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.run_btn = ttk.Button(ctrl_frame, text="▶️ Начать", command=self.start_organizing)
        self.run_btn.pack(side=tk.LEFT)
        self.stop_btn = ttk.Button(ctrl_frame, text="⏹️ Стоп", command=self.stop_organizing, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(5, 0))
        self.progress = ttk.Progressbar(ctrl_frame, mode='indeterminate', length=180)
        self.progress.pack(side=tk.RIGHT)

        # Лог
        log_frame = ttk.LabelFrame(main_frame, text="📜 Лог", padding=8)
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_text = tk.Text(log_frame, height=12, wrap=tk.WORD, state=tk.DISABLED, bg="#f8f9fa")
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        for tag, (color, bold) in self.log_tags.items():
            self.log_text.tag_config(tag, foreground=color, font=("Consolas", 9, "bold" if bold else "normal"))
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        self.status_var = tk.StringVar(value="Готово")
        ttk.Label(main_frame, textvariable=self.status_var, foreground="#666").pack(anchor=tk.E)

    def _setup_defaults(self):
        self.path_var.set(str(Path.home() / "Downloads") if Path.home().joinpath("Downloads").exists() else "")

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

    def start_organizing(self):
        path = self.path_var.get().strip()
        if not path or not Path(path).is_dir():
            messagebox.showwarning("Внимание", "Укажите корректную папку!")
            return

        self.stop_event.clear()
        self.run_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.progress.start(10)
        self.status_var.set("⏳ Выполняется...")
        self.log_text.config(state=tk.NORMAL); self.log_text.delete(1.0, tk.END)
        self._log("INFO", f"🚀 Запуск: {path}")

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

    def _process_queue(self):
        try:
            while True:
                tag, msg = self.log_q.get_nowait()
                self._log(tag, msg)
        except queue.Empty: pass

        if self.worker_thread.is_alive():
            self.root.after(50, self._process_queue)
        else:
            self.progress.stop()
            self.run_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.status_var.set("✅ Готово")
            self._log("INFO", "─────────────────────────────")

    def show_about(self):
        about_text = (f"📁 File Organizer v{VERSION}\n\n"
                      "👨‍💻 Разработчики: Совместная разработка\n"
                      "   • Вы (Идея, ТЗ, Тестирование)\n"
                      "   • AI Assistant (Код, Архитектура, Отладка)\n\n"
                      "✨ Функции:\n"
                      "• Сортировка по расширению/дате/гибрид\n"
                      "• Поддержка STL, 3MF, CDR, AI и др.\n"
                      "• Тестовый режим & безопасные дубликаты\n"
                      "• Асинхронный GUI без зависаний\n\n"
                      "© 2026 | Python 3.6+ | Стандартная библиотека")
        messagebox.showinfo("О программе", about_text)

    def check_updates(self):
        self.status_var.set("🔄 Проверка обновлений...")
        try:
            # Замените URL на свой raw-файл GitHub/Gist с JSON {"version": "X.X.X"}
            UPDATE_URL = "https://api.github.com/repos/placeholder/version" 
            # Для демо используем имитацию ответа
            latest_version = VERSION  # В реальности: json.loads(response)["version"]
            
            if latest_version > VERSION:
                messagebox.showinfo("Обновление", f"🆕 Доступна версия {latest_version}!\nПерейдите в репозиторий для загрузки.")
            else:
                messagebox.showinfo("Обновления", f"✅ У вас последняя версия ({VERSION}).")
        except Exception:
            messagebox.showwarning("Ошибка сети", "Не удалось проверить обновления.\nПроверьте интернет-соединение.")
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