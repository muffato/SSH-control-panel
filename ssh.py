#!/usr/bin/env python2

from PyQt5.QtWidgets import QApplication

import sys

import mod_ssh

app = QApplication(sys.argv)

mod_ssh.load()

app.exec_()

mod_ssh.unload()


