#!/usr/bin/env bash

# #################################################################################
# Setup the virtual environment for development.
# You may need to "python -M pip install --user virtualenv" globally.
# This is not required but some form of project isolation (conda, virtual env, etc.)
# is strongly encouraged.

if [[ ! -z "$VIRTUAL_ENV" ]]; then
  echo "'deactivate' before running this script."
  exit 1
fi

rm -r .venv
python3.10 -m venv .venv

source ./.venv/bin/activate

# ##############################################################################
# Install normal requirements

python -m pip install --upgrade pip setuptools wheel
if [ -f requirements.txt ]; then python -m pip install -r requirements.txt; fi

# ##############################################################################
# Dev only pip installs (not required because they're personal preference)
python -m pip install -U pynvim
python -m pip install -U 'python-lsp-server[all]'
python -m pip install -U pre-commit pre-commit-hooks
python -m pip install -U autopep8 flake8 isort pylint yapf pydocstyle black
python -m pip install -U bandit prospector pylama

# ##############################################################################
# I Run pre-commit hooks (optional)

 pre-commit install
