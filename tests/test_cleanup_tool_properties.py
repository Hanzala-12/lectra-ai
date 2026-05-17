"""
Property-based tests for the Project Cleanup Tool.
Uses Hypothesis to verify universal invariants across randomly generated inputs.

Each property is tagged with:
  # Feature: project-cleanup-tool, Property N: <property_text>
"""

import datetime
import re
import sys
import os
from pathlib import Path
from typing import List
from unittest.mock import patch

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cleanup_tool import (
    CandidateFile,
    FileCategory,
    ProtectedPathConfig,
    RiskLevel,
    Scanner,
    ScanResult,
    default_protected_config,
)

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

PROTECTED_DIRS = [
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

LOW_RISK_FILENAMES = [
    "foo.pyc",
    "bar.pyo",
    "lib.so",
    "lib.dll",
    "lib.dylib",
    "app.log",
    "tmp.tmp",
    "tmp.temp",
    "old.bak",
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
    ".directory",
    "file.swp",
    "file.swo",
    "patch.orig",
    "patch.rej",
    ".coverage",
    "~$document.docx",
]

LOW_RISK_DIR_NAMES = [
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "htmlcov",
    "build",
    "dist",
    ".pip_cache",
]

# ---------------------------------------------------------------------------
# Shared strategies
# ---------------------------------------------------------------------------

WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}

safe_name = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"),
        whitelist_characters="._-",
    ),
    min_size=1,
    max_size=30,
).filter(
    lambda s: s.strip() and not s.startswith(".") and s.upper() not in WINDOWS_RESERVED
)

non_protected_dir = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"),
        whitelist_characters="_-",
    ),
    min_size=1,
    max_size=20,
).filter(
    lambda s: s not in PROTECTED_DIRS
    and s.strip()
    and s.upper() not in WINDOWS_RESERVED
)

candidate_file_strategy = st.builds(
    CandidateFile,
    path=st.just(Path("/tmp/fake")),
    relative_path=st.just(Path("fake/file.pyc")),
    size_bytes=st.integers(min_value=0, max_value=10_000_000),
    category=st.sampled_from(list(FileCategory)),
    risk_level=st.sampled_from(list(RiskLevel)),
    action=st.just("DELETE"),
    is_directory=st.booleans(),
    reason=st.none(),
)

# ---------------------------------------------------------------------------
# Property 1: Protected paths are never classified as candidates
# ---------------------------------------------------------------------------


@given(
    protected_prefix=st.sampled_from(PROTECTED_DIRS),
    subpath=safe_name,
    filename=st.sampled_from(LOW_RISK_FILENAMES + LOW_RISK_DIR_NAMES),
)
@settings(max_examples=100)
def test_protected_paths_never_candidates(protected_prefix, subpath, filename):
    # Feature: project-cleanup-tool, Property 1: Protected paths are never classified as candidates
    root = Path("/fake/root")
    config = default_protected_config(root)
    scanner = Scanner(root=root, protected_paths=config)

    path = Path(protected_prefix) / subpath / filename
    result = scanner._classify_file(path)
    assert result is None, f"Expected None for protected path {path}, got {result}"


@given(
    protected_prefix=st.sampled_from(PROTECTED_DIRS),
    filename=st.sampled_from(LOW_RISK_FILENAMES + LOW_RISK_DIR_NAMES),
)
@settings(max_examples=100)
def test_protected_paths_direct_child_never_candidates(protected_prefix, filename):
    # Feature: project-cleanup-tool, Property 1: Protected paths are never classified as candidates (direct child)
    root = Path("/fake/root")
    config = default_protected_config(root)
    scanner = Scanner(root=root, protected_paths=config)

    path = Path(protected_prefix) / filename
    result = scanner._classify_file(path)
    assert result is None, f"Expected None for protected path {path}, got {result}"


# ---------------------------------------------------------------------------
# Property 2: Low-risk pattern classification is correct and mutually exclusive
# ---------------------------------------------------------------------------

