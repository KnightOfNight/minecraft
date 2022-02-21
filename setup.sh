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

colorize $black $yellow none "INFO: setup umask"
ssh minecraft@$host "grep -q umask .bashrc || echo "umask 077" >> .bashrc"

colorize $black $yellow none "INFO: make directories"
ssh minecraft@$host "umask 077; mkdir -p server/plugins"

colorize $black $yellow none "INFO: copy main jar"
scp jars/main/* minecraft@$host:lib/

colorize $black $yellow none "INFO: copy plugins"
scp jars/plugins/* minecraft@$host:server/plugins/

colorize $black $yellow none "INFO: copy other files"
scp go.sh minecraft@$host:bin/
ssh minecraft@$host "chmod 700 bin/*"
scp server/* minecraft@$host:server/
ssh minecraft@$host "echo $jar > .jar"
