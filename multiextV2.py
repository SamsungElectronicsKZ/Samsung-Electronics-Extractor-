#!/usr/bin/env python3
import os
import sys
import struct

def extract_images(input_file, output_dir):
    """Извлечение изображений .jpg .bmp .png .jpeg из файла"""
    if not os.path.isfile(input_file):
        print(f"Файл не найден: {input_file}")
        return
    
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Начало извлечения изображений...\nИсходный файл: {input_file}\nВыходная папка: {output_dir}")
    
    with open(input_file, 'rb') as f:
        content = f.read()
    
    # Сигнатуры изображений
    signatures = {
        b'\xFF\xD8\xFF': '.jpg',
        b'\x89PNG\r\n\x1a\n': '.png',
        b'BM': '.bmp',
        b'\xFF\xD8\xFF\xE0': '.jpeg',
        b'\xFF\xD8\xFF\xE1': '.jpeg'
    }
    
    extracted_count = 0
    for signature, extension in signatures.items():
        start = 0
        while True:
            pos = content.find(signature, start)
            if pos == -1:
                break
            
            output_path = os.path.join(output_dir, f"image_{extracted_count:04d}{extension}")
            try:
                with open(output_path, 'wb') as img_file:
                    if extension == '.png':
                        end_marker = b'IEND\xaeB`\x82'
                        end_pos = content.find(end_marker, pos)
                        if end_pos != -1:
                            img_file.write(content[pos:end_pos + 8])
                        else:
                            img_file.write(content[pos:pos + 5000000])
                    elif extension == '.bmp':
                        bmp_size = struct.unpack('<I', content[pos + 2:pos + 6])[0]
                        img_file.write(content[pos:pos + bmp_size])
                    else:
                        img_file.write(content[pos:pos + 5000000])
                print(f"Найдено изображение: {os.path.basename(output_path)}")
                extracted_count += 1
            except Exception as e:
                print(f"Ошибка при сохранении изображения: {e}")
            
            start = pos + 1
    
    print(f"\nИзвлечение завершено. Найдено {extracted_count} изображений.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Использование: python ext.py <путь к файлу> <путь к папке>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_dir = sys.argv[2]
    
    extract_images(input_file, output_dir)