# Map each low-risk filename to its expected FileCategory
LOW_RISK_FILE_CATEGORY_MAP = {
    ".pyc": FileCategory.PYTHON_BYTECODE,
    ".pyo": FileCategory.PYTHON_BYTECODE,
    ".so": FileCategory.COMPILED_EXTENSION,
    ".dll": FileCategory.COMPILED_EXTENSION,
    ".dylib": FileCategory.COMPILED_EXTENSION,
    ".log": FileCategory.LOG_FILE,
    ".tmp": FileCategory.TEMP_FILE,
    ".temp": FileCategory.TEMP_FILE,
    ".bak": FileCategory.TEMP_FILE,
    ".swp": FileCategory.EDITOR_ARTIFACT,
    ".swo": FileCategory.EDITOR_ARTIFACT,
    ".orig": FileCategory.TEMP_FILE,
    ".rej": FileCategory.TEMP_FILE,
}

LOW_RISK_EXACT_NAME_MAP = {
    ".DS_Store": FileCategory.OS_METADATA,
    "Thumbs.db": FileCategory.OS_METADATA,
    "desktop.ini": FileCategory.OS_METADATA,
    ".directory": FileCategory.OS_METADATA,
    ".coverage": FileCategory.COVERAGE_ARTIFACT,
}

LOW_RISK_DIR_CATEGORY_MAP = {
    "__pycache__": FileCategory.PYTHON_CACHE,
    ".pytest_cache": FileCategory.TEST_CACHE,
    ".mypy_cache": FileCategory.TEST_CACHE,
    "htmlcov": FileCategory.COVERAGE_ARTIFACT,
    "build": FileCategory.BUILD_ARTIFACT,
    "dist": FileCategory.BUILD_ARTIFACT,
    ".pip_cache": FileCategory.PIP_CACHE,
}


@given(
    suffix=st.sampled_from(list(LOW_RISK_FILE_CATEGORY_MAP.keys())),
    stem=safe_name,
    parent=non_protected_dir,
)
@settings(max_examples=100)
def test_low_risk_file_extensions_classified_correctly(suffix, stem, parent):
    # Feature: project-cleanup-tool, Property 2: Low-risk pattern classification is correct and mutually exclusive
    root = Path("/fake/root")
    config = default_protected_config(root)
    scanner = Scanner(root=root, protected_paths=config)

    path = Path(parent) / f"{stem}{suffix}"
    result = scanner._classify_file(path)

    assert result is not None, f"Expected candidate for {path}, got None"
    assert (
        result.risk_level == RiskLevel.LOW
    ), f"Expected LOW risk for {path}, got {result.risk_level}"
    expected_category = LOW_RISK_FILE_CATEGORY_MAP[suffix]
    assert (
        result.category == expected_category
    ), f"Expected {expected_category} for {path}, got {result.category}"


@given(
    name=st.sampled_from(list(LOW_RISK_EXACT_NAME_MAP.keys())),
    parent=non_protected_dir,
)
@settings(max_examples=100)
def test_low_risk_exact_names_classified_correctly(name, parent):
    # Feature: project-cleanup-tool, Property 2: Low-risk exact-name classification is correct
    root = Path("/fake/root")
    config = default_protected_config(root)
    scanner = Scanner(root=root, protected_paths=config)

    path = Path(parent) / name
    result = scanner._classify_file(path)

    assert result is not None, f"Expected candidate for {path}, got None"
    assert result.risk_level == RiskLevel.LOW
    assert result.category == LOW_RISK_EXACT_NAME_MAP[name]


@given(
    dir_name=st.sampled_from(list(LOW_RISK_DIR_CATEGORY_MAP.keys())),
    parent=non_protected_dir,
)
@settings(max_examples=100)
def test_low_risk_dirs_classified_correctly(dir_name, parent):
    # Feature: project-cleanup-tool, Property 2: Low-risk directory classification is correct
    root = Path("/fake/root")
    config = default_protected_config(root)
    scanner = Scanner(root=root, protected_paths=config)

    path = Path(parent) / dir_name
    result = scanner._classify_file(path)

    assert result is not None, f"Expected candidate for {path}, got None"
    assert result.risk_level == RiskLevel.LOW
    assert result.category == LOW_RISK_DIR_CATEGORY_MAP[dir_name]
    assert result.is_directory is True


