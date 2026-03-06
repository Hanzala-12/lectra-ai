# Dependency Management

This project uses multiple requirements files to manage dependencies efficiently.

## Requirements Files

### `requirements.txt` (Development)
- Use for local development
- Contains version ranges (e.g., `package>=1.0.0,<2.0.0`)
- Allows flexibility for updates while preventing breaking changes

### `requirements-prod.txt` (Production/CI)
- **Use this in CI/CD pipelines**
- Contains pinned versions (e.g., `package==1.2.3`)
- Ensures reproducible builds
- Prevents "resolution-too-deep" errors in CI/CD

### `requirements-dev.txt` (Development Tools)
- Testing tools (pytest, coverage)
- Linting tools (flake8, black)
- Development utilities

## Installation

### For Local Development
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### For Production/CI/CD
```bash
pip install -r requirements-prod.txt
```

### For Docker
The Dockerfile uses `requirements-prod.txt` for consistent builds.

## Common Issues

### "resolution-too-deep" Error

If you encounter this error during dependency installation:

**Solution 1:** Use the pinned requirements
```bash
pip install -r requirements-prod.txt
```

**Solution 2:** Install in stages
```bash
# Install core dependencies first
pip install torch==2.5.1 torchaudio==2.5.1 numpy==1.26.4

# Then install the rest
pip install -r requirements-prod.txt
```

**Solution 3:** Increase pip timeout
```bash
pip install -r requirements.txt --timeout 300
```

### Dependency Conflicts

If you encounter version conflicts:

1. Check which packages are conflicting:
   ```bash
   pip check
   ```

2. Use the production requirements with pinned versions:
   ```bash
   pip install -r requirements-prod.txt
   ```

3. If you need to update versions, test locally first:
   ```bash
   pip install package==new_version
   pip check
   ```

## Updating Dependencies

### Update Pinned Versions (requirements-prod.txt)

1. Create a fresh virtual environment:
   ```bash
   python -m venv test_env
   source test_env/bin/activate  # or test_env\Scripts\activate on Windows
   ```

2. Install from flexible requirements:
   ```bash
   pip install -r requirements.txt
   ```

3. Freeze exact versions:
   ```bash
   pip freeze > requirements-prod.txt
   ```

4. Clean up the frozen file (remove unnecessary packages)

5. Test the installation:
   ```bash
   deactivate
   python -m venv verify_env
   source verify_env/bin/activate
   pip install -r requirements-prod.txt
   python -c "from pipeline import VoiceCleaningPipeline; print('OK')"
   ```

### Update Flexible Requirements (requirements.txt)

When adding a new package:
```bash
# In requirements.txt, add with version constraints
new-package>=1.0.0,<2.0.0
```

Then update production pinned version:
```bash
pip install new-package
pip freeze | grep new-package >> requirements-prod.txt
```

## CI/CD Configuration

The GitHub Actions workflow uses `requirements-prod.txt` to ensure:
- Fast, reproducible builds
- No dependency resolution timeouts
- Consistent test environments

See `.github/workflows/ci.yml` for implementation details.

## Troubleshooting

### Slow Installation
- Use `requirements-prod.txt` with pinned versions
- Enable pip cache in CI/CD
- Consider using `uv` or `pip-tools` for faster resolution

### Version Incompatibilities
- Check Python version (requires 3.10+)
- Verify CUDA/PyTorch compatibility for GPU systems
- Review warning messages during installation

### Missing System Dependencies
Some packages require system libraries:
- ffmpeg (for moviepy, ffmpeg-python)
- libsndfile (for soundfile)

Install via system package manager:
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install ffmpeg libsndfile1

# macOS
brew install ffmpeg libsndfile

# Windows
# Download ffmpeg from https://ffmpeg.org/download.html
```
