#!/usr/bin/env python3

import argparse
import sys
import logging

import signal, lockfile, grp, os

from pwd import getpwnam
from daemonize import Daemonize

from prometheus_client import start_http_server, Gauge
from typing import Dict
import subprocess
import time

class IOSTATExporterDaemon:
	def __init__(self, args, logger):
		self.args = args
		self.logger = logger
		self.terminate = False
		self.rereadConfig = True

		self.metrics = {
			'iostat_rs' : Gauge(
				"iostat_rs", "Reads per second", labelnames = [ 'device' ]
			),
			'iostat_ws' : Gauge(
				"iostat_ws", "Writes per second", labelnames = [ 'device' ]
			),
			'iostat_krs' : Gauge(
				"iostat_krs", "Kilobytes read per second", labelnames = [ 'device' ]
			),
			'iostat_kws' : Gauge(
				"iostat_kws", "Kilobytes written per second", labelnames = [ 'device' ]
			),
			'iostat_msr' : Gauge(
				"iostat_msr", "Milliseconds per read", labelnames = [ 'device' ]
			),
			'iostat_msw' : Gauge(
				"iostat_msw", "Milliseconds per write", labelnames = [ 'device' ]
			),
			'iostat_mso' : Gauge(
				"iostat_mso", "Milliseconds per operation (?)", labelnames = [ 'device' ]
			),
			'iostat_mst' : Gauge(
				"iostat_mst", "Milliseconds per t (?)", labelnames = [ 'device' ]
			),
			'iostat_qlen' : Gauge(
				"iostat_qlen", "Queue length", labelnames = [ 'device' ]
			),
			'iostat_busy' : Gauge(
				"iostat_busy", "Busy percent", labelnames = [ 'device' ]
			)
		}

	def parseIostat(self, metrics):
		p = subprocess.Popen("iostat -x", stdout=subprocess.PIPE, shell=True)
		(output, err) = p.communicate()
		status = p.wait()

		output = output.decode("utf-8").split("\n")

		for i in range(len(output)):
			output[i] = output[i].strip()

		for i in range(len(output)):
			if output[i].startswith("ada"):
				line = output[i].split()

				if len(line) != 11:
					continue

				vdevname = line[0]
				rs = float(line[1])
				ws = float(line[2])
				krs = float(line[3])
				kws = float(line[4])
				msr = float(line[5])
				msw = float(line[6])
				mso = float(line[7])
				mst = float(line[8])
				qlen = float(line[9])
				busypct = float(line[10])

				self.metrics['iostat_rs'].labels(vdevname).set(rs)
				self.metrics['iostat_ws'].labels(vdevname).set(ws)
				self.metrics['iostat_krs'].labels(vdevname).set(krs)
				self.metrics['iostat_kws'].labels(vdevname).set(kws)
				self.metrics['iostat_msr'].labels(vdevname).set(msr)
				self.metrics['iostat_msw'].labels(vdevname).set(msw)
				self.metrics['iostat_mso'].labels(vdevname).set(mso)
				self.metrics['iostat_mst'].labels(vdevname).set(mst)
				self.metrics['iostat_qlen'].labels(vdevname).set(qlen)
				self.metrics['iostat_busy'].labels(vdevname).set(busypct)

	def signalSigHup(self, *args):
		self.rereadConfig = True
	def signalTerm(self, *args):
		self.terminate = True
	def __enter__(self):
		return self
	def __exit__(self, type, value, tb):
		pass

	def run(self):
		signal.signal(signal.SIGHUP, self.signalSigHup)
		signal.signal(signal.SIGTERM, self.signalTerm)
		signal.signal(signal.SIGINT, self.signalTerm)

		self.logger.info("Service running")

		start_http_server(self.args.port)
		while True:
			time.sleep(self.args.interval)
			self.parseIostat(self.metrics)

			if self.terminate:
				break

		self.logger.info("Shutting down due to user request")

def mainDaemon():
	parg = parseArguments()
	args = parg['args']
	logger = parg['logger']

	logger.debug("Daemon starting ...")
	with IOSTATExporterDaemon(args, logger) as exporterDaemon:
		exporterDaemon.run()

def parseArguments():
	ap = argparse.ArgumentParser(description = 'Iostat exporter daemon')
	ap.add_argument('-f', '--foreground', action='store_true', help="Do not daemonize - stay in foreground and dump debug information to the terminal")

	ap.add_argument('--uid', type=str, required=False, default=None, help="User ID to impersonate when launching as root")
	ap.add_argument('--gid', type=str, required=False, default=None, help="Group ID to impersonate when launching as root")
	ap.add_argument('--chroot', type=str, required=False, default=None, help="Chroot directory that should be switched into")
	ap.add_argument('--pidfile', type=str, required=False, default="/var/run/iostatexporter.pid", help="PID file to keep only one daemon instance running")
	ap.add_argument('--loglevel', type=str, required=False, default="error", help="Loglevel to use (debug, info, warning, error, critical). Default: error")
	ap.add_argument('--logfile', type=str, required=False, default="/var/log/iostatexporter.log", help="Logfile that should be used as target for log messages")

	ap.add_argument('--port', type=int, required=False, default=9250, help="Port to listen on")
	ap.add_argument('--interval', type=int, required=False, default=30, help="Interval in seconds in which data is gathered")

	args = ap.parse_args()
	loglvls = {
		"DEBUG"     : logging.DEBUG,
		"INFO"      : logging.INFO,
		"WARNING"   : logging.WARNING,
		"ERROR"     : logging.ERROR,
		"CRITICAL"  : logging.CRITICAL
	}
	if not args.loglevel.upper() in loglvls:
		print("Unknown log level {}".format(args.loglevel.upper()))
		sys.exit(1)

	logger = logging.getLogger()
	logger.setLevel(loglvls[args.loglevel.upper()])
	if args.logfile:
		fileHandleLog = logging.FileHandler(args.logfile)
		logger.addHandler(fileHandleLog)

	return { 'args' : args, 'logger' : logger }

def mainStartup():
	parg = parseArguments()
	args = parg['args']
	logger = parg['logger']

	daemonPidfile = args.pidfile
	daemonUid = None
	daemonGid = None
	daemonChroot = "/"

	if args.uid:
		try:
			args.uid = int(args.uid)
		except ValueError:
			try:
				args.uid = getpwnam(args.uid).pw_uid
			except KeyError:
				logger.critical("Unknown user {}".format(args.uid))
				print("Unknown user {}".format(args.uid))
				sys.exit(1)
		daemonUid = args.uid
	if args.gid:
		try:
			args.gid = int(args.gid)
		except ValueError:
			try:
				args.gid = grp.getgrnam(args.gid)[2]
			except KeyError:
				logger.critical("Unknown group {}".format(args.gid))
				print("Unknown group {}".format(args.gid))
				sys.exit(1)

		daemonGid = args.gid

	if args.chroot:
		if not os.path.isdir(args.chroot):
			logger.critical("Non existing chroot directors {}".format(args.chroot))
			print("Non existing chroot directors {}".format(args.chroot))
			sys.exit(1)
		daemonChroot = args.chroot

	if args.foreground:
		logger.debug("Launching in foreground")
		with IOSTATExporterDaemon(args, logger) as iostatDaemon:
			iostatDaemon.run()
	else:
		logger.debug("Daemonizing ...")
		daemon = Daemonize(
			app="IOSTAT exporter",
			action=mainDaemon,
			pid=daemonPidfile,
			user=daemonUid,
			group=daemonGid,
			chdir=daemonChroot
		)
		daemon.start()


if __name__ == "__main__":
	mainStartup()
