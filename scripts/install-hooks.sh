#!/bin/bash
#
# Install git hooks for teeclip project
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}teeclip Git Hook Installer${NC}"
echo "=========================="
echo ""

# Find git directory (handles worktrees where .git is a file, not a directory)
GIT_DIR=$(git rev-parse --git-common-dir 2>/dev/null)
if [ -z "$GIT_DIR" ]; then
    echo -e "${RED}Error:${NC} Git repository not found"
    echo "Please run from the project root directory"
    exit 1
fi

HOOKS_DIR="$GIT_DIR/hooks"
SCRIPT_DIR="$(dirname "$0")"

echo -e "${GREEN}Found git repository at:${NC} $GIT_DIR"
echo ""

# Check if hooks already exist
if [ -f "$HOOKS_DIR/pre-commit" ]; then
    echo -e "${YELLOW}Warning:${NC} pre-commit hook already exists"
    echo "Do you want to overwrite it? (y/n)"
    read -r response
    if [ "$response" != "y" ] && [ "$response" != "Y" ]; then
        echo "Installation cancelled"
        exit 0
    fi
fi

# Install pre-commit hook
echo -e "${GREEN}Installing pre-commit hook...${NC}"
cp "$SCRIPT_DIR/hooks/pre-commit" "$HOOKS_DIR/pre-commit"
chmod +x "$HOOKS_DIR/pre-commit"

# Install post-commit hook
if [ -f "$SCRIPT_DIR/hooks/post-commit" ]; then
    echo -e "${GREEN}Installing post-commit hook...${NC}"
    cp "$SCRIPT_DIR/hooks/post-commit" "$HOOKS_DIR/post-commit"
    chmod +x "$HOOKS_DIR/post-commit"
fi

# Install pre-push hook
if [ -f "$SCRIPT_DIR/hooks/pre-push" ]; then
    echo -e "${GREEN}Installing pre-push hook...${NC}"
    cp "$SCRIPT_DIR/hooks/pre-push" "$HOOKS_DIR/pre-push"
    chmod +x "$HOOKS_DIR/pre-push"
fi

# Make version update script executable
if [ -f "$SCRIPT_DIR/update-version.sh" ]; then
    chmod +x "$SCRIPT_DIR/update-version.sh"
    echo -e "${GREEN}Made update-version.sh executable${NC}"
fi

echo ""
echo -e "${GREEN}Git hooks installed successfully!${NC}"
echo ""
echo "The pre-commit hook will:"
echo "  - Automatically update _version.py with build information"
echo "  - Prevent committing private files to public branches"
echo "  - Check for oversized files (>10MB)"
echo ""
echo "The post-commit hook will:"
echo "  - Update _version.py with the actual commit hash"
echo ""
echo "The pre-push hook will:"
echo "  - Validate Python syntax"
echo "  - Run tests"
echo "  - Check for debug statements"
echo ""
echo "You can manually update the version at any time with:"
echo "  ./scripts/update-version.sh"
echo ""
echo -e "${BLUE}Version format:${NC}"
echo "  VERSION_BRANCH_BUILD-YYYYMMDD-COMMITHASH"
echo "  Example: 0.1.0_main_4-20260211-a1b2c3d4"