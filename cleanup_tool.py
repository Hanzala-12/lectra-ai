"""
Project Cleanup Tool — safe maintenance utility for the voice-processing pipeline.

A single-file Python CLI utility that performs a safe, two-phase workflow:
1. Dry-run phase (default): Recursively scans the repository, classifies files
   against deletion patterns and protected-path rules, and writes a human-readable
   Markdown report (DRY_RUN_CLEANUP.md) without touching any file.
2. Execute phase (opt-in): After the user reviews the report and explicitly approves,
   creates a compressed backup, deletes files in a defined safe order, runs three
   post-deletion validation commands, and writes a final audit report
   (CLEANUP_DELETION_REPORT.md). If any validation fails, the backup is automatically
   restored.
"""

import os
import re
import pathlib
import tarfile
import subprocess
import logging
import argparse
import shutil
import datetime
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"


class FileCategory(Enum):
    PYTHON_BYTECODE = "Python Bytecode"
    PYTHON_CACHE = "Python Cache Directory"
    COMPILED_EXTENSION = "Compiled Extension"
    LOG_FILE = "Log File"
    TEMP_FILE = "Temporary/Backup File"
    OS_METADATA = "OS Metadata"
    EDITOR_ARTIFACT = "Editor Artifact"
    TEST_CACHE = "Test/Type-Check Cache"
    COVERAGE_ARTIFACT = "Coverage Artifact"
    BUILD_ARTIFACT = "Build Artifact"
    PIP_CACHE = "Pip Cache"
    ORPHANED_SCRIPT = "Orphaned Script"
    PLAIN_TEXT = "Plain Text File"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class CandidateFile:
    path: Path  # Absolute path
    relative_path: Path  # Relative to project root
    size_bytes: int  # 0 for directories (sum of contents)
    category: FileCategory
    risk_level: RiskLevel
    action: str  # "DELETE" or "KEEP"
    is_directory: bool
    reason: Optional[str] = None  # Explanation for medium-risk items


@dataclass
class ScanResult:
    candidates: List[CandidateFile]
    protected_paths_encountered: List[Path]
    skipped_paths: List[Path]
    scan_timestamp: datetime.datetime
    root: Path


@dataclass
class BackupRecord:
    archive_path: Path
    created_at: datetime.datetime
    archived_files: List[Path]
    total_size_bytes: int


@dataclass
class DeletionRecord:
    path: Path
    success: bool
    error: Optional[str] = None
    skipped: bool = False
    skip_reason: Optional[str] = None


@dataclass
class CommandResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str


@dataclass
class ValidationResult:
    passed: bool
    command_results: List[CommandResult]


@dataclass
class ExecutionResult:
    deletions: List[DeletionRecord]
    backup_record: BackupRecord
    validation_result: ValidationResult
    restored: bool
    execution_timestamp: datetime.datetime
    total_bytes_reclaimed: int


@dataclass
class ProtectedPathConfig:
    protected_dirs: List[str]  # e.g. ["src", "tests", "frontend", ...]
    protected_filenames: List[str]  # e.g. ["requirements.txt", ".gitignore", ...]
    protected_extensions: List[str]  # e.g. [".md", ".yaml", ".yml", ".json"]
    protected_exact_paths: List[Path]  # Absolute paths computed at startup


@dataclass
class RestoreResult:
    success: bool
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Task 2.1: ProtectedPathConfig factory function
# ---------------------------------------------------------------------------


def default_protected_config(root: Path) -> ProtectedPathConfig:
    protected_dirs = [
        "src",
        "tests",
        "examples",
        "kaggle_demo",
        "frontend",
        "docs",
        "outputs",
        "venv",
        ".venv",
        ".git",
        ".cleanup_backups",
    ]
    protected_filenames = [
        ".gitignore",
        ".env.example",
        "Dockerfile",
        "docker-compose.yml",
        "config.yaml",
        "README.md",
        "LICENSE",
        "pytest.ini",
        ".pre-commit-config.yaml",
        "cleanup_tool.log",
        "requirements.txt",
        "requirements-dev.txt",
        "requirements-prod.txt",
    ]
    protected_extensions = [".md", ".yaml", ".yml", ".json"]
    protected_exact_paths = []  # populated at runtime
    return ProtectedPathConfig(
        protected_dirs=protected_dirs,
        protected_filenames=protected_filenames,
        protected_extensions=protected_extensions,
        protected_exact_paths=protected_exact_paths,
    )


