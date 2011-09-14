__author__ = "Andrey Nikishaev"
__email__ = "creotiv@gmail.com"
 
import pymongo, sys
from gevent.queue import Queue
 
class GeventMongoPool(object):
    """
    Rewrited connection pool for working with global connections.
    """
 
    # Non thread-locals
    __slots__ = ["sockets", "socket_factory"]
    sock = None
 
    def __init__(self, socket_factory):
        self.socket_factory = socket_factory
        if not hasattr(self, "sockets"):
            self.sockets = []
 
    def socket(self):
        # we store the pid here to avoid issues with fork /
        # multiprocessing - see
        # test.test_connection:TestConnection.test_fork for an example
        # of what could go wrong otherwise
        pid = os.getpid()
 
        if self.sock is not None and self.sock[0] == pid:
            return self.sock[1]
 
        try:
            self.sock = (pid, self.sockets.pop())
        except IndexError:
            self.sock = (pid, self.socket_factory())
 
        return self.sock[1]
 
    def return_socket(self):
        if self.sock is not None and self.sock[0] == os.getpid():
            self.sockets.append(self.sock[1])
        self.sock = None
 
pymongo.connection.Pool = GeventMongoPool
 
class MongoConnection(object):
    """Memcache pool auto-destruct connection"""
    def __init__(self,pool,conn):
        self.pool = pool
        self.conn = conn
 
    def getDB(self):
        return self.conn
 
    def __getattr__(self, name):
        return getattr(self.conn, name)
 
    def __getitem__(self, name):
        return self.conn[name]
 
    def __del__(self):
        self.pool.queue.put(self.conn)
        del self.pool
        del self.conn
 
class Mongo(object):    
    """MongoDB Pool"""
    def __new__(cls,db_name,size=5,*args,**kwargs):
        if not hasattr(cls,'_instance'):
	    # use your own config library
            cls._instance = object.__new__(cls)
            cls._instance.queue = Queue(size)
            for x in xrange(size):
                try:
		    # use your own config library
                    cls._instance.queue.put(
                        pymongo.Connection(*args,**kwargs)[db_name]
                    )
                except:
                    sys.exc_clear()
                    error('Can\'t connect to mongo servers')
 
        return cls._instance     
 
    def get_conn(self,block=True,timeout=None):
        """Get Mongo connection wrapped in MongoConnection object"""
        obj = MongoConnection
        return obj(self,self.queue.get(block,timeout))
