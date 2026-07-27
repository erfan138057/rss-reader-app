#!/usr/bin/env python3
"""
release-notes.py - Generate release notes from changelog
"""

import re
import sys
from datetime import datetime

def extract_version_notes(changelog_path, version):
    """Extract release notes for a specific version from CHANGELOG.md"""
    with open(changelog_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to find the version section
    pattern = rf'## \[{re.escape(version)}\] - (.*?)(?=## \[|\Z)'
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        print(f"Version {version} not found in changelog")
        return None
    
    notes = match.group(0).strip()
    return notes

def generate_github_release_notes(version_notes):
    """Convert changelog format to GitHub release format"""
    # Remove the version header
    lines = version_notes.split('\n')
    if lines and lines[0].startswith('## ['):
        lines = lines[1:]
    
    # Convert changelog sections to GitHub format
    github_notes = []
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('### Added'):
            current_section = '🚀 Added'
            github_notes.append(f'### {current_section}')
        elif line.startswith('### Changed'):
            current_section = '🔄 Changed'  
            github_notes.append(f'### {current_section}')
        elif line.startswith('### Fixed'):
            current_section = '🐛 Fixed'
            github_notes.append(f'### {current_section}')
        elif line.startswith('### Removed'):
            current_section = '🗑️ Removed'
            github_notes.append(f'### {current_section}')
        elif line.startswith('### Security'):
            current_section = '🔒 Security'  
            github_notes.append(f'### {current_section}')
        elif line.startswith('### Deprecated'):
            current_section = '⚠️ Deprecated'
            github_notes.append(f'### {current_section}')
        elif line.startswith('- '):
            if current_section:
                github_notes.append(line)
            else:
                github_notes.append(f'📝 {line[2:]}')
        else:
            github_notes.append(line)
    
    return '\n'.join(github_notes)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python release-notes.py <version>")
        print("Example: python release-notes.py 1.0.0")
        sys.exit(1)
    
    version = sys.argv[1]
    changelog_path = "CHANGELOG.md"
    
    version_notes = extract_version_notes(changelog_path, version)
    if version_notes:
        github_notes = generate_github_release_notes(version_notes)
        print("Generated GitHub Release Notes:")
        print("=" * 50)
        print(github_notes)
        
        # Save to file
        output_file = f"release-notes-{version}.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(github_notes)
        print(f"\n✅ Notes saved to {output_file}")
    else:
        sys.exit(1)