# ---------------------------------------------------------------------------
# Task 2.2 / 2.4 / 2.6: Scanner class
# ---------------------------------------------------------------------------


class Scanner:
    def __init__(self, root: Path, protected_paths: ProtectedPathConfig):
        self.root = root
        self.protected_paths = protected_paths

    def _is_protected(self, path: Path) -> bool:
        """Return True if path matches any protected-path rule."""
        # Check protected_exact_paths
        try:
            abs_path = path if path.is_absolute() else self.root / path
        except Exception:
            abs_path = path

        for exact in self.protected_paths.protected_exact_paths:
            try:
                if abs_path == exact or abs_path.is_relative_to(exact):
                    return True
            except Exception:
                pass

        # Get relative path for dir/filename checks
        try:
            rel = path.relative_to(self.root) if path.is_absolute() else path
        except ValueError:
            rel = path

        parts = rel.parts

        # Check protected dirs (prefix match)
        if parts:
            for protected_dir in self.protected_paths.protected_dirs:
                if parts[0] == protected_dir:
                    return True

        # Check protected filenames
        if rel.name in self.protected_paths.protected_filenames:
            return True

        # Check protected extensions
        if rel.suffix in self.protected_paths.protected_extensions:
            return True

        return False

    def _classify_file(
        self, path: Path, all_py_files: Optional[List[Path]] = None
    ) -> Optional[CandidateFile]:
        """Classify a file/dir as a candidate or return None if not a candidate."""
        # Protected check first
        if self._is_protected(path):
            return None

        # Get relative path
        try:
            rel = path.relative_to(self.root) if path.is_absolute() else path
        except ValueError:
            rel = path

        name = rel.name
        suffix = rel.suffix.lower()

        # --- Directory candidates ---
        DIR_CANDIDATES = {
            "__pycache__": (FileCategory.PYTHON_CACHE, RiskLevel.LOW),
            ".pytest_cache": (FileCategory.TEST_CACHE, RiskLevel.LOW),
            ".mypy_cache": (FileCategory.TEST_CACHE, RiskLevel.LOW),
            "htmlcov": (FileCategory.COVERAGE_ARTIFACT, RiskLevel.LOW),
            "build": (FileCategory.BUILD_ARTIFACT, RiskLevel.LOW),
            "dist": (FileCategory.BUILD_ARTIFACT, RiskLevel.LOW),
            ".pip_cache": (FileCategory.PIP_CACHE, RiskLevel.LOW),
        }

        if name in DIR_CANDIDATES:
            category, risk = DIR_CANDIDATES[name]
            try:
                abs_path = path if path.is_absolute() else self.root / path
            except Exception:
                abs_path = path
            return CandidateFile(
                path=abs_path,
                relative_path=rel,
                size_bytes=0,
                category=category,
                risk_level=risk,
                action="DELETE",
                is_directory=True,
            )

        # *.egg-info directories
        if name.endswith(".egg-info"):
            try:
                abs_path = path if path.is_absolute() else self.root / path
            except Exception:
                abs_path = path
            return CandidateFile(
                path=abs_path,
                relative_path=rel,
                size_bytes=0,
                category=FileCategory.BUILD_ARTIFACT,
                risk_level=RiskLevel.LOW,
                action="DELETE",
                is_directory=True,
            )

        # --- File size helper ---
        def get_size(p: Path) -> int:
            try:
                abs_p = p if p.is_absolute() else self.root / p
                return abs_p.stat().st_size
            except Exception:
                return 0

        # --- Low-risk file patterns ---

        # *.pyc, *.pyo → PYTHON_BYTECODE / LOW
        if suffix in (".pyc", ".pyo"):
            return CandidateFile(
                path=path if path.is_absolute() else self.root / path,
                relative_path=rel,
                size_bytes=get_size(path),
                category=FileCategory.PYTHON_BYTECODE,
                risk_level=RiskLevel.LOW,
                action="DELETE",
                is_directory=False,
            )

        # *.so, *.dll, *.dylib → COMPILED_EXTENSION / LOW
        if suffix in (".so", ".dll", ".dylib"):
            return CandidateFile(
                path=path if path.is_absolute() else self.root / path,
                relative_path=rel,
                size_bytes=get_size(path),
                category=FileCategory.COMPILED_EXTENSION,
                risk_level=RiskLevel.LOW,
                action="DELETE",
                is_directory=False,
            )

        # *.log → LOG_FILE / LOW
        if suffix == ".log":
            return CandidateFile(
                path=path if path.is_absolute() else self.root / path,
                relative_path=rel,
                size_bytes=get_size(path),
                category=FileCategory.LOG_FILE,
                risk_level=RiskLevel.LOW,
                action="DELETE",
                is_directory=False,
            )

        # *.tmp, *.temp, *.bak → TEMP_FILE / LOW
        if suffix in (".tmp", ".temp", ".bak"):
            return CandidateFile(
                path=path if path.is_absolute() else self.root / path,
                relative_path=rel,
                size_bytes=get_size(path),
                category=FileCategory.TEMP_FILE,
                risk_level=RiskLevel.LOW,
                action="DELETE",
                is_directory=False,
            )

        # .DS_Store, Thumbs.db, desktop.ini, .directory → OS_METADATA / LOW
        if name in (".DS_Store", "Thumbs.db", "desktop.ini", ".directory"):
            return CandidateFile(
                path=path if path.is_absolute() else self.root / path,
                relative_path=rel,
                size_bytes=get_size(path),
                category=FileCategory.OS_METADATA,
                risk_level=RiskLevel.LOW,
                action="DELETE",
                is_directory=False,
            )

        # *.swp, *.swo → EDITOR_ARTIFACT / LOW
        if suffix in (".swp", ".swo"):
            return CandidateFile(
                path=path if path.is_absolute() else self.root / path,
                relative_path=rel,
                size_bytes=get_size(path),
                category=FileCategory.EDITOR_ARTIFACT,
                risk_level=RiskLevel.LOW,
                action="DELETE",
                is_directory=False,
            )

        # *.orig, *.rej → TEMP_FILE / LOW (git leftovers)
        if suffix in (".orig", ".rej"):
            return CandidateFile(
                path=path if path.is_absolute() else self.root / path,
                relative_path=rel,
                size_bytes=get_size(path),
                category=FileCategory.TEMP_FILE,
                risk_level=RiskLevel.LOW,
                action="DELETE",
                is_directory=False,
            )

        # .coverage → COVERAGE_ARTIFACT / LOW
        if name == ".coverage":
            return CandidateFile(
                path=path if path.is_absolute() else self.root / path,
                relative_path=rel,
                size_bytes=get_size(path),
                category=FileCategory.COVERAGE_ARTIFACT,
                risk_level=RiskLevel.LOW,
                action="DELETE",
                is_directory=False,
            )

        # name starts with ~$ → EDITOR_ARTIFACT / LOW
        if name.startswith("~$"):
            return CandidateFile(
                path=path if path.is_absolute() else self.root / path,
                relative_path=rel,
                size_bytes=get_size(path),
                category=FileCategory.EDITOR_ARTIFACT,
                risk_level=RiskLevel.LOW,
                action="DELETE",
                is_directory=False,
            )

        # --- Task 2.6: *.txt medium-risk (not requirements*.txt) ---
        if suffix == ".txt":
            # Exclude requirements*.txt variants
            if name.startswith("requirements") and suffix == ".txt":
                return None
            return CandidateFile(
                path=path if path.is_absolute() else self.root / path,
                relative_path=rel,
                size_bytes=get_size(path),
                category=FileCategory.PLAIN_TEXT,
                risk_level=RiskLevel.MEDIUM,
                action="DELETE",
                is_directory=False,
                reason="Plain text file — verify it is not needed before deleting.",
            )

        # --- *.py files → orphaned-script detection (task 3.3) ---
        if suffix == ".py":
            # all_py_files must be provided for orphan detection
            if all_py_files is None:
                return None
            # Derive module name from relative path
            module_name = str(rel).replace("\\", "/")
            if module_name.endswith(".py"):
                module_name = module_name[:-3]
            has_ref = self._check_import_references(module_name, all_py_files)
            has_guard = self._has_main_guard(path)
            if not has_ref and not has_guard:
                return CandidateFile(
                    path=path if path.is_absolute() else self.root / path,
                    relative_path=rel,
                    size_bytes=get_size(path),
                    category=FileCategory.ORPHANED_SCRIPT,
                    risk_level=RiskLevel.MEDIUM,
                    action="DELETE",
                    is_directory=False,
                    reason=(
                        "Orphaned script — not imported by any other module "
                        "and has no if __name__ == '__main__' guard."
                    ),
                )
            return None

        return None

    def _build_import_index(self, all_py_files: List[Path]) -> set:
        """Pass 1: scan all .py files and build a set of imported module names."""
        imported_modules: set = set()
        import_re = re.compile(r"^\s*import\s+([\w\.,\s]+)")
        from_import_re = re.compile(r"^\s*from\s+([\w\.]+)\s+import\s+([\w\.,\s\*]+)")

        def _add_module(module: str) -> None:
            module = module.strip()
            if not module:
                return
            imported_modules.add(module)
            imported_modules.add(module.split(".")[-1])
            imported_modules.add(module.split(".")[0])

        for py_file in all_py_files:
            try:
                abs_file = py_file if py_file.is_absolute() else self.root / py_file
                with open(abs_file, "r", encoding="utf-8", errors="ignore") as fh:
                    for line in fh:
                        import_match = import_re.match(line)
                        if import_match:
                            modules = [
                                m.strip() for m in import_match.group(1).split(",")
                            ]
                            for module in modules:
                                # Handle aliases: "import pkg.mod as alias"
                                module = module.split(" as ")[0].strip()
                                _add_module(module)
                            continue

                        from_import_match = from_import_re.match(line)
                        if from_import_match:
                            base_module = from_import_match.group(1)
                            imported_names = [
                                n.strip() for n in from_import_match.group(2).split(",")
                            ]

                            _add_module(base_module)

                            for imported_name in imported_names:
                                # Skip wildcard imports for specific module-name indexing.
                                if imported_name == "*":
                                    continue
                                imported_name = imported_name.split(" as ")[0].strip()
                                # Include both symbol and fully qualified module form.
                                _add_module(imported_name)
                                _add_module(f"{base_module}.{imported_name}")
            except Exception:
                logging.warning("Could not read %s for import index", py_file)
        return imported_modules

    def _check_import_references(
        self, module_name: str, all_py_files: List[Path]
    ) -> bool:
        """Return True if module_name is imported anywhere in all_py_files."""
        index = self._build_import_index(all_py_files)
        # Normalise: strip .py, replace path separators with dots
        norm = module_name.replace("/", ".").replace("\\", ".")
        if norm.endswith(".py"):
            norm = norm[:-3]
        stem = norm.split(".")[-1]
        return norm in index or stem in index

    def _has_main_guard(self, path: Path) -> bool:
        """Return True if the file contains an if __name__ guard."""
        try:
            abs_path = path if path.is_absolute() else self.root / path
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    if "if __name__" in line:
                        return True
            return False
        except Exception:
            logging.warning("Could not read %s for __main__ guard check", path)
            return False  # safe default: treat as non-orphaned

    def scan(self) -> ScanResult:
        """Recursively traverse the project tree and classify all files."""
        candidates: List[CandidateFile] = []
        protected_encountered: List[Path] = []
        skipped_paths: List[Path] = []

        # Pass 1: collect all .py files for the import index
        all_py_files: List[Path] = []
        for dirpath, dirnames, filenames in os.walk(self.root, topdown=True):
            current = Path(dirpath)
            # Prune protected dirs from traversal
            dirnames[:] = [
                d
                for d in dirnames
                if not self._is_protected(
                    current.relative_to(self.root) / d
                    if current != self.root
                    else Path(d)
                )
            ]
            for filename in filenames:
                if filename.endswith(".py"):
                    all_py_files.append(current / filename)

        # Pass 2: full classification walk
        for dirpath, dirnames, filenames in os.walk(self.root, topdown=True):
            current = Path(dirpath)
            try:
                current_rel = current.relative_to(self.root)
            except ValueError:
                current_rel = current

            # Prune protected dirs
            pruned = []
            for d in list(dirnames):
                dir_rel = current_rel / d if str(current_rel) != "." else Path(d)
                if self._is_protected(dir_rel):
                    protected_encountered.append(current / d)
                    pruned.append(d)
            dirnames[:] = [d for d in dirnames if d not in pruned]

            # Check if current directory itself is a candidate (skip root)
            if current != self.root:
                dir_candidate = self._classify_file(current_rel)
                if dir_candidate is not None:
                    candidates.append(dir_candidate)
                    dirnames[:] = []  # prune subtree — no need to recurse
                    continue

            # Classify files
            for filename in filenames:
                filepath = current / filename
                try:
                    rel = filepath.relative_to(self.root)
                except ValueError:
                    rel = Path(filename)

                if self._is_protected(rel):
                    protected_encountered.append(filepath)
                    continue

                try:
                    candidate = self._classify_file(rel, all_py_files=all_py_files)
                except Exception as exc:
                    logging.warning("Error classifying %s: %s", filepath, exc)
                    skipped_paths.append(filepath)
                    continue

                if candidate is not None:
                    candidates.append(candidate)

        return ScanResult(
            candidates=candidates,
            protected_paths_encountered=protected_encountered,
            skipped_paths=skipped_paths,
            scan_timestamp=datetime.datetime.now(),
            root=self.root,
        )


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

