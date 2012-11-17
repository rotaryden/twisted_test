# -*- coding: utf-8 -*-

from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.internet import reactor
from twisted.web.client import Agent, HTTPConnectionPool
from twisted.internet.defer import inlineCallbacks, returnValue

import json

#logging
from twisted.python import log as the_log
from twisted.python.logfile import DailyLogFile
the_log.startLogging(open("./twisted_test.log", 'w'))
def log(msg): #shortcut
    the_log.msg("----- TEST TASK ---->>> " + msg)
    
#mysql with a pool
from twisted.enterprise import adbapi
mysql_pool = adbapi.ConnectionPool("MySQLdb", db="twisted_test", user="d", passwd="hydrason")

#redis
import txredisapi as redis
redis_pool = redis.lazyConnectionPool() #not Deferred

class HttpFetcher(object):
    """
        URL fetching small wrapper
    """
    HTTP_POOL = HTTPConnectionPool(reactor)
    HTTP_AGENT = Agent(reactor, pool=HTTP_POOL)
    
    def __init__(self, method):
        self.method = method
        
            
    def get(self, url, method=None):
        return self.HTTP_AGENT.request(method or self.method, url)
        
    
class TestPage(Resource):
    """
        Request handler
    """
    PAGE = "http://www.google.com" 
    REDIS_KEY = "twisted_test_key"

    def __init__(self, kv_pool, rdb_pool):
        self.kv_pool = kv_pool
        self.rdb_pool = rdb_pool
        Resource.__init__(self)  #Resource is old-style class by some reason


    def update_mysql_db(self, data):
        def _make_txn(txn, user):
            #CREATE DATABASE twisted_test
            txn.execute("CREATE TABLE IF NOT EXISTS sizes "
                        "(box_id varchar(10) PRIMARY KEY, "
                        "width INTEGER NOT NULL, "
                        "length INTEGER NOT NULL)")
            txn.execute("INSERT INTO sizes (box_id, length, width) "
                        "VALUES (%(id)s, %(l)s, %(w)s)"
                        "ON DUPLICATE KEY UPDATE length=%(l)s, width=%(w)s",
                        {'w': data['width'], 'l':data['length'], 'id':data['box_id']})
            #should be committed upon end
            return 'Okay'
        self.rdb_pool.runInteraction(_make_txn, data)\
            .addCallback(lambda res: log('Database update returned: ' + str(res)))


    def _get_json_data(self, request):
        return json.loads(request.content.getvalue())  #looks like getvalue() works only on Twisted Web


    @inlineCallbacks
    def refresh_redis_settings(self, key, new_value):
        """
           Redis updating, and inline callbacks test
        """
        try:
            exists = yield self.kv_pool.exists(key)
            if not exists:
                log('key=%s was not found' % str(key))                
            yield self.kv_pool.set(key, new_value)
            log("set is successful, value= %s\n" % repr(new_value))
                
        except Exception, e:
            log("Redis error %s" % e.message)
        
        
    def render_POST(self, request):
        """
            POST handler, test logic goes here
        """
        #1: JSON handling
        data = self._get_json_data(request)
        
        #2: MySQL update
        self.update_mysql_db(data['data'])
        
        #3: redis
        value = data['data']['length']
        self.refresh_redis_settings(self.REDIS_KEY, value)
    
        #4: url fetching
        @inlineCallbacks
        def fetch():  #yet another small test of co-routines
            response = yield HttpFetcher('GET').get(self.PAGE)
            log("HTTP fetch response length: %s" % response.length)
        fetch()
        
        return '<html><body>Post request was handled</body></html>'
        

    def render_GET(self, request):
        """
            here is Javascript code to send test JSON object back to server and trigger POST
            goto localhost:8880/test and press 'Send JSON' button        
        """
        return "<html><body><input id='i' type='button' value='Send JSON'><br />" \
               "<p id='prg'>{'type': 'A', 'data': {'length': 200, 'width': 500, 'box_id': '1'}}</p>"\
               '<script src="//ajax.googleapis.com/ajax/libs/jquery/1.8.2/jquery.min.js"></script>'\
               """<script type="text/javascript">
                  $('#i').on('click',function(e){
                  $.ajax({
                    type: "POST",
                    url: "/test",
                    data: JSON.stringify( {'type': 'A', 'data': {'length': 200, 'width': 500, 'box_id': '1'}}),
                    contentType: "application/json; charset=utf-8",
                    dataType: "json"
                    });});</script>"""\
               "</body></html>"

root = Resource()
root.putChild("test", TestPage(redis_pool, mysql_pool))
factory = Site(root)

reactor.listenTCP(8880, factory)
reactor.run()


