#!/data/data/com.termux/files/usr/bin/env python3
import os
import subprocess
import sys
import time

# ─── Удобная функция для выполнения команд ─────────────────────────────
def run(cmd, fatal=True):
    print(f"\n>>> Выполняем: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if fatal and result.returncode != 0:
        print(f"Ошибка при выполнении: {cmd}")
        sys.exit(1)
    return result.returncode

# ─── Проверяем, установлен ли tkinter ─────────────────────────────
def check_tkinter():
    print("Проверка наличия tkinter...")
    try:
        import tkinter  # noqa
        print("✅ Tkinter установлен и работает.")
        return True
    except Exception as e:
        print("❌ Tkinter не найден или не работает:", e)
        return False

# ─── Основная установка ─────────────────────────────
def install_all():
    run("pkg update -y && pkg upgrade -y")
    run("pkg install x11-repo -y")
    run("pkg install termux-x11 -y")
    run("pkg install PyQt5")
    run("python -m pip install --upgrade pip setuptools wheel")
    run("python -m pip install --no-cache-dir --force-reinstall pillow")
run("pkg install abootimg")
run("pkg install gzip")
run("pkg install p7zip")

# ─── Настройка DISPLAY и запуск X11 ─────────────────────────────
def start_x11():
    os.environ["DISPLAY"] = ":0"
    print("\n▶ Запуск Termux X11...")
    subprocess.Popen("termux-x11 :0 &", shell=True)
    time.sleep(2)

# ─── Окно с изображением ─────────────────────────────
def show_image(img_path):
    from tkinter import Tk, Label
    from PIL import Image, ImageTk

    if not os.path.exists(img_path):
        print(f"Файл не найден: {img_path}")
        return

    root = Tk()
    root.title("Просмотрщик изображений")

    image = Image.open(img_path)
    photo = ImageTk.PhotoImage(image)

    label = Label(root, image=photo)
    label.pack(expand=True)
    root.mainloop()

# ─── Главный запуск ─────────────────────────────
if __name__ == "__main__":
    if not check_tkinter():
        print("\n⚙ Устанавливаем зависимости...")
        install_all()
        if not check_tkinter():
            print("❌ Tkinter всё ещё не установлен. Попробуй вручную:")
            print("   pkg install python-tkinter -y")
            sys.exit(1)

    start_x11()

    IMG_PATH = "/sdcard/test_image.jpg"
    show_image(IMG_PATH)