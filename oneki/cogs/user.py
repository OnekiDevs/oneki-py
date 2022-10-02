import utils
from utils import ui
from utils.context import Context

import os
from PIL import Image
from typing import Optional, Union


class AvatarEmbed(utils.discord.Embed):
    def __init__(self, user: Union[utils.discord.Member, utils.discord.User], avatar: utils.discord.Asset, author: utils.discord.Member, translation):
        super().__init__(color=user.color, timestamp=utils.utcnow())
        self.set_author(name=translation.embed.author.format(user), url=avatar.url)
        self.set_image(url=avatar.url)
        self.set_footer(text=translation.embed.footer.format(author.name), icon_url=author.avatar.url)


class MemberInfoEmbed(utils.discord.Embed):
    def __init__(self, member: utils.discord.Member, author: utils.discord.Member, translation):
        roles = "".join([
            role.mention for role in member.roles 
            if role != member.guild.default_role
        ])
        
        super().__init__(
            title=translation.embed.title,
            description=roles,
            color=member.color,
            timestamp=utils.utcnow() 
        )
        self.set_author(name=f"{member}", url=member.avatar.url)
        self.set_thumbnail(url=member.avatar.url)
        
        if member.activity is not None: 
            activity = member.activity if isinstance(member.activity, utils.discord.CustomActivity) else member.activity.name
            self.add_field(name=translation.embed.fields[0], value=f"```{activity}```", inline=False)
    
        self.add_field(name=translation.embed.fields[1], value=utils.discord.utils.format_dt(member.created_at, "F"))
        self.add_field(name=translation.embed.fields[2], value=utils.discord.utils.format_dt(member.joined_at, "F"))
        self.add_field(name=translation.embed.fields[3], value=f"```{member.color}```")
        self.add_field(name=translation.embed.fields[4], value=f"```{member.id}```")
        self.add_field(name=translation.embed.fields[5], value=f"```{member.raw_status}```")
        
        self.set_footer(text=translation.embed.footer.format(author.name), icon_url=author.avatar.url)


class Avatar(ui.ExitableView):
    name = "avatar"
    
    def __init__(self, **kwargs):
        member = kwargs.pop("member")
        super().__init__(**kwargs)
        self.member: utils.discord.Member = member
        self._avatar: utils.discord.Asset = member.display_avatar

    def get_embed(self, *args) -> Optional[utils.discord.Embed]:
        return AvatarEmbed(self.member, self._avatar, self.author, self.translations)
    
    def update_components(self, *args):
        if self.member.guild_avatar is not None:
            pass
        else:
            self.clear_items()
            self.stop()

    @ui.button(label="User Avatar", emoji="🖼️", style=utils.discord.ButtonStyle.primary)
    async def avatar(self, interaction: utils.discord.Interaction, button: utils.discord.ui.Button, translation):
        if self._avatar == self.member.guild_avatar:
            button.label = "Guild Avatar"
            self._avatar = self.member.avatar
        else:
            button.label = "User Avatar"
            self._avatar = self.member.guild_avatar
        
        await self.update(interaction)


class Profile(ui.ExitableView):
    name = "profile"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.member: utils.discord.Member = None
        self.user: utils.discord.User = None
        self.user_banner = None
    
    async def init(self, *, member: utils.discord.Member):
        self.member = member
        self.user = await self.client.fetch_user(self.member.id)
    
    async def get_embed(self, *args) -> utils.discord.Embed:
        if self.user.banner is not None:
            self.user_banner = self.user.banner.url
        else:
            path = f"resource/img/default_banner_{self.user.id}.png"
            Image.new("RGB", (600, 240), self.user.colour.to_rgb()).save(path)
            
            with open(path, "rb") as f:
                self.user_banner = await utils.send_file_and_get_url(self.ctx.bot, utils.discord.File(fp=f))
            
            os.remove(path)
        
        embed = utils.discord.Embed(colour=self.user.color, timestamp=utils.utcnow())
        embed.set_author(name=self.translations.embed.author.format(self.user))
        embed.set_image(url=self.user_banner)
        embed.set_footer(text=self.translations.embed.footer.format(self.author.name), icon_url=self.author.avatar.url)
        return embed
    
    @ui.change_color_when_used
    @ui.button(label="Avatar", style=utils.discord.ButtonStyle.secondary)
    async def avatar(self, interaction: utils.discord.Interaction, button: utils.discord.ui.Button, translation):
        embed = AvatarEmbed(self.user, self.user.avatar, interaction.user, translation)
        await interaction.response.edit_message(embed=embed, view=self)
        
    @ui.change_color_when_used
    @ui.button(label="Banner", emoji="🖼️", style=utils.discord.ButtonStyle.secondary)
    async def banner(self, interaction: utils.discord.Interaction, button: utils.discord.ui.Button, translation):
        embed = utils.discord.Embed(colour=self.member.color, timestamp=utils.utcnow())
        embed.set_author(name=translation.embed.author.format(self.member), url=self.user_banner)
        embed.set_image(url=self.user_banner)
        embed.set_footer(text=translation.embed.footer.format(interaction.user.name), icon_url=interaction.user.avatar.url)

        await interaction.response.edit_message(embed=embed, view=self)
        
    @ui.change_color_when_used
    @ui.button(label="Member Information", emoji="📑", style=utils.discord.ButtonStyle.secondary)
    async def information(self, interaction: utils.discord.Interaction, button: utils.discord.ui.Button, translation):
        embed = MemberInfoEmbed(self.member, self.author, translation)
        await interaction.response.edit_message(embed=embed, view=self)
        
        
