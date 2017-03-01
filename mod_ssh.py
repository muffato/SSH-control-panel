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

	def __init__(self, config, parent=None):
		QtGui.QWidget.__init__(self, parent)
		QtGui.QToolTip.setFont(QtGui.QFont('OldEnglish', 10))

		self.setFixedSize(140*len(config['networks']), 370)
		self.rt = ControlPanelRuntime(config, self)

		self.grpMount = {}

		layout = QHBoxLayout()
		menu = QMenu(self)
		for (groupname,conf) in config['networks']:
			groupBox = QGroupBox(groupname)
			boxLayout = QVBoxLayout()
			subMenu = menu.addMenu(groupname)
			subMenu.setSeparatorsCollapsible(False)

			if 'tunnels' in conf:
				grpTunnel = self.addTunnelOptions(boxLayout, groupname, conf['tunnels'], subMenu)
				if 'mounts' in conf:
					subMenu.addSeparator().setText('Dep. mounts')
					self.grpMount[groupname] = self.addMountOptions(grpTunnel.layout(), groupname, conf['mounts'], subMenu, 'Dep. mounts')
				self.rt.updateTunnel(groupname, None, True)

			boxLayout.addStretch()

			if 'mounts_direct' in conf:
				subMenu.addSeparator().setText('Mounts')
				self.addMountOptions(boxLayout, groupname, conf['mounts_direct'], subMenu, 'Mounts')

			groupBox.setLayout(boxLayout)
			layout.addWidget(groupBox)

		menu.addSeparator()
		superLayout = QVBoxLayout()
		superLayout.addLayout(layout)
		btn = QPushButton("reset")
		self.connect(btn, SIGNAL("pressed()"), callWithAddParams(self.rt.network.updateAllTunnels, ()))
		act = menu.addAction(QIcon.fromTheme("view-refresh"), "reset", btn, SLOT("click()"))
		btn.addAction(act)
		superLayout.addWidget(btn)
		self.setLayout(superLayout)
		self.connect(self, SIGNAL("close()"), callWithAddParams(self.rt.close, ()))
		menu.addAction(QIcon.fromTheme("window-close"), "Quit", self, SLOT("close()"))

		trayIcon = QSystemTrayIcon(self)
		self.connect(trayIcon, SIGNAL("activated(QSystemTrayIcon::ActivationReason)"), callWithAddParams(self.trayClick, ()))

		trayIcon.setToolTip('SSH control panel')
		self.setWindowTitle('SSH control panel')
		icon = QIcon.fromTheme("certificate-server")
		if icon is None:
			sys.exit(1)
		self.setWindowIcon(icon)
		trayIcon.setIcon(icon)

		trayIcon.setContextMenu(menu)
		trayIcon.show()

	def trayClick(self, reason):
		if reason == QSystemTrayIcon.Trigger:
			self.setVisible(not self.isVisible())

	def addTunnelOptions(self, boxLayout, groupname, conf, menu):

		# Groups
		groupG = QGroupBox("Tunnel")
		tmpLayout = QVBoxLayout()
		groupG.setLayout(tmpLayout)
		boxLayout.addWidget(groupG)

		s = menu.addSeparator()
		s.setText('Tunnel')
		s.setCheckable(True)
		groupA = QActionGroup(self)

		for (i,(host,displayname)) in enumerate([(None, "(closed)")] + conf):

			# Radio button
			qrcRadioButton = QRadioButton(displayname)
			action = menu.addAction(displayname)
			action.setCheckable(True)

			# Default option
			if i == 0:
				action.setChecked(True)
				qrcRadioButton.setChecked(True)

			# Signals
			self.connect(qrcRadioButton, SIGNAL("toggled(bool)"), callWithAddParams(self.rt.updateTunnel, (groupname, host)))
			self.connect(action, SIGNAL("toggled(bool)"), qrcRadioButton, SLOT("setChecked(bool)"))
			self.connect(qrcRadioButton, SIGNAL("toggled(bool)"), action, SLOT("setChecked(bool)"))

			# Inside the group
			action.setActionGroup(groupA)
			tmpLayout.addWidget(qrcRadioButton)

		return groupG


	def addMountOptions(self, boxLayout, groupname, conf, menu, title):

		# Groups
		groupG = QGroupBox(title)
		tmpLayout = QVBoxLayout()
		groupG.setLayout(tmpLayout)
		boxLayout.addWidget(groupG)

		groupA = QActionGroup(self)
		groupA.setExclusive(False)

		for (host,displayname) in conf:

			# Checkable controller
			button = QCheckBox(displayname)
			action = menu.addAction(displayname)
			action.setCheckable(True)

			# Inside the group
			tmpLayout.addWidget(button)
			groupA.addAction(action)

			# Signals
			self.connect(button, SIGNAL("toggled(bool)"), callWithAddParams(self.rt.switchMount, (host, displayname, groupname)))
			self.connect(action, SIGNAL("toggled(bool)"), button, SLOT("setChecked(bool)"))
			self.connect(button, SIGNAL("toggled(bool)"), action, SLOT("setChecked(bool)"))

		return (groupG,groupA)


