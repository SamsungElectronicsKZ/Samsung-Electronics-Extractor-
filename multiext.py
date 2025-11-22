#!/usr/bin/env python3
import os
import sys
import re

def extract_jpg_with_names(file_path, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(file_path, "rb") as f:
        data = f.read()

    count = 0
    i = 0
    while i < len(data):
        if data[i:i+2] == b'\xFF\xD8':  # JPEG SOI
            # Попытка найти имя файла рядом с изображением
            # Ищем ASCII-строку оканчивающуюся на ".jpg" в 200 байтах до SOI
            name_match = re.search(rb'([A-Za-z0-9_\-]+\.jpg)', data[max(0,i-200):i])
            if name_match:
                filename = name_match.group(1).decode(errors='ignore')
            else:
                filename = f'image_{count}.jpg'

            end = data.find(b'\xFF\xD9', i)
            if end != -1:
                jpg_data = data[i:end+2]
                out_file = os.path.join(output_dir, filename)
                with open(out_file, 'wb') as out:
                    out.write(jpg_data)
                print(f"[+] Extracted {out_file}")
                count += 1
                i = end + 2
            else:
                i += 2
        else:
            i += 1

    if count == 0:
        print("[!] No JPEG images found.")
    else:
        print(f"[+] Extraction finished. Total JPEG images: {count}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: python {sys.argv[0]} <sbl.mbn|sbl.bin> <output_folder>")
        sys.exit(1)

    extract_jpg_with_names(sys.argv[1], sys.argv[2])