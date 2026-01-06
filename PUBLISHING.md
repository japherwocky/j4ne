# Publishing J4NE to PyPI

This guide covers how to build and publish J4NE to PyPI.

## Prerequisites

1. **Install build tools:**
   ```bash
   pip install build twine
   ```

2. **PyPI Account Setup:**
   - Create accounts on [TestPyPI](https://test.pypi.org/account/register/) and [PyPI](https://pypi.org/account/register/)
   - Generate API tokens for both platforms
   - Configure tokens in `~/.pypirc` or use environment variables

## Building the Package

1. **Clean previous builds:**
   ```bash
   rm -rf dist/ build/ *.egg-info/
   ```

2. **Build the package:**
   ```bash
   python -m build
   ```

   This creates:
   - `dist/j4ne-X.X.X-py3-none-any.whl` (wheel distribution)
   - `dist/j4ne-X.X.X.tar.gz` (source distribution)

## Testing the Build

1. **Create a test virtual environment:**
   ```bash
   python -m venv test_env
   source test_env/bin/activate  # On Windows: test_env\Scripts\activate
   ```

2. **Install the built package:**
   ```bash
   pip install dist/j4ne-*.whl
   ```

3. **Test CLI functionality:**
   ```bash
   j4ne --help
   j4ne greet "Test"
   # Test other commands as needed
   ```

4. **Clean up:**
   ```bash
   deactivate
   rm -rf test_env
   ```

## Publishing

### Test Upload (Recommended First)

1. **Upload to TestPyPI:**
   ```bash
   twine upload --repository testpypi dist/*
   ```

2. **Test installation from TestPyPI:**
   ```bash
   pip install --index-url https://test.pypi.org/simple/ j4ne
   ```

### Production Upload

1. **Upload to PyPI:**
   ```bash
   twine upload dist/*
   ```

2. **Verify installation:**
   ```bash
   pip install j4ne
   ```

## Version Management

1. **Update version in `pyproject.toml`:**
   ```toml
   version = "0.1.1"  # Increment as needed
   ```

2. **Follow semantic versioning:**
   - `MAJOR.MINOR.PATCH`
   - MAJOR: Breaking changes
   - MINOR: New features (backward compatible)
   - PATCH: Bug fixes (backward compatible)

## Automated Publishing with GitHub Actions

Consider setting up automated publishing on release tags:

```yaml
# .github/workflows/publish.yml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.x'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine
    - name: Build package
      run: python -m build
    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: twine upload dist/*
```

## Troubleshooting

- **Build fails:** Check that all dependencies are listed in `pyproject.toml`
- **Upload fails:** Verify API tokens and package name availability
- **Import errors:** Ensure all required files are included in `MANIFEST.in`
- **CLI not working:** Verify entry point configuration in `pyproject.toml`

## Security Notes

- Never commit API tokens to version control
- Use environment variables or `~/.pypirc` for credentials
- Consider using trusted publishing with GitHub Actions for enhanced security
