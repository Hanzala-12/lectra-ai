# Requirements Document

## Introduction

The Project Cleanup Tool is a maintenance utility for the voice-processing pipeline project. It performs a safe, non-destructive dry-run scan of the entire repository, identifies unnecessary files (cache artifacts, OS metadata, build outputs, temp files, and orphaned scripts), generates a structured cleanup report, and — upon explicit user approval — executes deletions in a defined safe order while validating that the pipeline remains functional after each cleanup pass.

The tool targets a Python/FastAPI backend project with a React/TypeScript frontend, a Kaggle demo notebook, DSP source modules under `src/`, tests under `tests/`, and examples under `examples/`. All of those directories are protected from deletion.

## Glossary

- **Cleanup_Tool**: The project cleanup/maintenance utility described in this document.
- **Scanner**: The component responsible for recursively traversing the project directory tree and classifying files.
- **Report_Generator**: The component that produces the `DRY_RUN_CLEANUP.md` report from Scanner output.
- **Executor**: The component that performs approved deletions in the defined safe order.
- **Validator**: The component that runs post-deletion checks to confirm pipeline integrity.
- **Backup_Manager**: The component that creates and restores a pre-deletion backup.
- **Candidate_File**: Any file or directory identified by the Scanner as a potential deletion target.
- **Protected_Path**: Any file or directory that must never be deleted (see Requirement 4).
- **Orphaned_Script**: A `.py` file that is never imported by any other module and contains no `if __name__ == "__main__"` guard.
- **Risk_Level**: A classification (`low`, `medium`, `high`) assigned to each Candidate_File indicating the consequence of accidental deletion.
- **Dry_Run**: A read-only scan pass that produces a report without modifying the filesystem.
- **Pipeline_Validation**: The set of three post-deletion checks that confirm the project still works correctly.

---

## Requirements

### Requirement 1: Dry-Run File Scan

**User Story:** As a developer, I want the Cleanup_Tool to scan the entire project without deleting anything, so that I can review what would be removed before committing to any changes.

#### Acceptance Criteria

1. WHEN the Cleanup_Tool is invoked in dry-run mode, THE Scanner SHALL recursively traverse the entire project directory tree starting from the repository root.
2. WHEN the Scanner encounters a file or directory whose name matches any pattern in the deletion pattern list (see Requirement 2), THE Scanner SHALL add it to the Candidate_File list.
3. WHEN the Scanner encounters a file or directory whose path matches any Protected_Path rule (see Requirement 4), THE Scanner SHALL exclude it from the Candidate_File list regardless of filename pattern.
4. THE Scanner SHALL complete the dry-run traversal without modifying, moving, or deleting any file or directory.
5. WHEN the Scanner finishes traversal, THE Scanner SHALL produce a structured list of Candidate_Files grouped by file type category.

---

### Requirement 2: Deletion Pattern Classification

**User Story:** As a developer, I want the Scanner to classify files into well-defined categories, so that I can understand exactly what type of clutter is being targeted.

#### Acceptance Criteria

1. THE Scanner SHALL identify files matching `*.pyc`, `*.pyo` as Python bytecode artifacts with Risk_Level `low`.
2. THE Scanner SHALL identify directories named `__pycache__` as Python cache directories with Risk_Level `low`.
3. THE Scanner SHALL identify files matching `*.so`, `*.dll`, `*.dylib` as compiled extension artifacts with Risk_Level `low`.
4. THE Scanner SHALL identify files matching `*.log` as log files with Risk_Level `low`.
5. THE Scanner SHALL identify files matching `*.tmp`, `*.temp`, `*.bak` as temporary or backup files with Risk_Level `low`.
6. THE Scanner SHALL identify files named `.DS_Store` as macOS metadata with Risk_Level `low`.
7. THE Scanner SHALL identify files named `Thumbs.db` as Windows thumbnail cache with Risk_Level `low`.
8. THE Scanner SHALL identify files matching `*.swp`, `*.swo` as Vim swap files with Risk_Level `low`.
9. THE Scanner SHALL identify files named `desktop.ini` as Windows folder settings with Risk_Level `low`.
10. THE Scanner SHALL identify files named `.directory` as KDE folder settings with Risk_Level `low`.
11. THE Scanner SHALL identify files matching `~$*` as Office temporary files with Risk_Level `low`.
12. THE Scanner SHALL identify files matching `*.orig`, `*.rej` as git/rebase leftover files with Risk_Level `low`.
13. THE Scanner SHALL identify directories named `.pytest_cache`, `.mypy_cache` as test/type-check cache directories with Risk_Level `low`.
14. THE Scanner SHALL identify files named `.coverage` and directories named `htmlcov` as coverage report artifacts with Risk_Level `low`.
15. THE Scanner SHALL identify directories named `build`, `dist` as build artifact directories with Risk_Level `low`.
16. THE Scanner SHALL identify directories matching `*.egg-info` as Python package metadata directories with Risk_Level `low`.
17. WHEN the Scanner encounters a `*.txt` file, THE Scanner SHALL classify it as a Candidate_File with Risk_Level `medium` only if the filename is not `requirements.txt` and the file does not reside in a Protected_Path.
18. WHEN the Scanner encounters a `*.py` file that is not in a Protected_Path, THE Scanner SHALL check whether it qualifies as an Orphaned_Script (see Requirement 3) and, if so, classify it as a Candidate_File with Risk_Level `medium`.
19. THE Scanner SHALL identify directories named `.pip_cache` as pip HTTP cache directories with Risk_Level `low`.

