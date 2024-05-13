#!/bin/bash

JAVA="/usr/local/lib/jdk-22.0.1/bin/java"

MEMORY="2G"

JAR="$HOME/lib/$(cat $HOME/.jar)"

SERVER_DIR="$HOME/server"

cd $SERVER_DIR

screen -S minecraft_server -d -m $JAVA -Xmx$MEMORY -Xms$MEMORY -jar $JAR nogui

typeset -i tries; let tries=0
typeset -i max; let max=10

while [ $tries -lt $max ]; do
    process=$(ps -ww -e -o "pid cmd" | egrep "^[ 0-9][ 0-9]*  *${JAVA}..*${JAR}.*$")

    if [ "$process" == "" ]; then
        sleep 1
    else
        pid=$(echo $process | awk '{print $1}')
        echo $pid > server.pid
        exit 0
    fi

    tries+=1
done

if [ $tries -eq $max ]; then
    echo "Error: tried $max times to find running server process"
    exit 1
fi