# Deletion order per Requirement 7.2
_DELETION_ORDER: Dict[FileCategory, int] = {
    FileCategory.PYTHON_BYTECODE: 0,
    FileCategory.PYTHON_CACHE: 0,
    FileCategory.OS_METADATA: 1,
    FileCategory.LOG_FILE: 2,
    FileCategory.TEMP_FILE: 2,
    FileCategory.TEST_CACHE: 3,
    FileCategory.COVERAGE_ARTIFACT: 3,
    FileCategory.BUILD_ARTIFACT: 4,
    FileCategory.PIP_CACHE: 4,
    FileCategory.COMPILED_EXTENSION: 4,
    FileCategory.EDITOR_ARTIFACT: 5,
    FileCategory.PLAIN_TEXT: 6,
    FileCategory.ORPHANED_SCRIPT: 7,
}


class Executor:

    def __init__(self, root: Path, protected_paths: ProtectedPathConfig):
        self.root = root
        self.protected_paths = protected_paths
        # Reuse Scanner's _is_protected logic via a Scanner instance
        self._scanner = Scanner(root=root, protected_paths=protected_paths)

    def _double_check_protected(self, path: Path) -> bool:
        """Re-apply protected-path rules independently of the Scanner result."""
        try:
            rel = path.relative_to(self.root) if path.is_absolute() else path
        except ValueError:
            rel = path
        return self._scanner._is_protected(rel)

    def _delete_item(self, candidate: CandidateFile) -> DeletionRecord:
        """Delete a single candidate file or directory."""
        abs_path = (
            candidate.path
            if candidate.path.is_absolute()
            else self.root / candidate.path
        )

        # Second independent protected-path check
        if self._double_check_protected(abs_path):
            logging.warning(
                "Executor: skipping protected path %s (double-check triggered)",
                abs_path,
            )
            return DeletionRecord(
                path=abs_path,
                success=False,
                skipped=True,
                skip_reason="Protected path detected at execution time",
            )

        if not abs_path.exists():
            logging.warning("Executor: file no longer exists: %s", abs_path)
            return DeletionRecord(
                path=abs_path,
                success=False,
                skipped=True,
                skip_reason="File no longer exists",
            )

        try:
            if candidate.is_directory:
                shutil.rmtree(abs_path)
            else:
                os.remove(abs_path)
            return DeletionRecord(path=abs_path, success=True)
        except Exception as exc:
            logging.error("Executor: failed to delete %s: %s", abs_path, exc)
            return DeletionRecord(path=abs_path, success=False, error=str(exc))

    def _confirm_medium_risk(self, candidate: CandidateFile) -> bool:
        """Prompt the user for confirmation on a medium-risk item."""
        print(f"\n⚠️  Medium-risk item: {candidate.relative_path}")
        if candidate.reason:
            print(f"   Reason: {candidate.reason}")
        answer = input("   Delete this file? [y/N] ").strip().lower()
        return answer in ("y", "yes")

    def execute(
        self, candidates: List[CandidateFile], interactive: bool = True
    ) -> ExecutionResult:
        """Execute deletions in safe order, returning an ExecutionResult."""
        # Sort by deletion order; medium-risk items (PLAIN_TEXT, ORPHANED_SCRIPT) come last
        sorted_candidates = sorted(
            candidates,
            key=lambda c: _DELETION_ORDER.get(c.category, 99),
        )

        deletions: List[DeletionRecord] = []
        total_bytes = 0

        for candidate in sorted_candidates:
            # Medium-risk items require explicit confirmation
            if candidate.risk_level == RiskLevel.MEDIUM:
                if not interactive:
                    deletions.append(
                        DeletionRecord(
                            path=candidate.path,
                            success=False,
                            skipped=True,
                            skip_reason="Medium-risk item skipped in non-interactive mode",
                        )
                    )
                    continue
                if not self._confirm_medium_risk(candidate):
                    deletions.append(
                        DeletionRecord(
                            path=candidate.path,
                            success=False,
                            skipped=True,
                            skip_reason="User declined deletion",
                        )
                    )
                    continue

            record = self._delete_item(candidate)
            deletions.append(record)
            if record.success:
                total_bytes += candidate.size_bytes

        # backup_record and validation_result are filled in by the caller
        return ExecutionResult(
            deletions=deletions,
            backup_record=None,  # type: ignore[arg-type]
            validation_result=None,  # type: ignore[arg-type]
            restored=False,
            execution_timestamp=datetime.datetime.now(),
            total_bytes_reclaimed=total_bytes,
        )