class ControlPanelRuntime:

	def __init__(self, conf, gui):
		self.gui = gui
		self.tunnel = {}
		self.mounted = {}
		for (groupname, groupconfig) in conf['networks']:
			tunnels = groupconfig.get('tunnels', {})
			print "tmp", groupname, tunnels
			self.tunnel[groupname] = tunnels[0][0] if len(tunnels) == 1 else None
			self.mounted[groupname] = set()
		self.network = ControlPanelNetwork(conf)

	def updateTunnel(self, groupname, host, x):
		if x:
			self.tunnel[groupname] = host
			if host is not None:
				self.network.openTunnel(self.tunnel[groupname])
				for (s,u) in self.mounted[groupname]:
					self.network.mount(s, u)
			for btn in self.gui.grpMount[groupname]:
				btn.setEnabled(x and (host is not None))
		else:
			if self.tunnel[groupname] is not None:
				for (_,u) in self.mounted[groupname]:
					self.network.umount(u)
				self.network.closeTunnel(self.tunnel[groupname])
			self.tunnel[groupname] = None

	def switchMount(self, host, displayname, groupname, x):
		if x:
			if self.network.mount(host, displayname):
				return False
			self.mounted[groupname].add( (host,displayname) )
		else:
			if self.network.umount(displayname):
				return False
			self.mounted[groupname].remove( (host,displayname) )
		return True

	def close(self):
		print "closing application"
		for name in self.mounted:
			for (s,u) in self.mounted[name]:
				self.network.umount(u)
		for name in self.network.tunnels.keys():
			self.network.closeTunnel(name)


# TODO mount/umount return value

class ControlPanelNetwork():

	def __init__(self, config):
		self.tunnels = {}
		self.config = config
		self.devnull = open('/dev/null', 'r')

	def openTunnel(self, host):
		print "opening tunnel", host
		print "cmd", self.config['paths']['sshCmd'] + [host]
		self.tunnels[host] = subprocess.Popen( self.config['paths']['sshCmd'] + [host], close_fds=True, shell=False, env=os.environ)
		print self.tunnels[host]
		time.sleep(4)

	def closeTunnel(self, host):
		print "closing tunnel", host
		self.tunnels[host].terminate()
		self.tunnels[host].wait()
		del self.tunnels[host]

	def updateAllTunnels(self):
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


def callWithAddParams(f, par):
	def newf(*args, **kwargs):
		print "call", f, par, args, kwargs
		return f(*(par+args), **kwargs)
	return newf


import ssh_conf


os.environ["AUTOSSH_POLL"] = "15"


def load():
	w = ControlPanelGUI(ssh_conf.config)
	w.show()
	w.hide()

def unload():
	pass

