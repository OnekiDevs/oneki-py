import traceback
import aiohttp
import sys

import utils
from utils import translations, context, db, env
from typing import Union

description = """
Hola!, soy Oneki un bot multitareas y estare muy feliz en ayudarte en los que necesites :D
"""

initial_extensions = (
    "cogs.user",
)

private_extensions = (
    # "cogs.clubs",
    "cogs.makeover_event",
)

def _prefix_callable(bot, msg):
    user_id = bot.user.id
    base = [f'<@!{user_id}> ', f'<@{user_id}> ']
    if msg.guild is None:
        base.append('?')
        base.append('>')
    else:
        base.extend(bot.get_raw_guild_prefixes(msg.guild.id))
    
    return base


class OnekiBot(utils.commands.AutoShardedBot):
    def __init__(self):
        allowed_mentions = utils.discord.AllowedMentions(roles=False, everyone=False, users=True)
        intents = utils.discord.Intents(
            guilds=True,
            members=True,
            presences=True,
            voice_states=True,
            messages=True,
            message_content=True,
            bans=True
        )
        
        super().__init__(
            command_prefix=_prefix_callable,
            description=description,
            allowed_mentions=allowed_mentions,
            intents=intents,
        )
        
        self.db = db.async_client()

    async def _get_guild_settings(self):
        # guild_id: list
        prefixes = {}
        
        collection_ref = self.db.collection("guilds")
        async for doc_ref in collection_ref.list_documents():
            doc = await doc_ref.get()
            if doc.exists: 
                data = doc.to_dict()
                if data.get("prefixes") is not None:
                    prefixes[doc.id] = data.get("prefixes")
        
        return prefixes

    async def _get_blacklist(self):
        # {users: {id, ...}, guilds: {id, ...}}
        blacklist = {"users": set(), "guilds": set()}

        guilds_doc = await self.db.document("blacklist/guilds").get()
        if guilds_doc.exists:
            blacklist["guilds"] = guilds_doc.to_dict().keys()
            
        users_doc = await self.db.document("blacklist/users").get()
        if users_doc.exists:
            blacklist["users"] = set(users_doc.to_dict().keys())
        
        return blacklist

    def get_guild_prefixes(self, guild, *, local_inject=_prefix_callable):
        proxy_msg = utils.discord.Object(id=0)
        proxy_msg.guild = guild
        return local_inject(self, proxy_msg)

    def get_raw_guild_prefixes(self, guild_id):
        return self.prefixes.get(str(guild_id), ['?', '>'])

    def get_guild_lang(self, guild):
        return guild.preferred_locale.value.split("-")[0]

    async def add_to_blacklist(self, object, *, reason=None):
        doc_ref = self.db.document(f"blacklist/{'guilds' if isinstance(object, utils.discord.Guild) else 'users'}")
        await doc_ref.set({str(object.id): reason})
        
        self.blacklist['guilds' if isinstance(object, utils.discord.Guild) else 'users'].add(str(object.id))

    async def remove_from_blacklist(self, object):
        doc_ref = self.db.document(f"blacklist/{'guilds' if isinstance(object, utils.discord.Guild) else 'users'}")
        blacklist = self.blacklist['guilds' if isinstance(object, utils.discord.Guild) else 'users']
        if not str(object.id) in blacklist:
            raise Exception(f"{object.id} not in blacklist")

        await doc_ref.delete(str(object.id))
        blacklist.remove(str(object.id))

    def in_blacklist(self, object):
        if isinstance(object, utils.discord.Guild):
            return True if object.id in self.blacklist['guilds'] else False
        return True if object.id in self.blacklist['users'] else False

    async def load_extensions(self, extensions):
        for ext in extensions:
            try:
                await self.load_extension(ext)
            except Exception as e:
                print(f'Failed to load extension {ext}.', file=sys.stderr)
                traceback.print_exc()

    async def setup_hook(self) -> None:
        self.session = aiohttp.ClientSession(loop=self.loop)
        
        # prefixes[guild_id]: list
        self.prefixes = await self._get_guild_settings()

        # user_id mapped to True
        # these are users globally blacklisted
        self.blacklist = await self._get_blacklist()
            
        self.translations = translations.Translations.load()
        
        # cogs unload
        await self.load_extensions(initial_extensions)
        
        if env.PRIVATE_EXTENSIONS:
            print("[*] Private extensions unload")
            await self.load_extensions(private_extensions)
                
    async def on_ready(self):
        await self.tree.sync()
        activity = utils.discord.Activity(type=utils.discord.ActivityType.watching, name=f"{len(self.guilds)} servidores")
        await self.change_presence(status=utils.discord.Status.idle, activity=activity)

        print(f'[+] Ready: {self.user} (ID: {self.user.id})')

    async def on_command_error(self, ctx, error):
        if isinstance(error, utils.commands.errors.CommandNotFound): 
            pass
        else: 
            # Error message
            msg = "".join(traceback.format_exception(type(error), error, error.__traceback__))

            # Embed
            embed = utils.discord.Embed(color=utils.discord.Colour.blue(), timestamp=utils.datetime.datetime.utcnow())
            embed.set_author(name="Error", url=f"{ctx.message.jump_url}")
            embed.add_field(name="Type:", value=f"```{type(error)}```", inline = False)
            embed.add_field(name="Message:", value=f"```{ctx.message.content}```")
            embed.add_field(name="Detail:", value=f"```{error}```", inline = False)

            # Send message
            channel = self.get_channel(885674115615301651)
            print('Ignoring exception in command {}:'.format(ctx.command))
            traceback.print_exception(type(error), error, error.__traceback__)
            
            await channel.send(f"**Context:**\n```py\n{msg}\n```", embed=embed)
            await ctx.send(error)

    async def get_context(
        self, 
        origin: Union[utils.discord.Message, utils.discord.Interaction], 
        *, 
        cls=context.Context
    ):
        return await super().get_context(origin, cls=cls)

    async def process_commands(self, message):
        ctx = await self.get_context(message)

        if message.author.bot:
            return

        if self.in_blacklist(ctx.author) or self.in_blacklist(ctx.guild):
            return

        await self.invoke(ctx)

    async def on_message(self, message):
        if message.author.bot:
            return

        # Si pingearon al bot
        if message.content in [f'<@!{self.user.id}>', f'<@{self.user.id}>']:
            translation = self.translations.event(self.get_guild_lang(message.guild), "ping")
            prefixes = self.get_raw_guild_prefixes(message.guild.id)
            if len(prefixes) == 1:
                await message.channel.send(translation.one.format(prefixes[0]))
            else:
                p = ", ".join([prefix for prefix in prefixes])
                await message.channel.send(translation.more.format(p))

        await self.process_commands(message)

    async def close(self):
        await super().close()
        await self.session.close()
        print("goodbye!")

    def run(self):
        token = env.DISCORD_DEV_TOKEN or env.DISCORD_TOKEN
        super().run(token, reconnect=True)
