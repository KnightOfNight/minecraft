#!/bin/bash


export MC_GAME_PATH="/usr/local/games/minecraft"
export MC_BACKUP_PATH="/usr/local/games/minecraft/backups"
export MC_GAME_JAR="minecraft_server.jar"
export MC_SCREEN_PREFIX="mcserver"


usage () {
	cat <<EOUSAGE

USAGE: mcctl [ --help | --list ]

--help  program information
--list  list running servers

USAGE: mccct <server> <action>

<server>  name of a server to control
<action>  one of the following...

start [<mem>]    start the server
                 <mem> VM memory in MB (default 512)

stop             stop the server

restart [<mem>]  restart the server
                 <mem> VM memory in MB (default 512)

status           report server status

snapshot         take a snapshot of a server

backup           take a backup of the server

save             force save the databases

auto-save-off    disable auto-save

auto-save-on     enable auto-save

wledit           edit the white list

wlreload         reload the white list

players          list all connected players

console          connect to the server console

god <user> {on|off}        turn create-mode on/off for a user

op <user> {on|off}         turn operator status on/off for a user

give <user> <item> [<qty>] give a user an item
                           <item> name of an item in the ID files
                           <qty>  1-64, default 1

command <command>          run an arbitrary command on the server

EOUSAGE
}


list_servers () {
	echo "Currently running servers..."

	echo

	servers=$(screen -list | grep "$MC_SCREEN_PREFIX:" | sed -e "s/[^:][^:]*://" -e "s/[ \t][ \t]*.*//" | sort)

	for server in $servers; do

		java_proc=$( ps -eo 'pid rss args' | \
			grep java | grep "$server" | grep -v "$MC_SCREEN_PREFIX" | \
			grep -v grep | \
			sed -e "s/[ \t][ \t]*/ /" -e "s/^[ \t][ \t]*//" )

		pid=$(echo "$java_proc" | cut -f 1 -d " ")

		typeset -i memused; memused=$(echo "$java_proc" | cut -f 2 -d " ")

		typeset -i memmax; memmax=$(echo "$java_proc" | sed -e "s/.* -Xmx\([0-9][0-9]*\)M .*/\1/")
		let memmax*=1024

		percent=$(echo $memused/$memmax*100 | bc -l)

		echo "Server: $server (PID $pid, $memused/$memmax kB ($(printf '%.1f%%' $percent)) memory"

		echo
	done

	if ps auxww | grep -i screen | grep Maps | grep -vq grep; then
		echo "NOTICE: maps are being generated."
		echo
	fi
}


if [ "$1" = "--help" ]; then
	usage
	exit

elif [ "$1" = "" -o "$1" = "--list" ]; then
	echo

	list_servers

	if [ "$1" = "" ]; then
		echo "Try 'mcctl --help' for more information."
		echo
	fi

	exit
fi


export MC_SERVER="$1"
export MC_ACTION="$2"

if [ -z "$MC_SERVER" -o -z "$MC_ACTION" ]; then
	usage
	exit
fi


export MC_SERVER_PATH="$MC_GAME_PATH/$MC_SERVER"
export MC_SERVER_JAR="$MC_SERVER_PATH/$MC_GAME_JAR"

export MC_SCREEN_SESSION="$MC_SCREEN_PREFIX:$MC_SERVER"

export MC_SNAPSHOT_PATH="$MC_GAME_PATH/snapshot/$MC_SERVER"

if [ ! -d "$MC_SERVER_PATH" ]; then
	echo "ERROR: server directory '$MC_SERVER_PATH' does not exist"
	exit -1
fi

if [ ! -s "$MC_SERVER_JAR" ]; then
	echo "ERROR: server file '$MC_SERVER_JAR' does not exist"
	exit -1
fi


# Load the library now, after all of the exported variables are verified.
. "$MC_GAME_PATH/bin/mclib.sh"


#
# Script execution begins here.
#


# basic actions
if [ "$MC_ACTION" = "start" ]; then

	typeset -i mem; mem=$3

	server_start "$mem"

elif [ "$MC_ACTION" = "stop" ]; then

	server_stop

elif [ "$MC_ACTION" = "restart" ]; then

	typeset -i mem; mem=$3

	server_stop

	server_start "$mem"

