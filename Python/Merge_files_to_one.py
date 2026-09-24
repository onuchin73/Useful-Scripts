import os
import argparse
from pathlib import Path

def merge_files_to_one(input_folder, output_file, extensions=None, recursive=False):
    """
    Сохраняет содержимое всех файлов из папки в один txt файл.
    
    Args:
        input_folder: путь к папке с файлами
        output_file: путь к выходному txt файлу
        extensions: список расширений для фильтрации (например, ['.txt', '.py'])
        recursive: включать ли подпапки
    """
    
    input_path = Path(input_folder)
    
    # Проверяем существует ли папка
    if not input_path.exists():
        print(f"Ошибка: Папка '{input_folder}' не существует!")
        return False
    
    if not input_path.is_dir():
        print(f"Ошибка: '{input_folder}' не является папкой!")
        return False
    
    # Собираем все файлы
    files_to_process = []
    
    if recursive:
        # Рекурсивный обход всех подпапок
        for file_path in input_path.rglob('*'):
            if file_path.is_file():
                if extensions is None or file_path.suffix.lower() in extensions:
                    files_to_process.append(file_path)
    else:
        # Только файлы в текущей папке
        for file_path in input_path.iterdir():
            if file_path.is_file():
                if extensions is None or file_path.suffix.lower() in extensions:
                    files_to_process.append(file_path)
    
    if not files_to_process:
        print("Не найдено файлов для обработки!")
        return False
    
    # Сортируем файлы для удобства
    files_to_process.sort()
    
    # Записываем содержимое в выходной файл
    try:
        with open(output_file, 'w', encoding='utf-8') as outfile:
            outfile.write(f"Содержимое файлов из папки: {input_path.absolute()}\n")
            outfile.write("=" * 80 + "\n\n")
            
            for file_path in files_to_process:
                # Относительный путь для наглядности
                rel_path = file_path.relative_to(input_path) if recursive else file_path.name
                
                outfile.write(f"Файл: {rel_path}\n")
                outfile.write("-" * 60 + "\n")
                
                try:
                    # Пытаемся прочитать файл как текст
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        content = infile.read()
                        outfile.write(content)
                except UnicodeDecodeError:
                    # Если не текстовый файл, пишем предупреждение
                    outfile.write("[НЕВОЗМОЖНО ПРОЧИТАТЬ: бинарный файл или неподдерживаемая кодировка]\n")
                except Exception as e:
                    outfile.write(f"[ОШИБКА ПРИ ЧТЕНИИ: {str(e)}]\n")
                
                outfile.write("\n\n" + "=" * 80 + "\n\n")
        
        print(f"Готово! Содержимое {len(files_to_process)} файлов сохранено в '{output_file}'")
        return True
        
    except Exception as e:
        print(f"Ошибка при записи выходного файла: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Объединяет содержимое всех файлов из папки в один txt файл'
    )
    parser.add_argument('input_folder', help='Путь к папке с файлами')
    parser.add_argument('-o', '--output', default='merged_output.txt', 
                       help='Выходной txt файл (по умолчанию: merged_output.txt)')
    parser.add_argument('-e', '--extensions', nargs='+', 
                       help='Фильтр по расширениям (например: .txt .py .md)')
    parser.add_argument('-r', '--recursive', action='store_true',
                       help='Рекурсивно обрабатывать подпапки')
    
    args = parser.parse_args()
    
    # Преобразуем расширения в нижний регистр с точкой
    extensions = None
    if args.extensions:
        extensions = [ext if ext.startswith('.') else f'.{ext}' 
                     for ext in args.extensions]
        extensions = [ext.lower() for ext in extensions]
    
    merge_files_to_one(args.input_folder, args.output, extensions, args.recursive)


if __name__ == "__main__":
    main()