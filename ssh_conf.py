
config = {
	'networks' : [
		('EBI', {
			'tunnels': [
				('tunnel-ebi-inside', 'login'),
				('tunnel-ebi-outside-stargate', 'stargate'),
				('tunnel-ebi-outside-gate', 'gate')
			],
			'mounts': [
				('login.ebi.ac.uk', 'ebi')
			]
		}),
		('Sanger', {
			'tunnels': [
				('tunnel-sanger', 'ssh.sanger')
			],
			'mounts': [
				('lenny-dev64.internal.sanger.ac.uk', 'sanger')
			]
		}),
		('ENS', {
			'tunnels': [
				('tunnel-wotan', 'wotan')
			],
			'mounts': [
				('heimdall.ens.fr', 'heimdall'),
				('ldog21.ens.fr', 'ldog21')
			],
			'mounts_direct': [
				('wotan.ens.fr', 'wotan')
			]
		}),
		('IIE', {
			'mounts_direct': [
				('perso.iiens.net', 'arise')
			]
		}),
	],
	'paths' : {
		'mountFolder': '/home/matthieu/sshfs',
		'sshCmd': ['/usr/bin/autossh', '-N'],
		'mountCmd': ['/usr/bin/sshfs', '-o', 'follow_symlinks', '-o', 'idmap=user'],
		'umountCmd': ['/bin/fusermount', '-u']
	}
}


# Ensures that the configuration variable is correct
#####################################################

def validateListTupleTwoStrings(l):
	assert isinstance(l, list)
	assert len(l) > 0
	assert all(isinstance(x, tuple) for x in l)
	assert all(len(x) == 2 for x in l)
	assert all(isinstance(x[0], basestring) for x in l)
	assert all(isinstance(x[1], basestring) for x in l)

assert isinstance(config, dict)
assert set(config.keys()) == set(['networks', 'paths'])

assert isinstance(config['paths'], dict)
assert set(config['paths'].keys()) == set(['mountFolder', 'sshCmd', 'mountCmd', 'umountCmd'])
assert isinstance(config['paths']['mountFolder'], basestring)
assert isinstance(config['paths']['sshCmd'], list)
assert all(isinstance(x, basestring) for x in config['paths']['sshCmd'])
assert isinstance(config['paths']['mountCmd'], list)
assert all(isinstance(x, basestring) for x in config['paths']['mountCmd'])
assert isinstance(config['paths']['umountCmd'], list)
assert all(isinstance(x, basestring) for x in config['paths']['umountCmd'])

assert isinstance(config['networks'], list)
for x in config['networks']:
	assert isinstance(x, tuple)
	assert len(x) == 2
	(groupname,groupconf) = x
	assert isinstance(groupname, basestring)
	assert isinstance(groupconf, dict)
	assert len(groupconf) > 0
	assert set(groupconf.keys()).issubset(['tunnels', 'mounts', 'mounts_direct'])
	if 'tunnels' in groupconf:
		validateListTupleTwoStrings(groupconf['tunnels'])
	if 'mounts' in groupconf:
		assert 'tunnels' in groupconf, groupconf.keys()
		validateListTupleTwoStrings(groupconf['mounts'])
	if 'mounts_direct' in groupconf:
		validateListTupleTwoStrings(groupconf['mounts_direct'])

print "validated"
