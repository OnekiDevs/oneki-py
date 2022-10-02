import discord
from discord import ui 
from typing import Union
import functools


def component(deco):
    def decorator(func):
        @deco
        @functools.wraps(func)
        async def callback_wrapper(self, interaction: discord.Interaction, component: Union[ui.Button, ui.Select]):
            args = (self, interaction, component)
            if self.name is not None and hasattr(self.translations, func.__name__):
                if translation := getattr(self.translations, func.__name__, None):
                    args = (*args, translation)
                
            await func(*args)
        
        return callback_wrapper
    
    return decorator
        
    
def button(**kwargs):
    return component(ui.button(**kwargs))


def select(**kwargs):
    return component(ui.select(**kwargs))
