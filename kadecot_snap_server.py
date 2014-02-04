#!/usr/bin/env python
#coding:utf-8

# This code is under MIT License.
# http://opensource.org/licenses/MIT

import http.server
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer
import urllib.parse
import urllib.request
import tempfile
import json
import sys
import os

KADECOT_IP_ADDRESS = ""
KADECOT_PORT = "31413"
KADECOT_TIMEOUT = 10

BLOCK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),"block.xml")

def get_kadecot_url(ip,query):
    base = "http://" + ip + ":" + KADECOT_PORT + "/call.json"
    return base + "?" + urllib.parse.urlencode(query)

# for example,
#  ip = "192.168.0.5" and method = "get" and params = ["hoge",0x80]
def send_query_to_kadecot(ip,method,params):
    query = {"method":method,"params":str(params).replace("'","")}
    url = get_kadecot_url(ip,query)
    print("send request to " + url)
    o = urllib.request.urlopen(url,timeout=KADECOT_TIMEOUT)
    return o.read().decode("utf-8")

# split with : and ;
#  first is nickname,second is devicetype.
def send_list(ip):
    ret = []
    nicknames = []
    device_types = []

    r = send_query_to_kadecot(ip,"list",[])
    js = json.loads(r)
    print(js,file=sys.stderr)
    for res in js["result"]:
        nicknames.append(res["nickname"])
        device_types.append(res["deviceType"])

    ret = ":".join(nicknames)  + ";" + ":".join(device_types)
    return ret

# split with : and ;
#  first is fail or success,second is value
# do not return hexed value.
#  because there is a bug in snap!
#  see https://github.com/jmoenig/Snap--Build-Your-Own-Blocks/issues/207
def send_get(ip,nickname,epc):
    r = send_query_to_kadecot(ip,"get",[nickname,epc])
    js = json.loads(r)
    print(js,file=sys.stderr)
    if ("error" in js or
        js["result"]["property"] == [] or
        not js["result"]["property"][0]["success"]):
        return "fail;-1"
    else:
        return "success;" + ":".join(str(i) for i in 
                                         js["result"]["property"][0]["value"])
# split with : and ;
#  first is fail or success,second is value
# do not return hexed value.
#  because there is a bug in snap!
#  see https://github.com/jmoenig/Snap--Build-Your-Own-Blocks/issues/207
def send_set(ip,nickname,epc,edt):
    r = send_query_to_kadecot(ip,"set",[nickname,[epc,edt.split("-")]])
    js = json.loads(r)
    print(js,file=sys.stderr)
    if ("error" in js or
        js["result"]["property"] == [] or
        not js["result"]["property"][0]["success"]):
        return "fail;-1"
    else:
        return "success;" + ":".join(str(i) for i in 
                                         js["result"]["property"][0]["value"])

# for CROS, see https://gist.github.com/enjalot/2904124
class SnapKadecotHTTPRequestHandler(SimpleHTTPRequestHandler):
    def send_head(self):
        _query = urllib.parse.urlparse(self.path).query
        query = {}
        if len(_query) > 0:
            query = dict(qc.split("=") for qc in _query.split("&"))

        path = self.translate_path(self.path)
        method = os.path.basename(path)

        ret = None

        if method == "block":
            f = open(BLOCK_PATH, 'rb')
            self.send_response(200)
            self.send_header("Content-type","text/xml")
            fs = os.fstat(f.fileno())
            self.send_header("Content-Length", str(fs[6]))
            self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            return f

        elif method == "list":
            ret = self.send_list()
        elif method == "get":
            if not ("nickname" in query and "epc" in query):
                self.send_error(403,"Query doesn't have enough info")
                return None
            else:
                ret = self.send_get(query["nickname"],query["epc"])
        elif method == "set":
            if not ("nickname" in query and "epc" in query and "edt" in query):
                self.send_error(403,"Query doesn't have enough info")
                return None
            else:
                ret = self.send_set(query["nickname"],query["epc"],query["edt"])
        else:
            self.send_error(404, "Method not found")
            return None

        f = tempfile.TemporaryFile()
        f.write(bytes(ret,"utf-8"))
        f.flush()
        f.seek(0)

        self.send_response(200)
        self.send_header("Content-type","text/plain")
        fs = os.fstat(f.fileno())
        self.send_header("Content-Length", str(fs[6]))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        return f

    # split with : and ;
    #  first is nickname,second is devicetype.
    def send_list(self):
        return send_list(KADECOT_IP_ADDRESS)

    # split with : and ;
    #  first is fail or success,second is value
    def send_get(self,nickname,epc):
        return send_get(KADECOT_IP_ADDRESS,nickname,epc)

    # split with : and ;
    #  first is fail or success,second is value
    def send_set(self,nickname,epc,edt):
        return send_set(KADECOT_IP_ADDRESS,nickname,epc,edt)

def send_test():
    global KADECOT_IP_ADDRESS
    KADECOT_IP_ADDRESS = "192.168.1.176"
    test_dev = "HomeAirConditioner"

    print(send_list(KADECOT_IP_ADDRESS))
    print(send_get(KADECOT_IP_ADDRESS,test_dev,"0x80"))
    print(send_set(KADECOT_IP_ADDRESS,test_dev,"0x80","0x30"))


def main():
    global KADECOT_IP_ADDRESS
    PORT = 31338
    if len(sys.argv) > 1:
        KADECOT_IP_ADDRESS = sys.argv[1]
    else:
        KADECOT_IP_ADDRESS = input("Kadeoct JSONServer IP: ")
    Handler = SnapKadecotHTTPRequestHandler
    print("KadecotServer: " + KADECOT_IP_ADDRESS + ":" + str(PORT))

    httpd = TCPServer(("", PORT), Handler)

    print("serving at port", PORT)
    print("http://snap.berkeley.edu/snapsource/snap.html#open:http://localhost:"+str(PORT)+"/block")
    httpd.serve_forever()

if __name__ == "__main__":
    main()