---

### Requirement 3: Orphaned Script Detection

**User Story:** As a developer, I want the Cleanup_Tool to identify Python scripts that serve no purpose in the project, so that I can decide whether to remove them.

#### Acceptance Criteria

1. WHEN the Scanner evaluates a `*.py` file outside a Protected_Path, THE Scanner SHALL search all other `*.py` files in the project for any `import` or `from … import` statement that references the evaluated file's module name.
2. WHEN the Scanner finds no import references to a `*.py` file, THE Scanner SHALL inspect that file for the presence of an `if __name__ == "__main__"` guard.
3. IF a `*.py` file has no import references AND no `if __name__ == "__main__"` guard, THEN THE Scanner SHALL classify it as an Orphaned_Script Candidate_File with Risk_Level `medium`.
4. IF a `*.py` file has no import references BUT contains an `if __name__ == "__main__"` guard, THEN THE Scanner SHALL classify it as a standalone runnable script and exclude it from the Candidate_File list.
5. THE Scanner SHALL never classify any file under `src/`, `tests/`, `examples/`, `kaggle_demo/`, or `frontend/` as an Orphaned_Script Candidate_File.

---

### Requirement 4: Protected Path Rules

**User Story:** As a developer, I want the Cleanup_Tool to enforce a strict list of protected paths, so that critical project files are never accidentally targeted for deletion.

#### Acceptance Criteria

1. THE Scanner SHALL never add any file named `requirements.txt`, `requirements-dev.txt`, or `requirements-prod.txt` to the Candidate_File list.
2. THE Scanner SHALL never add any file matching `*.md` to the Candidate_File list.
3. THE Scanner SHALL never add any file matching `*.yaml` or `*.yml` to the Candidate_File list.
4. THE Scanner SHALL never add any file matching `*.json` to the Candidate_File list.
5. THE Scanner SHALL never add any file matching `*.py` that resides under `src/` to the Candidate_File list.
6. THE Scanner SHALL never add any file or directory under `frontend/` to the Candidate_File list.
7. THE Scanner SHALL never add any file or directory under `kaggle_demo/` to the Candidate_File list.
8. THE Scanner SHALL never add any file or directory under `tests/` to the Candidate_File list.
9. THE Scanner SHALL never add any file or directory under `examples/` to the Candidate_File list.
10. THE Scanner SHALL never add any file or directory under `docs/` to the Candidate_File list.
11. THE Scanner SHALL never add `.gitignore`, `.env.example`, `Dockerfile`, or `docker-compose.yml` to the Candidate_File list.
12. THE Scanner SHALL never add any file or directory under `.git/` to the Candidate_File list.
13. THE Scanner SHALL never add `config.yaml`, `README.md`, `LICENSE`, `pytest.ini`, or `.pre-commit-config.yaml` to the Candidate_File list.
14. THE Scanner SHALL never add any file or directory under `outputs/` to the Candidate_File list.
15. THE Scanner SHALL never add any file or directory under `venv/` to the Candidate_File list.
16. THE Scanner SHALL never add any file or directory under `.venv/` to the Candidate_File list.

---

### Requirement 5: Cleanup Report Generation

**User Story:** As a developer, I want a structured Markdown report of all Candidate_Files, so that I can review and approve the cleanup plan before any deletions occur.

#### Acceptance Criteria

1. WHEN the dry-run scan is complete, THE Report_Generator SHALL create a file named `DRY_RUN_CLEANUP.md` in the project root directory.
2. THE Report_Generator SHALL group Candidate_Files in the report by file type category (e.g., Python bytecode, OS metadata, temp files, orphaned scripts, `.txt` files).
3. FOR EACH Candidate_File, THE Report_Generator SHALL include the relative file path, the file or directory size in human-readable form (bytes, KB, or MB), the proposed action (`DELETE` or `KEEP`), and the Risk_Level.
4. FOR EACH Candidate_File with Risk_Level `medium`, THE Report_Generator SHALL include an explanation of why the file is flagged and a recommendation for the user to confirm before deletion.
5. THE Report_Generator SHALL include a summary section listing the total number of files proposed for deletion, the total estimated disk space to be reclaimed, and the total number of files kept with reasons.
6. THE Report_Generator SHALL include a section listing all Protected_Paths that were encountered and skipped during the scan, including any `outputs/` directory found, noting that it is protected and its contents were not evaluated for deletion.
7. WHEN the Report_Generator writes `DRY_RUN_CLEANUP.md`, THE Report_Generator SHALL not delete, move, or modify any other file in the project.

---

### Requirement 6: Backup Before Deletion

**User Story:** As a developer, I want a backup created before any files are deleted, so that I can restore the project if something goes wrong.

#### Acceptance Criteria

