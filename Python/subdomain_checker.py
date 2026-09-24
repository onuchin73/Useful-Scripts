import requests
import concurrent.futures
from urllib.parse import urlparse
import sys
from tabulate import tabulate
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from collections import defaultdict
import re

# Отключаем предупреждения о небезопасных соединениях
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SubdomainChecker:
    def __init__(self, timeout=5, max_workers=20):
        self.timeout = timeout
        self.max_workers = max_workers
        self.session = self._create_session()
        self.results = []

    def _create_session(self):
        """Создание сессии с повторными попытками"""
        session = requests.Session()
        retry_strategy = Retry(
            total=2,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def check_subdomain(self, subdomain):
        """Проверка одного поддомена"""
        subdomain = subdomain.strip()
        if not subdomain:
            return None

        result = {
            'subdomain': subdomain,
            'http': {
                'available': False,
                'status': None,
                'error': None,
                'url': None,
                'redirect_url': None
            },
            'https': {
                'available': False,
                'status': None,
                'error': None,
                'url': None,
                'redirect_url': None
            }
        }

        # Проверяем HTTP
        http_url = f"http://{subdomain}"
        result['http']['url'] = http_url
        try:
            response = self.session.get(http_url, timeout=self.timeout, allow_redirects=True, verify=False)
            result['http']['available'] = True
            result['http']['status'] = response.status_code
            result['http']['redirect_url'] = response.url if response.url != http_url else None
        except requests.exceptions.RequestException as e:
            result['http']['error'] = str(e)

        # Проверяем HTTPS
        https_url = f"https://{subdomain}"
        result['https']['url'] = https_url
        try:
            response = self.session.get(https_url, timeout=self.timeout, allow_redirects=True, verify=False)
            result['https']['available'] = True
            result['https']['status'] = response.status_code
            result['https']['redirect_url'] = response.url if response.url != https_url else None
        except requests.exceptions.RequestException as e:
            result['https']['error'] = str(e)

        return result

    def check_subdomains(self, subdomains):
        """Проверка списка поддоменов с использованием многопоточности"""
        self.results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_subdomain = {
                executor.submit(self.check_subdomain, subdomain): subdomain
                for subdomain in subdomains if subdomain.strip()
            }

            for future in concurrent.futures.as_completed(future_to_subdomain):
                subdomain = future_to_subdomain[future]
                try:
                    result = future.result()
                    if result:
                        self.results.append(result)
                except Exception as e:
                    print(f"Ошибка при проверке {subdomain}: {e}")

    def _categorize_status(self, status_code):
        """Категоризация HTTP статус-кода"""
        if status_code is None:
            return 'errors'
        elif 200 <= status_code < 300:
            return '2xx_success'
        elif 300 <= status_code < 400:
            return '3xx_redirect'
        elif 400 <= status_code < 500:
            return '4xx_client_error'
        elif 500 <= status_code < 600:
            return '5xx_server_error'
        else:
            return 'unknown'

    def _get_working_url(self, result):
        """Получение рабочей ссылки"""
        # Сначала проверяем HTTPS если доступен и статус не 4xx и не 5xx
        if result['https']['available'] and result['https']['status']:
            if result['https']['status'] < 400:
                if result['https']['redirect_url']:
                    return result['https']['redirect_url']
                return result['https']['url']
        # Затем HTTP если доступен и статус не 4xx и не 5xx
        if result['http']['available'] and result['http']['status']:
            if result['http']['status'] < 400:
                if result['http']['redirect_url']:
                    return result['http']['redirect_url']
                return result['http']['url']
        return None

    def _prepare_results(self):
        """Подготовка объединённых результатов для JSON с сортировкой"""
        categories = {
            '2xx_success': [],
            '3xx_redirect': [],
            '4xx_client_error': [],
            '5xx_server_error': [],
            'errors': []
        }

        for r in self.results:
            if r['https']['available'] and r['https']['status']:
                primary_status = r['https']['status']
            elif r['http']['available'] and r['http']['status']:
                primary_status = r['http']['status']
            else:
                primary_status = None

            category = self._categorize_status(primary_status)

            item = {
                'subdomain': r['subdomain'],
                'http': {
                    'available': r['http']['available'],
                    'status': r['http']['status'],
                    'error': r['http']['error'],
                    'url': r['http']['url'],
                    'redirect_url': r['http']['redirect_url']
                },
                'https': {
                    'available': r['https']['available'],
                    'status': r['https']['status'],
                    'error': r['https']['error'],
                    'url': r['https']['url'],
                    'redirect_url': r['https']['redirect_url']
                },
                'working_url': self._get_working_url(r)
            }

            categories[category].append(item)

        for category in categories:
            if category == 'errors':
                categories[category] = sorted(categories[category], key=lambda x: x['subdomain'])
            else:
                categories[category] = sorted(
                    categories[category],
                    key=lambda x: (
                        x['https']['status'] if x['https']['status'] is not None else 999,
                        x['http']['status'] if x['http']['status'] is not None else 999
                    )
                )

        return categories

    def display_results(self):
        """Отображение результатов в виде таблицы с сортировкой"""
        if not self.results:
            print("Нет результатов для отображения")
            return

        # Собираем только рабочие домены (2xx)
        working_domains = []
        for r in self.results:
            working_url = self._get_working_url(r)
            if working_url:
                # Определяем протокол
                if r['https']['available'] and r['https']['status'] and 200 <= r['https']['status'] < 300:
                    protocol = 'HTTPS'
                elif r['http']['available'] and r['http']['status'] and 200 <= r['http']['status'] < 300:
                    protocol = 'HTTP'
                else:
                    continue
                
                working_domains.append({
                    'subdomain': r['subdomain'],
                    'working_url': working_url,
                    'protocol': protocol
                })
        
        # Сортируем по поддомену
        working_domains = sorted(working_domains, key=lambda x: x['subdomain'])
        
        if not working_domains:
            print("❌ Рабочих доменов (2xx) не найдено")
            return
        
        # Формируем таблицу
        table_data = []
        headers = ["Домен", "Рабочая ссылка", "Протокол"]
        
        for item in working_domains:
            table_data.append([
                item['subdomain'],
                item['working_url'],
                item['protocol']
            ])
        
        print("\n" + "=" * 80)
        print("🌐 РАБОЧИЕ ДОМЕНЫ (2xx статус)")
        print("=" * 80)
        print(tabulate(table_data, headers=headers, tablefmt="grid", stralign="left"))
        
        print(f"\n📊 Всего рабочих доменов: {len(working_domains)}")
        
        # Сохраняем результаты
        self.save_results()
        self.save_working_domains()

    def save_working_domains(self):
        """Сохранение рабочих доменов (2xx) в txt файл"""
        timestamp = int(time.time())
        filename = f"working_domains_{timestamp}.txt"
        
        try:
            # Собираем только рабочие домены (2xx)
            working_domains = []
            for r in self.results:
                working_url = self._get_working_url(r)
                if working_url:
                    # Определяем протокол
                    if r['https']['available'] and r['https']['status'] and 200 <= r['https']['status'] < 300:
                        protocol = 'HTTPS'
                    elif r['http']['available'] and r['http']['status'] and 200 <= r['http']['status'] < 300:
                        protocol = 'HTTP'
                    else:
                        continue
                    
                    working_domains.append({
                        'subdomain': r['subdomain'],
                        'working_url': working_url,
                        'protocol': protocol
                    })
            
            # Сортируем по поддомену
            working_domains = sorted(working_domains, key=lambda x: x['subdomain'])
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("# Рабочие домены (2xx статус)\n")
                f.write("# Формат: домен | рабочая ссылка | протокол\n")
                f.write("#" + "=" * 70 + "\n\n")
                
                for item in working_domains:
                    f.write(f"{item['subdomain']} | {item['working_url']} | {item['protocol']}\n")
                
                f.write("\n" + "#" + "=" * 70 + "\n")
                f.write(f"# Всего рабочих доменов: {len(working_domains)}\n")
                f.write(f"# Дата генерации: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            print(f"\n✅ Рабочие домены сохранены в файл: {filename}")
            print(f"   Всего найдено: {len(working_domains)} доменов с 2xx статусом")
            
        except Exception as e:
            print(f"⚠️ Не удалось сохранить рабочие домены: {e}")

    def save_results(self):
        """Сохранение результатов в JSON файл с сортировкой"""
        import json
        timestamp = int(time.time())
        filename = f"subdomain_results_{timestamp}.json"

        results_data = self._prepare_results()

        total_checked = len(self.results)
        http_available = sum(
            1 for r in self.results if r['http']['available'] and r['http']['status'] and r['http']['status'] < 400)
        https_available = sum(
            1 for r in self.results if r['https']['available'] and r['https']['status'] and r['https']['status'] < 400)

        json_data = {
            'summary': {
                'total_checked': total_checked,
                'total_available_http': http_available,
                'total_available_https': https_available,
                'total_unavailable_http': total_checked - http_available,
                'total_unavailable_https': total_checked - https_available,
                'check_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'timestamp': timestamp
            },
            'results': results_data
        }

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Результаты сохранены в файл: {filename}")

            print("\n📋 Краткая статистика (из JSON):")
            print(f"  Всего проверено: {json_data['summary']['total_checked']}")
            print(f"  HTTP доступно: {json_data['summary']['total_available_http']}")
            print(f"  HTTPS доступно: {json_data['summary']['total_available_https']}")
            print(f"  HTTP недоступно: {json_data['summary']['total_unavailable_http']}")
            print(f"  HTTPS недоступно: {json_data['summary']['total_unavailable_https']}")

            print("\n  Результаты по категориям:")
            category_names = {
                '2xx_success': '2xx (Успешно)',
                '3xx_redirect': '3xx (Редиректы)',
                '4xx_client_error': '4xx (Ошибки клиента)',
                '5xx_server_error': '5xx (Ошибки сервера)',
                'errors': 'Ошибки соединения'
            }
            for category, items in json_data['results'].items():
                if items:
                    http_count = sum(1 for item in items if item['http']['available'])
                    https_count = sum(1 for item in items if item['https']['available'])
                    print(
                        f"    {category_names.get(category, category)}: {len(items)} (HTTP: {http_count}, HTTPS: {https_count})")

        except Exception as e:
            print(f"⚠️ Не удалось сохранить результаты: {e}")

    def load_subdomains_from_file(self, filename):
        """Загрузка поддоменов из файла"""
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                subdomains = [line.strip() for line in file if line.strip()]
            if not subdomains:
                print(f"⚠️ Файл {filename} пуст или содержит только пустые строки")
                return []
            print(f"✅ Загружено {len(subdomains)} поддоменов из {filename}")
            return subdomains
        except FileNotFoundError:
            print(f"❌ Файл {filename} не найден")
            return []
        except Exception as e:
            print(f"❌ Ошибка при чтении файла {filename}: {e}")
            return []


def main():
    if len(sys.argv) < 2:
        print("Использование: python subdomain_checker.py <файл_с_поддоменами.txt>")
        print("Пример: python subdomain_checker.py subdomains.txt")
        sys.exit(1)

    filename = sys.argv[1]

    checker = SubdomainChecker(timeout=5, max_workers=20)

    subdomains = checker.load_subdomains_from_file(filename)
    if not subdomains:
        sys.exit(1)

    print("\n🔄 Начинаем проверку поддоменов...")
    print("=" * 60)

    start_time = time.time()
    checker.check_subdomains(subdomains)
    elapsed_time = time.time() - start_time

    print(f"\n⏱️ Время выполнения: {elapsed_time:.2f} секунд")
    print("=" * 60)

    checker.display_results()


if __name__ == "__main__":
    main()