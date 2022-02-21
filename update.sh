#!/bin/bash

source ~/bin/colors.sh

usage() {
    cat << EOUSAGE
$(basename $0) <FQDN>
EOUSAGE
}

host="$1"
if [[ -z $host ]]; then
    usage
    exit 1
fi

jar=$(ls jars/main)

colorize $black $yellow none "INFO: host='${host}'"

colorize $black $yellow none "INFO: stop server"
ssh minecraft@$host sudo systemctl stop minecraft-server
colorize $black $yellow none "INFO: sleep 60"
sleep 60
ssh minecraft@$host sudo systemctl status minecraft-server

colorize $black $yellow none "INFO: copy main jar"
scp jars/main/* minecraft@$host:lib/

colorize $black $yellow none "INFO: remove old plugins"
ssh minecraft@$host rm -f -v server/plugins/*.jar

colorize $black $yellow none "INFO: copy plugins"
scp jars/plugins/* minecraft@$host:server/plugins/

colorize $black $yellow none "INFO: copy other files"
scp go.sh minecraft@$host:bin/
ssh minecraft@$host "chmod 700 bin/*"
ssh minecraft@$host "echo $jar > .jar"

colorize $black $yellow none "INFO: start server"
ssh minecraft@$host sudo systemctl start minecraft-server
ssh minecraft@$host sudo systemctl status minecraft-server
