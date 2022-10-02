import discord
from . import View, decorators, disable_after_pressed
from typing import Any, Optional


class Confirm(View):
    def __init__(self, content: Optional[str] = None, embed: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.value = None
        
        if content is not None:
            self.get_content = lambda *_: content
        
        if embed is not None:
            self.get_embed = lambda *_: embed

    async def start(self, interaction: Optional[discord.Interaction] = None, *, ephemeral=False):
        await super().start(interaction, ephemeral=ephemeral)
        return await self.wait()

    @decorators.button(label="Confirm", style=discord.ButtonStyle.red)
    @disable_after_pressed
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button, _):
        await interaction.response.send_message("Confirming", ephemeral=True)
        self.value = True

    @decorators.button(label="Cancel", style=discord.ButtonStyle.grey)
    @disable_after_pressed
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button, _):
        await interaction.response.send_message("Cancelling", ephemeral=True)
        self.value = False