# ---------------------------------------------------------------------------
# BackupManager
# ---------------------------------------------------------------------------


class BackupManager:

    def __init__(self, root: Path, backup_dir: Path):
        self.root = root
        self.backup_dir = backup_dir

    def create_backup(self, candidates: List[CandidateFile]) -> BackupRecord:
        """Create a compressed tar archive of all candidate files before deletion."""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = self.backup_dir / f"cleanup_backup_{timestamp}.tar.gz"

        archived_files: List[Path] = []
        total_size = 0

        with tarfile.open(archive_path, "w:gz") as tar:
            for candidate in candidates:
                abs_path = (
                    candidate.path
                    if candidate.path.is_absolute()
                    else self.root / candidate.path
                )
                if abs_path.exists():
                    tar.add(abs_path, arcname=str(candidate.relative_path))
                    archived_files.append(candidate.relative_path)
                    total_size += candidate.size_bytes

        return BackupRecord(
            archive_path=archive_path,
            created_at=datetime.datetime.now(),
            archived_files=archived_files,
            total_size_bytes=total_size,
        )

    def restore(self, record: BackupRecord) -> RestoreResult:
        """Restore all files from the backup archive."""
        try:
            with tarfile.open(record.archive_path, "r:gz") as tar:
                tar.extractall(path=self.root)
            return RestoreResult(success=True)
        except Exception as exc:
            logging.critical("Restore failed: %s", exc)
            return RestoreResult(success=False, error=str(exc))


