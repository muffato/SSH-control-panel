#!/usr/bin/env python2

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import os
import sys
import time
import signal
import subprocess



class ControlPanelGUI(QWidget):

	def __init__(self, config, parent=None):
		QWidget.__init__(self, parent)

		height = 3+max(sum(1+len(_) for _ in _[1].values()) + (1 if 'tunnels' in _[1] else 0) + (1 if 'undergrounds' in _[1] else 0) for _ in config['networks'])
		width = len(config['networks'])
		self.setFixedSize(1.5*width*self.logicalDpiX(), height*self.fontMetrics().height()*1.9)
		self.rt = ControlPanelRuntime(config, self)

		self.grpMount = {}
		self.grpUnderground = {}

		layout = QHBoxLayout()
		menu = QMenu(self)
		for (groupname,conf) in config['networks']:
			groupBox = QGroupBox(groupname)
			boxLayout = QVBoxLayout()
			subMenu = menu.addMenu(groupname)
			subMenu.setSeparatorsCollapsible(False)

			if 'tunnels' in conf:
				grpTunnel = self.addTunnelOptions(boxLayout, groupname, conf['tunnels'], subMenu, 'Tunnel', self.rt.updateTunnel)[0]
				if 'mounts' in conf:
					subMenu.addSeparator().setText('Dep. mounts')
					self.grpMount[groupname] = self.addMountOptions(grpTunnel.layout(), groupname, conf['mounts'], subMenu, True)
				if 'undergrounds' in conf:
					self.grpUnderground[groupname] = self.addTunnelOptions(grpTunnel.layout(), groupname, conf['undergrounds'], subMenu, 'Underground', self.rt.updateUnderground)
				self.rt.updateTunnel(groupname, None, True)

			boxLayout.addStretch()

			if 'mounts_direct' in conf:
				subMenu.addSeparator().setText('Mounts')
				self.addMountOptions(boxLayout, groupname, conf['mounts_direct'], subMenu, False)

			groupBox.setLayout(boxLayout)
			layout.addWidget(groupBox)

		menu.addSeparator()
		superLayout = QVBoxLayout()
		superLayout.addLayout(layout)

		icon = QIcon.fromTheme("view-refresh")
		btn = QPushButton(icon, "Reset")
		btn.pressed.connect(callWithAddParams(self.rt.network.updateAllTunnels, ()))
		act = menu.addAction(icon, "reset", btn.click)
		btn.addAction(act)
		superLayout.addWidget(btn)

		icon = QIcon.fromTheme("window-close")
		btn = QPushButton(icon, "Quit")
		btn.pressed.connect(self.close)
		act = menu.addAction(icon, "Quit", self.close)
		btn.addAction(act)
		superLayout.addWidget(btn)

		self.setLayout(superLayout)

		trayIcon = QSystemTrayIcon(self)
		self.trayIcon = trayIcon

		trayIcon.setToolTip('SSH control panel')
		self.setWindowTitle('SSH control panel')
		icon = QIcon.fromTheme("security-medium-symbolic")
		if icon is None:
			sys.exit(1)
		self.setWindowIcon(icon)
		trayIcon.setIcon(icon)

		trayIcon.setContextMenu(menu)
		trayIcon.activated.connect(self.trayClick)
		trayIcon.show()

	def trayClick(self, reason):
		if reason == QSystemTrayIcon.Trigger:
			self.setVisible(not self.isVisible())

	def addTunnelOptions(self, boxLayout, groupname, conf, menu, title, callback):

		# Groups
		groupG = QGroupBox(title)
		tmpLayout = QVBoxLayout()
		groupG.setLayout(tmpLayout)
		boxLayout.addWidget(groupG)

		s = menu.addSeparator()
		s.setText(title)
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
			qrcRadioButton.toggled.connect(callWithAddParams(callback, (groupname, host)))
			action.toggled.connect(qrcRadioButton.setChecked)
			qrcRadioButton.toggled.connect(action.setChecked)

			# Inside the group
			action.setActionGroup(groupA)
			tmpLayout.addWidget(qrcRadioButton)

		return (groupG,groupA)


	def addMountOptions(self, boxLayout, groupname, conf, menu, inTunnel):

		# Groups
		groupG = QGroupBox('Dep. mounts' if inTunnel else 'Mounts')
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
			button.toggled.connect(callWithAddParams(self.rt.switchMount, (host, displayname, groupname, inTunnel)))
			action.toggled.connect(button.setChecked)

		return (groupG,groupA)

	def closeEvent(self, event):
		print event, event.type(), event.spontaneous()
		if event.spontaneous():
			self.setVisible(not self.isVisible())
			event.ignore()
		else:
			self.rt.close()
			self.trayIcon.hide()


