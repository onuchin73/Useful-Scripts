import os
import re

def remove_text_from_names(root_dir, text_to_remove):
    """
    Переименовывает файлы и папки, удаляя указанный текст.

    Args:
        root_dir: Путь к корневой директории, с которой начинается поиск.
        text_to_remove: Текст, который нужно удалить из имен файлов и папок.
    """

    pattern = re.compile(re.escape(text_to_remove) + r'\s*')

    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames_copy = list(dirnames)

        for dirname in reversed(sorted(dirnames_copy)):
            new_dirname = re.sub(pattern, '', dirname)
            if new_dirname != dirname:
                old_path = os.path.join(dirpath, dirname)
                new_path = os.path.join(dirpath, new_dirname)
                try:
                   os.rename(old_path, new_path)
                   print(f"Переименована папка: {dirname} -> {new_dirname}")

                   index = dirnames.index(dirname)
                   dirnames[index] = new_dirname

                except Exception as e:
                   print(f"Ошибка при переименовании папки {dirname}: {e}")

        for filename in filenames:
           new_filename = re.sub(pattern, '', filename)
           if new_filename != filename:
               old_path = os.path.join(dirpath, filename)
               new_path = os.path.join(dirpath, new_filename)
               try:
                  os.rename(old_path, new_path)
                  print(f"Переименован файл: {filename} -> {new_filename}")
               except Exception as e:
                    print(f"Ошибка при переименовании файла {filename}: {e}")

if __name__ == "__main__":
    root_directory = input("Введите путь к корневой директории: ")
    text_to_remove = input("Введите текст, который нужно удалить из имен: ")

    if os.path.isdir(root_directory):
        remove_text_from_names(root_directory, text_to_remove)
        print("Готово! Все папки и файлы были обработаны.")
    else:
        print("Ошибка: Указанный путь не является директорией.")
