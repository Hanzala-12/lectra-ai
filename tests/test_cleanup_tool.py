import datetime
import sys
import tarfile
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from cleanup_tool import (
    BackupManager,
    CandidateFile,
    CommandResult,
    Executor,
    FileCategory,
    ReportGenerator,
    RiskLevel,
    ScanResult,
    Scanner,
    ValidationResult,
    Validator,
    default_protected_config,
    main,
)


def _write_file(path: Path, content: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _build_candidate(
    path: Path, root: Path, category: FileCategory, risk: RiskLevel
) -> CandidateFile:
    return CandidateFile(
        path=path,
        relative_path=path.relative_to(root),
        size_bytes=path.stat().st_size if path.exists() else 0,
        category=category,
        risk_level=risk,
        action="DELETE",
        is_directory=path.is_dir(),
    )


class TestScanner:
    def test_empty_directory_returns_no_candidates(self, tmp_path):
        scanner = Scanner(tmp_path, default_protected_config(tmp_path))

        result = scanner.scan()

        assert result.candidates == []
        assert result.protected_paths_encountered == []

    def test_all_protected_directory_returns_no_candidates(self, tmp_path):
        _write_file(tmp_path / "src" / "module.pyc", "data")
        _write_file(tmp_path / "docs" / "guide.md", "data")
        scanner = Scanner(tmp_path, default_protected_config(tmp_path))

        result = scanner.scan()

        assert result.candidates == []
        assert any(path.name == "src" for path in result.protected_paths_encountered)
        assert any(path.name == "docs" for path in result.protected_paths_encountered)

    @pytest.mark.parametrize(
        "filename,category",
        [
            ("module.pyc", FileCategory.PYTHON_BYTECODE),
            ("module.pyo", FileCategory.PYTHON_BYTECODE),
            ("lib.so", FileCategory.COMPILED_EXTENSION),
            ("lib.dll", FileCategory.COMPILED_EXTENSION),
            ("lib.dylib", FileCategory.COMPILED_EXTENSION),
            ("app.log", FileCategory.LOG_FILE),
            ("temp.tmp", FileCategory.TEMP_FILE),
            ("temp.temp", FileCategory.TEMP_FILE),
            ("backup.bak", FileCategory.TEMP_FILE),
            ("file.swp", FileCategory.EDITOR_ARTIFACT),
            ("file.swo", FileCategory.EDITOR_ARTIFACT),
            ("patch.orig", FileCategory.TEMP_FILE),
            ("patch.rej", FileCategory.TEMP_FILE),
        ],
    )
    def test_each_low_risk_file_pattern_is_classified(
        self, tmp_path, filename, category
    ):
        scanner = Scanner(tmp_path, default_protected_config(tmp_path))

        candidate = scanner._classify_file(Path("work") / filename)

        assert candidate is not None
        assert candidate.category == category
        assert candidate.risk_level == RiskLevel.LOW

    @pytest.mark.parametrize(
        "name,category",
        [
            (".DS_Store", FileCategory.OS_METADATA),
            ("Thumbs.db", FileCategory.OS_METADATA),
            ("desktop.ini", FileCategory.OS_METADATA),
            (".directory", FileCategory.OS_METADATA),
            (".coverage", FileCategory.COVERAGE_ARTIFACT),
        ],
    )
    def test_exact_low_risk_names_are_excluded(self, tmp_path, name, category):
        scanner = Scanner(tmp_path, default_protected_config(tmp_path))

        candidate = scanner._classify_file(Path("work") / name)

        assert candidate is not None
        assert candidate.category == category
        assert candidate.risk_level == RiskLevel.LOW

    @pytest.mark.parametrize(
        "dirname,category",
        [
            ("__pycache__", FileCategory.PYTHON_CACHE),
            (".pytest_cache", FileCategory.TEST_CACHE),
            (".mypy_cache", FileCategory.TEST_CACHE),
            ("htmlcov", FileCategory.COVERAGE_ARTIFACT),
            ("build", FileCategory.BUILD_ARTIFACT),
            ("dist", FileCategory.BUILD_ARTIFACT),
            (".pip_cache", FileCategory.PIP_CACHE),
        ],
    )
    def test_low_risk_directories_are_classified(self, tmp_path, dirname, category):
        scanner = Scanner(tmp_path, default_protected_config(tmp_path))

        candidate = scanner._classify_file(Path(dirname))

        assert candidate is not None
        assert candidate.category == category
        assert candidate.risk_level == RiskLevel.LOW
        assert candidate.is_directory is True

    @pytest.mark.parametrize(
        "name",
        [
            "requirements.txt",
            "requirements-dev.txt",
            "requirements-prod.txt",
            "requirements-test.txt",
            "requirements-base.txt",
        ],
    )
    def test_requirements_variants_are_excluded(self, tmp_path, name):
        scanner = Scanner(tmp_path, default_protected_config(tmp_path))

        assert scanner._classify_file(Path("work") / name) is None

    @pytest.mark.parametrize(
        "name", ["notes.md", "config.yaml", "config.yml", "data.json"]
    )
    def test_protected_extensions_are_excluded(self, tmp_path, name):
        scanner = Scanner(tmp_path, default_protected_config(tmp_path))

        assert scanner._classify_file(Path("work") / name) is None

    def test_unreferenced_python_file_with_no_guard_is_orphaned(self, tmp_path):
        target = _write_file(tmp_path / "work" / "unused.py", "x = 1\n")
        other = _write_file(tmp_path / "other.py", "import os\n")
        scanner = Scanner(tmp_path, default_protected_config(tmp_path))

        candidate = scanner._classify_file(
            target.relative_to(tmp_path), all_py_files=[target, other]
        )

        assert candidate is not None
        assert candidate.category == FileCategory.ORPHANED_SCRIPT
        assert candidate.risk_level == RiskLevel.MEDIUM

    def test_python_file_with_main_guard_is_not_orphaned(self, tmp_path):
        target = _write_file(
            tmp_path / "work" / "runner.py",
            'if __name__ == "__main__":\n    print("hi")\n',
        )
        other = _write_file(tmp_path / "other.py", "import os\n")
        scanner = Scanner(tmp_path, default_protected_config(tmp_path))

        candidate = scanner._classify_file(
            target.relative_to(tmp_path), all_py_files=[target, other]
        )

        assert candidate is None

    def test_python_file_with_import_reference_is_not_orphaned(self, tmp_path):
        target = _write_file(tmp_path / "work" / "helper.py", "x = 1\n")
        importer = _write_file(tmp_path / "importer.py", "from work import helper\n")
        scanner = Scanner(tmp_path, default_protected_config(tmp_path))

        candidate = scanner._classify_file(
            target.relative_to(tmp_path), all_py_files=[target, importer]
        )

        assert candidate is None

    def test_python_file_with_from_import_style_reference_is_not_orphaned(
        self, tmp_path
    ):
        target = _write_file(tmp_path / "work" / "module.py", "x = 1\n")
        importer = _write_file(tmp_path / "importer.py", "from work.module import x\n")
        scanner = Scanner(tmp_path, default_protected_config(tmp_path))

        candidate = scanner._classify_file(
            target.relative_to(tmp_path), all_py_files=[target, importer]
        )

        assert candidate is None

    def test_python_file_with_import_and_main_guard_is_not_orphaned(self, tmp_path):
        target = _write_file(
            tmp_path / "work" / "runner.py",
            'if __name__ == "__main__":\n    print("run")\n',
        )
        importer = _write_file(tmp_path / "importer.py", "from work import runner\n")
        scanner = Scanner(tmp_path, default_protected_config(tmp_path))

        candidate = scanner._classify_file(
            target.relative_to(tmp_path), all_py_files=[target, importer]
        )

        assert candidate is None


class TestReportGenerator:
    def test_empty_candidate_list_produces_valid_report(self, tmp_path):
        result = ScanResult(
            candidates=[],
            protected_paths_encountered=[],
            skipped_paths=[],
            scan_timestamp=datetime.datetime(2024, 1, 1),
            root=tmp_path,
        )
        report_path = tmp_path / "DRY_RUN_CLEANUP.md"

        ReportGenerator().write_dry_run_report(result, report_path)

        content = report_path.read_text(encoding="utf-8")
        assert "Total candidates for deletion" in content
        assert "0" in content

    def test_all_risk_levels_appear_in_report(self, tmp_path):
        candidates = [
            CandidateFile(
                path=tmp_path / "module.pyc",
                relative_path=Path("module.pyc"),
                size_bytes=10,
                category=FileCategory.PYTHON_BYTECODE,
                risk_level=RiskLevel.LOW,
                action="DELETE",
                is_directory=False,
            ),
            CandidateFile(
                path=tmp_path / "notes.txt",
                relative_path=Path("notes.txt"),
                size_bytes=20,
                category=FileCategory.PLAIN_TEXT,
                risk_level=RiskLevel.MEDIUM,
                action="DELETE",
                is_directory=False,
                reason="Verify this text file before deleting.",
            ),
        ]
        report_path = tmp_path / "DRY_RUN_CLEANUP.md"
        result = ScanResult(
            candidates=candidates,
            protected_paths_encountered=[tmp_path / "src" / "keep.py"],
            skipped_paths=[],
            scan_timestamp=datetime.datetime(2024, 1, 1),
            root=tmp_path,
        )

        ReportGenerator().write_dry_run_report(result, report_path)

        content = report_path.read_text(encoding="utf-8")
        assert "Python Bytecode" in content
        assert "Plain Text File" in content
        assert "Verify this text file" in content
        assert "Protected Paths Encountered" in content

    @pytest.mark.parametrize(
        "size_bytes,expected",
        [(12, "12 B"), (1536, "1.5 KB"), (1024 * 1024 * 3, "3.0 MB")],
    )
    def test_size_formatting(self, size_bytes, expected):
        assert ReportGenerator()._format_size(size_bytes) == expected

    def test_summary_totals_match_candidate_data(self, tmp_path):
        candidates = [
            CandidateFile(
                path=tmp_path / "a.pyc",
                relative_path=Path("a.pyc"),
                size_bytes=100,
                category=FileCategory.PYTHON_BYTECODE,
                risk_level=RiskLevel.LOW,
                action="DELETE",
                is_directory=False,
            ),
            CandidateFile(
                path=tmp_path / "b.log",
                relative_path=Path("b.log"),
                size_bytes=200,
                category=FileCategory.LOG_FILE,
                risk_level=RiskLevel.LOW,
                action="DELETE",
                is_directory=False,
            ),
        ]
        result = ScanResult(
            candidates=candidates,
            protected_paths_encountered=[],
            skipped_paths=[],
            scan_timestamp=datetime.datetime(2024, 1, 1),
            root=tmp_path,
        )
        report_path = tmp_path / "DRY_RUN_CLEANUP.md"

        ReportGenerator().write_dry_run_report(result, report_path)

        content = report_path.read_text(encoding="utf-8")
        assert "2" in content
        assert "300 B" in content


class TestBackupManager:
    def test_successful_backup_contains_all_candidates(self, tmp_path):
        root = tmp_path
        backup_dir = root / ".cleanup_backups"
        file_a = _write_file(root / "work" / "a.pyc", "aaa")
        file_b = _write_file(root / "work" / "b.log", "bbbb")
        candidates = [
            _build_candidate(file_a, root, FileCategory.PYTHON_BYTECODE, RiskLevel.LOW),
            _build_candidate(file_b, root, FileCategory.LOG_FILE, RiskLevel.LOW),
        ]

        record = BackupManager(root, backup_dir).create_backup(candidates)

        assert record.archive_path.exists()
        with tarfile.open(record.archive_path, "r:gz") as tar:
            names = tar.getnames()
        assert "work/a.pyc" in names
        assert "work/b.log" in names

    def test_restore_extracts_files_back_to_original_paths(self, tmp_path):
        root = tmp_path
        backup_dir = root / ".cleanup_backups"
        source = _write_file(root / "work" / "restore_me.txt", "restore")
        candidate = _build_candidate(
            source, root, FileCategory.PLAIN_TEXT, RiskLevel.MEDIUM
        )
        manager = BackupManager(root, backup_dir)
        record = manager.create_backup([candidate])

        source.unlink()
        assert not source.exists()

        restore_result = manager.restore(record)

        assert restore_result.success is True
        assert source.exists()

    def test_backup_failure_raises_without_deleting_source_files(self, tmp_path):
        root = tmp_path
        backup_dir = root / ".cleanup_backups"
        source = _write_file(root / "work" / "to_keep.pyc", "payload")
        candidate = _build_candidate(
            source, root, FileCategory.PYTHON_BYTECODE, RiskLevel.LOW
        )
        manager = BackupManager(root, backup_dir)

        with patch("cleanup_tool.tarfile.open", side_effect=PermissionError("denied")):
            with pytest.raises(PermissionError):
                manager.create_backup([candidate])

        assert source.exists()


class TestExecutor:
    def test_deletion_order_matches_defined_sequence(self, tmp_path):
        root = tmp_path
        config = default_protected_config(root)
        executor = Executor(root, config)
        candidates = []
        ordered_categories = [
            FileCategory.PYTHON_BYTECODE,
            FileCategory.OS_METADATA,
            FileCategory.LOG_FILE,
            FileCategory.TEST_CACHE,
            FileCategory.BUILD_ARTIFACT,
            FileCategory.EDITOR_ARTIFACT,
        ]
        for index, category in enumerate(ordered_categories):
            file_path = _write_file(root / f"item_{index}.txt", str(index))
            candidates.append(
                CandidateFile(
                    path=file_path,
                    relative_path=file_path.relative_to(root),
                    size_bytes=file_path.stat().st_size,
                    category=category,
                    risk_level=RiskLevel.LOW,
                    action="DELETE",
                    is_directory=False,
                )
            )

        seen_categories = []
        original_delete = executor._delete_item

        def tracking_delete(candidate):
            seen_categories.append(candidate.category)
            return original_delete(candidate)

        executor._delete_item = tracking_delete
        executor.execute(candidates, interactive=False)

        assert seen_categories == ordered_categories

    def test_medium_risk_item_is_skipped_without_confirmation(self, tmp_path):
        root = tmp_path
        file_path = _write_file(root / "notes.txt", "keep me")
        candidate = CandidateFile(
            path=file_path,
            relative_path=file_path.relative_to(root),
            size_bytes=file_path.stat().st_size,
            category=FileCategory.PLAIN_TEXT,
            risk_level=RiskLevel.MEDIUM,
            action="DELETE",
            is_directory=False,
            reason="Verify this text file before deleting.",
        )

        result = Executor(root, default_protected_config(root)).execute(
            [candidate], interactive=False
        )

        assert result.deletions[0].skipped is True
        assert file_path.exists()

    def test_missing_file_logs_warning_and_continues(self, tmp_path, caplog):
        root = tmp_path
        file_path = root / "gone.pyc"
        candidate = CandidateFile(
            path=file_path,
            relative_path=Path("gone.pyc"),
            size_bytes=0,
            category=FileCategory.PYTHON_BYTECODE,
            risk_level=RiskLevel.LOW,
            action="DELETE",
            is_directory=False,
        )

        with caplog.at_level("WARNING"):
            result = Executor(root, default_protected_config(root)).execute(
                [candidate], interactive=False
            )

        assert result.deletions[0].skipped is True
        assert "no longer exists" in caplog.text

    def test_directory_candidate_triggers_recursive_removal(self, tmp_path):
        root = tmp_path
        directory = root / "build"
        nested = _write_file(directory / "nested" / "artifact.txt", "data")
        candidate = CandidateFile(
            path=directory,
            relative_path=Path("build"),
            size_bytes=nested.stat().st_size,
            category=FileCategory.BUILD_ARTIFACT,
            risk_level=RiskLevel.LOW,
            action="DELETE",
            is_directory=True,
        )

        result = Executor(root, default_protected_config(root))._delete_item(candidate)

        assert result.success is True
        assert not directory.exists()


class TestValidator:
    def test_all_commands_pass(self, tmp_path):
        validator = Validator(tmp_path)
        responses = [
            CommandResult("cmd1", 0, "ok", ""),
            CommandResult("cmd2", 0, "ok", ""),
            CommandResult("cmd3", 0, "ok", ""),
        ]

        with patch.object(validator, "_run_command", side_effect=responses):
            result = validator.validate()

        assert result.passed is True
        assert len(result.command_results) == 3

    def test_first_command_fails(self, tmp_path):
        validator = Validator(tmp_path)
        responses = [
            CommandResult("cmd1", 1, "", "boom"),
            CommandResult("cmd2", 0, "ok", ""),
            CommandResult("cmd3", 0, "ok", ""),
        ]

        with patch.object(validator, "_run_command", side_effect=responses):
            result = validator.validate()

        assert result.passed is False
        assert result.command_results[0].exit_code == 1

    def test_second_command_fails(self, tmp_path):
        validator = Validator(tmp_path)
        responses = [
            CommandResult("cmd1", 0, "ok", ""),
            CommandResult("cmd2", 2, "", "boom"),
            CommandResult("cmd3", 0, "ok", ""),
        ]

        with patch.object(validator, "_run_command", side_effect=responses):
            result = validator.validate()

        assert result.passed is False
        assert result.command_results[1].exit_code == 2

    def test_third_command_fails(self, tmp_path):
        validator = Validator(tmp_path)
        responses = [
            CommandResult("cmd1", 0, "ok", ""),
            CommandResult("cmd2", 0, "ok", ""),
            CommandResult("cmd3", 3, "", "boom"),
        ]

        with patch.object(validator, "_run_command", side_effect=responses):
            result = validator.validate()

        assert result.passed is False
        assert result.command_results[2].exit_code == 3


class TestIntegration:
    def test_dry_run_produces_report(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_file(tmp_path / "cache" / "module.pyc", "data")
        _write_file(tmp_path / "notes.txt", "review me")
        _write_file(tmp_path / "README.md", "keep")

        exit_code = main(["--root", str(tmp_path)])

        report = tmp_path / "DRY_RUN_CLEANUP.md"
        assert exit_code == 0
        assert report.exists()

        content = report.read_text(encoding="utf-8")
        assert "cache/module.pyc" in content.replace("\\", "/")
        assert "notes.txt" in content
        assert "`README.md` |" not in content

    def test_execute_deletes_only_expected_files(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_file(tmp_path / "cache" / "module.pyc", "data")
        _write_file(tmp_path / "notes.txt", "review me")
        _write_file(tmp_path / "README.md", "keep")

        validation_result = ValidationResult(
            passed=True,
            command_results=[
                CommandResult("cmd1", 0, "ok", ""),
                CommandResult("cmd2", 0, "ok", ""),
                CommandResult("cmd3", 0, "ok", ""),
            ],
        )

        with patch("cleanup_tool.Validator.validate", return_value=validation_result):
            exit_code = main(["--execute", "--yes", "--root", str(tmp_path)])

        assert exit_code == 0
        assert not (tmp_path / "cache" / "module.pyc").exists()
        assert (tmp_path / "notes.txt").exists()
        assert (tmp_path / "README.md").exists()

    def test_validation_failure_triggers_restore(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_file(tmp_path / "cache" / "module.pyc", "data")
        _write_file(tmp_path / "notes.txt", "review me")

        failing_validation = ValidationResult(
            passed=False,
            command_results=[
                CommandResult("cmd1", 1, "", "boom"),
                CommandResult("cmd2", 0, "ok", ""),
                CommandResult("cmd3", 0, "ok", ""),
            ],
        )

        with patch("cleanup_tool.Validator.validate", return_value=failing_validation):
            exit_code = main(["--execute", "--yes", "--root", str(tmp_path)])

        assert exit_code == 1
        assert (tmp_path / "cache" / "module.pyc").exists()
        assert (tmp_path / "notes.txt").exists()

    def test_first_validation_failure_triggers_restore_call(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        _write_file(tmp_path / "cache" / "module.pyc", "data")

        failing_validation = ValidationResult(
            passed=False,
            command_results=[
                CommandResult("cmd1", 1, "", "boom"),
                CommandResult("cmd2", 0, "ok", ""),
                CommandResult("cmd3", 0, "ok", ""),
            ],
        )

        with patch("cleanup_tool.BackupManager.restore") as restore_mock:
            restore_mock.return_value.success = True
            with patch(
                "cleanup_tool.Validator.validate", return_value=failing_validation
            ):
                exit_code = main(["--execute", "--yes", "--root", str(tmp_path)])

        assert exit_code == 1
        restore_mock.assert_called_once()

    def test_yes_flag_skips_interactive_prompt(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_file(tmp_path / "cache" / "module.pyc", "data")

        validation_result = ValidationResult(
            passed=True,
            command_results=[
                CommandResult("cmd1", 0, "ok", ""),
                CommandResult("cmd2", 0, "ok", ""),
                CommandResult("cmd3", 0, "ok", ""),
            ],
        )

        with patch(
            "builtins.input", side_effect=AssertionError("input should not be called")
        ):
            with patch(
                "cleanup_tool.Validator.validate", return_value=validation_result
            ):
                exit_code = main(["--execute", "--yes", "--root", str(tmp_path)])

        assert exit_code == 0
