# -*- coding: utf-8 -*-
import urllib2 
import re
from utils.rwlogging import log

def sms(msg):
	url = 'https://quanapi.sinaapp.com/fetion.php?u=13811830642&p=rw314159&to=13811830642&m='
	url = url + re.sub(' ', '%20', msg)
	ret = urllib2.urlopen(url).read()
	#ret = '00000'
	log.info('Sending ' + msg + ', result: ' + ret)
