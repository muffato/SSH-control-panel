#! /usr/bin/python

from PyQt4 import QtGui
from PyQt4 import QtCore

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import os
import sys
import time
import signal
import subprocess



class ControlPanelGUI(QtGui.QWidget):

	def __init__(self, rt, config, parent=None):
		QtGui.QWidget.__init__(self, parent)
		QtGui.QToolTip.setFont(QtGui.QFont('OldEnglish', 10))

		self.setFixedSize(120*len(config['networks']), 285)
		self.rt = rt
		rt.gui = self

		self.grpTunnel = {}
		self.grpMount = {}

		layout = QHBoxLayout()
		for (groupname,conf) in config['networks']:
			groupBox = QGroupBox(groupname)
			boxLayout = QVBoxLayout()

			if 'tunnels' in conf:
				self.grpTunnel[groupname] = self.addOptions(boxLayout, groupname, conf['tunnels'])

			if 'mounts' in conf:
				self.grpMount[groupname] = self.addOptions2(boxLayout, groupname, conf['mounts'])
				self.grpMount[groupname].setEnabled(False)

			boxLayout.addStretch()
			if 'mounts_direct' in conf:
				self.addOptions2(boxLayout, groupname, conf['mounts_direct'])

			groupBox.setLayout(boxLayout)
			layout.addWidget(groupBox)

		superLayout = QVBoxLayout()
		superLayout.addLayout(layout)
		btn = QPushButton("reset")
		self.connect(btn, SIGNAL("pressed()"), callWithAddParams(self.rt.network.updateTunnels, ()))
		superLayout.addWidget(btn)
		self.setLayout(superLayout)
		self.connect(self, SIGNAL("close()"), callWithAddParams(self.rt.close, ()))

		self.setWindowTitle('SSH control panel')

	def addOptions(self, boxLayout, groupname, conf):

		groupG = QGroupBox("SSH tunnel")
		groupG.setCheckable(True)
		groupG.setChecked(False)
		self.connect(groupG, SIGNAL("toggled(bool)"), callWithAddParams(self.rt.switchTunnel, (groupname,)))
		tmpLayout = QVBoxLayout()
		for (host,displayname) in conf:
			qrcRadioButton = QRadioButton(displayname)
			qrcRadioButton.setObjectName(host)
			if len(conf) == 1:
				qrcRadioButton.setChecked(True)
			self.connect(qrcRadioButton, SIGNAL("toggled(bool)"), callWithAddParams(self.rt.updateTunnel, (host, groupname)))
			tmpLayout.addWidget(qrcRadioButton)
		groupG.setLayout(tmpLayout)
		boxLayout.addWidget(groupG)
		return groupG


	def addOptions2(self, boxLayout, groupname, conf):

		group = QGroupBox("SSHFS")
		tmpLayout = QVBoxLayout()
		group.setLayout(tmpLayout)
		for (host,displayname) in conf:
			button = QCheckBox(displayname)
			self.connect(button, SIGNAL("toggled(bool)"), callWithAddParams(self.rt.switchMount, (host, displayname, groupname)))
			tmpLayout.addWidget(button)
		boxLayout.addWidget(group)
		return group

# TODO mount/umount return value

class ControlPanelNetwork():

	def __init__(self, config):
		self.tunnels = {}
		self.config = config
		self.devnull = open('/dev/null', 'r')

	def openTunnel(self, host):
		print "opening tunnel", host
		print "cmd", self.config['paths']['sshCmd'] + [host]
		env = os.environ
		env["AUTOSSH_POLL"] = "15"
		self.tunnels[host] = subprocess.Popen( self.config['paths']['sshCmd'] + [host], close_fds=True, shell=False, env=env)
		print self.tunnels[host]

	def closeTunnel(self, host):
		print "closing tunnel", host
		self.tunnels[host].terminate()
		self.tunnels[host].wait()
		del self.tunnels[host]

	def updateTunnels(self):
		print "sending SIGUSR1 to autossh"
		for process in self.tunnels.itervalues():
			os.kill(process.pid, signal.SIGUSR1)

	def mount(self, host, target):
		print "mounting", host, target
		print "cmd", self.config['paths']['mountCmd'] + ["%s:" % host, os.path.join(self.config['paths']['mountFolder'], target)]
		ret = subprocess.call( self.config['paths']['mountCmd'] + ["%s:" % host, os.path.join(self.config['paths']['mountFolder'], target)] )
		print ret
		return ret

	def umount(self, target):
		print "umounting", target
		print "cmd", self.config['paths']['umountCmd'] + [os.path.join(self.config['paths']['mountFolder'], target)]
		ret = subprocess.call( self.config['paths']['umountCmd'] + [os.path.join(self.config['paths']['mountFolder'], target)] )
		print ret
		return ret


class ControlPanelRuntime:

	def __init__(self, conf):
		self.tunnel = {}
		self.mounted = {}
		for (groupname, groupconfig) in conf['networks']:
			tunnels = groupconfig.get('tunnels', {})
			print "tmp", groupname, tunnels
			self.tunnel[groupname] = tunnels[0][0] if len(tunnels) == 1 else None
			self.mounted[groupname] = set()
		self.network = ControlPanelNetwork(conf)

	def switchTunnel(self, name, x):
		print "switch", self, name, x, self.tunnel[name]
		if self.tunnel[name] is not None:
			if x:
				self.network.openTunnel(self.tunnel[name])
				time.sleep(4)
				for (s,u) in self.mounted[name]:
					self.network.mount(s, u)
			else:
				for (_,u) in self.mounted[name]:
					self.network.umount(u)
				self.network.closeTunnel(self.tunnel[name])
				btn = self.gui.grpTunnel[name].findChild(QRadioButton, name=self.tunnel[name])
				if (btn is not None) and (len(self.gui.grpTunnel[name].children()) > 2):
					self.tunnel[name] = None
					btn.setAutoExclusive(False)
					btn.setChecked(False)
					btn.setAutoExclusive(True)
			self.gui.grpMount[name].setEnabled(x)

	def updateTunnel(self, s, name, t):
		if t:
			self.tunnel[name] = s
		self.switchTunnel(name, t)

	def switchMount(self, s, u, name, t):
		if t:
			if self.network.mount(s, u):
				return False
			self.mounted[name].add( (s,u) )
		else:
			if self.network.umount(u):
				return False
			self.mounted[name].remove( (s,u) )
		return True

	def close(self):
		print "closing application"
		for name in self.mounted:
			for (s,u) in self.mounted[name]:
				self.network.umount(u)
		for name in self.network.tunnels.keys():
			self.network.closeTunnel(name)

def callWithAddParams(f, par):
	def newf(*args, **kwargs):
		print "call", f, par, args, kwargs
		return f(*(par+args), **kwargs)
	return newf


import ssh_conf

rt = ControlPanelRuntime(ssh_conf.config)

app = QtGui.QApplication(sys.argv)
tooltip = ControlPanelGUI(rt, ssh_conf.config)
tooltip.show()
app.exec_()
rt.close()

