#! /usr/bin/python

from PyQt4 import QtGui
from PyQt4 import QtCore

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from PyKDE4.plasma import Plasma
from PyKDE4 import plasmascript
from PyKDE4.kdecore import KUrl

import os
import sys
import time
import subprocess


config = {
	'networks' : [
		('EBI', {
			'tunnels': [
				('tunnel-ebi-inside', 'login'),
				('tunnel-ebi-outside-stargate', 'stargate'),
				('tunnel-ebi-outside-gate', 'gate')
			],
			'mounts': [
				('login.ebi.ac.uk', 'ebi', False)
			]
		}),
		('Sanger', {
			'tunnels': [
				('tunnel-sanger', 'ssh.sanger')
			],
			'mounts': [
				('farm2-head4.internal.sanger.ac.uk', 'sanger', False)
			]
		}),
		('ENS', {
			'tunnels': [
				('tunnel-wotan', 'wotan')
			],
			'mounts': [
				('heimdall.ens.fr', 'heimdall', False),
				('wotan.ens.fr', 'wotan', True),
				('ldog21.ens.fr', 'ldog21', False)
			]
		}),
		('IIE', {
			'mounts': [
				('perso.iiens.net', 'arise', True)
			]
		}),
	],
	'paths' : {
		'mountFolder': '/home/matthieu/sshfs',
		'sshCmd': ['/usr/bin/autossh', '-N'],
		'mountCmd': ['/usr/bin/sshfs', '-o', 'follow_symlinks'],
		'umountCmd': ['/bin/fusermount', '-u']
	}
}


# Ensures that the configuration variable is correct
#####################################################
def doValidateConf(conf):

	def validateListTupleTwoStringsBool(l):
		assert isinstance(l, list)
		assert len(l) > 0
		assert all(isinstance(x, tuple) for x in l)
		assert all(len(x) == 3 for x in l)
		assert all(isinstance(x[0], basestring) for x in l)
		assert all(isinstance(x[1], basestring) for x in l)
		assert all(isinstance(x[2], bool) for x in l)

	def validateListTupleTwoStrings(l):
		assert isinstance(l, list)
		assert len(l) > 0
		assert all(isinstance(x, tuple) for x in l)
		assert all(len(x) == 2 for x in l)
		assert all(isinstance(x[0], basestring) for x in l)
		assert all(isinstance(x[1], basestring) for x in l)

	assert isinstance(conf, dict)
	assert set(conf.keys()) == set(['networks', 'paths'])

	assert isinstance(conf['paths'], dict)
	assert set(conf['paths'].keys()) == set(['mountFolder', 'sshCmd', 'mountCmd', 'umountCmd'])
	assert isinstance(conf['paths']['mountFolder'], basestring)
	assert isinstance(conf['paths']['sshCmd'], list)
	assert all(isinstance(x, basestring) for x in conf['paths']['sshCmd'])
	assert isinstance(conf['paths']['mountCmd'], list)
	assert all(isinstance(x, basestring) for x in conf['paths']['mountCmd'])
	assert isinstance(conf['paths']['umountCmd'], list)
	assert all(isinstance(x, basestring) for x in conf['paths']['umountCmd'])

	assert isinstance(conf['networks'], list)
	for x in conf['networks']:
		assert isinstance(x, tuple)
		assert len(x) == 2
		(groupname,groupconf) = x
		assert isinstance(groupname, basestring)
		assert isinstance(groupconf, dict)
		assert len(groupconf) > 0
		assert set(groupconf.keys()).issubset(['tunnels', 'mounts'])
		if 'tunnels' in groupconf:
			validateListTupleTwoStrings(groupconf['tunnels'])
		if 'mounts' in groupconf:
			validateListTupleTwoStringsBool(groupconf['mounts'])

