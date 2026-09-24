import os

def find_string_in_files(directory, search_string):
    """
    Обходит все файлы в указанной директории (и поддиректориях) и ищет в них
    заданную подстроку.

    Args:
        directory: Путь к директории, в которой нужно искать файлы.
        search_string: Подстрока, которую нужно найти в файлах.

    Returns:
        Список кортежей, где каждый кортеж содержит путь к файлу и номер строки,
        в которой найдена подстрока.  Если подстрока не найдена ни в одном файле,
        возвращает пустой список.
    """
    results = []
    for root, _, files in os.walk(directory):  # os.walk возвращает (путь_к_директории, список_поддиректорий, список_файлов)
        for filename in files:
            filepath = os.path.join(root, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:  # Указываем кодировку, чтобы избежать проблем
                    for line_number, line in enumerate(f, 1):  # enumerate начинает с 0, добавляем 1 для нумерации строк
                        if search_string in line:
                            results.append((filepath, line_number))
            except Exception as e:
                print(f"Ошибка при обработке файла {filepath}: {e}")

    return results

# Пример использования:
directory_to_search = r"C:\Users\Anton Onuchin\Desktop\Новая папка"
string_to_find = "Информационное сообщение" # Замените на подстроку, которую хотите найти

search_results = find_string_in_files(directory_to_search, string_to_find)

if search_results:
    print(f"Подстрока '{string_to_find}' найдена в следующих файлах:")
    for filepath, line_number in search_results:
        print(f"- {filepath}, строка {line_number}")
else:
    print(f"Подстрока '{string_to_find}' не найдена ни в одном файле в директории {directory_to_search}")
