

vars="MC_GAME_PATH
MC_BACKUP_PATH
MC_GAME_JAR
MC_SCREEN_PREFIX
MC_SERVER
MC_ACTION
MC_SERVER_PATH
MC_SERVER_JAR
MC_SCREEN_SESSION
MC_SNAPSHOT_PATH"

for var in $vars; do
	[ -z "${!var}" ] && fatal_error "variable '$var' is not set"
done


message () {

	message="$1"
	[ -z "$message" ] && message="no message specified"

	echo "$(date +'%T %Z') $MC_SERVER: $message"

}

warning () {

	message="$1"
	[ -z "$message" ] && message="no warning message specified"

	message "WARNING: $message"

}

fatal_error () {

	message="$1"
	[ -z "$message" ] && message="no error message specified"

	message "ERROR: $message"

	exit -1

}

short_pause () {

	usleep 333333

}

is_server_running () {

	typeset -i ret

	ps auxww | grep -i screen | grep "$MC_SCREEN_SESSION" | grep -i java | grep "$MC_GAME_JAR" | grep -vq grep
	ret=$?

	if [ $ret -eq 0 ]; then
		return 0
	else
		return 1
	fi

}

server_status () {

	typeset -i lines; lines="$1"
	if [ $lines -eq 0 ]; then
		lines=5
	fi

	message "current status..."

	tail -$lines $MC_SERVER_PATH/server.log

}

server_command () {

	command="$1"
	[ -z "$command" ] && fatal_error "server_command() - no command specified"

	if ! is_server_running ; then
		fatal_error "server_command() - unable to send command to server, it is not running"
	fi

	typeset -i ret
	/usr/bin/screen -p 0 -S "$MC_SCREEN_SESSION" -X eval "stuff \"$command\"\015"
	ret=$?

}

server_message () {

	message="$1"
	[ -z "$message" ] && fatal_error "server_message() - no message specified"

	server_command "say $(date +'%T %Z') $message"

}

server_start () {

	typeset -i mem; mem=$1
	if [ $mem -lt 1 -o $mem -gt 8192 ]; then
		let mem=512
	fi

	typeset -i max_ctr; let max_ctr=60

	if is_server_running ; then
		fatal_error "server_start() - server is already running"
	fi

	message "starting, may pause up to $max_ctr seconds..."

	cd $MC_SERVER_PATH

	cp -a "$MC_GAME_JAR" "$MC_SERVER:$MC_GAME_JAR"

	/usr/bin/screen -S "$MC_SCREEN_SESSION" -d -m /usr/bin/java -Xms${mem}M -Xmx${mem}M -jar "$MC_SERVER:$MC_GAME_JAR" nogui

	typeset -i ctr; let ctr=$max_ctr
	while true; do
		if tail -5 server.log | grep -q Done; then
			break
		fi

		sleep 1

		let ctr--
		if [ $ctr -eq 0 ]; then
			break
		fi
	done

	if [ $ctr -eq 0 ]; then
		fatal_error "server_start() - waited $max_ctr for server to start"
		exit -1
	fi

	server_status

}

server_stop () {

	typeset -i max_ctr; let max_ctr=60

	if ! is_server_running ; then
		fatal_error "server_stop() - unable to stop server, it is not running"
		exit -1
	fi

	server_save

	message "stopping, may pause up to $max_ctr seconds..."

	server_command "stop"

	typeset -i ctr; let ctr=$max_ctr
	while is_server_running ; do
		sleep 1

		let ctr--
		if [ $ctr -eq 0 ]; then
			break
		fi
	done

	if [ $ctr -eq 0 ]; then
		fatal_error "server_stop() - waited $max_ctr for server to stop"
		exit -1
	fi

	server_status

}

server_save () {

	if ! is_server_running ; then
		fatal_error "server_save() - unable to save server, it is not running"
		exit -1
	fi

	message "saving databases..."

	# server_message "saving server databases"

	server_command "save-all"

}

server_snapshot () {

	lockfile="$MC_SERVER_PATH/.snapshot"

	if [ -e "$lockfile" ]; then
		fatal_error "server snapshot already in progress"
		exit -1
	else
		touch "$lockfile"
	fi

	if is_server_running; then
		message "disabling auto-save..."
		# server_message "server snapshot in progress, auto-save disabled"
		server_command "save-off"

		short_pause
		server_save

		sync

		sleep="15"
		message "sync and wait $sleep..."
		sleep $sleep
	fi

	message "copying files..."

	rm -fr "$MC_SNAPSHOT_PATH" 2> /dev/null

	cp -a "$MC_SERVER_PATH" "$MC_SNAPSHOT_PATH"

	message "comparing snapshot..."
	cd "$MC_SNAPSHOT_PATH"

	for file in $(find -type f); do
		if ! cmp "$file" "$MC_SERVER_PATH/$file"; then
			fatal_error "server_snapshot() - snapshot file '$file' does not match source"
			exit -1
		fi
	done

	if is_server_running; then
		short_pause
		message "enabling auto-save..."
		server_command "save-on"
		# server_message "server snapshot complete, auto-save re-enabled"

		short_pause
		server_status 10
	fi

	rm -f "$lockfile" 2> /dev/null

}

find_item () {
	name="$1"
	[ -z "$name" ] && fatal_error "find_item() - no item name specified"

	id_db_files="$MC_GAME_PATH/etc/*ids.txt"

	tmp=$(mktemp /tmp/XXXXXX)
	egrep -hi ":${name}$" $id_db_files > "$tmp"

	typeset -i linecount
	linecount=$(wc -l $tmp | cut -f 1 -d " ")

	if [ $linecount -ne 1 ]; then
		rm "$tmp"
		fatal_error "find_item() - zero or multiple matches found for name '$name' in ID databases"
	fi

	id=$(cat "$tmp" | cut -f 1 -d ":")

	rm "$tmp"

	echo "$id"
}

