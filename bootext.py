#!/usr/bin/env python3
import os
import sys
import subprocess
import tempfile
import shutil

def is_gzip(file_path):
    with open(file_path, "rb") as f:
        return f.read(2) == b'\x1f\x8b'

def is_lz4(file_path):
    with open(file_path, "rb") as f:
        return f.read(4) == b'\x02\x21\x4c\x18'

def decompress(file_path, out_dir):
    """Распаковка gzip/lz4, возвращает путь к распакованному файлу"""
    base_name = os.path.basename(file_path)
    decompressed_path = os.path.join(out_dir, base_name + ".dec")
    
    if is_gzip(file_path):
        print(f"[+] Распаковка gzip: {base_name}")
        subprocess.run(["gunzip", "-c", file_path], stdout=open(decompressed_path, "wb"))
        return decompressed_path
    elif is_lz4(file_path):
        print(f"[+] Распаковка lz4: {base_name}")
        subprocess.run(["lz4", "-d", file_path, decompressed_path])
        return decompressed_path
    else:
        return file_path  # уже распакован

def extract_cpio(cpio_file, out_dir):
    """Распаковать cpio архив"""
    print(f"[+] Распаковка cpio: {cpio_file}")
    subprocess.run(["cpio", "-idm", "--no-absolute-filenames"], cwd=out_dir, stdin=open(cpio_file, "rb"))

def extract_bootimg(boot_img, out_dir):
    if not os.path.isfile(boot_img):
        print(f"[-] Файл не найден: {boot_img}")
        return

    os.makedirs(out_dir, exist_ok=True)

    with open(boot_img, "rb") as f:
        data = f.read()

    parts = {
        "zImage": data.find(b"\x18\x28\x6f\x01"),
        "kernel": data.find(b"ANDROID!"),
        "initrd.img": data.find(b"\x1f\x8b\x08"),
        "ramdisk.cpio": data.find(b"cpio"),
        "lz4": data.find(b"\x02\x21\x4c\x18"),
    }

    extracted_any = False
    for name, offset in parts.items():
        if offset == -1:
            continue
        path = os.path.join(out_dir, name)
        with open(path, "wb") as out:
            out.write(data[offset:])
        print(f"[+] Найден {name} @ 0x{offset:x}, сохранил как {path}")

        # Распаковываем initrd/ramdisk если нужно
        if name in ["initrd.img", "ramdisk.cpio"]:
            decompressed = decompress(path, out_dir)
            # Если это cpio, распаковываем его
            extract_cpio(decompressed, out_dir)

        extracted_any = True

    if not extracted_any:
        print("[-] Не найден kernel, initrd или ramdisk")
    else:
        print(f"[✓] Готово! Все файлы в: {out_dir}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Использование: python {sys.argv[0]} <boot.img> <output_folder>")
        sys.exit(1)

    boot_img_path = sys.argv[1]
    output_folder = sys.argv[2]

    extract_bootimg(boot_img_path, output_folder)