# -*- coding: utf-8 -*-
import datetime, time, csv, os
import numpy as np
from utils.db import SqliteDB
from utils.rwlogging import log
from utils.rwlogging import strategyLogger as logs
from utils.rwlogging import balLogger as logb
from strader import Trader
from indicator import ma, macd, bolling, rsi, kdj
from mas.maPool import Pool

mas = emas = smas = lwmas = std = prices = None

def runStrategy(in_prices):
	global mas, emas, smas, lwmas, std, prices
	log.debug('beginning ma strategy ...')
	
	prices = in_prices
	ps = [p['close'] for p in prices]
	
	std = [0] * 51
	l = len(prices)
	for period in range(2, 51):
		std[period] = [0] * l
		for i in range(period - 1, l):
			std[period][i] = np.std(ps[i-period+1 : i+1], dtype=np.float64, ddof=0)
		
	mas = [0] * 81
	emas = [0] * 81
	smas = [0] * 81
	lwmas = [0] * 81
	for period in range(2, 81):
		mas[period] = ma.calc_ma(ps, period)
		emas[period] = ma.calc_ema(ps, period)
		smas[period] = ma.calc_sma(ps, period)
		lwmas[period] = ma.calc_lwma(ps, period)
		
	pool = Pool(100)
	#t = doTrade(pool, 25, 1.0, 'MA', 7, 'SMA', 12, 'EMA', 31, 'SMA', 7, 'MA', 12, 'MA', 13)
	#t = doTrade(pool, 25, 1.3, 'MA', 7, 'SMA', 13, 'EMA', 31, 'SMA', 7, 'MA', 12, 'MA', 13)
	#pool.showStrategies()
	#return 
	
	log.debug('running ma strategy ...')
	starttime = datetime.datetime.now() 
	matypes = ['MA', 'EMA', 'SMA', 'LWMA']
	
	farr = range(5, 20)
	s1arr = range(8, 40)
	s2arr = range(0, 80)
	
	poola = Pool(30)
	poolb = Pool(30)
	for stdPeriod in [20, 25]:
		for stdGuage in [15, 18, 20, 25, 30, 40]:
			log.debug('*** ' + str(stdPeriod) + ',' + str(stdGuage) + ' ***')
			for ft, f in [(matype, period) for matype in matypes for period in farr]:
				for s1t, s1 in [(matype, period) for matype in matypes for period in s1arr]:
					if s1 != 0 and s1 <= f: continue
					elapsed = (datetime.datetime.now() - starttime).seconds
					log.debug('== ' + str(elapsed) + ',' + ft + '_' + str(f) + ',' + s1t + '_' + str(s1) + ' ==')
					for s2t, s2 in [(matype, period) for matype in matypes for period in s2arr]:
						if s2 != 0 and s2 <= s1: continue
						if s2 == 0 and (s2t == 'EMA' or s2t == 'SMA' or s2t == 'LWMA'): continue
						
						doTrade(poola, stdPeriod, stdGuage, ft, f, s1t, s1, s2t, s2, '', 0, '', 0, '', 0)
						doTrade(poolb, stdPeriod, stdGuage, '', 0, '', 0, '', 0, ft, f, s1t, s1, s2t, s2)
						
	poola.showStrategies()
	poolb.showStrategies()
	
