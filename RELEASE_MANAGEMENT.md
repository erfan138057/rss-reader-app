# Release Management System

This document explains how to manage releases for the RSS Reader project.

## 📋 Files Created

1. **RELEASES.md** - Comprehensive release notes and version history
2. **CHANGELOG.md** - Detailed changelog following Keep a Changelog format
3. **version.py** - Version information and feature flags
4. **version-tag.sh** - Helper script for version tagging
5. **release-notes.py** - Automated release notes generation
6. **.github/workflows/release.yml** - GitHub Actions for automatic builds
7. **.github/RELEASE_TEMPLATE.md** - GitHub release template

## 🛠️ Release Process

### 1. Update Version
```bash
# Run the version tagging helper
./version-tag.sh

# Or manually update version.py
# Update __version__, __release_date__, etc.
```

### 2. Update Changelog
Edit `CHANGELOG.md` to add changes for the new version following the Keep a Changelog format.

### 3. Generate Release Notes
```bash
python release-notes.py 1.0.0
```

### 4. Create Git Tag
```bash
git add .
git commit -m "Release v1.0.0"
git tag -a "v1.0.0" -m "Release v1.0.0"
```

### 5. Push to GitHub
```bash
git push
git push --tags
```

### 6. GitHub Actions
- Pushing tags triggers the release workflow
- Windows executable is built automatically
- Release is created on GitHub with generated notes

## 📊 Versioning Scheme

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Incompatible API changes
- **MINOR** (1.X.0): New backward-compatible functionality  
- **PATCH** (1.0.X): Backward-compatible bug fixes

## 📝 Changelog Format

Follow [Keep a Changelog](https://keepachangelog.com/) format:

```markdown
## [1.0.0] - 2025-01-01

### Added
- New feature description

### Changed
- Changes to existing functionality

### Fixed
- Bug fixes
```

## 🎯 Release Types

- **Stable** (v1.0.0+): Production-ready releases
- **Beta** (v0.9.0): Feature-complete testing releases  
- **Alpha** (v0.8.0): Early development releases

## 📈 Automation Features

- **Automatic Builds**: GitHub Actions builds executables on tag push
- **Release Notes**: Automated generation from changelog
- **Version Management**: Script-assisted version updates
- **Multi-Platform**: Support for Windows and Linux builds

## 📖 Usage Examples

### Create a Patch Release
```bash
./version-tag.sh
# Choose option 3 (Patch)
# Review and push: git push && git push --tags
```

### Generate Release Notes for v1.1.0
```bash
python release-notes.py 1.1.0
# Output saved to release-notes-1.1.0.md
```

### Manual Version Update
```python
# In version.py
__version__ = "1.2.0"
__release_date__ = "2025-02-01"
__status__ = "Stable"
```

## 📊 Quality Assurance

Before each release:

1. Run all tests: `python test_core.py`
2. Test the executable build locally
3. Verify changelog is up to date
4. Check version information is correct
5. Test on target platform (Windows)

## 📧 Support

For release-related issues:

1. Check GitHub Actions logs
2. Verify version.py format
3. Ensure changelog follows correct format
4. Test the version-tag script locally

---

*This release system ensures consistent, automated releases with proper documentation and version management.*