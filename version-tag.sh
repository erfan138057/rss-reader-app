#!/bin/bash
# version-tag.sh - Helper script for version tagging

echo "RSS Reader Version Tagging Helper"
echo "================================"

# Read current version from version.py
CURRENT_VERSION=$(grep "__version__" version.py | cut -d'"' -f2)
echo "Current version: $CURRENT_VERSION"

# Get version components
MAJOR=$(echo $CURRENT_VERSION | cut -d. -f1)
MINOR=$(echo $CURRENT_VERSION | cut -d. -f2)  
PATCH=$(echo $CURRENT_VERSION | cut -d. -f3)

echo ""
echo "What type of release is this?"
echo "1) Major (v$((MAJOR+1)).0.0)"
echo "2) Minor (v$MAJOR.$((MINOR+1)).0)"  
echo "3) Patch (v$MAJOR.$MINOR.$((PATCH+1)))"
echo "4) Custom version"

read -p "Enter choice [1-4]: " choice

case $choice in
  1)
    NEW_VERSION="$((MAJOR+1)).0.0"
    ;;
  2) 
    NEW_VERSION="$MAJOR.$((MINOR+1)).0"
    ;;
  3)
    NEW_VERSION="$MAJOR.$MINOR.$((PATCH+1))"
    ;;
  4)
    read -p "Enter new version (e.g., 1.2.3): " NEW_VERSION
    ;;
  *)
    echo "Invalid choice"
    exit 1
    ;;
esac

# Update version.py
echo "Updating version.py to $NEW_VERSION..."
sed -i "s/__version__ = \"$CURRENT_VERSION\"/__version__ = \"$NEW_VERSION\"/" version.py
sed -i "s/__release_date__ = \".*\"/__release_date__ = \"$(date +%Y-%m-%d)\"/" version.py

# Create tag
echo "Creating git tag v$NEW_VERSION..."
git add version.py
git commit -m "Bump version to v$NEW_VERSION"
git tag -a "v$NEW_VERSION" -m "Release v$NEW_VERSION"

echo ""
echo "✅ Version updated to v$NEW_VERSION"
echo "📝 Commit created and tagged"
echo "🚀 Push with: git push && git push --tags"
echo ""
echo "Next steps:"
echo "1. Review changes: git show"
echo "2. Push to GitHub: git push && git push --tags"  
echo "3. GitHub Actions will automatically build the release"