import pytest
import os
import argparse
from src.main import WorkmateParser
from collections import defaultdict
from unittest.mock import MagicMock
from datetime import date, datetime


class TestParser:
    # Тестирование основной функциональности парсера
    def test_parse_logs(self):
        valid_file = os.path.join(os.path.dirname(__file__), 'test_data', 'valid.log')
        empty_file = os.path.join(os.path.dirname(__file__), 'test_data', 'empty.log')

        stats = WorkmateParser.parse_logs([valid_file])
        empty_stats = WorkmateParser.parse_logs([empty_file])

        assert stats['/api/users/...']['total'] == 1
        assert stats['/api/homeworks/...']['total'] == 71
        assert stats['/api/specializations/...']['avg_time'] == pytest.approx(0.208, rel=0.01)
        assert empty_stats == defaultdict(lambda: {'total': 0, 'avg_time': 0.0})

    def test_mixed_valid_and_invalid(self, tmp_path):
        test_file = tmp_path / "mixed.log"
        test_file.write_text(
            '{"url": "/api/valid1", "response_time": 0.1}\n'
            '{"url": "", "response_time": 0.2}\n'
            '{"no_url": "value"}\n'
            '{"url": "/api/valid2", "response_time": 0.3}\n'
        )

        stats = WorkmateParser.parse_logs([str(test_file)])

        assert "/api/valid1" in stats
        assert "/api/valid2" in stats
        assert "" not in stats
        assert len(stats) == 2
        assert stats["/api/valid1"]["total"] == 1
        assert stats["/api/valid2"]["avg_time"] == pytest.approx(0.3)

    def test_json_decode_error(self, tmp_path, capsys):
        test_file = tmp_path / "broken_log.log"
        test_file.write_text('{"url": "/api/test", "response_time": 0.1}\n{broken\n')

        stats = WorkmateParser.parse_logs([str(test_file)])
        captured = capsys.readouterr()

        assert "Ошибка в файле" in captured.out
        assert "/api/test" in stats
        assert stats["/api/test"]["total"] == 1

    def test_missing_url_field(self, tmp_path, capsys):
        test_file = tmp_path / "missing_url.log"
        test_file.write_text('{"response_time": 0.1}\n')

        stats = WorkmateParser.parse_logs([str(test_file)])
        captured = capsys.readouterr()

        assert "отсутствует поле url" in captured.out
        assert stats == defaultdict(lambda: {'total': 0, 'avg_time': 0.0})
        assert "" not in stats

    def test_missing_response_time_field(self, tmp_path, capsys):
        test_file = tmp_path / 'missing_res_time.log'
        test_file.write_text('{"url": "/api/valid1"}\n')

        stats = WorkmateParser.parse_logs([str(test_file)])
        captured = capsys.readouterr()

        assert "отсутствует поле response_time" in captured.out

    # Тестирование генерации отчета
    def test_generate_report(self):
        stats = {
            '/api/users': {'total': 10, 'avg_time': 5.0},
            '/api/context': {'total': 8, 'avg_time': 3.0}
        }

        empty_stats = {}

        report = WorkmateParser.generate_report(stats, 'average')

        empty_report = WorkmateParser.generate_report(empty_stats, 'average')

        assert report[0]['headers'] == '/api/users'
        assert report[0]['total'] == 10
        assert report[0]['avg_response_time'] == 0.5
        assert report[1]['headers'] == '/api/context'
        assert report[1]['total'] == 8
        assert report[1]['avg_response_time'] == pytest.approx(0.37, rel=0.05)
        assert len(report) == 2
        assert empty_report == []

    def test_zero_division(self, capsys):
        stats = {
            '/api/users': {'total': 0, 'avg_time': 5.0},
        }

        report = WorkmateParser.generate_report(stats, 'average')
        captured = capsys.readouterr()

        assert 'Деление на 0' in captured.out
        assert report == []

    # Тестирование валидации данных
    def test_no_args(self):
        with pytest.raises(ValueError) as e:
            WorkmateParser.validate_args(None)
        assert str(e.value) == 'Ошибка: Не указаны аргументы для работы парсера'

    def test_no_files(self):
        args = MagicMock(file=[])
        with pytest.raises(ValueError) as e:
            WorkmateParser.validate_args(args)
        assert str(e.value) == 'Ошибка: Не указаны файлы для парсера'

    def test_invalid_filename(self):
        args = MagicMock(file=[123, 'invalid.txt'])
        with pytest.raises(ValueError) as e:
            WorkmateParser.validate_args(args)
        assert str(e.value) == 'Ошибка: Некорректное имя файла: 123'

    def test_valid_args(self):
        args = MagicMock(file=['example1.log', 'example2.log'])
        WorkmateParser.validate_args(args)

    def test_valid_date(self):
        test_date = "2025-22-06"
        validated = WorkmateParser.valid_date(test_date)
        assert validated == date(2025, 6, 22)

    def test_valid_date_incorrect_format(self):
        test_date = "2025-12-25"
        with pytest.raises(argparse.ArgumentTypeError):
            WorkmateParser.valid_date(test_date)

    def test_valid_date_incorrect_date(self):
        test_date = "2025-31-02"
        with pytest.raises(argparse.ArgumentTypeError):
            WorkmateParser.valid_date(test_date)

    # Тестирование фильтрации по дате
    def test_filter_by_date_without_target(self):
        logs = [
            {"@timestamp": "2025-06-21T13:57:34+00:00"},
            {"@timestamp": "2025-01-26T13:57:32+00:00"},
            {"@timestamp": "2025-03-22T13:57:32+00:00"},
        ]

        filtered = WorkmateParser.filter_by_date(logs)
        assert filtered == logs

    def test_filter_by_date_with_target(self):
        logs = [
            {"@timestamp": "2025-06-21T13:57:34+00:00"},
            {"@timestamp": "2025-01-26T13:57:32+00:00"},
            {"@timestamp": "2025-06-21T13:57:32+00:00"},
            {"@timestamp": "2025-03-23T13:57:32+00:00"},
        ]

        target_date = date(2025, 6, 21)
        filtered = WorkmateParser.filter_by_date(logs, target_date)

        assert len(filtered) == 2
        for log in filtered:
            log_date = datetime.strptime(log['@timestamp'], "%Y-%m-%dT%H:%M:%S%z").date()
            assert log_date == target_date