elif [ "$MC_ACTION" = "status" ]; then

	server_status 25

elif [ "$MC_ACTION" = "snapshot" ]; then

	server_snapshot

elif [ "$MC_ACTION" = "backup" ]; then

#	message "backing up server..."

#	if is_server_running; then
#		message "server is running, saving..."
#
#		server_snapshot
#
#		message "disabling auto-save..."
#		server_command "save-off"
#
#		server_message "database backup in progress, auto-save disabled"
#
#		sync
#
#		short_pause
#		server_status
#
#		message "save & sync, wait 10..."
#
#		sleep 10
#	fi


	if ps auxww | grep -i screen | grep Maps | grep -vq grep; then
		echo "$(date +'%T %Z') unable to backup data files, maps are being generated."
		exit -1
	fi


	message "backing up server..."
	server_snapshot

	message "tar..."
	seconds=$(date +%s)
	tar -czf "$MC_BACKUP_PATH/$MC_SERVER.$seconds.tgz" "$MC_SNAPSHOT_PATH"


	#tar -czf "$MC_BACKUP_PATH/$MC_SERVER.full.$seconds.tgz" "$MC_SERVER_PATH"

#	if is_server_running; then
#		short_pause
#
#		message "enabling auto-save..."
#		server_command "save-on"
#
#		server_message "database backup complete, auto-save re-enabled"
#
#		short_pause
#		server_status
#	fi


# save actions
elif [ "$MC_ACTION" = "save" ]; then

	server_save

elif [ "$MC_ACTION" = "auto-save-off" ]; then

	server_save

	message "disabling auto-save..."

	server_command "save-off"

	server_message "auto-save disabled"

	sync

	short_pause
	server_status

elif [ "$MC_ACTION" = "auto-save-on" ]; then

	message "enabling auto-save..."

	server_command "save-on"

	server_message "auto-save enabled"

	short_pause
	server_save

	short_pause
	server_status


# white-list actions
elif [ "$MC_ACTION" = "wledit" ]; then

	message "editing white list..."

	vi $MC_SERVER_PATH/white-list.txt

	message "reloading white list..."
	server_command "whitelist reload"

	short_pause
	server_status

elif [ "$MC_ACTION" = "wlreload" ]; then

	message "reloading white list..."
	server_command "whitelist reload"

	short_pause
	server_status


# player actions
elif [ "$MC_ACTION" = "give" ]; then

	user="$3"
	item="$4"
	typeset -i qty; qty=$5
	typeset -i dv; dv=$6

	if [ -z "$user" -o -z "$item" -o -z "$qty" ]; then
		usage
		exit -1
	fi

	if [ $qty -lt 1 -o $qty -gt 64 ]; then
		usage
		exit -1
	fi

	server_command "give $user $(find_item $item) $qty $dv"

	short_pause
	server_status

elif [ "$MC_ACTION" = "god" ]; then

	user="$3"
	status="$4"

	if [ -z "$user" -o -z "$status" ]; then
		usage
		exit -1
	fi

	if [ "$status" = "on" ]; then
		status="1"
	elif [ "$status" = "off" ]; then
		status="0"
	else
		usage
		exit -1
	fi

	server_command "gamemode $status $user"

	short_pause
	server_status

elif [ "$MC_ACTION" = "op" ]; then

	user="$3"
	status="$4"

	if [ -z "$user" -o -z "$status" ]; then
		usage
		exit -1
	fi

	if [ "$status" = "on" ]; then
		command="op"
	elif [ "$status" = "off" ]; then
		command="deop"
	else
		usage
		exit -1
	fi

	server_command "$command $user"

	short_pause
	server_status


# run an arbitrary command
elif [ "$MC_ACTION" = "command" ]; then

	command="$3"

	if [ -z "$command" ]; then
		usage
		exit -1
	fi

	server_command "$command"

	short_pause
	server_status


# list connected players
elif [ "$MC_ACTION" = "players" ]; then

	server_command "list"

	short_pause
	server_status


# connect to server console
elif [ "$MC_ACTION" = "console" ]; then

	screen -r $MC_SCREEN_SESSION 


# fall through
else
	usage
	exit -1
fi


