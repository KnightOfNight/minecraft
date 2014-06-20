#!/usr/bin/python


import argparse
import filecmp
import logging
import os
import re
import shutil
import subprocess
import sys
import time



class Defaults:
	screen_prefix = "mcserver"

	dir_servers = "/usr/local/games/minecraft"

	dir_backups = "/usr/local/games/minecraft/backups"

	dir_snapshots = "/usr/local/games/minecraft/snapshot"

	log_file = "logs/latest.log"

	game_jar = "minecraft_server.jar"



class Server:
	def __init__(self, name):
		self.name = name
		self.server_dir = "%s/%s" % (Defaults.dir_servers, self.name)
		self.screen_name = "%s:%s" % (Defaults.screen_prefix, self.name)

	def is_started(self):
		servers = server_screen_sessions()

		if self.name in servers and java_process_info(self.name):
			return True

		return False

	def logtail(self, log_lines = -25, log_wait_timeout = 5):
		log_file = "%s/%s" % (self.server_dir, Defaults.log_file)

		checks = 0
		while True:
			checks += 1

			if checks == log_wait_timeout:
				logging.error("server log file '%s' does not exist" % (log_file))
				sys.exit(1)

			elif os.path.exists(log_file):
				break

			time.sleep(1)

		with open(log_file) as f:
			lines = f.readlines()
			lines = [ line.strip() for line in lines ]
			tail = []
			for line in lines[log_lines:]:
				tail.append(line)
			return(tail)

	def status(self):
		logging.info("server '%s' current status..." % (self.name))
		for line in self.logtail():
			print line

	def command(self, command):
		if not self.is_started():
			logging.error("cannot send command '%s' to server '%s', it is not started" % (command, self.name))
			sys.exit(1)

		logging.debug("sending command '%s' to server '%s'" % (command, self.name))

		system("/usr/bin/screen -p 0 -S '%s' -X eval 'stuff \"%s\"\015'" % (self.screen_name, command))

	def save(self):
		logging.info("saving server '%s'" % (self.name))
		self.command("save-all")

	def start(self, memory = 512, log_wait_timeout = 5):
		if self.is_started():
			logging.error("cannot start server '%s', it is already started" % (self.name))
			sys.exit(1)

		logging.info("starting server '%s'" % self.name)

		jar_file = "%s:%s" % (self.name, Defaults.game_jar)

		cmd = "/usr/bin/screen -S %s -d -m /usr/bin/java -Xms%sM -Xmx%sM -jar %s nogui" % (self.screen_name, memory, memory, jar_file)

		os.chdir(self.server_dir)

		shutil.copy(Defaults.game_jar, jar_file)

		system(cmd)

		started = False
		checks = 0
		max_checks = 60

		while True:
			checks += 1

			if checks == max_checks:
				logging.error("timed out %ds waiting for server '%s' to start" % (max_checks, self.name))
				sys.exit(1)

			for line in self.logtail(log_lines = -5, log_wait_timeout = log_wait_timeout):
				match = re.search("Done", line)

				if match:
					started = True
					break

			if started:
				break

			time.sleep(1)

		logging.info("server '%s' started" % self.name)

	def stop(self):
		if not self.is_started():
			logging.error("cannot stop server '%s', it is not started" % self.name)
			sys.exit(1)

		self.save()

		time.sleep(1)

		logging.info("stopping server '%s'" % self.name)

		self.command("stop")

		stopped = False
		max_checks = 60

		checks = 0
		while True:
			checks += 1

			if checks == max_checks:
				logging.error("timed out %ds waiting for server '%s' Java process to stop" % (max_checks, self.name))
				sys.exit(1)

			if not java_process_info(self.name):
				break

			time.sleep(1)

		checks = 0
		while True:
			checks += 1

			if checks == max_checks:
				logging.error("timed out %ds waiting for server '%s' screen session to stop" % (max_checks, self.name))
				sys.exit(1)

			if not self.name in server_screen_sessions():
				break

			time.sleep(1)

		logging.info("server '%s' stopped" % self.name)

	def snapshot(self):
		logging.info("taking snapshot of server '%s'", self.name)

		lock = "%s/.snapshot" % (self.server_dir)

		if not lockfile(lock):
			logging.error("cannot snapshot server '%s', a snapshot is already in progress" % (self.name))
			sys.exit(1)

		if self.is_started():
			logging.debug("disabling auto-save")
			self.command("save-off")
			logging.debug("syncing filesystem")
			system("/bin/sync")
			logging.debug("waiting 15s for filesystem to sync")
			time.sleep(15)

		snapshot_dir = "%s/%s" % (Defaults.dir_snapshots, self.name)

		if os.path.exists(snapshot_dir):
			logging.debug("removing old snapshot")
			shutil.rmtree(snapshot_dir)

		logging.debug("copying files for new snapshot")
		shutil.copytree(self.server_dir, snapshot_dir)

		logging.debug("comparing snapshot files to original server files")
		server_files = []
		for path, dirs, files in os.walk(self.server_dir):
			for file in files:
				server_files.append(os.path.join(path, file))
		server_files = [ str.replace(file, self.server_dir + "/", "") for file in server_files ]
		cmp = filecmp.cmpfiles(self.server_dir, snapshot_dir, server_files)

		if cmp[1] or cmp[2]:
			logging.error("snapshot of server '%s' failed, differences found in one or more files" % (self.name))
			os.unlink(lock)
			sys.exit(1)

		if self.is_started():
			logging.debug("enabling auto-save")
			self.command("save-on")

		os.unlink(lock)

		logging.info("snapshot of server '%s' complete" % (self.name))

	def backup(self):
		self.snapshot()

		snapshot_dir = "%s/%s" % (Defaults.dir_snapshots, self.name)
		backup = "%s/%s.%s.tgz" % (Defaults.dir_backups, self.name, str(int(time.time())))

		cmd = "/bin/tar -czf %s %s 2> /dev/null" % (backup, snapshot_dir)

		logging.info("taking backup of server '%s'" % (self.name))

		logging.debug("command = '%s'" % (cmd))

		system(cmd)

		logging.info("backup of server '%s' complete" % (self.name))

	def setup(self, memory, source_jar):
		if os.path.exists(self.server_dir):
			logging.error("server '%s' has already been setup" % (self.name))
			sys.exit(1)

		if not os.path.exists(source_jar):
			logging.error("jar file '%s' not found" % (source_jar))
			sys.exit(1)

		logging.info("setting up new server '%s'" % (self.name))

		logging.debug("creating directory '%s'" % (self.server_dir))
		os.mkdir(self.server_dir)

		new_jar = "%s/%s" % (self.server_dir, Defaults.game_jar)

		logging.debug("copying jar file '%s' to '%s'" % (source_jar, new_jar))
		shutil.copy(source_jar, new_jar)

		self.start(memory = memory, log_wait_timeout = 30)



