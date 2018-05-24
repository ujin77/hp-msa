#!/usr/bin/python
# -*- coding: utf-8
#

import os, sys
import urllib2, ssl
from hashlib import md5
from xml.etree.ElementTree import fromstring, ElementTree as ET, dump as ETdump
import json
import xmltodict

PROG=os.path.basename(sys.argv[0]).rstrip('.py')
PROG_DESC='hp-msa client'
USAGE='Usage: hp-msa.py <HOSTNAME> <USERNAME> <PASSWORD> [lld|stats|data|connect]'


def debug_obj(obj, xml=False):
    if xml:
        ETdump(obj)
    else:
        print 'tag: %s | name: %s | text: %s' % (obj.tag, obj.get('name'), obj.text)
        # print 'tag:', obj.tag, '| name:', obj.get('name'), '| text:', obj.text
        # print 'tag:', obj.tag, '|attrib:', obj.attrib, '|text:', obj.text, '|name:', obj.get('name'), '|type:', obj.get('type')

def _out(str_text):
    sys.stdout.write(str_text)
    sys.stdout.flush()

class msa_storage(object):

    username = None
    password = None
    hostname = None
    sessionKey = None
    zbxData = {'data': []}

    def __init__(self, hostname, username, password):
        self.hostname = hostname
        self.username = username
        self.password = password

    def _request_url(self, api):
        return 'https://%s/api%s' % (self.hostname, api)

    def _request(self, api):
        if self.sessionKey:
            req = urllib2.Request(url=self._request_url(api))
            req.add_header('dataType', 'api-brief')
            req.add_header('sessionKey', self.sessionKey)
            xml=urllib2.urlopen(req, context=ssl._create_unverified_context()).read()
            if len(xml)>10:
                return ET(fromstring(xml)).getroot()
        return None

    def _request_show(self, api):
        return self._request('/show/' + api)

    def _login_url(self):
        login = md5( '%s_%s' % (self.username, self.password)).hexdigest()
        url = 'https://%s/api/login/%s' % ( self.hostname, login)
        return url

    def login(self):
        return_code = 0
        req = urllib2.Request(url=self._login_url())
        req.add_header('dataType', 'api-brief')
        xml = urllib2.urlopen(req, context=ssl._create_unverified_context()).read()
        tree = ET(fromstring(xml))
        for obj in tree.getroot():
            for prop in obj:
                if prop.get('name') == 'response-type':
                    response_type = prop.text
                if prop.get('name') == 'return-code':
                    return_code = int(prop.text)
                if prop.get('name') == 'response':
                    self.sessionKey = prop.text
        # print(response_type, return_code, self.sessionKey)
        return return_code

    def logout(self):
        self._request('/exit')

    # def objects(self, api, objectName=None, idName=None, pType=None):
    #     xml=self._request(api)
    #     print('====================')
    #     for obj in xml:
    #         # print('--------------------')
    #         # self.debug_obj(obj)
    #         if obj.get('name') == objectName:
    #             for prop in obj:
    #                 # self.debug_obj(prop)
    #                 if prop.get('name') == idName:
    #                     self.debug_obj(prop, xml=False)
    #                     s = "{'{#KEY}' => " + prop.text + ", '{#CLASS}' => " + pType + "}"
    #                     print s

    def _add_zbx(self, data):
        self.zbxData['data'].append(data)

    def get_zbx(self):
        return json.dumps(self.zbxData, sort_keys=True, indent=2)

    def lld(self, api, objectName=None, idName=None, pType=None):
        xml = self._request_show(api)
        for obj in xml:
            if obj.get('name') == objectName:
                for prop in obj:
                    if prop.get('name') == idName:
                        self._add_zbx({'{#KEY}': prop.text, '{#CLASS}': pType})
        print self.get_zbx()

    def stats(self, api, objectName=None, idName=None, pName=None):
        xml = self._request('%s/%s' % (api, idName))
        for obj in xml:
            if obj.get('name') == objectName:
                for prop in obj:
                    if prop.get('name') == pName:
                        _out(prop.text)
                        return

    def data(self, api, objectName=None, idName=None, idVal=None, key=None):
        xml = self._request_show(api)
        for obj in xml:
            if obj.get('name') == objectName:
                is_idVal = False
                is_key = False
                for prop in obj:
                    if prop.get('name') == idName and prop.text == idVal:
                        is_idVal = True
                    if prop.get('name') == key:
                        res = prop.text
                        is_key = True
                    if is_idVal and is_key:
                        _out(res)
                        return


if __name__ == "__main__":
    if len(sys.argv)<5:
        print(USAGE)
        sys.exit(0)
    cmd = sys.argv[4]
    p1 = sys.argv[5]
    if len(sys.argv) > 6:
        p2 = sys.argv[6]
    if len(sys.argv) > 7:
        p3 = sys.argv[7]
    msa = msa_storage(sys.argv[1], sys.argv[2], sys.argv[3])
    msa.login()
    if cmd == 'lld':
        if p1 == 'disk':
            msa.lld('controllers',    'controllers',  'controller-id',    'Controller')
        if p1 == 'controller':
            msa.lld('disks',          'drive',        'durable-id',       'Disk')
        if p1 == 'volume':
            msa.lld('volumes', 'volume', 'volume-name', 'Volume')
        if p1 == 'vdisk':
            msa.lld('vdisks',     'virtual-disk', 'name',             'Vdisk')
        if p1 == 'enclosure':
            msa.lld('enclosures', 'enclosures',   'enclosure-id',     'Enclosure')

    elif cmd == 'data':
        if p1 == "disk":
            msa.data('disks', 'drive', "durable-id", p2, p3)
        if p1 == "controller":
            msa.data('controllers', "controllers", "controller-id", p2, p3)
        if p1 == "volume":
            msa.data('volumes', "volume", "volume-name", p2, p3)
        if p1 == "vdisk":
            msa.data('vdisks', "virtual-disk", "name", p2, p3)
        if p1 == "enclosure":
            msa.data('enclosures', "enclosures", "enclosure-id", p2, p3)
    elif cmd == 'stats':
        if p1 == "volume":
            msa.stats('volume-statistics',  'volume-statistics', p2, p3)
        if p1 == "vdisk":
            msa.stats('vdisk-statistics', 'vdisk-statistics', p2, p3)

    # print( msa.request('/show/cli-parameters'))
    # print( msa.request('/show/cli-parameters'))
    msa.logout()
