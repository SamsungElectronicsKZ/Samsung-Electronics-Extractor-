#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil
import gzip

def is_recovery_img(file_path):
    return os.path.isfile(file_path) and file_path.lower().endswith(".img")

def detect_format(file_path):
    """Определяем формат initrd.img (gzip, lz4 или unknown)"""
    try:
        result = subprocess.run(["file", file_path], capture_output=True, text=True)
        desc = result.stdout.lower()
        if "gzip" in desc:
            return "gzip"
        elif "lz4" in desc:
            return "lz4"
        else:
            return "unknown"
    except Exception:
        return "unknown"

def extract_initrd(initrd_target, out_dir):
    """Распаковываем initrd.img в initrd.cpio, а затем в initrd_contents"""
    initrd_cpio = os.path.join(out_dir, "initrd.cpio")
    initrd_contents = os.path.join(out_dir, "initrd_contents")
    os.makedirs(initrd_contents, exist_ok=True)

    fmt = detect_format(initrd_target)
    if fmt == "gzip":
        with gzip.open(initrd_target, "rb") as f_in:
            with open(initrd_cpio, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        print(f"[+] initrd.img распакован в {initrd_cpio} (gzip)")
    elif fmt == "lz4":
        subprocess.run(["lz4", "-d", initrd_target, initrd_cpio], check=True)
        print(f"[+] initrd.img распакован в {initrd_cpio} (lz4)")
    else:
        print(f"[-] Неизвестный формат initrd.img, копируем как есть")
        shutil.copy(initrd_target, initrd_cpio)

    # Распаковываем cpio
    try:
        subprocess.run(f"cpio -id < {initrd_cpio}", shell=True, cwd=initrd_contents, check=True)
        print(f"[+] initrd.cpio распакован в {initrd_contents}")
    except Exception as e:
        print(f"[-] Ошибка при распаковке initrd.cpio: {e}")

def extract_recovery(img_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    
    try:
        # Распаковка recovery.img через abootimg
        subprocess.run(["abootimg", "-x", img_path], check=True, cwd=out_dir)
    except FileNotFoundError:
        print("[-] abootimg не найден. Установите его.")
        return
    except subprocess.CalledProcessError:
        print("[-] Ошибка при извлечении recovery.img")
        return

    # Перемещение и распаковка файлов
    for f in os.listdir(out_dir):
        path = os.path.join(out_dir, f)

        # Ramdisk
        if f.lower().startswith("ramdisk") and f.endswith(".img"):
            target = os.path.join(out_dir, "Ramdisk.cpio")
            shutil.move(path, target)
            print(f"[+] Ramdisk.cpio извлечён: {target}")

        # Initrd
        elif f.lower() == "initrd.img":
            initrd_target = os.path.join(out_dir, "initrd.img")
            shutil.move(path, initrd_target)
            print(f"[+] initrd.img извлечён: {initrd_target}")
            extract_initrd(initrd_target, out_dir)

def main():
    if len(sys.argv) < 2:
        print("Использование: python3 extrecovery.py <recovery.img> [папка_вывода]")
        sys.exit(1)

    img_path = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.getcwd(), "recovery_out")

    if not is_recovery_img(img_path):
        print("[-] Файл не найден или не является recovery.img")
        sys.exit(1)

    extract_recovery(img_path, out_dir)
    print("[+] Готово!")

if __name__ == "__main__":
    main()