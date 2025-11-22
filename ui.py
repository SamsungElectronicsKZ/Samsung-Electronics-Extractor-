#!/usr/bin/env python3
# coding: utf-8

import sys
import os
import threading
import subprocess
import datetime
import time
import signal

from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QLabel,
    QFileDialog,
    QMessageBox,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QTextEdit,
    QProgressBar
)

from PyQt5.QtGui import (
    QPixmap,
    QPalette,
    QBrush,
    QPainterPath,
    QRegion
)

from PyQt5.QtCore import (
    Qt,
    QTimer
)

# Если XDG_RUNTIME_DIR не задан (на Termux/Android) — установить
if not os.environ.get("XDG_RUNTIME_DIR"):
    os.environ["XDG_RUNTIME_DIR"] = "/data/data/com.termux/files/usr/tmp/runtime-u0_a225"

# BASE_DIR — каталог этого файла
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Directory for logs
LOG_DIR = os.path.join("/storage/emulated/0", "log_SamsungElectronicsExtractor")
try:
    os.makedirs(LOG_DIR, exist_ok=True)
except Exception:
    # если не получилось создать — использовать временный каталог
    LOG_DIR = os.path.join(BASE_DIR, "logs")
    os.makedirs(LOG_DIR, exist_ok=True)


class WallpaperBackground(QWidget):
    """
    Фоновое полноэкранное окно с обоями.
    Отображается как отдельное окно под основным приложением.
    """
    def __init__(self, image_path=None):
        super().__init__(None, Qt.Window)  # top-level widget
        try:
            # окно без рамки и всегда снизу
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnBottomHint)
            screen = QApplication.primaryScreen()
            if screen is None:
                return
            size = screen.size()
            self.setGeometry(0, 0, size.width(), size.height())
            if image_path and os.path.exists(image_path):
                pixmap = QPixmap(image_path).scaled(
                    size.width(), size.height(),
                    Qt.IgnoreAspectRatio, Qt.SmoothTransformation
                )
                palette = QPalette()
                palette.setBrush(QPalette.Window, QBrush(pixmap))
                self.setPalette(palette)
                self.setAutoFillBackground(True)
            # показать фон сразу на весь экран
            try:
                self.showFullScreen()
            except Exception:
                # fallback
                self.show()
        except Exception as e:
            print("WallpaperBackground init error:", e)

    def stop(self):
        try:
            self.close()
        except Exception:
            pass


