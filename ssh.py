#! /usr/bin/python

from PyQt4 import QtGui

import sys

import mod_ssh

app = QtGui.QApplication(sys.argv)

mod_ssh.load()

app.exec_()

mod_ssh.unload()