class ControlPanelGUI(plasmascript.Applet):

	def __init__(self, rt, config, parent=None):
		QtGui.QWidget.__init__(self, parent)
		self.rt = rt
		rt.gui = self
		self.config = config

	def init(self):
		self.setHasConfigurationInterface(False)

		self.theme = Plasma.Svg(self)
		self.theme.setImagePath("widgets/background")
		self.setBackgroundHints(Plasma.Applet.DefaultBackground)
		self.setAspectRatioMode(Plasma.IgnoreAspectRatio)

		#self.layout = QGraphicsLinearLayout(Qt.Horizontal, self.applet)
		#self.setLayout(self.layout)
		#self.resize(300,400)

		#self.setFixedSize(120*len(config['networks']), 230)
		self.resize(120*len(config['networks']), 230)
		self.setWindowTitle('SSH panel control')

		self.grpTunnel = {}
		self.grpMount = {}

		layout = QGraphicsLinearLayout(Qt.Horizontal, self.applet)
		for (groupname,conf) in self.config['networks']:
			groupBox = Plasma.GroupBox(self.applet)
			continue
			groupBox.text = groupname
			#boxLayout = QGraphicsLinearLayout(Qt.Vertical, groupBox)
			#if 'tunnels' in conf:
			#	self.grpTunnel[groupname] = self.addOptions(groupBox, boxLayout, groupname, conf['tunnels'])
			#boxLayout.addStretch()
			#if 'mounts' in conf:
			#	self.grpMount[groupname] = self.addOptions2(boxLayout, groupname, conf['mounts'])
			#groupBox.setLayout(boxLayout)
			#layout.addItem(groupBox)

		QtGui.QToolTip.setFont(QtGui.QFont('OldEnglish', 10))

		#self.setLayout(layout)
		self.connect(self, SIGNAL("close()"), callWithAddParams(self.rt.close, ()))

	def addOptions(self, parent, boxLayout, groupname, conf):

		group = Plasma.GroupBox(parent)
		group.setText("SSH tunnel")
		return group
		#group.setCheckable(True)
		#group.setChecked(False)
		self.connect(group, SIGNAL("toggled(bool)"), callWithAddParams(self.rt.switchTunnel, (groupname,)))
		tmpLayout = QGraphicsLinearLayout(Qt.Vertical, self.applet)
		for (host,displayname) in conf:
			qrcRadioButton = Plasma.RadioButton(self.applet)
			qrcRadioButton.text = displayname
			qrcRadioButton.setObjectName(host)
			if len(conf) == 1:
				qrcRadioButton.setChecked(True)
			self.connect(qrcRadioButton, SIGNAL("toggled(bool)"), callWithAddParams(self.rt.updateTunnel, (host, groupname)))
			tmpLayout.addItem(qrcRadioButton)
		group.setLayout(tmpLayout)
		boxLayout.addItem(group)
		return group


	def addOptions2(self, boxLayout, groupname, conf):

		group = QGroupBox("SSHFS")
		tmpLayout = QVBoxLayout()
		group.setLayout(tmpLayout)
		allstate = False
		pending = []
		for (host,displayname,state) in conf:
			button = QCheckBox(displayname)
			button.setEnabled(state)
			if not state:
				pending.append(button)
			self.connect(button, SIGNAL("toggled(bool)"), callWithAddParams(self.rt.switchMount, (host, displayname, groupname)))
			tmpLayout.addWidget(button)
		boxLayout.addWidget(group)
		return pending

# TODO mount/umount return value

class ControlPanelNetwork():

	def __init__(self, config):
		self.tunnels = {}
		self.config = config
		self.devnull = open('/dev/null', 'r')

	def openTunnel(self, host):
		print "opening tunnel", host
		print "cmd", self.config['paths']['sshCmd'] + [host]
		self.tunnels[host] = subprocess.Popen( self.config['paths']['sshCmd'] + [host], close_fds=True, shell=False)
		print self.tunnels[host]

	def closeTunnel(self, host):
		print "closing tunnel", host
		self.tunnels[host].terminate()
		self.tunnels[host].wait()
		del self.tunnels[host]

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
			for mountButton in self.gui.grpMount[name]:
				mountButton.setEnabled(x)

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



def CreateApplet(parent):
	doValidateConf(config)
	rt = ControlPanelRuntime(config)
	return ControlPanelGUI(rt, config, parent)