class WaitWindow(QWidget):
    """Окно ожидания с горизонтальной полоской и кнопкой Cancel (без blur)."""
    def __init__(self, message="Пожалуйста, подождите..."):
        super().__init__(None, Qt.Window)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.CustomizeWindowHint)
        self.setFixedSize(500, 120)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.setStyleSheet("""
            background-color: rgba(10, 30, 60, 160);
            color: white;
            border-radius: 12px;
        """)
        self.center()

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)

        self.label = QLabel(message)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("color: white;")
        layout.addWidget(self.label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # бесконечный индикатор
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(18)
        self.progress.setStyleSheet("""
            QProgressBar {
                border-radius: 6px;
                background-color: rgba(0,0,0,60);
            }
            QProgressBar::chunk {
                background-color: rgba(80,150,255,200);
                width: 40px;
            }
        """)
        layout.addWidget(self.progress)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedHeight(32)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(20,70,160,120);
                color: white;
                border-radius:6px;
                border: 1px solid rgba(255,255,255,10);
                padding: 6px 10px;
            }
            QPushButton:hover { background-color: rgba(40,100,200,160); }
            QPushButton:pressed { background-color: rgba(10,40,120,200); }
        """)
        layout.addWidget(self.cancel_btn)

        self.setLayout(layout)

    def center(self):
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2,
                  (screen.height() - self.height()) // 2)


class ExtractorGUI(QWidget):
    def __init__(self):
        super().__init__()

        self.LANG = "ru"
        self.file_path = ""
        self.folder_path = ""
        self.process = None
        self.process_pg = None

        wallpaper_path = os.path.join(BASE_DIR, "wallpaper.jpg")
        # создаём фон и показываем его
        self.bg = WallpaperBackground(wallpaper_path)

        self.wait_window = None

        # Основное окно — без рамки, полупрозрачное тёмно-синее
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.radius = 18
        self._old_pos = None

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Samsung Electronics Extractor 31 Pro")
        self.setFixedSize(520, 640)

        # Тёмно-синий полупрозрачный фон
        self.setStyleSheet(f"""
            background-color: rgba(10, 30, 60, 180);
            color: white;
            border-radius: {self.radius}px;
        """)

        self.center()

        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(14, 14, 14, 14)

        title = QLabel("Samsung Electronics Extractor 31 Pro")
        title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        lang_layout = QHBoxLayout()
        lang_label = QLabel("Language:")
        lang_label.setStyleSheet("color: white;")
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Русский", "English"])
        self.lang_combo.currentIndexChanged.connect(self.change_language)
        self.lang_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(20,60,140,120);
                color: white;
                border-radius: 6px;
                padding: 4px;
            }
            QComboBox QAbstractItemView {
                background-color: rgba(5,15,30,200);
                color: white;
            }
        """)
        lang_layout.addWidget(lang_label)
        lang_layout.addWidget(self.lang_combo)
        layout.addLayout(lang_layout)

        # Buttons
        self.file_btn = QPushButton("Выбрать файл")
        self.folder_btn = QPushButton("Выбрать папку")
        self.extract_btn = QPushButton("Извлечь картинки")
        self.extract_v2_btn = QPushButton("Извлечь из файла картинки (улучшенная)")
        self.recovery_btn = QPushButton("Извлечь recovery")
        self.boot_btn = QPushButton("Извлечь boot")
        self.stop_btn = QPushButton("Остановить извлечение")
        self.restart_btn = QPushButton("Перезапустить Extractor")
        self.exit_btn = QPushButton("Выйти")

        
   # почти прозрачные кнопки (5-10% видимости)
        btn_style = """\
            QPushButton {
                background-color: rgba(10, 40, 120, 160);
                color: white;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: rgba(20, 70, 160, 200);
            }
            QPushButton:pressed {
                background-color: rgba(5, 20, 80, 220);
            }
            QPushButton:disabled {
                background-color: rgba(5, 20, 80, 220);
                color: rgba(200,200,200,120);
            }
        """
     

        for btn in [self.file_btn, self.folder_btn, self.extract_btn, self.extract_v2_btn,
                    self.recovery_btn, self.boot_btn, self.stop_btn, self.restart_btn, self.exit_btn]:
            btn.setFixedHeight(42)
            btn.setStyleSheet(btn_style)
            layout.addWidget(btn)

        self.stop_btn.setEnabled(False)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet("""
            background-color: rgba(5, 12, 28, 110);
            color: #7CFF7C;
            border-radius: 8px;
            font-family: monospace;
            font-size: 12px;
            padding: 8px;
        """)
        self.log_box.setFixedHeight(200)
        layout.addWidget(self.log_box)

        footer = QLabel("© Samsung Electronics Extractor 2025")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: rgba(255,255,255,180); font-size: 12px;")
        layout.addWidget(footer)

        self.setLayout(layout)

        # Connects
        self.file_btn.clicked.connect(self.select_file)
        self.folder_btn.clicked.connect(self.select_folder)
        self.extract_btn.clicked.connect(lambda: self.run_script("multiext.py", "Извлечение картинок завершено!"))
        self.extract_v2_btn.clicked.connect(lambda: self.run_script("multiextV2.py", "Извлечение картинок (улучшенная) завершено!"))
        self.recovery_btn.clicked.connect(lambda: self.run_script("recext.py", "Извлечение recovery завершено!"))
        self.boot_btn.clicked.connect(lambda: self.run_script("bootext.py", "Извлечение boot завершено!"))
        self.stop_btn.clicked.connect(self.stop_extraction)
        self.restart_btn.clicked.connect(self.restart_extractor)
        self.exit_btn.clicked.connect(self.confirm_exit)

        # Rounded mask
        try:
            path = QPainterPath()
            path.addRoundedRect(0, 0, self.width(), self.height(), self.radius, self.radius)
            region = QRegion(path.toFillPolygon().toPolygon())
            self.setMask(region)
        except Exception:
            pass

        self.show()

    # --- логирование и вспомогательные методы ---
    def _log_to_file(self, text):
        try:
            if self.folder_path:
                log_file = os.path.join(self.folder_path, "log_Extractor.txt")
            else:
                log_file = os.path.join(LOG_DIR, "log_Extractor.txt")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(text + "\n")
        except Exception:
            pass

    def log(self, text):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {text}"

        def _append():
            try:
                self.log_box.append(line)
                self.log_box.ensureCursorVisible()
            except Exception:
                pass

        # выполнить в GUI-потоке
        QTimer.singleShot(0, _append)
        # записать в файл (в отдельном потоке, чтобы не блокировать GUI)
        try:
            threading.Thread(target=self._log_to_file, args=(line,), daemon=True).start()
        except Exception:
            pass

    def select_file(self):
        path, _ = QFileDialog.getOpenFileName(self,
                                              "Выбрать файл" if self.LANG == "ru" else "Select File",
                                              "/storage/emulated/0")
        if path:
            self.file_path = path
            self.log(f"📄 Файл выбран: {path}")

    def select_folder(self):
        path = QFileDialog.getExistingDirectory(self,
                                                "Выбрать папку" if self.LANG == "ru" else "Select Folder",
                                                "/storage/emulated/0")
        if path:
            self.folder_path = path
            self.log(f"📁 Папка выбрана: {path}")

    def _set_running_state(self, running: bool):
        for btn in (self.extract_btn, self.extract_v2_btn, self.recovery_btn, self.boot_btn):
            try:
                btn.setEnabled(not running)
            except Exception:
                pass
        try:
            self.stop_btn.setEnabled(running)
            self.file_btn.setEnabled(not running)
            self.folder_btn.setEnabled(not running)
        except Exception:
            pass

    def run_script(self, script_name, finish_msg):
        # Проверка выбора файла и папки
        if not getattr(self, "file_path", "") or not getattr(self, "folder_path", ""):
            QMessageBox.warning(self, "Ошибка" if self.LANG == "ru" else "Error",
                                "Выберите файл и папку" if self.LANG == "ru" else "Select file and folder")
            return

        script_path = os.path.join(BASE_DIR, script_name)
        if not os.path.exists(script_path):
            self.log(f"❌ Скрипт не найден: {script_name} (ожидалось {script_path})")
            return

        # Если уже запущен процесс
        if self.process and self.process.poll() is None:
            self.log("⚠ Процесс уже запущен — сначала остановите его или дождитесь завершения.")
            return

        # Создать окно ожидания
        self.wait_window = WaitWindow(f"{finish_msg}... Подождите")
        try:
            self.wait_window.cancel_btn.clicked.connect(self.stop_extraction)
            self.wait_window.show()
        except Exception:
            pass

        # Определение интерпретатора python
        python_exec = sys.executable or "python3"
        cmd = [python_exec, script_path, self.file_path, self.folder_path]
        self.log("────────────────────────────────────────")
        self.log(f"▶ Команда: {' '.join(cmd)}")

        def target():
            try:
                preexec = None
                # использовать os.setsid только на POSIX
                if os.name == "posix" and hasattr(os, "setsid"):
                    preexec = os.setsid

                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1,
                    preexec_fn=preexec
                )
                try:
                    # попытаться получить pgid
                    if hasattr(os, "getpgid"):
                        self.process_pg = os.getpgid(self.process.pid)
                    else:
                        self.process_pg = None
                except Exception:
                    self.process_pg = None

                QTimer.singleShot(0, lambda: self._set_running_state(True))

                # Читать вывод в реальном времени
                for line in iter(self.process.stdout.readline, ''):
                    if not line:
                        break
                    stripped = line.rstrip('\n')
                    QTimer.singleShot(0, lambda s=stripped: self.log(s))

                self.process.wait()
                code = self.process.returncode
                if code == 0:
                    QTimer.singleShot(0, lambda: self.log(f"✅ {finish_msg}"))
                else:
                    QTimer.singleShot(0, lambda: self.log(f"❌ Скрипт завершился с кодом {code}"))
            except Exception as e:
                QTimer.singleShot(0, lambda: self.log(f"⚠ Ошибка при запуске: {e}"))
            finally:
                try:
                    if getattr(self.process, "stdout", None):
                        try:
                            self.process.stdout.close()
                        except Exception:
                            pass
                except Exception:
                    pass
                self.process = None
                self.process_pg = None
                QTimer.singleShot(0, lambda: self._set_running_state(False))
                QTimer.singleShot(0, lambda: (self.wait_window.close() if self.wait_window else None))
                self.wait_window = None

        threading.Thread(target=target, daemon=True).start()

    def stop_extraction(self):
        proc = getattr(self, "process", None)
        pg = getattr(self, "process_pg", None)
        if proc and proc.poll() is None:
            self.log("🛑 Останавливаю процесс...")
            try:
                proc.terminate()
            except Exception as e:
                self.log(f"⚠ Ошибка при terminate(): {e}")

            waited = 0.0
            timeout = 3.0
            while waited < timeout:
                if proc.poll() is not None:
                    break
                time.sleep(0.1)
                waited += 0.1

            if proc.poll() is None:
                self.log("⚠ Процесс не завершился — выполняю принудительное завершение группы процессов...")
                try:
                    if pg and os.name == "posix":
                        os.killpg(pg, signal.SIGKILL)
                    else:
                        proc.kill()
                except Exception as e:
                    self.log(f"⚠ Ошибка при принудительном завершении: {e}")

            try:
                proc.wait(timeout=2)
            except Exception:
                pass

            self.log("🛑 Извлечение остановлено.")
            self.process = None
            self.process_pg = None
            self._set_running_state(False)
            if self.wait_window:
                try:
                    self.wait_window.close()
                except Exception:
                    pass
                self.wait_window = None
        else:
            self.log("⚠ Нет активного процесса для остановки.")

    def restart_extractor(self):
        try:
            self.bg.stop()
        except Exception:
            pass
        python = sys.executable or "python3"
        try:
            os.execl(python, python, os.path.join(BASE_DIR, "ui.py"))
        except Exception as e:
            self.log(f"⚠ Не удалось перезапустить: {e}")

    def confirm_exit(self):
        reply = QMessageBox.question(self,
                                     "Выход" if self.LANG == "ru" else "Exit",
                                     "Вы точно хотите закрыть программу?" if self.LANG == "ru" else "Are you sure you want to exit?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                self.bg.stop()
            except Exception:
                pass
            if self.process and self.process.poll() is None:
                self.stop_extraction()
            self.close()

    def change_language(self, index):
        self.LANG = "ru" if index == 0 else "en"
        try:
            self.file_btn.setText("Выбрать файл" if self.LANG == "ru" else "Select File")
            self.folder_btn.setText("Выбрать папку" if self.LANG == "ru" else "Select Folder")
            self.extract_btn.setText("Извлечь картинки" if self.LANG == "ru" else "Extract Images")
            self.extract_v2_btn.setText("Извлечь из файла картинки (улучшенная)" if self.LANG == "ru" else "Extract Images (Improved)")
            self.recovery_btn.setText("Извлечь recovery" if self.LANG == "ru" else "Extract recovery")
            self.boot_btn.setText("Извлечь boot" if self.LANG == "ru" else "Extract boot")
            self.stop_btn.setText("Остановить извлечение" if self.LANG == "ru" else "Stop Extraction")
            self.restart_btn.setText("Перезапустить Extractor" if self.LANG == "ru" else "Restart Extractor")
            self.exit_btn.setText("Выйти" if self.LANG == "ru" else "Exit")
        except Exception:
            pass

    
 # --- перетаскивание окна ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._old_pos = event.globalPos()
        event.accept()

    def mouseMoveEvent(self, event):
        try:
            if self._old_pos is not None and event.buttons() & Qt.LeftButton:
                delta = event.globalPos() - self._old_pos
                self.move(self.x() + delta.x(), self.y() + delta.y())
                self._old_pos = event.globalPos()
        except Exception:
            pass
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._old_pos = None
        event.accept()

    # --- центрирование окна ---
    def center(self):
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2
        )


# ========== MAIN ==========
if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = ExtractorGUI()
    sys.exit(app.exec_())