# ---------------------------------------------------------------------------
# ReportGenerator
# ---------------------------------------------------------------------------


class ReportGenerator:

    def _format_size(self, size_bytes: int) -> str:
        """Format a byte count as a human-readable string."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    def _group_by_category(
        self, candidates: List[CandidateFile]
    ) -> Dict[str, List[CandidateFile]]:
        """Group candidates by their FileCategory display name."""
        groups: Dict[str, List[CandidateFile]] = {}
        for c in candidates:
            key = c.category.value
            groups.setdefault(key, []).append(c)
        return groups

    def write_dry_run_report(self, result: ScanResult, output_path: Path) -> None:
        """Write DRY_RUN_CLEANUP.md."""
        lines = []
        lines.append("# Dry-Run Cleanup Report\n")
        lines.append(f"**Scan timestamp:** {result.scan_timestamp.isoformat()}\n")
        lines.append(f"**Project root:** `{result.root}`\n\n")

        groups = self._group_by_category(result.candidates)
        total_files = 0
        total_bytes = 0

        for category_name, items in sorted(groups.items()):
            lines.append(f"## {category_name}\n\n")
            lines.append("| Relative Path | Size | Action | Risk Level |\n")
            lines.append("|---|---|---|---|\n")
            for item in items:
                size_str = self._format_size(item.size_bytes)
                lines.append(
                    f"| `{item.relative_path}` | {size_str} | {item.action} | {item.risk_level.value} |\n"
                )
                if item.reason:
                    lines.append(
                        f"\n> ⚠️ **{item.risk_level.value.upper()}**: {item.reason}\n\n"
                    )
                total_files += 1
                total_bytes += item.size_bytes
            lines.append("\n")

        # Summary
        lines.append("## Summary\n\n")
        lines.append(f"- **Total candidates for deletion:** {total_files}\n")
        lines.append(
            f"- **Estimated disk space to reclaim:** {self._format_size(total_bytes)}\n"
        )
        medium_count = sum(
            1 for c in result.candidates if c.risk_level == RiskLevel.MEDIUM
        )
        lines.append(
            f"- **Medium-risk items (require manual confirmation):** {medium_count}\n\n"
        )

        # Protected paths
        if result.protected_paths_encountered:
            lines.append("## Protected Paths Encountered (Skipped)\n\n")
            for p in result.protected_paths_encountered:
                try:
                    rel = p.relative_to(result.root)
                except ValueError:
                    rel = p
                lines.append(f"- `{rel}`\n")
            lines.append("\n")

        output_path.write_text("".join(lines), encoding="utf-8")

    def write_final_report(self, result: ExecutionResult, output_path: Path) -> None:
        """Write CLEANUP_DELETION_REPORT.md."""
        lines = []
        lines.append("# Cleanup Deletion Report\n\n")
        lines.append(
            f"**Execution timestamp:** {result.execution_timestamp.isoformat()}\n"
        )
        lines.append(f"**Backup archive:** `{result.backup_record.archive_path}`\n\n")

        deleted = [d for d in result.deletions if d.success and not d.skipped]
        kept = [d for d in result.deletions if d.skipped]

        lines.append("## Deleted Files\n\n")
        if deleted:
            lines.append("| Path | Notes |\n")
            lines.append("|---|---|\n")
            for d in deleted:
                lines.append(f"| `{d.path}` | |\n")
        else:
            lines.append("_No files were deleted._\n")
        lines.append("\n")

        lines.append("## Kept / Skipped Files\n\n")
        if kept:
            lines.append("| Path | Reason |\n")
            lines.append("|---|---|\n")
            for d in kept:
                reason = d.skip_reason or "skipped"
                lines.append(f"| `{d.path}` | {reason} |\n")
        else:
            lines.append("_No files were skipped._\n")
        lines.append("\n")

        lines.append(
            f"## Total Disk Space Reclaimed\n\n"
            f"{self._format_size(result.total_bytes_reclaimed)}\n\n"
        )

        lines.append("## Pipeline Validation Results\n\n")
        vr = result.validation_result
        status = "✅ PASSED" if vr.passed else "❌ FAILED"
        lines.append(f"**Overall status:** {status}\n\n")
        for cr in vr.command_results:
            lines.append(f"### `{cr.command}`\n\n")
            lines.append(f"- **Exit code:** {cr.exit_code}\n")
            if cr.stdout.strip():
                lines.append(f"- **stdout:**\n```\n{cr.stdout.strip()}\n```\n")
            if cr.stderr.strip():
                lines.append(f"- **stderr:**\n```\n{cr.stderr.strip()}\n```\n")
            lines.append("\n")

        if result.restored:
            lines.append(
                "## ⚠️ Restore Triggered\n\n"
                "Validation failed — all deleted files were restored from the backup archive.\n\n"
            )

        output_path.write_text("".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class Validator:
    """Runs post-deletion validation commands and triggers restore on failure."""

    def __init__(self, root: Path):
        self.root = root
        self.python_executable = sys.executable

    def _validation_commands(self) -> List[str]:
        """Build validation commands bound to the current interpreter."""
        src_path = (self.root / "src").as_posix()
        return [
            (
                f'"{self.python_executable}" -c '
                f"\"import sys; sys.path.insert(0, r'{src_path}'); "
                f"import pipeline; print('Pipeline OK')\""
            ),
            f'"{self.python_executable}" clean_voice.py --help',
            (
                f'"{self.python_executable}" -m pytest tests/ -v '
                f"--ignore=tests/test_custom_modules.py"
            ),
        ]

    def _run_command(self, cmd: str) -> CommandResult:
        """Run a shell command and return a CommandResult."""
        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                cwd=self.root,
                timeout=120,
            )
            return CommandResult(
                command=cmd,
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
            )
        except subprocess.TimeoutExpired:
            logging.error("Command timed out: %s", cmd)
            return CommandResult(
                command=cmd,
                exit_code=-1,
                stdout="",
                stderr="Command timed out after 120 seconds",
            )
        except Exception as exc:
            logging.error("Command failed to run: %s — %s", cmd, exc)
            return CommandResult(
                command=cmd,
                exit_code=-1,
                stdout="",
                stderr=str(exc),
            )

    def validate(self) -> ValidationResult:
        """Run all three validation commands and return a ValidationResult."""
        results: List[CommandResult] = []
        for cmd in self._validation_commands():
            result = self._run_command(cmd)
            results.append(result)
            if result.exit_code != 0:
                logging.error(
                    "Validation command failed (exit %d): %s\nstderr: %s",
                    result.exit_code,
                    cmd,
                    result.stderr,
                )

        passed = all(r.exit_code == 0 for r in results)
        return ValidationResult(passed=passed, command_results=results)


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------


def _setup_logging(verbose: bool) -> None:
    """Configure console and file logging handlers."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    root_logger.addHandler(console)

    # File handler — always DEBUG
    try:
        file_handler = logging.FileHandler("cleanup_tool.log", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
        )
        root_logger.addHandler(file_handler)
    except Exception as exc:
        logging.warning("Could not open log file: %s", exc)


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for the cleanup tool."""
    parser = argparse.ArgumentParser(
        prog="cleanup_tool.py",
        description=(
            "Project Cleanup Tool — safe maintenance utility for the "
            "voice-processing pipeline."
        ),
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute deletions after dry-run (requires confirmation)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip interactive confirmation prompt (use with --execute)",
    )
    parser.add_argument(
        "--backup-dir",
        metavar="DIR",
        default=None,
        help="Directory to store backup archive (default: .cleanup_backups/)",
    )
    parser.add_argument(
        "--root",
        metavar="DIR",
        default=None,
        help="Project root directory (default: current working directory)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print each file as it is scanned",
    )

    args = parser.parse_args(argv)
    _setup_logging(args.verbose)

    # Resolve root
    root = Path(args.root).resolve() if args.root else Path.cwd()

    # Build protected config and add .cleanup_backups to protected_exact_paths
    config = default_protected_config(root)
    backup_dir = (
        Path(args.backup_dir).resolve()
        if args.backup_dir
        else root / ".cleanup_backups"
    )
    config.protected_exact_paths.append(backup_dir)

    # -----------------------------------------------------------------------
    # Dry-run phase (always runs)
    # -----------------------------------------------------------------------
    logging.info("Starting dry-run scan of %s …", root)
    scanner = Scanner(root=root, protected_paths=config)
    scan_result = scanner.scan()

    report_path = root / "DRY_RUN_CLEANUP.md"
    rg = ReportGenerator()
    rg.write_dry_run_report(scan_result, report_path)

    # Console summary
    total = len(scan_result.candidates)
    total_bytes = sum(c.size_bytes for c in scan_result.candidates)
    medium = sum(1 for c in scan_result.candidates if c.risk_level == RiskLevel.MEDIUM)
    print(f"\n{'='*60}")
    print(f"  Dry-run complete — {total} candidate(s) found")
    print(f"  Estimated space to reclaim: {rg._format_size(total_bytes)}")
    print(f"  Medium-risk items (need confirmation): {medium}")
    print(f"  Report written to: {report_path}")
    print(f"{'='*60}\n")

    if not args.execute:
        logging.info("Dry-run only. Use --execute to perform deletions.")
        return 0

    # -----------------------------------------------------------------------
    # Execute phase
    # -----------------------------------------------------------------------

    # Prompt for approval unless --yes
    if not args.yes:
        print("Review the report above, then confirm to proceed with deletions.")
        answer = input("Proceed with cleanup? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("Aborted.")
            return 0

    # Create backup
    logging.info("Creating backup archive in %s …", backup_dir)
    bm = BackupManager(root=root, backup_dir=backup_dir)
    try:
        backup_record = bm.create_backup(scan_result.candidates)
        logging.info(
            "Backup created: %s (%s)",
            backup_record.archive_path,
            rg._format_size(backup_record.total_size_bytes),
        )
    except Exception as exc:
        logging.critical("Backup creation failed: %s — aborting.", exc)
        return 1

    # Execute deletions
    logging.info("Executing deletions …")
    executor = Executor(root=root, protected_paths=config)
    exec_result = executor.execute(scan_result.candidates, interactive=not args.yes)
    exec_result.backup_record = backup_record

    deleted_count = sum(1 for d in exec_result.deletions if d.success and not d.skipped)
    logging.info(
        "Deleted %d item(s), reclaimed %s.",
        deleted_count,
        rg._format_size(exec_result.total_bytes_reclaimed),
    )

    # Validate
    logging.info("Running post-deletion validation …")
    validator = Validator(root=root)
    validation_result = validator.validate()
    exec_result.validation_result = validation_result

    if not validation_result.passed:
        logging.error("Validation FAILED — triggering restore from backup.")
        restore_result = bm.restore(backup_record)
        exec_result.restored = True
        if not restore_result.success:
            logging.critical(
                "Restore FAILED: %s — backup archive preserved at %s",
                restore_result.error,
                backup_record.archive_path,
            )
        else:
            logging.info("Restore completed successfully.")
    else:
        logging.info("Validation PASSED.")

    # Write final report
    final_report_path = root / "CLEANUP_DELETION_REPORT.md"
    rg.write_final_report(exec_result, final_report_path)
    logging.info("Final report written to %s", final_report_path)

    return 0 if validation_result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