def doTrade(pool, stdPeriod, stdGuage, afmt, af, as1mt, as1, as2mt, as2, bfmt, bf, bs1mt, bs1, bs2mt, bs2):
	global std, prices
	
	sname = str(stdPeriod) + '_' + str(stdGuage)
	sname += '_' + afmt + '_' + str(af) + '_' + as1mt + '_' + str(as1)
	if as2 > 0: sname += '_' + as2mt + '_' + str(as2)
	sname +=  '_' + bfmt + '_' + str(bf) + '_' + bs1mt + '_' +str(bs1)
	if bs2 > 0: sname += '_' + bs2mt + '_' + str(bs2)
	
	afma, as1ma, as2ma = getMas(afmt, af), getMas(as1mt, as1), getMas(as2mt, as2)
	bfma, bs1ma, bs2ma = getMas(bfmt, bf), getMas(bs1mt, bs1), getMas(bs2mt, bs2)
	
	front = max(as1, as2, bs1, bs2)
	
	active = 0
	a1pos = a2pos = b1pos = b2pos = 0
	a1wait = a2wait = b1wait = b2wait = 0
	a1price = a2price = b1price = b2price = 0
	t = Trader(sname)
	for i in range(front, len(prices)):
		price = prices[i]
		
		volume = 0
		notes = ''
		oa1pos, oa2pos, ob1pos , ob2pos = a1pos, a2pos, b1pos , b2pos
		oa1wait, oa2wait, ob1wait, ob2wait = a1wait, a2wait, b1wait, b2wait
		
		if std[stdPeriod][i] >= stdGuage: active = 2
		else: active = 1
		
		#A
		if as1 > 0 and afma[i - 1] <= as1ma[i - 1] and afma[i] > as1ma[i]:
			a1wait = 1
		
		if as1 > 0 and afma[i - 1] >= as1ma[i - 1] and afma[i] < as1ma[i]:
			a1wait = -1
		
		if as2 > 0 and afma[i - 1] <= as2ma[i - 1] and afma[i] > as2ma[i]:
			a2wait = 1
		
		if as2 > 0 and afma[i - 1] >= as2ma[i - 1] and afma[i] < as2ma[i]:
			a2wait = -1
		
		if active == 1: a1pos, a2pos = a1wait, a2wait
		if active != 1 and a1pos * a1wait == -1: a1pos = 0
		if active != 1 and a2pos * a2wait == -1: a2pos = 0
		
		if oa1pos != a1pos:
			volume += a1pos - oa1pos
			notes += 'A1:'+ str(oa1pos) + '->' + str(a1pos) + ';' + str(a1price) + '->' + str(price['rmb']) + ';'
			a1price = price['rmb']
			
		if oa2pos != a2pos:
			volume += a2pos - oa2pos
			notes += 'A2:'+ str(oa1pos) + '->' + str(a1pos) + ';' + str(a2price) + '->' + str(price['rmb']) + ';'
			a2price = price['rmb']
		
		#B
		if bs1 > 0 and bfma[i - 1] <= bs1ma[i - 1] and bfma[i] > bs1ma[i]:
			b1wait = 1
		
		if bs1 > 0 and bfma[i - 1] >= bs1ma[i - 1] and bfma[i] < bs1ma[i]:
			b1wait = -1
		
		if bs2 > 0 and bfma[i - 1] <= bs2ma[i - 1] and bfma[i] > bs2ma[i]:
			b2wait = 1
		
		if bs2 > 0 and bfma[i - 1] >= bs2ma[i - 1] and bfma[i] < bs2ma[i]:
			b2wait = -1
		
		if active == 2: b1pos, b2pos = b1wait, b2wait
		if active != 2 and b1pos * b1wait == -1: b1pos = 0
		if active != 2 and b2pos * b2wait == -1: b2pos = 0
		
		if ob1pos != b1pos:
			volume += b1pos - ob1pos
			notes += 'B1:'+ str(ob1pos) + '->' + str(b1pos) + ';' + str(b1price) + '->' + str(price['rmb']) + ';'
			b1price = price['rmb']
			
		if ob2pos != b2pos:
			volume += b2pos - ob2pos
			notes += 'B2:'+ str(ob2pos) + '->' + str(b2pos) + ';' + str(b2price) + '->' + str(price['rmb']) + ';'
			b2price = price['rmb']
		
		if volume != 0:
			t.processOrder(price['dt'], price['rmb'], volume * 10, notes=notes)
		else:
			t.summary(price['dt'], price['rmb'])
		
	pool.estimate(t)
	return t
		
def getMas(matype, period):
	if matype == 'MA':
		return mas[period]
	elif matype == 'EMA':
		return emas[period]
	elif matype == 'SMA':
		return smas[period]
	elif matype == 'LWMA':
		return lwmas[period]
	else:
		return None

