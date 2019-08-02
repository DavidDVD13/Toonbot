from discord.ext.commands.cooldowns import BucketType
from discord.ext import commands
from lxml import html
import datetime
import asyncio
import discord
import random
import json

class Misc(commands.Cog):
	""" Miscellaneous things. """
	def __init__(self, bot):
		self.bot = bot
	
	
	@commands.command(hidden=True)
	async def itscominghome(self,ctx):
		""" Football's coming home """
		await ctx.send("No it's fucking not.")
	
	@commands.command(name="8ball",aliases=["8"])
	async def eightball(self,ctx):
		""" Magic Geordie 8ball """
		res = [ 
			# Affirmative
			"probably",
			"Aye",
			"aye mate",
			"wey aye.",
			"aye trust is pal.",
			"Deffo m8",
			"fuckin aye.",
			"fucking rights",
			"think so",
			"absofuckinlutely",
			# Negative
			"me pal says nar.",
			"divn't think so",
			"probs not like.",
			"nar pal soz",
			"fuck no",
			"deffo not.",
			"nar",
			"wey nar",
			"fuck off ya daftie",
			"absofuckinlutely not",
			
			# later
			"am not sure av just had a bucket",
			"al tel you later",
			"giz a minute to figure it out",
			"mebbe like",
			"dain't bet on it like"
		]
		await ctx.send(f":8ball: {ctx.author.mention} {random.choice(res)}")
	
	@commands.command()
	async def lenny(self,ctx):
		""" ( ͡° ͜ʖ ͡°) """
		lennys = ['( ͡° ͜ʖ ͡°)','(ᴗ ͜ʖ ᴗ)','(⟃ ͜ʖ ⟄) ','(͠≖ ͜ʖ͠≖)','ʕ ͡° ʖ̯ ͡°ʔ','( ͠° ͟ʖ ͡°)','( ͡~ ͜ʖ ͡°)','( ͡◉ ͜ʖ ͡◉)','( ͡° ͜V ͡°)','( ͡ᵔ ͜ʖ ͡ᵔ )',
		'(☭ ͜ʖ ☭)','( ° ͜ʖ °)','( ‾ ʖ̫ ‾)','( ͡° ʖ̯ ͡°)','( ͡° ل͜ ͡°)','( ͠° ͟ʖ ͠°)','( ͡o ͜ʖ ͡o)','( ͡☉ ͜ʖ ͡☉)','ʕ ͡° ͜ʖ ͡°ʔ','( ͡° ͜ʖ ͡ °)']
		await ctx.send(random.choice(lennys))
	
	@commands.command(aliases=["horo"],hidden=True)
	async def horoscope(self,ctx,*,sign):
		""" Find out your horoscope for this week """
		sign = sign.title()
		horos = {
			"Aquarius":"♒",
			"Aries":"♈",
			"Cancer":"♋",
			"Capricorn":"♑",
			"Gemini":"♊",
			"Leo":"♌",
			"Libra":"♎",
			"Scorpius":"♏",
			"Scorpio":"♏",
			"Sagittarius":"♐",
			"Pisces":"♓",
			"Taurus":"♉",
			"Virgo":"♍",
		}
		
		if sign not in horos:
			return
		
		# Get Sunday Just Gone.
		sun = datetime.datetime.now().date() - datetime.timedelta(days=datetime.datetime.now().weekday() + 1)
		# Get Saturday Coming
		sat = sun + datetime.timedelta(days=6)
		
		sunstring = sun.strftime('%a %d %B %Y')
		satstring = sat.strftime('%a %d %B %Y')
		
		e = discord.Embed()
		e.color = 0x7289DA
		e.description = "*\"The stars and planets will not affect your life in any way\"*"
		e.title = f"{horos[sign]} {sign}"
		ftstr = f"Horoscope for {sunstring} - {satstring}"
		e.set_footer(text=ftstr)
		await ctx.send(embed=e)
	
	@commands.command()
	async def poll(self,ctx,*,arg):
		""" Thumbs up / Thumbs Down """
		try:
			await ctx.message.delete()
		except:
			pass
		e = discord.Embed(color=0x7289DA)
		e.title = f"Poll"
		e.description = arg
		e.set_footer(text=f"Poll created by {ctx.author.name}")
		
		m = await ctx.send(embed=e)
		await m.add_reaction('👍')
		await m.add_reaction('👎')
		
	
	@commands.command(aliases=["rather"])
	async def wyr(self,ctx):
		""" Would you rather... """
		async def fetch():
			async with self.bot.session.get("http://www.rrrather.com/botapi") as resp:
				resp = await resp.json()
				return resp
		
		# Reduce dupes.
		cache = []
		tries = 0
		while tries < 20:
			resp = await fetch()
			# Skip stupid shit.
			if resp["choicea"] == resp["choiceb"]:
				continue
			if resp in cache:
				tries += 1
				continue
			else:
				cache += resp
				break
		
		async def write(resp):
			title = resp["title"].strip().capitalize().rstrip('.?,:')
			opta  = resp["choicea"].strip().capitalize().rstrip('.?,!').lstrip('.')
			optb  = resp["choiceb"].strip().capitalize().rstrip('.?,!').lstrip('.')
			mc = f"{ctx.author.mention} **{title}...** \n{opta} \n{optb}"
			return mc
			
		async def react(m):
			await m.add_reaction('🇦')
			await m.add_reaction('🇧')
			await m.add_reaction('🎲')
		
		m = await ctx.send(await write(resp))
		await react(m)
		
		# Reroller
		def check(reaction,user):
			if reaction.message.id == m.id and user == ctx.author:
				e = str(reaction.emoji)
				return e == '🎲'
		
		while True:
			try:
				rea = await self.bot.wait_for("reaction_add",check=check,timeout=120)
			except asyncio.TimeoutError:
				await m.remove_reaction('🎲',ctx.message.author)
				break
			rea = rea[0]
			if rea.emoji == '🎲':
				resp = await fetch()
				await m.clear_reactions()
				await m.edit(content=await write(resp))
				await react(m)
			
			
	@commands.command()
	@commands.is_owner()
	async def secrettory(self,ctx):
		await ctx.send(f"The secret tory is {random.choice(ctx.guild.members).mention}")
	
	# @commands.command(aliases=["games"])
	# async def roleme(self,ctx,*,game):
		# """ Give you the role for a game to allow players to @mention you for a game. """
		# games = ["haxball","cah"]
		# if game.lower in games:
			# grole = discord.utils.get(ctx.guild.roles, name=game)
			# if grole in ctx.author.roles:
				# await ctx.author.remove_roles(grole)
				# await ctx.send(f"{ctx.author.mention} has removed the {game} role.")
			# else:
				# await ctx.author.add_roles(grole,reason="Game role.")
				# await ctx.send(f"{ctx.author.mention} has added the {game} role.")
		# else:
			# await ctx.send("Invalid game specified, valid games are {', '.join(games)}}")
			
	@commands.command(aliases=["choice","pick","select"])
	async def choose(self,ctx,*,choices):
		""" Make a decision for me (seperate choices with commas)"""
		x = choices.split(",")
		if len(x) == 1:
			return
		await ctx.send(f"{ctx.author.mention}: {random.choice(x)}")
	
	@commands.command(hidden=True)
	@commands.bot_has_permissions(kick_members=True)
	@commands.cooldown(2,60,BucketType.user) 
	async def roulette(self,ctx):
		""" Russian Roulette """
		x = ["click.","click.","click.","click.","click.","🔫 BANG!"]
		outcome = random.choice(x)
		if outcome == "🔫 BANG!":
			await ctx.author.kick(reason="roulette")
			await ctx.send(f"🔫 BANG! {ctx.author.mention} was kicked.")
		else:
			await ctx.send(outcome)
			
	@commands.command(hidden=True,aliases=["flip","coinflip"])
	async def coin(self,ctx):
		""" Flip a coin """
		print(ctx.guild.name)
		await ctx.send(random.choice(["Heads","Tails"]))
	
	@commands.command(hidden=True)
	@commands.guild_only()
	async def kickme(self,ctx):
		""" Stop kicking yourself. """
		try:
			await ctx.author.kick(reason=f"Used {ctx.invoked_with}")
		except discord.Forbidden:
			await ctx.send("⛔ I can't kick you")
		except discord.HTTPException:
			await ctx.send('❔ Kicking failed.')
		else:
			await ctx.send(f"👢 {ctx.author.mention} kicked themself")

	@commands.command(hidden=True,aliases=["bamme"])
	@commands.guild_only()
	async def banme(self,ctx):
		""" Ban yourself. """
		try:
			await ctx.author.ban(reason="Used .banme",delete_message_days=0)
		except discord.Forbidden:
			await ctx.send("⛔ I can't ban you")
		except discord.HTTPException:
			await ctx.send("❔ Banning failed.")
		else:
			await ctx.send(f"☠ {ctx.author.mention} banned themself.")
	
	@commands.command(hidden=True)
	@commands.guild_only()
	async def triggered(self,ctx):
		""" WEEE WOO SPECIAL SNOWFLAKE DETECTED """
		trgmsg = await ctx.send("🚨 🇹 🇷 🇮 🇬 🇬 🇪 🇷  🇼 🇦 🇷 🇳 🇮 🇳 🇬  🚨")
		for i in range(5):
			await trgmsg.edit(content="⚠ 🇹 🇷 🇮 🇬 🇬 🇪 🇷  🇼 🇦 🇷 🇳 🇮 🇳 🇬  ⚠")
			await asyncio.sleep(1)
			await trgmsg.edit(content="🚨 🇹 🇷 🇮 🇬 🇬 🇪 🇷  🇼 🇦 🇷 🇳 🇮 🇳 🇬  🚨")
			await asyncio.sleep(1)
	
	@commands.command(hidden=True)
	@commands.guild_only()
	@commands.has_permissions(add_reactions=True)
	async def uprafa(self,ctx):
		""" Adds an upvote reaction to the last 10 messages """
		async for message in ctx.channel.history(limit=10):
			await message.add_reaction(":upvote:332196220460072970")
	
	@commands.command(hidden=True)
	@commands.guild_only()
	@commands.has_permissions(add_reactions=True)
	async def downrafa(self,ctx):
		""" Adds a downvote reaction to the last 10 messages """
		async for message in ctx.channel.history(limit=10):
			await message.add_reaction(":downvote:332196251959427073")
	
	@commands.command(hidden=True)
	@commands.has_permissions(manage_messages=True)
	@commands.guild_only()
	async def norafa(self,ctx,*,msgs=30):
		""" Remove reactions from last x messages """
		async for message in ctx.channel.history(limit=msgs):
			await message.clear_reactions()
			
	@commands.command(aliases=["ttj"],hidden=True)
	async def thatsthejoke(self,ctx):
		""" MENDOZAAAAAAAAAAAAA """
		await ctx.send("https://www.youtube.com/watch?v=xECUrlnXCqk")

	@commands.command(aliases=["alreadydead"],hidden=True)
	async def dead(self,ctx):
		""" STOP STOP HE'S ALREADY DEAD """
		await ctx.send("https://www.youtube.com/watch?v=mAUY1J8KizU")
		
	@commands.command(pass_context=True,aliases=["urbandictionary"])
	async def ud(self,ctx,*,lookup):
		""" Lookup a definition from urban dictionary """
		await ctx.trigger_typing()
		url = f"http://api.urbandictionary.com/v0/define?term={lookup}"
		async with self.bot.session.get(url) as resp:
			if resp.status != 200:
				await ctx.send(f"🚫 HTTP Error, code: {resp.status}")
				return
			json = await resp.json()
		
		tn = ("http://d2gatte9o95jao.cloudfront.net/assets/"
			  "apple-touch-icon-2f29e978facd8324960a335075aa9aa3.png")
	
		embeds = []

		deflist = json["list"]
		# Populate Embed, add to list
		count = 1
		if deflist:
			for i in deflist:
				e = discord.Embed(color=0xFE3511)
				auth = f"Urban Dictionary"
				e.set_author(name=auth)
				e.set_thumbnail(url=tn)
				e.title=i["word"]
				e.url=i["permalink"]
				e.description = i["definition"]
				e.description = e.description[:2047]
				if i["example"]:
					e.add_field(name="Example",value=i["example"])
				un = ctx.author.display_name
				ic = "http://pix.iemoji.com/twit33/0056.png"
				footertext = (f"Page {count} of {len(deflist)} ({un}) |"
							  f"👍🏻{i['thumbs_up']} 👎🏻{i['thumbs_down']}")
				e.set_footer(icon_url=ic,text=footertext)
				embeds.append(e)
				count += 1
		else:
				e = discord.Embed(color=0xFE3511)
				e.description = f"🚫 No results found for {lookup}."
				embeds.append(e)
		
		# Paginator
		page = 0
		m = await ctx.send(embed=embeds[page])
		
		# Add reactions
		if len(embeds) > 1:
			if len(embeds) > 2: 
				await m.add_reaction("⏮")#first
			await m.add_reaction("◀") #prev
			await m.add_reaction("▶") #next
			if len(embeds) > 2: 
				await m.add_reaction("⏭") #last
		def check(reaction,user):
			if reaction.message.id == m.id and user == ctx.author:
				e = str(reaction.emoji)
				return e.startswith(('⏮','◀','▶','⏭'))
		while not self.bot.is_closed():
			try:
				wf = "reaction_add"
				res = await self.bot.wait_for(wf,check=check,timeout=120)
			except asyncio.TimeoutError:
				await m.clear_reactions()
				break
			res = res[0]
			if res.emoji == "⏮": #first
				page = 0
				await m.remove_reaction("⏮",ctx.author)
			if res.emoji == "◀": #prev
				if page > 0:
					page += -1
				await m.remove_reaction("◀",ctx.author)
			if res.emoji == "▶": #next	
				if page < len(embeds) - 1:
					page += 1
				await m.remove_reaction("▶",ctx.author)
			if res.emoji == "⏭": #last
				page = len(embeds) - 1
				await m.remove_reaction("⏭",ctx.author)
			if res.emoji == "⏏": #eject:
				await m.clear_reactions()
				await m.delete()
			await m.edit(embed=embeds[page])
			
	@commands.command(hidden=True)
	@commands.is_owner()
	async def ircle(self,ctx):
		""" Generate Shitposts of the week """
		await ctx.trigger_typing()
		url = "https://www.reddit.com/r/nufcirclejerk/top/?sort=top&t=week"
		async with self.bot.session.get(url) as resp:
			if resp.status != 200:
				await ctx.send(f"{resp.status} error accessing top posts.")
				return
			posts = html.fromstring(await resp.text())
			posts = posts.xpath('.//div[contains(@class, "thing")]')
			table = [("\💩 r/nufcirclejerk Shitposts of the week roundup."
					 "\n\n Score | Link | Direct | Author \n--|--|--|--|")]
			for i in posts:
				title = i.xpath(".//a[contains(@class, 'title')]/text()")
				x = (".//ul[@class='flat-list buttons']/"
					"li[@class='first']//@href")
				comme = i.xpath(x)
				link  = i.xpath(".//a[contains(@class, 'title')]/@href")
				authn = i.xpath(".//a[contains(@class, 'author')]/text()")
				if len(authn) == 0:
					authn = "[Deleted]"
				else:
					authn = "u/{}".format(authn[0])
				score = i.xpath(".//div[@class='score unvoted']/text()")
				sc = score[0]
				t = title[0]
				c = comme[0]
				l = link[0]
				table.append(f"{sc}|[{t}]({c}) | [Direct]({l}) | {authn}")
			table = "\n".join(table)
			await ctx.send(table[:2000])
			await ctx.send(table[2001:4000])
			
	@commands.command(hidden=True)
	async def emojitext(self,ctx,*,string):
		""" Convert message to emojis """
		await ctx.trigger_typing()
		await ctx.message.delete()
		
		string = "".join([f":regional_indicator_{i.lower()}:" if i.isalpha()
						else f"{i}⃣" if i.isdigit() else i for i in string])
		await ctx.send(string)	
		
def setup(bot):
    bot.add_cog(Misc(bot))