import argparse
import json
from collections import defaultdict
from datetime import datetime
from tabulate import tabulate


class WorkmateParser:
    @staticmethod
    def parse_logs(files, target_date=None) -> dict:
        logs = []
        stats = defaultdict(lambda: {'total': 0, 'avg_time': 0.0})
        str_counter = 1

        if not files:
            raise ValueError("Ошибка: Не указаны файлы для парсинга.")
        logs = []
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    for line in file:
                        try:
                            log = json.loads(line)
                            if 'url' not in log or not log['url']:
                                print(f'Ошибка: В файле {file_path}, в строке {str_counter} отсутствует поле url')
                                continue
                            if log['response_time'] == 0:
                                print(f'Ошибка: В файле {file_path}, в строке {str_counter} поле response_time равно нулю')
                                continue
                            elif 'response_time' not in log or not log['response_time']:
                                print(f'Ошибка: В файле {file_path}, в строке {str_counter} отсутствует поле response_time')
                                continue
                            logs.append(log)
                            str_counter += 1
                        except json.JSONDecodeError:
                            print(f'Ошибка в файле {file_path}, строка {line}')
                            continue
                str_counter = 1
            except FileNotFoundError:
                print(f'Ошибка: Файл не найден: {file_path}')
                continue

        filtered_logs = WorkmateParser.filter_by_date(logs, target_date)

        for log in filtered_logs:
            url = log['url']
            stats[url]['total'] += 1
            stats[url]['avg_time'] += log['response_time']
        return stats

    @staticmethod
    def generate_report(stats, report_type: str):
        if report_type == 'average':
            report = []
            for url, values in stats.items():
                try:
                    avg_time = round(values['avg_time'] / values['total'], 3)
                    report.append({
                        'headers': url,
                        'total': values['total'],
                        'avg_response_time': avg_time
                    })
                    report.sort(key=lambda x: x['total'], reverse=True)
                except ZeroDivisionError:
                    print('Ошибка: Деление на 0')
                except KeyError as e:
                    print(f'Ошибка: Отсутствует ключ в данных: {e}')
                except Exception as e:
                    print(f'Ошибка при генерации отчета average: {e}')
            return report
        # Дополнительный вывод отчетов
        elif report_type == '...':
            try:
                return None
            except Exception as e:
                print(f'Ошибка при генерации отчета ...: {e}')

    @staticmethod
    def validate_args(args):
        if not args:
            argparse.ArgumentError
            raise ValueError('Ошибка: Не указаны аргументы для работы парсера')
        if not args.file:
            raise ValueError('Ошибка: Не указаны файлы для парсера')
        for file_path in args.file:
            if not isinstance(file_path, str):
                raise ValueError(f'Ошибка: Некорректное имя файла: {file_path}')

    @staticmethod
    def valid_date(date_str):
        try:
            date = datetime.strptime(date_str, "%Y-%d-%m").date()
            if date.strftime("%Y-%d-%m") != date_str:
                raise ValueError
            return date
        except ValueError:
            raise argparse.ArgumentTypeError(f'Некорректная дата: {date_str}. Ожидается формат YYYY-DD-MM')

    @staticmethod
    def filter_by_date(logs, target_date=None):
        if not target_date:
            return logs

        print(f'Фильтрация логов по дате: {target_date}')
        filtered = []
        skipped = 0

        for log in logs:
            try:
                log_date = datetime.strptime(log['@timestamp'], "%Y-%m-%dT%H:%M:%S%z").date()
                if log_date == target_date:
                    filtered.append(log)
                else:
                    skipped += 1
            except (ValueError) as e:
                print(f'Ошибка при обработке временной метки: {e}')
                skipped += 1
                continue
        print(f'Найдено {len(filtered)} записей \nВсего записей: {len(logs)} \nПропущено: {skipped}')
        return filtered


def main():
    parser = argparse.ArgumentParser(prog='Workmate parser')
    parser.add_argument('--file',
                        nargs='+',
                        required=True,
                        help='Файл с логами')
    parser.add_argument('--report',
                        default='average',
                        choices=['average'],
                        help='Тип отчета (по умолчанию average)')

    parser.add_argument('--date',
                        required=False,
                        type=WorkmateParser.valid_date,
                        help='Дата в формате YYYY-DD-MM'
                        )
    try:
        args = parser.parse_args()
        logs_parser = WorkmateParser()
        logs_parser.validate_args(args)

        stats = logs_parser.parse_logs(args.file, args.date)
        report_data = logs_parser.generate_report(stats, args.report)

        print(tabulate(report_data, headers='keys'))
    except Exception as e:
        print(f'Ошибка: {e}')


if __name__ == "__main__":
    main()
