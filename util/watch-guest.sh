#!/bin/bash
set -uo pipefail #enable bash's safer mode
IFS=$'\n'

#This script runs the Python-based Chronos on-board GUI.
#When a file is changed, Python is automatically restarted.
#brk() may be used in the Python script to enter an interactive debugger.

trap "{ stty sane; echo; kill 0; }" EXIT #Kill all children when we die. (This cleans up any windows lying around.) Also restore the console (keyboard stops being echoed after ctrl-c'ing out of pdb) and advance to a new line before printing the prompt again.

bash <<< "#sh doesn't do the equality test for 143, must use bash
	while true; do
		sleep 2 &
		python3 src/main.py < `readlink -f /dev/stdin` 2> `readlink -f /dev/stderr`
		PY_EXIT=\$?
		[[ \$PY_EXIT -eq 143 ]] || echo Python exited with code \$PY_EXIT. Restarting... #Python exits with 143 when killed by entr running pkill. We don't really care about that, since it's so frequent, but knowing when it's died of other causes is useful.
		wait #In combination with sleep 2, don't restart the python script until at least two seconds have passed since the last invocation. This stops python from running many times if python crashes immediately.
		echo; echo; echo; #Visually separate logs.
	done
" 2> /dev/null & #suppress bash terminated messages caused by entr pkill
PYTHON_PARENT_SHELL=$! #Used to limit pkill to the subshell we're running our python app in. Otherwise, pkill takes out entr as well.

watchmedo shell-command \
	--recursive --patterns="*.py;*.txt;*.ui" \
	--command="pkill -P $PYTHON_PARENT_SHELL -f main.py" \
	.