# Implementation Plan: Project Cleanup Tool

## Overview

Implement `cleanup_tool.py` as a single self-contained Python script at the project root. The implementation follows the five-component pipeline (Scanner → ReportGenerator → BackupManager → Executor → Validator) with a supporting `argparse` CLI. Tests live in `tests/test_cleanup_tool.py` (unit + integration) and `tests/test_cleanup_tool_properties.py` (property-based, Hypothesis).

## Tasks

- [x] 1. Define data models and enumerations
  - Create `cleanup_tool.py` at the project root with all `dataclass` definitions and enumerations
  - Implement `RiskLevel` and `FileCategory` enums
  - Implement `CandidateFile`, `ScanResult`, `BackupRecord`, `DeletionRecord`, `CommandResult`, `ValidationResult`, `ExecutionResult`, and `ProtectedPathConfig` dataclasses exactly as specified in the design
  - Add module-level imports (`os`, `pathlib`, `tarfile`, `subprocess`, `logging`, `argparse`, `dataclasses`, `datetime`, `enum`, `typing`)
  - _Requirements: 1.5, 2.1–2.19, 6.3, 7.2, 9.1_

- [x] 2. Implement `ProtectedPathConfig` initialisation and `Scanner` core
  - [x] 2.1 Implement `ProtectedPathConfig` factory / default constructor
    - Hard-code the protected dirs (`src`, `tests`, `examples`, `kaggle_demo`, `frontend`, `docs`, `outputs`, `venv`, `.venv`, `.git`, `.cleanup_backups`)
    - Hard-code protected filenames (`.gitignore`, `.env.example`, `Dockerfile`, `docker-compose.yml`, `config.yaml`, `README.md`, `LICENSE`, `pytest.ini`, `.pre-commit-config.yaml`)
    - Hard-code protected extensions (`.md`, `.yaml`, `.yml`, `.json`)
    - _Requirements: 4.1–4.16, 10.3, 10.4_

  - [x] 2.2 Implement `Scanner._is_protected(path)`
    - Check protected dirs (prefix match on relative path), protected filenames, protected extensions, and `protected_exact_paths`
    - Return `True` if any rule matches; `False` otherwise
    - _Requirements: 1.3, 4.1–4.16, 10.1_

  - [x] 2.3 Write property test for protected-path enforcement (Property 1)
    - **Property 1: Protected paths are never classified as candidates**
    - **Validates: Requirements 1.3, 4.1–4.16, 10.1**
    - Use `@given(protected_prefix=st.sampled_from(PROTECTED_DIRS), ...)` with `@settings(max_examples=100)`
    - Assert `scanner._classify_file(path)` returns `None` for any path under a protected dir

  - [x] 2.4 Implement `Scanner._classify_file(path)` for low-risk patterns
    - Match all 19 low-risk patterns from Requirement 2 (bytecode, cache dirs, compiled extensions, logs, temp/bak, OS metadata, editor artifacts, test caches, coverage, build artifacts, pip cache)
    - Return `None` for protected paths (call `_is_protected` first)
    - Return a `CandidateFile` with the correct `FileCategory` and `RiskLevel.LOW` on match
    - _Requirements: 2.1–2.16, 2.19_

  - [x] 2.5 Write property test for low-risk pattern classification (Property 2)
    - **Property 2: Low-risk pattern classification is correct and mutually exclusive**
    - **Validates: Requirements 1.5, 2.1–2.19**
    - Generate random low-risk filenames in non-protected dirs; assert correct `RiskLevel.LOW` and `FileCategory`; assert no path appears twice in a `ScanResult`

  - [x] 2.6 Implement `Scanner._classify_file(path)` for medium-risk `.txt` files
    - Classify `*.txt` files not matching `requirements*.txt` and not under a protected path as `RiskLevel.MEDIUM`
    - _Requirements: 2.17, 4.1_

  - [x] 2.7 Write property test for `requirements*.txt` exclusion (Property 6)
    - **Property 6: `requirements.txt` variants are never candidates**
    - **Validates: Requirements 2.17, 4.1**
    - Generate `requirements.txt`, `requirements-dev.txt`, `requirements-prod.txt` in arbitrary dirs; assert `_classify_file` returns `None`

