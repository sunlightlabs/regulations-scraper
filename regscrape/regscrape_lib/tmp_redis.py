try:
    import settings
except ImportError:
    settings = object()

import uuid, os, subprocess, time, shutil

class TmpRedis(object):
    REDIS_CONFIG = {'daemonize': 'no', 'pidfile': '{path}/redis.pid', 'port': '0', 'bind': '127.0.0.1', 'unixsocket': '{path}/redis.sock', 'timeout': '300', 'loglevel': 'warning', 'logfile': 'stdout', 'databases': '1', '' : 'save 900 1\nsave 300 10\nsave 60 10000', 'rdbcompression': 'yes', 'dbfilename': 'dump.rdb', 'dir': '{path}/data', 'slave-serve-stale-data': 'yes', 'appendonly': 'no', 'appendfsync': 'everysec', 'no-appendfsync-on-rewrite': 'no', 'vm-enabled': 'no', 'vm-swap-file': '{path}/redis.swap', 'vm-max-memory': '0', 'vm-page-size': '32', 'vm-pages': '134217728', 'vm-max-threads': '4', 'hash-max-zipmap-entries': '512', 'hash-max-zipmap-value': '64', 'list-max-ziplist-entries': '512', 'list-max-ziplist-value': '64', 'set-max-intset-entries': '512', 'activerehashing': 'yes'}

    def get_config(self, **kwargs):
        return '\n'.join([' '.join(option).strip() for option in self.REDIS_CONFIG.items()]).format(**kwargs)
    
    def __init__(self):
        redis_base = getattr(settings, 'REDIS_BASE', '/mnt/redis')
        redis_dir = os.path.join(redis_base, uuid.uuid4().__str__())
        
        os.mkdir(redis_dir)
        os.mkdir(os.path.join(redis_dir, 'data'))
        
        self.config = os.path.join(redis_dir, 'redis.conf')
        config_file = open(self.config, 'w')
        config_file.write(self.get_config(path=redis_dir))
        config_file.close()
        
        self.directory = redis_dir
        self.socket = os.path.join(redis_dir, 'redis.sock')
        self.process = subprocess.Popen(['redis-server', self.config], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        
        time.sleep(1)
    
    def get_connection(self):
        from redis import Redis
        return Redis(unix_socket_path=self.socket)
    
    def get_pickle_connection(self):
        # define an inner class so that we don't have to import redis until re try to get a connection
        import cPickle
        from redis import Redis
        
        class PickleRedis(Redis):
            def get(self, key):
                return cPickle.loads(super(PickleRedis, self).get(key))
            
            def set(self, key, value):
                return super(PickleRedis, self).set(key, cPickle.dumps(value, -1))
        
        return PickleRedis(unix_socket_path=self.socket)
    
    def terminate(self):
        self.process.terminate()
        time.sleep(1)
        shutil.rmtree(self.directory)
