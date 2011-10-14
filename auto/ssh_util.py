from fabric.api import *

def ssh_config(host):
    from os.path import expanduser
    from paramiko.config import SSHConfig

    def hostinfo(host, config):
        hive = config.lookup(host)
        if 'hostname' in hive:
            host = hive['hostname']
        if 'user' in hive:
            host = '%s@%s' % (hive['user'], host)
        if 'port' in hive:
            host = '%s:%s' % (host, hive['port'])
        return host

    try:
        config_file = file(expanduser('~/.ssh/config'))
    except IOError:
        pass
    else:
        config = SSHConfig()
        config.parse(config_file)
        key = config.lookup(host).get('identityfile', None)
        key_filename = expanduser(key)
        
        env.key_filename = [key_filename] if key_filename else []
        return hostinfo(host, config)
