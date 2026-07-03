#!/bin/bash
NAME="project"
MESSAGE="$1"
CHANGE="$(date '+%Y-%m-%d %H:%M:%S')"
AUTHOR=$(grep -E '^__author__\s*=\s*' src/$NAME/__version__.py | cut -d'"' -f2)
EMAIL=$(grep -E '^__email__\s*=\s*' src/$NAME/__version__.py | cut -d'"' -f2)

shift

if [ ! -d ".git" ]; then
    git init
fi

if ! git config user.name >/dev/null 2>&1; then
    git config user.name "$AUTHOR"
fi

if ! git config user.email >/dev/null 2>&1; then
    git config user.email "$EMAIL"
fi

python3 src/$NAME/__version__.py >> change.log

echo "[changelog-$CHANGE]" >> change.log

if [ -z "$MESSAGE" ]; then
    MESSAGE="update: $CHANGE"
fi

while [ -n "$1" ]; do
    case "$1" in
        --commit)
            git add .
            git commit -m "$MESSAGE"          
            printf "\nNEW COMMIT: %s\n" "$MESSAGE" >> change.log
            shift
            ;;
        --freeze)
            VERSION=$(grep -E '^__version__\s*=\s*' src/$NAME/__version__.py | cut -d'"' -f2)
            git tag -a "v$VERSION" -m "$MESSAGE"
            printf "\nNEW VERSION: %s -> %s\n" "$VERSION" "$MESSAGE" >> change.log
            shift
            ;;
        --push)
            shift
            git push "$@" && printf "\nNEW PUSH: %s\n" "$*" >> change.log
            break
            ;;
        *)
            shift
            ;;
    esac
done

if ! python -c "import $NAME" >/dev/null 2&>1; then
	pip install -e .
fi