- [x] 3. Implement orphaned-script detection
  - [x] 3.1 Implement `Scanner._check_import_references(module_name, all_py_files)`
    - Build import index (Pass 1): scan all `.py` files for `import X` and `from X import ...` lines; normalise module names (strip `.py`, replace `/` with `.`, also check bare stem)
    - Return `True` if `module_name` appears in the index
    - _Requirements: 3.1, 3.2_

  - [x] 3.2 Implement `Scanner._has_main_guard(path)`
    - Read file lines and check for `if __name__` pattern
    - Return `True` if found; on read error return `False` (safe default per design error-handling matrix)
    - _Requirements: 3.2, 3.4_

  - [x] 3.3 Implement orphaned-script classification in `Scanner._classify_file`
    - For `*.py` files outside protected paths: call `_check_import_references` and `_has_main_guard`
    - Classify as `ORPHANED_SCRIPT` / `RiskLevel.MEDIUM` only when both checks return `False`
    - _Requirements: 3.1–3.5_

  - [x] 3.4 Write property test for orphaned-script detection (Property 3)
    - **Property 3: Orphaned script detection is correct in both directions**
    - **Validates: Requirements 3.1–3.5**
    - Generate sets of `.py` files with varying import graphs and `__main__` guard presence; assert classification matches expected orphan/non-orphan status in both directions

- [x] 4. Implement `Scanner.scan()` — full traversal
  - Implement `os.walk` traversal with directory pruning (prune protected dirs and candidate dirs from `dirnames`)
  - Collect all `.py` files in a first pass for the import index
  - Apply `_classify_file` to each file and directory encountered
  - Return a `ScanResult` with candidates, protected paths encountered, skipped paths, timestamp, and root
  - _Requirements: 1.1–1.5, 2.1–2.19, 3.1–3.5_

- [x] 5. Implement `ReportGenerator`
  - [x] 5.1 Implement `ReportGenerator._format_size(size_bytes)` and `_group_by_category(candidates)`
    - Format sizes as bytes / KB / MB with one decimal place
    - Group candidates by `FileCategory`
    - _Requirements: 5.3_

  - [x] 5.2 Implement `ReportGenerator.write_dry_run_report(result, output_path)`
    - Write `DRY_RUN_CLEANUP.md` with grouped candidate sections, per-file rows (relative path, size, action, risk level), medium-risk explanations, summary totals, and protected-paths section
    - _Requirements: 5.1–5.7_

  - [x] 5.3 Implement `ReportGenerator.write_final_report(result, output_path)`
    - Write `CLEANUP_DELETION_REPORT.md` with deleted files list, kept files list, total bytes reclaimed, validation command results (exit codes + output), execution timestamp, and backup archive path
    - _Requirements: 9.1–9.6_

  - [x] 5.4 Write property test for report completeness and consistency (Property 7)
    - **Property 7: Report content is complete and internally consistent**
    - **Validates: Requirements 5.2–5.5, 9.1–9.6**
    - Generate arbitrary `List[CandidateFile]`; assert every candidate appears in the report and summary totals equal the arithmetic sum of individual entries

- [x] 6. Implement `BackupManager`
  - [x] 6.1 Implement `BackupManager.create_backup(candidates)`
    - Create `.cleanup_backups/` dir if absent
    - Open `tarfile` with `w:gz`, add each existing candidate file using its `relative_path` as `arcname`
    - Return a `BackupRecord` with archive path, timestamp, archived files list, and total size
    - _Requirements: 6.1–6.3_

  - [x] 6.2 Implement `BackupManager.restore(record)`
    - Open the archive with `r:gz` and call `extractall(path=root)`
    - Return a `RestoreResult` indicating success or failure with error details
    - _Requirements: 6.4, 8.4_