def lockfile(path):
	if os.path.exists(path):
		return(False)

	fd = open(path, "w")
	fd.write(str(int(time.time())) + "\n" )
	fd.close()

	return(True)



def system(cmd):
	ret = os.system(cmd)

	if ret & 127:
		logger.error("command '%s' exited with signal %d, %s coredump" % (cmd, ret & 127, "with" if ret & 128 else "without"))
		sys.exit(1)
	elif ret >> 8:
		logger.error("command '%s' exited with %d" % (cmd, ret >> 8))
		sys.exit(1)

	return True



def server_screen_sessions():
	proc = subprocess.Popen(["/usr/bin/screen", "-list"], stdout=subprocess.PIPE)
	(output, error) = proc.communicate()
	lines = output.split("\n")
	lines = [ line.strip() for line in lines ]
	servers = []
	for line in lines:
		match = re.match("^[0-9]+\.{0}:(.+)[ \t]+.*$".format(Defaults.screen_prefix), line)
		if match:
			servers.append(match.group(1))

	return(servers)



def java_process_info(server):
	proc = subprocess.Popen(["/bin/ps", "-eo", "pid rss args"], stdout=subprocess.PIPE)
	(output, error) = proc.communicate()
	lines = output.split("\n")
	lines = [ line.strip() for line in lines ]
	info = {}
	for line in lines:
		match = re.match("^([0-9]+) +([0-9]+) +/usr/bin/java -Xms[0-9]+M -Xmx([0-9]+)M -jar %s:%s nogui$" % (server, Defaults.game_jar), line)

		if match:
			info["pid"] = match.group(1)
			info["kb_used"] = match.group(2)
			info["kb_max"] = int(match.group(3)) * 1024

			break

	return(info)



