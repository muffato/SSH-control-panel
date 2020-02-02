SSH Control panel
---

Control panel for SSH tunnels and SSHFS mounts.
Build in Python and PyQT5


# Usage

- Configure your tunnels and mount points in `ssh_conf.py`. All entries
  are expected to be resolved by `ssh`, i.e. have an entry in
  `~/.ssh/config`
- Run `ssh.py`

The app will create an icon in the system tray bar, from where you can
control the app through the contextual menu, or bring the window to the
foreground.

# Support

I used this app everyday for about 10 years on a Linux laptop. Eat your own
dog food, as they say. I've stopped using it because I had to move to a Mac
:sigh: and the system-tray icon was not working (I think it's a QT issue).

I have therefore archived this repository, to keep it for the posterity.
