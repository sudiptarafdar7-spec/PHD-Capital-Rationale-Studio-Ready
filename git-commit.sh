#!/bin/bash
#
# Git Commit Helper Script
# PHD Capital Rationale Studio
#
# This script helps you commit all changes safely
#

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  GIT COMMIT HELPER"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Configure git safe directory
echo "🔐 Configuring git safe directory..."
git config --global --add safe.directory "$(pwd)"
echo "   ✅ Safe directory configured"
echo ""

# Show current status
echo "📊 Current Git Status:"
git status --short
echo ""

# Check if there are changes to commit
if [ -z "$(git status --porcelain)" ]; then
    echo "✅ No changes to commit. Working directory is clean."
    exit 0
fi

# Add all changes
echo "📝 Staging all changes..."
git add -A
echo "   ✅ Changes staged"
echo ""

# Show what will be committed
echo "📋 Files to be committed:"
git status --short
echo ""

# Commit with message
echo "💬 Enter commit message (or press Ctrl+C to cancel):"
read -p "Message: " COMMIT_MSG

if [ -z "$COMMIT_MSG" ]; then
    echo "❌ Commit message cannot be empty"
    exit 1
fi

echo ""
echo "📦 Committing changes..."
git commit -m "$COMMIT_MSG"
echo "   ✅ Committed successfully"
echo ""

# Ask about push
read -p "🚀 Push to remote? (y/n): " PUSH_CHOICE
if [ "$PUSH_CHOICE" = "y" ] || [ "$PUSH_CHOICE" = "Y" ]; then
    echo "📤 Pushing to remote..."
    git push
    echo "   ✅ Pushed successfully"
else
    echo "⏸️  Skipped push. You can push later with: git push"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ DONE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