1. WHEN the user approves the cleanup and the Executor is invoked, THE Backup_Manager SHALL create a compressed archive of all Candidate_Files before any deletion begins.
2. THE Backup_Manager SHALL store the backup archive in a location outside the project root or in a clearly named subdirectory that is excluded from the deletion pass.
3. WHEN the backup archive is created successfully, THE Backup_Manager SHALL record the archive path and creation timestamp in the execution log.
4. IF the backup archive creation fails, THEN THE Executor SHALL abort the cleanup and report the failure without deleting any files.

---

### Requirement 7: Safe Deletion Execution

**User Story:** As a developer, I want the Executor to delete files in a defined safe order, so that lower-risk artifacts are removed first and higher-risk items are handled last.

#### Acceptance Criteria

1. WHEN the user explicitly approves the cleanup by issuing the "proceed with cleanup" command, THE Executor SHALL begin the deletion pass.
2. THE Executor SHALL delete files in the following order: (1) `__pycache__` directories, `*.pyc`, `*.pyo`; (2) `.DS_Store`, `Thumbs.db`, `desktop.ini`, `.directory`; (3) `*.log`, `*.tmp`, `*.temp`, `*.bak`, `*.orig`, `*.rej`; (4) `.pytest_cache`, `.mypy_cache`, `.coverage`, `htmlcov`; (5) `build`, `dist`, `*.egg-info` directories; (6) `*.swp`, `*.swo`, `~$*` files.
3. THE Executor SHALL skip all `*.txt` files during the automated deletion pass and instead list them in the report for manual user review.
4. THE Executor SHALL skip all Orphaned_Script Candidate_Files during the automated deletion pass and instead list them in the report for manual user confirmation.
5. WHEN the Executor deletes a directory, THE Executor SHALL remove the directory and all its contents recursively.
6. IF a file targeted for deletion no longer exists at the time of deletion, THEN THE Executor SHALL log a warning and continue without treating the missing file as an error.

---

### Requirement 8: Post-Deletion Pipeline Validation

**User Story:** As a developer, I want the pipeline validated automatically after cleanup, so that I know the deletions did not break any functionality.

#### Acceptance Criteria

1. WHEN the Executor completes all deletions, THE Validator SHALL run the command `python -c "import src.pipeline; print('Pipeline OK')"` and verify it exits with code 0.
2. WHEN the Executor completes all deletions, THE Validator SHALL run the command `python clean_voice.py --help` and verify it exits with code 0.
3. WHEN the Executor completes all deletions, THE Validator SHALL run the command `pytest tests/ -v --ignore=tests/test_custom_modules.py` and verify it exits with code 0.
4. IF any validation command exits with a non-zero code, THEN THE Validator SHALL trigger the Backup_Manager to restore all deleted files from the backup archive.
5. WHEN restoration is complete after a validation failure, THE Validator SHALL produce an error report describing which validation command failed and its output.
6. WHEN all three validation commands exit with code 0, THE Validator SHALL record the validation results as passed in the final report.

---

### Requirement 9: Final Cleanup Report

**User Story:** As a developer, I want a final report after successful cleanup, so that I have a permanent record of what was removed and how much space was reclaimed.

#### Acceptance Criteria

1. WHEN all deletions and validations succeed, THE Report_Generator SHALL create a file named `CLEANUP_DELETION_REPORT.md` in the project root directory.
2. THE Report_Generator SHALL include in `CLEANUP_DELETION_REPORT.md` a list of every deleted file and directory with its relative path and original size.
3. THE Report_Generator SHALL include the total disk space reclaimed in human-readable form.
4. THE Report_Generator SHALL include a list of files that were kept and the reason each was kept (Protected_Path, medium-risk pending confirmation, or not matched).
5. THE Report_Generator SHALL include the results of all three Pipeline_Validation commands, including their exit codes and relevant output.
6. THE Report_Generator SHALL include the timestamp of the cleanup execution and the path to the backup archive.

---

### Requirement 10: Safety Guardrails

**User Story:** As a developer, I want hard safety rules enforced at every step, so that no critical file is ever deleted by mistake.

#### Acceptance Criteria

1. THE Cleanup_Tool SHALL enforce Protected_Path rules at both the Scanner stage and the Executor stage independently, so that a file cannot be deleted even if it was incorrectly added to the Candidate_File list.
2. IF the Executor encounters a Candidate_File whose path matches any Protected_Path rule at deletion time, THEN THE Executor SHALL skip the file, log a warning, and continue.
3. THE Cleanup_Tool SHALL never delete any file under `src/`, `tests/`, `examples/`, `kaggle_demo/`, `frontend/`, `docs/`, `outputs/`, `venv/`, or `.venv/` at any stage of execution.
4. THE Cleanup_Tool SHALL never delete `requirements.txt`, `requirements-dev.txt`, `requirements-prod.txt`, `config.yaml`, `README.md`, `LICENSE`, `pytest.ini`, `.gitignore`, `.env.example`, `Dockerfile`, or `docker-compose.yml`.
5. WHEN the Executor is about to delete a file with Risk_Level `medium`, THE Executor SHALL require explicit per-file user confirmation before proceeding with that deletion.