# ---------------------------------------------------------------------------
# Property 6: requirements*.txt variants are never candidates
# ---------------------------------------------------------------------------

REQUIREMENTS_VARIANTS = [
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-prod.txt",
    "requirements-test.txt",
    "requirements-base.txt",
]


@given(
    req_name=st.sampled_from(REQUIREMENTS_VARIANTS),
    parent=st.one_of(
        st.just(""),
        non_protected_dir,
        st.sampled_from(PROTECTED_DIRS),
    ),
)
@settings(max_examples=100)
def test_requirements_txt_variants_never_candidates(req_name, parent):
    # Feature: project-cleanup-tool, Property 6: requirements.txt variants are never candidates
    root = Path("/fake/root")
    config = default_protected_config(root)
    scanner = Scanner(root=root, protected_paths=config)

    if parent:
        path = Path(parent) / req_name
    else:
        path = Path(req_name)

    result = scanner._classify_file(path)
    assert result is None, f"Expected None for requirements file {path}, got {result}"


@given(
    suffix=st.sampled_from(
        [
            "",
            "-dev",
            "-prod",
            "-test",
            "-base",
            "-local",
            "-ci",
            "-staging",
        ]
    ),
    parent=non_protected_dir,
)
@settings(max_examples=100)
def test_any_requirements_txt_never_candidate(suffix, parent):
    # Feature: project-cleanup-tool, Property 6: Any requirements*.txt is never a candidate
    root = Path("/fake/root")
    config = default_protected_config(root)
    scanner = Scanner(root=root, protected_paths=config)

    stem = f"requirements{suffix}"
    path = Path(parent) / f"{stem}.txt"
    result = scanner._classify_file(path)
    assert result is None, f"Expected None for requirements file {path}, got {result}"


# ---------------------------------------------------------------------------
# Property 3: Orphaned script detection is correct in both directions
# ---------------------------------------------------------------------------


@given(
    stem=safe_name,
    parent=non_protected_dir,
)
@settings(max_examples=100)
def test_orphaned_script_no_ref_no_guard_is_candidate(stem, parent):
    # Feature: project-cleanup-tool, Property 3: Orphaned script detection is correct in both directions
    # A .py file with no imports referencing it and no __main__ guard → orphaned
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        config = default_protected_config(root)
        scanner = Scanner(root=root, protected_paths=config)

        target_dir = root / parent
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / f"{stem}.py"
        target_file.write_text("x = 1\n", encoding="utf-8")

        other_file = root / "other_module.py"
        other_file.write_text("import os\n", encoding="utf-8")

        all_py_files = [target_file, other_file]
        rel_path = target_file.relative_to(root)
        result = scanner._classify_file(rel_path, all_py_files=all_py_files)

        assert result is not None, f"Expected orphan candidate for {rel_path}"
        assert result.category == FileCategory.ORPHANED_SCRIPT
        assert result.risk_level == RiskLevel.MEDIUM


@given(
    stem=safe_name,
    parent=non_protected_dir,
)
@settings(max_examples=100)
def test_script_with_main_guard_not_orphaned(stem, parent):
    # Feature: project-cleanup-tool, Property 3: Script with __main__ guard is NOT orphaned
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        config = default_protected_config(root)
        scanner = Scanner(root=root, protected_paths=config)

        target_dir = root / parent
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / f"{stem}.py"
        target_file.write_text(
            'if __name__ == "__main__":\n    pass\n', encoding="utf-8"
        )

        other_file = root / "other_module.py"
        other_file.write_text("import os\n", encoding="utf-8")

        all_py_files = [target_file, other_file]
        rel_path = target_file.relative_to(root)
        result = scanner._classify_file(rel_path, all_py_files=all_py_files)

        assert (
            result is None
        ), f"Expected None (not orphaned) for script with __main__ guard: {rel_path}"