- [x] 7. Implement `Executor`
  - [x] 7.1 Implement `Executor._double_check_protected(path)` and `Executor._delete_item(candidate)`
    - `_double_check_protected`: re-apply all protected-path rules independently of the Scanner result
    - `_delete_item`: for directories use `shutil.rmtree`; for files use `os.remove`; handle missing-file case (log warning, mark `skipped=True`); handle protected-path detection (skip, log warning)
    - _Requirements: 7.5, 7.6, 10.1, 10.2_

  - [x] 7.2 Write property test for Executor protected-path enforcement (Property 4)
    - **Property 4: Protected paths are never deleted by the Executor**
    - **Validates: Requirements 10.1, 10.2, 10.3, 10.4**
    - Construct `CandidateFile` objects with protected paths (simulating a Scanner bug); assert `_delete_item` returns `DeletionRecord(skipped=True)` and the file is not removed

  - [x] 7.3 Implement `Executor._confirm_medium_risk(candidate)` and medium-risk handling
    - Prompt user with `input()` for each medium-risk item when `interactive=True`
    - Skip (record as `skipped=True`) when `interactive=False` or user declines
    - _Requirements: 7.3, 7.4, 10.5_

  - [x] 7.4 Write property test for medium-risk confirmation requirement (Property 5)
    - **Property 5: Medium-risk items require explicit confirmation and are never auto-deleted**
    - **Validates: Requirements 7.3, 7.4, 10.5**
    - Generate `CandidateFile` objects with `RiskLevel.MEDIUM`; run `Executor.execute` in non-interactive mode; assert all medium-risk files are recorded as skipped and remain on disk

  - [x] 7.5 Implement `Executor.execute(candidates, interactive)` — deletion loop with ordering
    - Sort candidates by the deletion order defined in Requirement 7.2 (bytecode → OS metadata → temp → test caches → build artifacts → editor artifacts)
    - Iterate in order, calling `_double_check_protected`, then `_delete_item` or `_confirm_medium_risk`
    - Collect `DeletionRecord` entries; compute `total_bytes_reclaimed`
    - Return an `ExecutionResult` (backup record and validation result filled in by the caller)
    - _Requirements: 7.1–7.6_

  - [x] 7.6 Write property test for deletion ordering (Property 8)
    - **Property 8: Deletion order follows the defined safe sequence**
    - **Validates: Requirements 7.1, 7.2**
    - Generate `CandidateFile` lists spanning all deletion categories; assert the sequence of processed deletions matches the required category order

- [x] 8. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Implement `Validator`
  - [x] 9.1 Implement `Validator._run_command(cmd)`
    - Run via `subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=root, timeout=120)`
    - Return a `CommandResult` with command string, exit code, stdout, and stderr
    - _Requirements: 8.1–8.3_

  - [x] 9.2 Implement `Validator.validate()`
    - Run all three validation commands in sequence
    - Return `ValidationResult(passed=all exit codes are 0, command_results=[...])`
    - _Requirements: 8.1–8.6_

- [x] 10. Implement `CLI` entry point and wire all components together
  - [x] 10.1 Implement `argparse` CLI (`--execute`, `--yes`, `--backup-dir`, `--root`, `--verbose`)
    - Set up `logging` with console handler (`INFO` default, `DEBUG` with `--verbose`) and file handler (`DEBUG`, writes to `cleanup_tool.log`)
    - _Requirements: 1.1, 6.1, 7.1_

  - [x] 10.2 Implement dry-run flow in `main()`
    - Instantiate `ProtectedPathConfig` (add `.cleanup_backups/` to `protected_exact_paths` at runtime)
    - Run `Scanner.scan()`, then `ReportGenerator.write_dry_run_report()`
    - Print summary to console
    - _Requirements: 1.1–1.5, 5.1–5.7_

  - [x] 10.3 Implement execute flow in `main()`
    - If `--execute`: show dry-run summary, prompt for approval (skip if `--yes`), call `BackupManager.create_backup()`; abort on backup failure
    - Call `Executor.execute()`, then `Validator.validate()`
    - On validation failure: call `BackupManager.restore()`, log critical error if restore fails
    - Call `ReportGenerator.write_final_report()`
    - _Requirements: 6.1–6.4, 7.1–7.6, 8.1–8.6, 9.1–9.6, 10.1–10.5_

