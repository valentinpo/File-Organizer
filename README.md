# 📁 File-Organizer

Кроссплатформенный GUI-органайзер файлов на Python. Сортировка по расширениям и датам, тёмная/светлая тема, безопасный тестовый режим, автообновление и логирование.

## ✨ Возможности

- 📁 **Сортировка файлов** по расширениям и датам
- 📂 **Предустановленные категории** — Construct 3, 3D-модели (STL/OBJ), вектор/Corel (CDR/SVG) и др.
- 🌓 **Тёмная / светлая тема** интерфейса
- 🧪 **Тестовый режим** — безопасная «репетиция» без реального перемещения файлов
- 🔄 **Автообновление** через GitHub Releases
- 📜 **Логирование** всех операций
- ⚡ **Без внешних зависимостей** — работает на стандартной библиотеке Python (Tkinter)

## ⬇️ Скачать

Готовую сборку можно взять в [Releases](https://github.com/valentinpo/File-Organizer/releases) — **`FileOrganizer.exe`** (v1.5.0).

## 📁 Структура

```
File-Organizer/
├── file_organizer_gui.py   # Основной файл программы (актуальная версия)
├── history/                # История разработки (v1.2 → v1.5)
│   ├── file_organizer_gui_v2.py
│   ├── file_organizer_gui_v3.py
│   ├── file_organizer_gui_v4.py
│   ├── file_organizer_gui_v4_fixed.py
│   ├── file_organizer_gui_v5.py
│   └── FileOrganizer.spec  # spec-файл PyInstaller для сборки .exe
├── LICENSE
└── README.md
```

## 🚀 Запуск из исходников

```bash
python file_organizer_gui.py
```

Python 3.x с Tkinter (входит в стандартную поставку Python для Windows).

## 🔨 Сборка .exe

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole --icon icon.ico --add-data "icon.ico;." file_organizer_gui.py
```

Или используйте готовый `FileOrganizer.spec` из `history/`.

## 📜 История версий

| Версия | Что добавлено |
|--------|---------------|
| v1.0 | Базовая сортировка по расширениям |
| v1.2 | Кнопка «Стоп», категории STL и Corel, меню «О программе», проверка обновлений |
| v1.3 | Тёмная тема, категория Construct 3, изменяемое окно, лог в файл |
| v1.4 | Переключение светлой/тёмной темы, кредиты |
| v1.4 Fixed | Исправлен порядок инициализации темы |
| v1.5 | Меню «Справка»: что нового, проверка обновлений, о программе |
| v1.5.0 | Автообновление .exe, тёмная/светлая тема, GitHub-интеграция |

## 📄 Лицензия

MIT (см. [LICENSE](LICENSE)).