@given(
    stem=safe_name,
    parent=non_protected_dir,
)
@settings(max_examples=100, deadline=None)
def test_script_with_import_reference_not_orphaned(stem, parent):
    # Feature: project-cleanup-tool, Property 3: Script referenced by import is NOT orphaned
    assume(stem.isidentifier())

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        config = default_protected_config(root)
        scanner = Scanner(root=root, protected_paths=config)

        target_dir = root / parent
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / f"{stem}.py"
        target_file.write_text("x = 1\n", encoding="utf-8")

        other_file = root / "importer.py"
        other_file.write_text(f"import {stem}\n", encoding="utf-8")

        all_py_files = [target_file, other_file]
        rel_path = target_file.relative_to(root)
        result = scanner._classify_file(rel_path, all_py_files=all_py_files)

        assert (
            result is None
        ), f"Expected None (not orphaned) for imported script: {rel_path}"


# ---------------------------------------------------------------------------
# Property 7: Report content is complete and internally consistent
# ---------------------------------------------------------------------------

from cleanup_tool import (
    ReportGenerator,
    ScanResult,
    ExecutionResult,
    BackupRecord,
    ValidationResult,
)


@given(candidates=st.lists(candidate_file_strategy, min_size=0, max_size=20))
@settings(max_examples=100)
def test_dry_run_report_contains_all_candidates(candidates):
    # Feature: project-cleanup-tool, Property 7: Report content is complete and internally consistent
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        result = ScanResult(
            candidates=candidates,
            protected_paths_encountered=[],
            skipped_paths=[],
            scan_timestamp=datetime.datetime(2024, 1, 1),
            root=root,
        )
        report_path = root / "DRY_RUN_CLEANUP.md"
        rg = ReportGenerator()
        rg.write_dry_run_report(result, report_path)

        content = report_path.read_text(encoding="utf-8")

        # Every candidate's relative path must appear in the report
        for c in candidates:
            assert (
                str(c.relative_path) in content
            ), f"Candidate {c.relative_path} missing from dry-run report"

        # Summary total count must match
        total = len(candidates)
        assert f"**Total candidates for deletion:** {total}" in content


@given(candidates=st.lists(candidate_file_strategy, min_size=0, max_size=20))
@settings(max_examples=100)
def test_dry_run_report_size_totals_are_correct(candidates):
    # Feature: project-cleanup-tool, Property 7: Summary totals equal arithmetic sum of individual entries
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        result = ScanResult(
            candidates=candidates,
            protected_paths_encountered=[],
            skipped_paths=[],
            scan_timestamp=datetime.datetime(2024, 1, 1),
            root=root,
        )
        report_path = root / "DRY_RUN_CLEANUP.md"
        rg = ReportGenerator()
        rg.write_dry_run_report(result, report_path)

        expected_total = sum(c.size_bytes for c in candidates)
        expected_str = rg._format_size(expected_total)
        content = report_path.read_text(encoding="utf-8")
        assert (
            expected_str in content
        ), f"Expected size total {expected_str} not found in report"


# ---------------------------------------------------------------------------
# Property 4: Protected paths are never deleted by the Executor
# ---------------------------------------------------------------------------

from cleanup_tool import Executor, DeletionRecord


@given(
    protected_prefix=st.sampled_from(PROTECTED_DIRS),
    filename=st.sampled_from(["foo.pyc", "bar.log", "baz.tmp", ".DS_Store"]),
    subpath=safe_name,
)
@settings(max_examples=100)
def test_executor_never_deletes_protected_paths(protected_prefix, filename, subpath):
    # Feature: project-cleanup-tool, Property 4: Protected paths are never deleted by the Executor
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        config = default_protected_config(root)
        executor = Executor(root=root, protected_paths=config)

        protected_dir = root / protected_prefix / subpath
        protected_dir.mkdir(parents=True, exist_ok=True)
        protected_file = protected_dir / filename
        protected_file.write_bytes(b"important data")

        rel_path = protected_file.relative_to(root)

        candidate = CandidateFile(
            path=protected_file,
            relative_path=rel_path,
            size_bytes=14,
            category=FileCategory.PYTHON_BYTECODE,
            risk_level=RiskLevel.LOW,
            action="DELETE",
            is_directory=False,
        )

        record = executor._delete_item(candidate)

        assert (
            record.skipped is True
        ), f"Executor should have skipped protected path {rel_path}, got {record}"
        assert (
            protected_file.exists()
        ), f"Protected file {protected_file} was deleted — this must never happen"


