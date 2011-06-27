
from PyQt4 import QtGui
from PyQt4 import QtCore

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import os
import sys
import time
import subprocess


config = ([
	("EBI", [("tunnel-ebi-inside", "LAN"), ("tunnel-ebi-outside", "Wi-Fi")], [("login.ebi.ac.uk","ebi")]),
	("Sanger", [("tunnel-sanger",)], [("farm2-head4.internal.samger.ac.uk","sanger")]),
	("ENS", [("tunnel-wotan",)], [("heimdall.ens.fr","heimdall"), ("wotan.ens.fr","wotan"), ("ldog21.ens.fr","ldog21")]),
	("IIE", [], [("perso.iiens.net","arise")])
], "/home/muffato/sshfs")


class ControlPanelGUI(QtGui.QWidget):

	def __init__(self, rt, parent=None):
		QtGui.QWidget.__init__(self, parent)

		self.setFixedSize(120*len(rt.config), 230)
		self.setWindowTitle('SSH panel control')
		self.rt = rt
		rt.gui = self

		self.grpTunnel = {}
		self.grpMount = {}

		layout = QHBoxLayout()
		for conf in rt.config:
			groupBox = QGroupBox(conf[0])
			boxLayout = QVBoxLayout()
			self.grpTunnel[conf[0]] = self.addOptions(boxLayout, conf)
			self.grpMount[conf[0]] = self.addOptions2(boxLayout, conf)
			groupBox.setLayout(boxLayout)
			layout.addWidget(groupBox)

		QtGui.QToolTip.setFont(QtGui.QFont('OldEnglish', 10))

		self.setLayout(layout)
		self.connect(self, SIGNAL("close()"), callWithAddParams(self.rt.close, ()))

	def addOptions(self, boxLayout, conf):
		if len(conf[1]) >= 1:
			group = QGroupBox("SSH tunnel")
			group.setCheckable(True)
			group.setChecked(False)
			self.connect(group, SIGNAL("toggled(bool)"), callWithAddParams(self.rt.switchTunnel, (conf[0],)))
			tmpLayout = QVBoxLayout()
			if len(conf[1]) >= 2:
				for (host,displayname) in conf[1]:
					qrcRadioButton = QRadioButton(displayname)
					qrcRadioButton.setObjectName(host)
					self.connect(qrcRadioButton, SIGNAL("toggled(bool)"), callWithAddParams(self.rt.updateTunnel, (host, conf[0])))
					tmpLayout.addWidget(qrcRadioButton)
					first = False
			else:
				tmpLayout.addStretch()
			group.setLayout(tmpLayout)
			boxLayout.addWidget(group)
			return group
		else:
			boxLayout.addStretch()


	def addOptions2(self, boxLayout, conf):
		if len(conf[2]) >= 1:
			group = QGroupBox("SSHFS")
			tmpLayout = QVBoxLayout()
			group.setLayout(tmpLayout)
			group.setEnabled(len(conf[1]) == 0)
			for (host,displayname) in conf[2]:
				button = QCheckBox(displayname)
				self.connect(button, SIGNAL("toggled(bool)"), callWithAddParams(self.rt.switchMount, (host, displayname, conf[0])))
				tmpLayout.addWidget(button)
			boxLayout.addWidget(group)
			return group
		else:
			boxLayout.addStretch()

# TODO mount/umount return value

class ControlPanelNetwork():

	def __init__(self, sshfsdir):
		self.tunnels = {}
		self.sshfsdir = sshfsdir

	def openTunnel(self, host):
		print "opening tunnel", host
		self.tunnels[host] = subprocess.Popen(['/usr/bin/autossh', '-N', host], close_fds=True, shell=False, stdin=open('/dev/null', 'r'))

	def closeTunnel(self, host):
		print "closing tunnel", host
		self.tunnels[host].terminate()
		self.tunnels[host].wait()
		del self.tunnels[host]

	def mount(self, host, target):
		print "mounting", host, target
		return subprocess.call(['/usr/bin/sshfs', '-o', 'follow_symlinks', "%s:" % host, os.path.join(self.sshfsdir, target)])

	def umount(self, target):
		print "umounting", target
		return subprocess.call(['/bin/fusermount', '-u', os.path.join(self.sshfsdir, target)])


class ControlPanelRuntime:

	def __init__(self, conf):
		self.config = conf[0]
		self.tunnel = {}
		self.mounted = {}
		for x in conf[0]:
			self.tunnel[x[0]] = x[1][0][0] if len(x[1]) == 1 else None
			self.mounted[x[0]] = set()
		self.network = ControlPanelNetwork(conf[1])

	def switchTunnel(self, name, x):
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
				if btn is not None:
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



rt = ControlPanelRuntime(config)

app = QtGui.QApplication(sys.argv)
tooltip = ControlPanelGUI(rt)
tooltip.show()
app.exec_()
rt.close()