class User(utils.Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self.afks = {}
        
    async def cog_load(self):
        self.afks = await self._get_afks()
        
    async def _get_afks(self):
        # user_id: dict(reason, time)
        afks = {}

        doc = await self.bot.db.document("users/afks").get()
        if doc.exists:
            for key, value in doc.to_dict().items():
                afks[key] = value
        
        return afks
    
    @utils.commands.hybrid_command()
    async def profile(self, ctx: Context, member: Optional[utils.discord.Member] = None):
        member = member or ctx.author
        await Profile(member=member).start(ctx)
    
    @utils.commands.hybrid_command()
    async def avatar(self, ctx: Context, member: Optional[utils.discord.Member] = None):
        member = member or ctx.author
        await Avatar(member=member).start(ctx)
    
    @utils.commands.hybrid_command()
    async def info(self, ctx: Context, member: Optional[utils.discord.Member] = None): 
        member = member or ctx.author
        await ctx.send(embed=MemberInfoEmbed(member, ctx.author, ctx.translation))
    
    # afk

    async def add_to_afk(self, user_id, *, reason):
        data = {"reason": reason, "time": utils.utcnow()}
        self.afks[str(user_id)] = data
        
        doc_ref = self.bot.db.document("users/afks")
        doc = await doc_ref.get()
        if doc.exists:
            await doc_ref.update({str(user_id): data})
        else:
            await doc_ref.set(self.afks)

    async def remove_from_afk(self, user_id):
        self.afks.pop(str(user_id))
        
        doc_ref = self.bot.db.document("users/afks")
        await doc_ref.delete(str(user_id))

    @utils.commands.hybrid_command()
    async def afk(self, ctx: Context, *, reason=None):
        member = ctx.author
        if str(member.id) in self.afks:
            translation = self.translations.event(ctx.lang, "afk")

            await self.remove_from_afk(member.id)
            try:
                await member.edit(nick=member.display_name.replace("[AFK] ", ""))
            except: pass
            
            embed = utils.discord.Embed(title=translation.no_longer_afk.format(member.display_name), color=0xFCE64C)
            return await ctx.send(embed=embed)
            
        reason = reason or ctx.translation.no_reason
        if len(reason) > 50: 
            return await ctx.send(ctx.translation.too_long)
        
        if utils.check_links(reason): 
            return await ctx.send(ctx.translation.no_links)

        await self.add_to_afk(member.id, reason=reason)
        embed = utils.discord.Embed(title=ctx.translation.embed.title.format(member.display_name), color=0x383FFF)
        if len(member.display_name) >= 27: 
            ctx.send(ctx.translation.max_name_length.format(member.mention))
        else: 
            try:
                await member.edit(nick=f"[AFK] {member.display_name}")
            except utils.discord.errors.Forbidden:
                await ctx.send(ctx.translation.no_permissions)
                
        await ctx.send(embed=embed)
    
    @utils.Cog.listener()
    async def on_message(self, message: utils.discord.Message):
        # if the user is afk
        if str(message.author.id) in self.afks:
            ctx = await self.bot.get_context(message)
            if ctx.valid and ctx.command == self.bot.get_command("afk"): 
                return 
            
            member = message.author
            translation = self.translations.event(self.bot.get_guild_lang(message.guild), "afk")

            await self.remove_from_afk(member.id)
            try:
                await member.edit(nick=member.display_name.replace("[AFK] ", ""))
            except: pass
            
            embed = utils.discord.Embed(title=translation.no_longer_afk.format(member.display_name), color=0xFCE64C)
            await message.channel.send(embed=embed, delete_after=10.0)

        # is there a mention of an afk user?
        if message.mentions:
            translation = self.translations.event(self.bot.get_guild_lang(message.guild), "afk")
            for user in message.mentions:
                if str(user.id) in self.afks:
                    data = self.afks[str(user.id)]
                    embed = utils.discord.Embed(
                        title=translation.embed.title.format(user.display_name),
                        description=translation.embed.reason.format(data["reason"]),
                        timestamp=data["time"],
                        color=0xFCE64C
                    )
                    await message.channel.send(embed=embed, delete_after=15.0)
        
        
async def setup(bot):
    await bot.add_cog(User(bot))
        