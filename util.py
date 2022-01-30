
from nextcord.ext import commands
import nextcord


client = commands.Bot(command_prefix='!', intents=nextcord.Intents.all())


def clean_code(content):
    if content.startswith("```") and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:])[:-3]
    else:
        return content