import discord
from discord import ui 
from ..context import Context
from ..translations import Translation
from typing import Optional, Union
import dexui

import sys
import traceback


class View(dexui.View):
    TIMEOUT = 320
    name: Optional[str] = None
    
    def __init__(self, **kwargs):
        name = kwargs.pop("name", self.name)
        timeout = kwargs.pop("timeout", self.TIMEOUT)
        super().__init__(timeout=timeout, **kwargs)
        
        self.name = name
        self.translations: Optional[Translation] = None
        
    async def _get_translations(self, origin: Union[Context, discord.abc.Messageable, discord.Interaction]) -> Translation:
        if self.name is not None:
            if isinstance(origin, discord.Interaction):
                return origin.client.translations.view(origin.locale.value, self.name)
            elif isinstance(origin, Context):
                return origin.bot.translations.view(origin.lang, self.name)
            else:
                ch = await origin._get_channel()
                client = origin._state._get_client()
                return client.translations.view(ch.guild.preferred_locale.value, self.name)
            
    async def start(self, origin: Union[discord.abc.Messageable, discord.Interaction], **kwargs):
        self.translations = await self._get_translations(origin)
        return await super().start(origin, **kwargs)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.user_check:
            check = interaction.user == self.author
            if not check:
                translation = interaction.client.translations.view(interaction.locale.value, "generic")
                await interaction.response.send_message(translation.user_check.format(interaction.client.bot_emojis["enojao"]), ephemeral=True) 

            return check
        
        return True
    
    async def on_error(self, interaction: discord.Interaction, error: Exception, item) -> None:
        from .report_bug import ReportBug
        view = ReportBug(error=error)
        await view.start(interaction)
        
        print(f"In view {self} for item {item}:", file=sys.stderr)
        traceback.print_tb(error.__traceback__)
        print(f"{error.__class__.__name__}: {error}", file=sys.stderr)


class ExitableView(dexui.ExitableView, View):
    def __init__(self, **kwargs):
        super(dexui.ExitableView, self).__init__(**kwargs)


class CancellableView(dexui.CancellableView, View):
    def __init__(self, **kwargs):
        super(dexui.CancellableView, self).__init__(**kwargs)
