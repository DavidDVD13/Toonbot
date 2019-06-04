import asyncio
import discord
from discord.ext import commands

import aiohttp
import requests
from lxml import html
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import TimeoutException

from colorthief import ColorThief
import datetime
from copy import deepcopy
from PIL import Image
from io import BytesIO
import os
import json

class Fixtures(commands.Cog):
	""" Rewrite of fixture & result lookups. """
	def __init__(self, bot):
		self.bot = bot
		self.driver = None
	
	def __unload(self):
		if self.driver:
			self.driver.quit()
	
	# Spawn an instance of headerless chrome.
	def spawn_chrome(self):
		if self.driver:
			self.driver.quit()
		caps = DesiredCapabilities().CHROME
		caps["pageLoadStrategy"] = "normal"  #  complete
		chrome_options = Options()
		chrome_options.add_argument('log-level=3')
		chrome_options.add_argument("--headless")
		chrome_options.add_argument("--window-size=1920x1200")
		chrome_options.add_argument('--no-proxy-server')
		
		driver_path = os.getcwd() +"\\chromedriver.exe"
		prefs = {'profile.default_content_setting_values': {'images': 2, 'javascript': 2}}
		chrome_options.add_experimental_option('prefs', prefs)
		self.driver = webdriver.Chrome(desired_capabilities=caps,chrome_options=chrome_options, executable_path=driver_path)
		self.driver.set_page_load_timeout(20)
		
	def __unload(self):
		if self.driver is not None:
			self.driver.quit()
		
	async def _search(self,ctx,m,qry):
		qryurl = f"https://s.flashscore.com/search/?q={qry}&l=1&s=1&f=1%3B1&pid=2&sid=1"
		async with self.bot.session.get(qryurl) as resp:
			res = await resp.text()
			res = res.lstrip('cjs.search.jsonpCallback(').rstrip(");")
			res = json.loads(res)
		
		resdict = {}
		key = 0
		# Remove irrel.
		for i in res["results"]:
			# Format for LEAGUE
			if i["participant_type_id"] == 0:
				# Sample League URL: https://www.flashscore.com/soccer/england/premier-league/
				resdict[str(key)] = {"Match":i['title'],"url":f"soccer/{i['country_name'].lower()}/{i['url']}"} 
			
			# Format for TEAM
			elif i["participant_type_id"] == 1:
				# Sample Team URL: https://www.flashscore.com/team/thailand-stars/jLsL0hAF/
				resdict[str(key)] = {"Match":i["title"],"url":f"team/{i['url']}/{i['id']}"}
			
			key += 1
		
		if not resdict:
			return await m.edit(content=f"No results for query: {qry}")
		
		if len(resdict) == 1:
			try:
				await m.delete()
			except:
				pass
			return f'https://www.flashscore.com/{resdict["0"]["url"]}'
			
		outtext = ""
		for i in resdict:
			outtext += f"{i}: {resdict[i]['Match']}\n"
		
		try:
			await m.edit(content=f"Please type matching id: ```{outtext}```")
		except discord.HTTPException:
			return await m.edit(content=f"Too many matches to display, please be more specific.")
		
		def check(message):
			if message.author.id == ctx.author.id and message.content in resdict:
				return True
		
		match = await self.bot.wait_for("message",check=check,timeout=30)
		try:
			await m.delete()
		except:
			pass
		mcontent = match.content
		try:
			await match.delete()
		except:
			pass
		return f'https://www.flashscore.com/{resdict[mcontent]["url"]}'

	@commands.command()
	async def table(self,ctx,*,qry=None):
		""" Get table for a league """
		if qry is None:
			if ctx.guild is not None:
				if ctx.guild.id == 332159889587699712:
					url = "https://www.flashscore.com/soccer/england/premier-league"
				else:
					return await ctx.send("Specify a search query.")
			else:
				return await ctx.send("Please specify a search query.")
		else:
			m = await ctx.send(f"Searching for {qry}...")
			url = await self._search(ctx,m,qry)
		
		if url is None:
			return #rip
		m = await ctx.send(f"Grabbing table from {url}...")
		await ctx.trigger_typing()
		p = await self.bot.loop.run_in_executor(None,self.parse_table,url)
		await m.delete()
		await ctx.send(file=p)
	
	def parse_table(self,url):
		url += "/standings/"
		self.spawn_chrome()
		self.driver.get(url)
		self.driver.save_screenshot('screenie.png')
		xp = './/table[contains(@id,"table-type-")]'
		
		try:
			tbl = self.driver.find_element_by_xpath(xp)
		except NoSuchElementException:
			WebDriverWait(self.driver, 2)
			try:
				tbl = self.driver.find_element_by_xpath(xp)
			except NoSuchElementException:
				self.driver.quit()
				return # Rip
		
		location = tbl.location
		size = tbl.size
		im = Image.open("screenie.png")
		left = location['x']
		top = location['y']
		right = location['x'] + size['width']
		bottom = location['y'] + size['height']
		im = im.crop((left, top, right, bottom))
		output = BytesIO()
		im.save(output,"PNG")
		output.seek(0)
		df = discord.File(output,filename="table.png")
		self.driver.quit()
		return df

	@commands.command()
	async def bracket(self,ctx,*,qry=None):
		""" Get btacket for a tournament """
		if qry is None:
			return await ctx.send("Specify a search query.")
		else:
			m = await ctx.send(f"Searching for {qry}...")
			url = await self._search(ctx,m,qry)
			
		if url is None:
			return #rip	
		m = await ctx.send(f"Grabbing bracket from {url}...")
		await ctx.trigger_typing()
		p = await self.bot.loop.run_in_executor(None,self.parse_bracket,url)
		await m.delete()
		await ctx.send(file=p)
		
	@commands.command(aliases=["fx"])
	async def fixtures(self,ctx,*,qry=None):
		""" Displays upcoming fixtures for a team or league.
			Navigate with reactions.
		"""
		if qry is None:
			if ctx.guild is not None:
				if ctx.guild.id == 332159889587699712:
					url = "https://www.flashscore.com/team/newcastle-utd/p6ahwuwJ"
				else:
					return await ctx.send("Specify a search query.")
			else:
				return await ctx.send("Specify a search query.")
		else:
			m = await ctx.send(f"Searching for {qry}...")
			url = await self._search(ctx,m,qry)
		pages = await self.bot.loop.run_in_executor(None,self.parse_fixtures,url,ctx.author.name)
		await self.paginate(ctx,pages)

	@commands.command(aliases=['sc'])
	async def scorers(self,ctx,*,qry=None):
		""" Displays top scorers for a team or league.
			Navigate with reactions.
		"""
		if qry is None:
			if ctx.guild is not None:
				if ctx.guild.id == 332159889587699712:
					url = "https://www.flashscore.com/soccer/england/premier-league"
			else:
				return await ctx.send("Specify a search query.")
		else:
			m = await ctx.send(f"Searching for {qry}...")
			url = await self._search(ctx,m,qry)
		pages = await self.bot.loop.run_in_executor(None,self.parse_scorers,url,ctx.author.name)
		await self.paginate(ctx,pages)		
		
	@commands.command(aliases=["rx"])
	async def results(self,ctx,*,qry="Newcastle Utd"):
		""" Displays previous results for a team or league.
			Navigate with reactions.
		"""
		if qry is None:
			if ctx.guild is not None:
				if ctx.guild.id == 332159889587699712:
					url = "https://www.flashscore.com/team/newcastle-utd/p6ahwuwJ"
			else:
				return await ctx.send("Specify a search query.")
		else:
			m = await ctx.send(f"Searching for {qry}...")
			url = await self._search(ctx,m,qry)
		
		if url is None:
			return #rip
		
		pages = await self.bot.loop.run_in_executor(None,self.parse_results,url,ctx.author.name)
		await self.paginate(ctx,pages)	
		
	def get_color(self,url):
		url = url.strip('"')
		r = requests.get(url).content
		r = BytesIO(r)
		r.seek(0)
		ct = ColorThief(r)
		rgb = ct.get_color(quality=1)
		# Convert to base 16 int.
		return int('%02x%02x%02x' % rgb,16)	
		
	def get_html(self,url):
		self.spawn_chrome()		
		try:
			self.driver.get(url)
		except TimeoutException:
			self.driver.execute_script("window.stop();")
		except ConnectionAbortedError: 
			self.driver.quit()
			self.spawn_chrome()
			 
		e = discord.Embed()
		try:
			th = self.driver.find_element_by_xpath(".//div[contains(@class,'logo')]")
			th = th.value_of_css_property('background-image')
			th = th.strip("url(").strip(")")
			e.set_thumbnail(url=th.strip('"'))
			e.color = self.get_color(th)
		except:
			pass
		
		e.url = url
		
		t = html.fromstring(self.driver.page_source)
		return t,e

	def parse_results(self,url,au):
		url = f"{url}/results"
		t,e = self.get_html(url)
		rstb = t.xpath('.//div[@id="fs-results"]//tbody/tr')
		now = datetime.datetime.now()
		dates = []
		games = []
		if "/team/" in url:
			team = "".join(t.xpath('.//div[@class="team-name"]/text()')).strip()
			e.title = f"≡ Results for {team}"
			for i in rstb:
				d = "".join(i.xpath('.//td[contains(@class,"time")]//text()'))
				# Skip header rows.
				if not d:
					continue
					
				# Get match date
				try:
					d = datetime.datetime.strptime(d,"%d.%m. %H:%M")
					d = d.replace(year=now.year)
					d = datetime.datetime.strftime(d,"%a %d %b: %H:%M")
				except ValueError:
					# Fix older than a year games.
					d = datetime.datetime.strptime(d,"%d.%m.%Y")
					d = datetime.datetime.strftime(d,"%d/%m/%Y")
				
				# Score
				sc = i.xpath('.//td[contains(@class,"score")]/text()')
				sc = "".join(sc).replace('\xa0','').split(':')
				h = sc[0]
				a = sc[1]
				sc = "-".join(sc)
				# Assume we're playing at home.
				op = "".join(i.xpath('.//span[@class="padl"]/text()')).strip() # PADR IS HOME.
				
				wh = "H"
				w = "W" if h > a else "D" if h == a else "L"
				if team in op:
					# if we're actually the away team.
					wh = "A"
					op = "".join(i.xpath('.//span[@class="padr"]/text()')).strip()
					w = "L" if h > a else "D" if h == a else "W"
					
				dates.append(f"`{wh}: {d}`")
				games.append(f"`{w}: {sc} v {op}`")
		else:
			comp = "".join(t.xpath('.//div[@class="tournament-name"]/text()'))
			e.title = f"≡ Fixtures for {comp}"
			for i in rstb:
				d = "".join(i.xpath('.//td[contains(@class,"time")]//text()'))
				# Skip header rows.
				if not d:
					continue
				d = datetime.datetime.strptime(d,"%d.%m. %H:%M")
				d = d.replace(year=now.year)
				d = datetime.datetime.strftime(d,"%a %d %b: %H:%M")
				dates.append(f"`{d}`")
				sc = i.xpath('.//td[contains(@class,"score")]/text()')
				sc = "".join(sc).replace('\xa0','').split(':')
				hos = sc[0]
				aws = sc[1]
				
				
				h = "".join(i.xpath('.//span[@class="padr"]/text()'))
				a = "".join(i.xpath('.//span[@class="padl"]/text()'))
				sc = f"`{hos}-{aws}`"
				games.append(f"{h} {sc} {a}")
		if not games:
			return # Rip
		z = list(zip(dates,games))
		embeds = self.build_embeds(au,e,z,"Result")
		return embeds
		
	def parse_fixtures(self,url,au):
		url = f"{url}/fixtures"
		print("Fetching HTML from get_html")
		t,e = self.get_html(url)
		print("Performing x-path requests.")
		fxtb = t.xpath('.//div[@id="fs-fixtures"]//tbody/tr')
		now = datetime.datetime.now()
				
		dates = []
		games = []
		print("fx / POF / A ")
		if "team" in url:
			team = "".join(t.xpath('.//div[@class="team-name"]/text()')).strip()
			e.title = f"≡ Fixtures for {team}"
			print("fx / POF / B 1")
			for i in fxtb:
				d = "".join(i.xpath('.//td[contains(@class,"time") and not(contains(@class,"canceled"))]//text()'))
				# Skip header rows.
				if not d:
					continue
				d = datetime.datetime.strptime(d,"%d.%m. %H:%M")
				d = d.replace(year=now.year)
				d = datetime.datetime.strftime(d,"%a %d %b: %H:%M")
				dates.append(f"`{d}`")
				tv = i.xpath(".//span[contains(@class,'tv')]")
				if tv:
					tv = i.xpath("./@id")[0].split("_")[-1]
					tv = f" [`📺`](http://www.flashscore.com/match/{tv}/)"
				else:
					tv = ""
				op = "".join(i.xpath('.//span[@class="padr"]/text()')).strip()
				wh = "A"
				
				if team in op:
					op = "".join(i.xpath('.//span[@class="padl"]/text()'))
					wh = "H"
				games.append(f"`{wh}: {op}`{tv}")
		else:
			print("fx / POF / B 2 ")
			comp = "".join(t.xpath('.//div[@class="tournament-name"]/text()'))
			e.title = f"≡ Fixtures for {comp}"
			for i in fxtb:
				d = "".join(i.xpath('.//td[contains(@class,"time")]//text()'))
				# Skip header rows.
				if not d:
					continue
				d = datetime.datetime.strptime(d,"%d.%m. %H:%M")
				d = d.replace(year=now.year)
				d = datetime.datetime.strftime(d,"%a %d %b: %H:%M")
				tv = i.xpath(".//span[contains(@class,'tv')]")
				if tv:
					tv = i.xpath("./@id")[0].split("_")[-1]
					tv = f"[`📺`](http://www.flashscore.com/match/{tv}/)"
				else:
					tv = ""
				dates.append(f"`{d}`{tv}")
				h = "".join(i.xpath('.//span[@class="padr"]/text()'))
				a = "".join(i.xpath('.//span[@class="padl"]/text()'))
				games.append(f"`{h} v {a}`")
		print("fx / POF / C ")
		if not games:
			return # Rip
		z = list(zip(dates,games))
		embeds = self.build_embeds(au,e,z,"Fixture")
		return embeds
	
	def parse_bracket(self,bracket):
		if self.driver is None:
			self.spawn_chrome()
		self.driver.get(bracket)
		stitches = []
		totwid = 0
		xp = './/div[@class="viewport"]'
		
		# Generate our base image.
		canvas = Image.new('RGB',(0,0))
		initheight = 0
		runnum = 0

		lastrun = False
		while True:
			bkt = self.driver.find_element_by_xpath(xp)
			location = bkt.location
			size = bkt.size
			# Try to delete dem ugly arrows.
			try:
				self.driver.execute_script("document.getElementsByClassName('scroll-left playoff-scroll-button playoff-scroll-button-left')[0].style.display = 'none';")
			except WebDriverException as e:
				print(f"Error'd.\n {e}")
			im = Image.open(BytesIO(bkt.screenshot_as_png))
			left = location['x']
			top = location['y']
			right = location['x'] + size['width']
			bottom = location['y'] + size['height']
			im = im.crop((left, top, right, bottom))
			try:
				z = self.driver.find_element_by_link_text("scroll right »")
				z.click()
				time.sleep(1)
			except NoSuchElementException:
				lastrun = True
			
			if initheight == 0:
				initheight = size['height']
			# Create new base image and paste old, new.
			if canvas.size[0] == 0:
				newcanvas = Image.new('RGB',(size['width'],initheight))
			else:
				newcanvas = Image.new('RGB',(canvas.size[0] + 220,initheight))
			newcanvas.paste(canvas,(0,0))
			newcanvas.paste(im,(newcanvas.size[0] - size['width'],0,newcanvas.size[0] - size['width'] + im.size[0],0 + im.size[1]))
			canvas = newcanvas
			if lastrun:
				break
		output = BytesIO()
		canvas.save(output,"PNG")
		output.seek(0)
		df = discord.File(output,filename="bracket.png")
		return df
	
	def parse_scorers(self,url,au):
		t,e = self.get_html(url)
		now = datetime.datetime.now()
		
		if "team" in url:
			# For individual Team
			scorerdict = {}
			team = "".join(t.xpath('.//div[@class="team-name"]/text()'))
			e.title = f"≡ Top Scorers for {team}"
			players = t.xpath('.//table[contains(@class,"squad-table")]/tbody/tr')
			for i in players:
				p = "".join(i.xpath('.//td[contains(@class,"player-name")]/a/text()'))
				
				if not p:
					continue	
				g = "".join(i.xpath('.//td[5]/text()'))
				if g == "0" or not g:
					continue
				l = "".join(i.xpath('.//td[contains(@class,"player-name")]/a/@href'))
				if g in scorerdict.keys():
					scorerdict[g].append(f"[{' '.join(p.split(' ')[::-1])}](http://www.flashscore.com{l})")
				else:
					scorerdict.update({g:[f"[{' '.join(p.split(' ')[::-1])}](http://www.flashscore.com{l})"]})
			sclist = [[f"{k} : {i}" for i in v] for k,v in scorerdict.items()]
			sclist = [i for sublist in sclist for i in sublist]
			tmlist = [f"[{team}]({url})" for i in sclist]
		else:
			# For cross-league.
			sclist = []
			tmlist = []
			comp = "".join(t.xpath('.//div[@class="tournament-name"]/text()'))
			e.title = f"≡ Top Scorers for {comp}"
			# Re-scrape!
			self.driver.get(url)
			WebDriverWait(self.driver, 2)
			x = self.driver.find_element_by_link_text("Top Scorers")
			x.click()
			players = self.driver.find_element_by_id("table-type-10")
			t = players.get_attribute('innerHTML')
			tree = html.fromstring(t)
			players = tree.xpath('.//tbody/tr')
			for i in players:
				p = "".join(i.xpath('.//td[contains(@class,"player_name")]//a/text()'))
				p = ' '.join(p.split(' ')[::-1])
				if not p:
					continue
				pl = "".join(i.xpath('.//td[contains(@class,"player_name")]/span[contains(@class,"team_name_span")]/a/@onclick'))
				pl = pl.split("'")[1]
				pl = f"http://www.flashscore.com{pl}"
				g = "".join(i.xpath('.//td[contains(@class,"goals_for")]/text()'))
				if g == "0":
					continue
				tm = "".join(i.xpath('.//td[contains(@class,"team_name")]/span/a/text()'))
				tml = "".join(i.xpath('.//td[contains(@class,"team_name")]/span/a/@onclick'))
				tml = tml.split("\'")[1]
				tml = f"http://www.flashscore.com{tml}"
				sclist.append(f"{g} [{p}]({pl})")
				tmlist.append(f"[{tm}]({tml})")
		z = list(zip(sclist,tmlist))
		# Make Embeds.
		embeds = []
		p = [z[i:i+10] for i in range(0, len(z), 10)]
		pages = len(p)
		count = 1
		for i in p:
			j = "\n".join([j for j,k in i])
			k = "\n".join([k for j,k in i])
			e.add_field(name="Goals / Player",value=j,inline=True)
			e.add_field(name="Team",value=k,inline=True)
			iu = "http://pix.iemoji.com/twit33/0056.png"
			e.set_footer(text=f"Page {count} of {pages} ({au})",icon_url=iu)
			te = deepcopy(e)
			embeds.append(te)
			e.clear_fields()
			count += 1

		return embeds	

	async def paginate(self,ctx,pages):
		page = 0
		if not pages:
			return
		numpages = len(pages)
		m = await ctx.send(embed=pages[0])
		if numpages == 1:
			return
		await m.add_reaction("⏮")
		if numpages > 2:
			await m.add_reaction("⬅")
			await m.add_reaction("➡")
		await m.add_reaction("⏭")
		await m.add_reaction("⏏")
		def check(r,u):
			if r.message.id == m.id and u == ctx.author:
				e = str(r.emoji)
				return e.startswith(('⏮','⬅','➡','⏭','⏏'))
		while True:
			try:
				wf = "reaction_add"
				r = await self.bot.wait_for(wf,check=check,timeout=120)
			except asyncio.TimeoutError:
				try:
					await m.clear_reactions()
				except discord.Forbidden:
					pass
				break
			r = r[0]
			if r.emoji == "⏮": #first	
				page = 0
				try:
					await m.remove_reaction("⏮",ctx.author)
				except discord.Forbidden:
					pass
			if r.emoji == "⬅": #prev
				try:
					await m.remove_reaction("⬅",ctx.author)
				except discord.Forbidden:
					pass
				if page > 0:
					page = page - 1
			if r.emoji == "➡": #next
				try:
					await m.remove_reaction("➡",ctx.author)
				except discord.Forbidden:
					pass
				if page < numpages - 1:
					page = page + 1
			if r.emoji == "⏭": #last
				page = numpages - 1
				try:
					await m.remove_reaction("⏭",ctx.author)
				except discord.Forbidden:
					pass
			if r.emoji == "⏏": #eject
				return await m.delete()
			await m.edit(embed=pages[page])
		
	def build_embeds(self,au,e,z,type):
		embeds = []
		p = [z[i:i+10] for i in range(0, len(z), 10)]
		pages = len(p)
		count = 1
		for i in p:
			j = "\n".join([j for j,k in i])
			k = "\n".join([k for j,k in i])
			e.add_field(name="Date",value=j,inline=True)
			e.add_field(name=type,value=k,inline=True)
			iu = "http://pix.iemoji.com/twit33/0056.png"
			e.set_footer(text=f"Page {count} of {pages} ({au})",icon_url=iu)
			te = deepcopy(e)
			embeds.append(te)
			e.clear_fields()
			count += 1
		return embeds
	
	
	
def setup(bot):
	bot.add_cog(Fixtures(bot))