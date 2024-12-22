# Grunnleggende PATH
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Dynamisk prompt som viser (.venv) foran når virtuelt miljø er aktivert
function virtualenv_info {
    if [[ -n "$VIRTUAL_ENV" ]]; then
        echo "(.venv) "
    fi
}
PROMPT='$(virtualenv_info)%n@%m %~ $ '

# Python alias
alias python=python3
alias pip=pip3

# Created by `pipx` on 2024-12-07 06:27:42
export PATH="$PATH:/Users/tor.inge.jossang@aftenbladet.no/.local/bin"
export PYENV_ROOT="$HOME/.pyenv"
command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