def action_list_servers(args):
	logging.debug("list servers")

	for server in server_screen_sessions():
		info = java_process_info(server)

		if not info:
			logging.warn("no Java process information found for server '%s'" % server)
			continue

		memory = float(info['kb_used']) / float(info['kb_max']) * 100
		print "Server: %s, PID %s, %s/%s kB (%.1f%%) memory" % (server, info['pid'], info['kb_used'], info['kb_max'], memory)



def action_start_server(args):
	logging.debug("start a server")

	server = args.server
	s = Server(server)
	s.start(memory = args.memory)



def action_restart_server(args):
	logging.debug("restart a server")

	server = args.server
	s = Server(server)
	s.stop()
	s.start(args.memory)



def action_stop_server(args):
	logging.debug("stop a server")

	server = args.server
	s = Server(server)
	s.stop()
	


def action_command_server(args):
	logging.debug("send a command to a server")

	server = args.server
	s = Server(server)
	s.command(args.command)



def action_status_server(args):
	logging.debug("server status")

	server = args.server
	s = Server(server)
	s.status()



def action_snapshot_server(args):
	logging.debug("snapshot a server")

	server = args.server
	s = Server(server)
	s.snapshot()



def action_backup_server(args):
	logging.debug("backup a server")

	server = args.server
	s = Server(server)
	s.backup()



def action_setup_server(args):
	logging.debug("setup a server")

	server = args.server
	s = Server(server)
	s.setup(source_jar = args.jar, memory = args.memory)



# parse arguments and call the requested action function
parser = argparse.ArgumentParser(description="Minecraft Server Control", formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument("-v", "--version", action="version", version="mcctl v1.0.1")
parser.add_argument("-d", "--debug", dest="debug", action="store_true", help="turn on debugging output")

subparser = parser.add_subparsers(title="actions")

parser_list = subparser.add_parser("list", help="list running servers")
parser_list.set_defaults(func=action_list_servers)

parser_start = subparser.add_parser("start", help="start a server", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser_start.add_argument("server", metavar="SERVER", help="name of the server")
parser_start.add_argument("-m", "--memory", metavar="MB", help="allocate this much memory to the server", default=512, type=int)
parser_start.set_defaults(func=action_start_server)

parser_restart = subparser.add_parser("restart", help="restart a server", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser_restart.add_argument("server", metavar="SERVER", help="name of the server")
parser_restart.add_argument("-m", "--memory", metavar="MB", help="allocate this much memory to the server", default=512, type=int)
parser_restart.set_defaults(func=action_restart_server)

parser_stop = subparser.add_parser("stop", help="stop a server")
parser_stop.add_argument("server", metavar="SERVER", help="name of the server")
parser_stop.set_defaults(func=action_stop_server)

parser_send = subparser.add_parser("send", help="send a command to a server")
parser_send.add_argument("server", metavar="SERVER", help="name of the server")
parser_send.add_argument("command", metavar="COMMAND", help="command to send")
parser_send.set_defaults(func=action_command_server)

parser_status = subparser.add_parser("status", help="report server status")
parser_status.add_argument("server", metavar="SERVER", help="name of the server")
parser_status.set_defaults(func=action_status_server)

parser_snapshot = subparser.add_parser("snapshot", help="snapshot a server")
parser_snapshot.add_argument("server", metavar="SERVER", help="name of the server")
parser_snapshot.set_defaults(func=action_snapshot_server)

parser_backup = subparser.add_parser("backup", help="backup a server")
parser_backup.add_argument("server", metavar="SERVER", help="name of the server")
parser_backup.set_defaults(func=action_backup_server)

parser_setup = subparser.add_parser("setup", help="setup and start a new server")
parser_setup.add_argument("server", metavar="SERVER", help="name of the server")
parser_setup.add_argument("-j", "--jar", metavar="JAR", help="jar file to use for the server", required=True)
parser_setup.add_argument("-m", "--memory", metavar="MB", help="allocate this much memory to the server", default=512, type=int)
parser_setup.set_defaults(func=action_setup_server)


args = parser.parse_args()

if args.debug:
	logging.basicConfig(format="%(asctime)s: %(levelname)s: %(message)s", level=logging.DEBUG, datefmt="%Y/%m/%d %H:%M:%S")
else:
	logging.basicConfig(format="%(asctime)s: %(levelname)s: %(message)s", level=logging.INFO, datefmt="%Y/%m/%d %H:%M:%S")

args.func(args)

