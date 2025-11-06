#!/bin/bash

set -e

SCRIPT_NAME=$(basename "$0")
APP_NAME="image-labeling-viewer"

usage() {
    echo "Usage: $SCRIPT_NAME {add|delete} [branch-name]"
    echo "  add     - Create new Amplify branch"
    echo "  delete  - Delete Amplify branch"
    echo "  branch-name - Git branch name (defaults to current branch)"
    exit 1
}

get_current_branch() {
    git branch --show-current 2>/dev/null || git rev-parse --abbrev-ref HEAD
}

get_app_id() {
    aws amplify list-apps --query "apps[?name=='$APP_NAME'].appId" --output text
}

branch_exists() {
    local app_id="$1"
    local branch_name="$2"
    aws amplify list-branches --app-id "$app_id" --query "branches[?branchName=='$branch_name'].branchName" --output text | grep -q "$branch_name"
}

confirm_main_branch() {
    local action="$1"
    echo "WARNING: You are about to $action the 'main' branch!"
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Operation cancelled."
        exit 0
    fi
}

add_branch() {
    local branch_name="$1"
    local app_id="$2"
    
    if branch_exists "$app_id" "$branch_name"; then
        echo "Branch '$branch_name' already exists in Amplify. Skipping add operation."
        exit 0
    fi
    
    echo "Creating Amplify branch: $branch_name"
    aws amplify create-branch \
        --app-id "$app_id" \
        --branch-name "$branch_name" \
        --enable-auto-build
    
    echo "Branch '$branch_name' created successfully."
}

delete_branch() {
    local branch_name="$1"
    local app_id="$2"
    
    if ! branch_exists "$app_id" "$branch_name"; then
        echo "Branch '$branch_name' does not exist in Amplify. Skipping delete operation."
        exit 0
    fi
    
    echo "Deleting Amplify branch: $branch_name"
    aws amplify delete-branch \
        --app-id "$app_id" \
        --branch-name "$branch_name"
    
    echo "Branch '$branch_name' deleted successfully."
}

# Parse arguments
if [ $# -lt 1 ]; then
    usage
fi

ACTION="$1"
BRANCH_NAME="${2:-$(get_current_branch)}"

if [ -z "$BRANCH_NAME" ]; then
    echo "Error: Could not determine branch name"
    exit 1
fi

# Check for main branch
if [ "$BRANCH_NAME" = "main" ]; then
    confirm_main_branch "$ACTION"
fi

# Get Amplify app ID
APP_ID=$(get_app_id)
if [ -z "$APP_ID" ]; then
    echo "Error: Could not find Amplify app '$APP_NAME'"
    exit 1
fi

# Execute action
case "$ACTION" in
    add)
        add_branch "$BRANCH_NAME" "$APP_ID"
        ;;
    delete)
        delete_branch "$BRANCH_NAME" "$APP_ID"
        ;;
    *)
        echo "Error: Invalid action '$ACTION'"
        usage
        ;;
esac