class ControlPanelRuntime:

	def __init__(self, conf, gui):
		self.gui = gui
		self.tunnel = {}
		self.underground = {}
		self.mounted = {}
		self.mounted_direct = {}
		for (groupname, groupconfig) in conf['networks']:
			tunnels = groupconfig.get('tunnels', {})
			print "group", groupname, tunnels
			self.tunnel[groupname] = None
			self.mounted[groupname] = set()
			self.mounted_direct[groupname] = set()
			self.underground[groupname] = None
		print self.tunnel
		self.network = ControlPanelNetwork(conf)

	def updateTunnel(self, groupname, host, x):
		print "updateTunnel", groupname, host, x
		if x:
			self.tunnel[groupname] = host
			if host is not None:
				self.network.openTunnel(self.tunnel[groupname])
				for (s,u) in self.mounted[groupname]:
					self.network.mount(s, u, True)
				if self.underground[groupname] is not None:
					self.network.openTunnel(self.underground[groupname])
			allGuiGroups = (self.gui.grpMount[groupname] if groupname in self.gui.grpMount else tuple()) + (self.gui.grpUnderground[groupname] if groupname in self.gui.grpUnderground else tuple())
			for guiGroup in allGuiGroups:
				guiGroup.setEnabled(host is not None)
		else:
			if self.tunnel[groupname] is not None:
				for (_,u) in self.mounted[groupname]:
					self.network.umount(u)
				if self.underground[groupname] is not None:
					self.network.closeTunnel(self.underground[groupname])
				self.network.closeTunnel(self.tunnel[groupname])
			self.tunnel[groupname] = None

	def updateUnderground(self, groupname, host, x):
		print "updateUnderground", groupname, host, x
		if x:
			self.underground[groupname] = host
			if host is not None:
				self.network.openTunnel(self.underground[groupname])
		else:
			if self.underground[groupname] is not None:
				self.network.closeTunnel(self.underground[groupname])
			self.underground[groupname] = None

	def switchMount(self, host, displayname, groupname, inTunnel, x):
		mount_set = self.mounted if inTunnel else self.mounted_direct
		if x:
			if self.network.mount(host, displayname, inTunnel):
				return False
			mount_set[groupname].add( (host,displayname) )
		else:
			if self.network.umount(displayname):
				return False
			mount_set[groupname].remove( (host,displayname) )
		return True

	def close(self):
		print "closing application"
		for name in self.mounted:
			for (s,u) in self.mounted[name]:
				self.network.umount(u)
			for (s,u) in self.mounted_direct[name]:
				self.network.umount(u)
		for name in self.network.tunnels.keys():
			self.network.closeTunnel(name)


# TODO mount/umount return value

class ControlPanelNetwork():

	def __init__(self, config):
		self.tunnels = {}
		self.config = config

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
		for (name, process) in self.tunnels.items():
			print "sending SIGUSR1 to autossh", name
			os.kill(process.pid, signal.SIGUSR1)
		else:
			print "nothing to reset"

	def mount(self, host, target, inTunnel):
		print "mounting", host, target
		cmd = self.config['paths']['mountCmd'] + (self.config['paths']['depMountOptions'] if inTunnel else []) + ["%s:" % host, os.path.join(self.config['paths']['mountFolder'], target)]
		print "cmd", cmd
		ret = subprocess.call(cmd)
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