- [x] 11. Write unit tests (`tests/test_cleanup_tool.py`)
  - [x] 11.1 Write unit tests for `Scanner`
    - Test: empty directory returns empty candidate list
    - Test: all-protected directory returns no candidates
    - Test: each low-risk pattern type individually
    - Test: `requirements*.txt` variants are excluded
    - Test: `.md`, `.yaml`, `.yml`, `.json` files are excluded
    - _Requirements: 1.1–1.5, 2.1–2.19, 4.1–4.16_

  - [x] 11.2 Write unit tests for orphaned-script detection
    - Test: file with import reference → not orphaned
    - Test: file with `__main__` guard → not orphaned
    - Test: file with both → not orphaned
    - Test: file with neither → orphaned
    - Test: `from x import y` style import → not orphaned
    - _Requirements: 3.1–3.5_

  - [x] 11.3 Write unit tests for `ReportGenerator`
    - Test: empty candidate list produces valid report with zero totals
    - Test: all risk levels present in report
    - Test: size formatting (bytes, KB, MB)
    - Test: summary totals match candidate data
    - _Requirements: 5.1–5.7, 9.1–9.6_

  - [x] 11.4 Write unit tests for `BackupManager`
    - Test: successful backup creates archive containing all candidates
    - Test: backup failure (mock permission error) aborts without deletion
    - Test: restore extracts files back to original relative paths
    - _Requirements: 6.1–6.4_

  - [x] 11.5 Write unit tests for `Executor`
    - Test: deletion order matches Requirement 7.2 sequence
    - Test: medium-risk item skipped without confirmation in non-interactive mode
    - Test: missing-file at deletion time logs warning and continues
    - Test: directory candidate triggers recursive removal
    - _Requirements: 7.1–7.6, 10.1–10.5_

  - [x] 11.6 Write unit tests for `Validator`
    - Test: all commands pass → `ValidationResult.passed == True`
    - Test: first command fails → `passed == False`, restore triggered
    - Test: second command fails → `passed == False`
    - Test: third command fails → `passed == False`
    - _Requirements: 8.1–8.6_

- [x] 12. Write integration tests (`tests/test_cleanup_tool.py` — integration section using `tmp_path`)
  - [x] 12.1 Write integration test: dry-run produces correct `DRY_RUN_CLEANUP.md`
    - Create synthetic project tree in `tmp_path` with known candidates and protected files
    - Run dry-run; assert report contains all expected candidates and no protected files
    - _Requirements: 1.1–1.5, 5.1–5.7_

  - [x] 12.2 Write integration test: execute phase deletes only expected files
    - Run execute phase on synthetic tree; assert candidate files are deleted and protected files remain
    - _Requirements: 7.1–7.6, 10.1–10.5_

  - [x] 12.3 Write integration test: validation failure triggers restore
    - Mock `Validator.validate()` to return failure; assert all deleted files are restored from backup
    - _Requirements: 8.4–8.5_

  - [x] 12.4 Write integration test: `--yes` flag skips interactive prompt
    - Run execute flow with `--yes`; assert execution proceeds without any `input()` call
    - _Requirements: 7.1_

- [x] 13. Write property-based tests (`tests/test_cleanup_tool_properties.py`)
  - [x] 13.1 Write property test file scaffold
    - Create `tests/test_cleanup_tool_properties.py` with Hypothesis imports and shared strategies (protected dirs list, low-risk filename generators, `CandidateFile` strategy)
    - _Requirements: all_

  - [x] 13.2 Consolidate and verify all 8 property tests are present
    - Confirm Properties 1–8 are each implemented as a separate `@given`/`@settings(max_examples=100)` test function
    - Each test must include the comment `# Feature: project-cleanup-tool, Property N: <property_text>`
    - _Requirements: 1.3, 1.5, 2.1–2.19, 3.1–3.5, 4.1–4.16, 5.2–5.5, 7.1–7.2, 8.4, 9.1–9.6, 10.1–10.5_

- [x] 14. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Property tests (Properties 1–8) are distributed close to the implementation tasks they validate to catch errors early
- Each property test references its property number and the requirements it validates
- Unit tests and integration tests are in `tests/test_cleanup_tool.py`; property tests are in `tests/test_cleanup_tool_properties.py`
- The tool must remain a single file (`cleanup_tool.py`) with no third-party runtime dependencies; Hypothesis is a test-only dependency
- `shutil` must be imported in `cleanup_tool.py` for recursive directory deletion