# ---------------------------------------------------------------------------
# Property 5: Medium-risk items require explicit confirmation and are never auto-deleted
# ---------------------------------------------------------------------------

medium_risk_candidate_strategy = st.builds(
    CandidateFile,
    path=st.just(Path("/tmp/fake_medium.txt")),
    relative_path=st.just(Path("some_file.txt")),
    size_bytes=st.integers(min_value=0, max_value=1_000_000),
    category=st.sampled_from([FileCategory.PLAIN_TEXT, FileCategory.ORPHANED_SCRIPT]),
    risk_level=st.just(RiskLevel.MEDIUM),
    action=st.just("DELETE"),
    is_directory=st.just(False),
    reason=st.none(),
)


@given(candidates=st.lists(medium_risk_candidate_strategy, min_size=1, max_size=10))
@settings(max_examples=100)
def test_medium_risk_items_skipped_in_non_interactive_mode(candidates):
    # Feature: project-cleanup-tool, Property 5: Medium-risk items require explicit confirmation and are never auto-deleted
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        root = tmp_path
        config = default_protected_config(root)
        executor = Executor(root=root, protected_paths=config)

        real_candidates = []
        for i, c in enumerate(candidates):
            f = tmp_path / f"medium_file_{i}.txt"
            f.write_text("data", encoding="utf-8")
            real_candidates.append(
                CandidateFile(
                    path=f,
                    relative_path=f.relative_to(tmp_path),
                    size_bytes=4,
                    category=c.category,
                    risk_level=RiskLevel.MEDIUM,
                    action="DELETE",
                    is_directory=False,
                )
            )

        result = executor.execute(real_candidates, interactive=False)

        for record in result.deletions:
            assert (
                record.skipped is True
            ), f"Medium-risk item {record.path} was not skipped in non-interactive mode"

        for c in real_candidates:
            assert (
                c.path.exists()
            ), f"Medium-risk file {c.path} was deleted without confirmation"


# ---------------------------------------------------------------------------
# Property 8: Deletion order follows the defined safe sequence
# ---------------------------------------------------------------------------

from cleanup_tool import _DELETION_ORDER

# Categories that are auto-deleted (LOW risk only) for ordering test
LOW_RISK_CATEGORIES = [
    FileCategory.PYTHON_BYTECODE,
    FileCategory.PYTHON_CACHE,
    FileCategory.OS_METADATA,
    FileCategory.LOG_FILE,
    FileCategory.TEMP_FILE,
    FileCategory.TEST_CACHE,
    FileCategory.COVERAGE_ARTIFACT,
    FileCategory.BUILD_ARTIFACT,
    FileCategory.EDITOR_ARTIFACT,
]


@given(
    categories=st.lists(
        st.sampled_from(LOW_RISK_CATEGORIES),
        min_size=2,
        max_size=15,
    )
)
@settings(max_examples=100)
def test_deletion_order_follows_safe_sequence(categories):
    # Feature: project-cleanup-tool, Property 8: Deletion order follows the defined safe sequence
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        config = default_protected_config(root)
        executor = Executor(root=root, protected_paths=config)

        candidates = []
        for i, cat in enumerate(categories):
            f = root / f"file_{i}.pyc"
            f.write_bytes(b"x")
            candidates.append(
                CandidateFile(
                    path=f,
                    relative_path=f.relative_to(root),
                    size_bytes=1,
                    category=cat,
                    risk_level=RiskLevel.LOW,
                    action="DELETE",
                    is_directory=False,
                )
            )

        deletion_order_seen = []
        original_delete = executor._delete_item

        def tracking_delete(candidate):
            deletion_order_seen.append(candidate.category)
            return original_delete(candidate)

        executor._delete_item = tracking_delete
        executor.execute(candidates, interactive=False)

        order_values = [_DELETION_ORDER.get(cat, 99) for cat in deletion_order_seen]
        assert order_values == sorted(order_values), (
            f"Deletion order violated: categories={deletion_order_seen}, "
            f"order_values={order_values}"
        )
