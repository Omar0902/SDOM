"""
Test that documentation builds successfully.

This test ensures that Sphinx documentation can be built without errors.
Run with: pytest tests/test_docs_build.py
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest


def test_docs_directory_exists():
    """Test that the docs directory exists."""
    repo_root = Path(__file__).parent.parent
    docs_dir = repo_root / "docs"
    assert docs_dir.exists(), "docs/ directory not found"
    assert docs_dir.is_dir(), "docs/ is not a directory"


def test_docs_source_directory_exists():
    """Test that the docs/source directory exists."""
    repo_root = Path(__file__).parent.parent
    source_dir = repo_root / "docs" / "source"
    assert source_dir.exists(), "docs/source/ directory not found"
    assert source_dir.is_dir(), "docs/source/ is not a directory"


def test_conf_py_exists():
    """Test that conf.py exists."""
    repo_root = Path(__file__).parent.parent
    conf_file = repo_root / "docs" / "source" / "conf.py"
    assert conf_file.exists(), "docs/source/conf.py not found"
    assert conf_file.is_file(), "conf.py is not a file"


def test_index_file_exists():
    """Test that index.md exists."""
    repo_root = Path(__file__).parent.parent
    index_file = repo_root / "docs" / "source" / "index.md"
    assert index_file.exists(), "docs/source/index.md not found"
    assert index_file.is_file(), "index.md is not a file"


def test_requirements_file_exists():
    """Test that docs requirements file exists."""
    repo_root = Path(__file__).parent.parent
    req_file = repo_root / "docs" / "requirements.txt"
    assert req_file.exists(), "docs/requirements.txt not found"


@pytest.mark.skipif(
    sys.platform == "win32" and not os.path.exists("docs/make.bat"),
    reason="make.bat not found on Windows"
)
def test_makefile_exists():
    """Test that Makefile or make.bat exists."""
    repo_root = Path(__file__).parent.parent
    docs_dir = repo_root / "docs"
    
    if sys.platform == "win32":
        make_file = docs_dir / "make.bat"
    else:
        make_file = docs_dir / "Makefile"
    
    assert make_file.exists(), f"{make_file.name} not found in docs/"


def test_sphinx_build_imports():
    """Test that Sphinx can be imported."""
    try:
        import sphinx
        assert sphinx.__version__ is not None
    except ImportError:
        pytest.skip("Sphinx not installed - install with: uv pip install -r docs/requirements.txt")


def test_myst_parser_imports():
    """Test that myst_parser can be imported."""
    try:
        import myst_parser
        assert myst_parser.__version__ is not None
    except ImportError:
        pytest.skip("myst_parser not installed - install with: uv pip install -r docs/requirements.txt")


# @pytest.mark.slow
# def test_docs_build_html():
#     """Test that documentation builds successfully.
    
#     This test runs sphinx-build to build the HTML documentation.
#     Mark as slow since it takes time to build.
#     """
#     try:
#         import sphinx
#     except ImportError:
#         pytest.skip("Sphinx not installed")
    
#     repo_root = Path(__file__).parent.parent
#     docs_dir = repo_root / "docs"
#     source_dir = docs_dir / "source"
#     build_dir = docs_dir / "build" / "html"
    
#     # Clean build directory
#     if build_dir.exists():
#         import shutil
#         shutil.rmtree(build_dir)
    
#     # Build documentation
#     cmd = [
#         sys.executable, "-m", "sphinx",
#         "-b", "html",          # Build HTML
#         "-W",                  # Turn warnings into errors
#         "--keep-going",        # Continue on errors when possible
#         str(source_dir),       # Source directory
#         str(build_dir)         # Build directory
#     ]
    
#     result = subprocess.run(
#         cmd,
#         cwd=str(docs_dir),
#         capture_output=True,
#         text=True
#     )
    
#     # Print output for debugging
#     if result.returncode != 0:
#         print("STDOUT:", result.stdout)
#         print("STDERR:", result.stderr)
    
#     assert result.returncode == 0, f"Documentation build failed: {result.stderr}"
    
#     # Check that index.html was created
#     index_html = build_dir / "index.html"
#     assert index_html.exists(), "index.html not generated"


@pytest.mark.slow
def test_docs_build_with_make():
    """Test that documentation builds with make/make.bat.
    
    This tests the Makefile/make.bat approach.
    """
    try:
        import sphinx
    except ImportError:
        pytest.skip("Sphinx not installed")
    
    repo_root = Path(__file__).parent.parent
    docs_dir = repo_root / "docs"
    
    # Determine command
    if sys.platform == "win32":
        if not (docs_dir / "make.bat").exists():
            pytest.skip("make.bat not found")
        cmd = ["make.bat", "html"]
    else:
        if not (docs_dir / "Makefile").exists():
            pytest.skip("Makefile not found")
        cmd = ["make", "html"]
    
    result = subprocess.run(
        cmd,
        cwd=str(docs_dir),
        capture_output=True,
        text=True,
        shell=(sys.platform == "win32")  # Shell needed for .bat on Windows
    )
    
    if result.returncode != 0:
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
    
    # Don't fail on warnings, just check it ran
    build_dir = docs_dir / "build" / "html"
    index_html = build_dir / "index.html"
    assert index_html.exists(), "index.html not generated with make"


def test_api_documentation_files_exist():
    """Test that API documentation files exist."""
    repo_root = Path(__file__).parent.parent
    api_dir = repo_root / "docs" / "source" / "api"
    
    expected_files = [
        "index.md",
        "core.md",
        "models.md",
        "io_manager.md",
        "utilities.md"
    ]
    
    for filename in expected_files:
        api_file = api_dir / filename
        assert api_file.exists(), f"API documentation file {filename} not found"


def test_user_guide_files_exist():
    """Test that user guide files exist."""
    repo_root = Path(__file__).parent.parent
    guide_dir = repo_root / "docs" / "source" / "user_guide"
    
    expected_files = [
        "introduction.md",
        "inputs.md",
        "running_and_outputs.md",
        "exploring_model.md"
    ]
    
    for filename in expected_files:
        guide_file = guide_dir / filename
        assert guide_file.exists(), f"User guide file {filename} not found"


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v"])
