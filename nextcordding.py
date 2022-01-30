import datetime
from traceback import format_exception

from nextcord import Interaction, SlashOption, ChannelType
from nextcord.abc import GuildChannel
from nextcord.ext import commands
import nextcord
import asyncio
import contextlib
import io
import json
import textwrap
from util import clean_code

client = commands.Bot(command_prefix='!', intents=nextcord.Intents.all())

@client.event
async def on_ready():
    print('Pronto.')
    #guild = client.get_guild(823744695296852018)
    #channel_aju = guild.get_channel(928740867626393610)


class Fechar(nextcord.ui.View):
    def __init__(self):
        super().__init__() 
        self.value = None

    @nextcord.ui.button(label = 'Fechar', style=nextcord.ButtonStyle.red)
    async def fechar(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        thread = interaction.channel
        await thread.edit(archived=True)
    

 
class Sim_nao(nextcord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None
    
    @nextcord.ui.button(label = 'Sim', style=nextcord.ButtonStyle.green)
    async def sim(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        
        guild = client.get_guild(823744695296852018)
        channel_aju = guild.get_channel(928740867626393610)

        thread_created = await channel_aju.create_thread(name=f"Ajuda a ({interaction.user.name}#{interaction.user.discriminator})", message=None, type=nextcord.ChannelType.public_thread)
        embed = nextcord.Embed(title=f'Alguém precisa de ajuda em {Fisica_quimica().value}!', description='Muito bem, agora que estamos todos aqui para ajudar, com que precisas de ajuda?')
        await thread_created.add_user(interaction.user)
        await thread_created.send(embed=embed, view=Fechar())
        self.value = True


    @nextcord.ui.button(label = 'Não', style=nextcord.ButtonStyle.red)
    async def nao(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_message(content='Cancelado.', ephemeral=True)
        self.stop()

class Fisica_quimica(nextcord.ui.View):
  def __init__(self):
    super().__init__()
    self.value = None


  @nextcord.ui.button(label = 'Física', style=nextcord.ButtonStyle.green)
  async def fisica(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
    await interaction.response.send_message('De certeza que queres criar um subcanal de ajuda de física?', view=Sim_nao() , ephemeral=True)
    self.value = 'Física'
    

  @nextcord.ui.button(label='Química', style=nextcord.ButtonStyle.red)
  async def quimica(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
    await interaction.response.send_message('De certeza que queres criar um subcanal de ajuda de química?', view=Sim_nao(), ephemeral=True)
    self.value = 'Química'





@client.slash_command(guild_ids=[823744695296852018])
async def silenciar(
    interaction=Interaction,
    membro: nextcord.Member = SlashOption(name="membro", description="Qual membro?", required=True),
    tempo: int = SlashOption(name="tempo", description="Por quanto tempo?(segundos)", required=False, default='Não especificado.'),
    razao: str = SlashOption(name="razão", description="Razão?", required=False, default="Razão não dada.")
    ):

        guild = client.get_guild(823744695296852018)
        owner = guild.get_role(824766184389083226)
        if owner in interaction.user.roles:
    


            muted = guild.get_role(929867420754141184)
            await membro.edit(roles=[muted])
            aprendizes = guild.get_role(929867352068202526)
            await membro.add_roles(muted)
            time = tempo
            if type(tempo)==int:
                tempo = str(tempo)+' segundos.'




            await membro.send(
                    
                embed=nextcord.Embed(
                    title="Foste silenciado!",
                    color=nextcord.Color.dark_red()
                    ).add_field(
                        name="**Info:**",
                        value=f"""
                        \n**Silenciado no server**:\n {guild.name} ({guild.id})
                        \n**Por**:\n {tempo}
                        \n**Responsável**:\n {interaction.user.mention} ({interaction.user.id})
                                """,
                        inline = False
                        
                        ).add_field(

                            name="\n**Reason:**",
                            value=f"{razao}",
                            inline = False

                        )

                )
            await interaction.channel.send(embed=nextcord.Embed(
                title="Silenciado!",
                color=nextcord.Color.green(),
                
                ).add_field(
                    name="**Info:**",
                    value=f"""
                    \n**Silenciado**:\n {membro.mention} ({membro.id})
                    \n**Por**:\n {tempo}
                    \n**Responsável**:\n {interaction.user.mention} ({interaction.user.id})
                    """,
                    inline=False
                ).add_field(
                    name="**Razão:**",
                    value=f"{razao}",
                    inline=False
                )
            )

            if tempo != 'Não especificado.':
                await asyncio.sleep(time)
                await membro.edit(roles=[aprendizes])
        else:
            await interaction.channel.send(f'Não tens permissões para usar este comando {interaction.user.mention}.')


@client.command(name='eval', aliases=['exec'])
async def _eval(ctx, *, code):
    """
    Permite a execução de código simples em python
    Chamar `input()` ou outras funções/bibliotecas que necessitem
    de interação com o usuário não funciona.

    """
    code = clean_code(code)
    if 'exit()' in code or 'quit()' in code:
        await ctx.send('```Traceback(most recent call last):\n  Não estás autorizado a executar o código.\n```')
        return
    if 'while' in code:
        await ctx.send('🛑⚠ Não tens autorização para utilizares `while` loops dentro deste comando.')
        return

    local_variables = {
        'nextcord': nextcord,
        'commands': commands,
        'bot': client,
        'ctx': ctx,
        'channel': ctx.channel,
        'author': ctx.author,
        'guild': ctx.guild,
        'message': ctx.message
    }

    stdout = io.StringIO()

    try:
        with contextlib.redirect_stdout(stdout):
            exec(
                f'async def func():\n{textwrap.indent(code, "    " )}', local_variables
            )

            obj = await local_variables['func']()
            result = f'{stdout.getvalue()}\n-- {obj}\n'
    except Exception as e:
        result = "".join(format_exception(e, e, e.__traceback__))

    await ctx.send(f'```py\n{result}\n```')



from nextcord import Embed
from nextcord.ext import commands, menus


class MyEmbedFieldPageSource(menus.ListPageSource):
    def __init__(self, data):
        super().__init__(data, per_page=2)

    async def format_page(self, menu, entries):
        embed = Embed(title="Entries")
        for entry in entries:
            embed.add_field(name=entry[0], value=entry[1], inline=True)
        embed.set_footer(text=f'Página {menu.current_page + 1}/{self.get_max_pages()}')
        return embed


@client.command()
async def reaction_embed_field(ctx):

    data = [
        ("Black", "#000000"),
        ("Blue", "#0000FF"),
        ("Brown", "#A52A2A"),
        ("Green", "#00FF00"),
        ("Grey", "#808080"),
        ("Orange", "#FFA500"),
        ("Pink", "#FFC0CB"),
        ("Purple", "#800080"),
        ("Red", "#FF0000"),
        ("White", "#FFFFFF"),
        ("Yellow", "#FFFF00"),
    ]
    pages = menus.MenuPages(
        source=MyEmbedFieldPageSource(data),
        clear_reactions_after=True,
    )
    await pages.start(ctx)


class MyEmbedDescriptionPageSource(menus.ListPageSource):
    def __init__(self, data):
        super().__init__(data, per_page=6)

    async def format_page(self, menu, entries):
        embed = Embed(title="Entries", description="\n".join(entries))
        embed.set_footer(text=f'Page {menu.current_page + 1}/{self.get_max_pages()}')
        return embed


@client.command()
async def button_embed_description(ctx):
    data = [f'Description for entry #{num}' for num in range(1, 51)]
    pages = menus.ButtonMenuPages(
        source=MyEmbedDescriptionPageSource(data),
        clear_buttons_after=True,
    )
    await pages.start(ctx)



@client.event
async def on_message(msg):
    await client.process_commands(msg)
    channel = msg.channel
    guild = msg.guild
    membro = msg.author
    texto = msg.content
    if 'nitro' in texto:
        await msg.delete()
        with open('warns.json') as json_file:
            data = json.load(json_file)
            for x in data:
                if x['membro_id'] == membro.id:
                    x['conta'] += 1
                    x['moderador_id'].append(825196564061749248)
                    x['razao'].append('Utilização da palavra `nitro` sem qualquer tipo de contexto\n(Possível scam)')
                    if x['conta'] == 3:
                        razoes = ''
                        for r in list(dict.fromkeys(x['razao'])):
                            razoes += f'**{x["razao"].index(r) + 1}.** ' + r + '\n'
                        await membro.edit(timeout=nextcord.utils.utcnow() + datetime.timedelta(days=3))
                        await channel.send(embed=nextcord.Embed(title=f'**{membro.name}#{membro.discriminator}** silenciado', description=f'**Razões:**\n {razoes}Hoje às **{str(nextcord.utils.utcnow())[11:16]}   Duração** __3 dias__.', color=nextcord.Color.red()).set_thumbnail(url=membro.default_avatar.url))
                        x['razao'], x['moderador_id'], x['conta'], = [], [], 0

        with open('warns.json', 'w') as j:
            json.dump(data, j, indent=4)








extensions = ['jelp', 'help_command', 'warns']
if __name__ == '__main__':
    for ext in extensions:
        client.load_extension(ext)


client.run('ODI1MTk2NTY0MDYxNzQ5MjQ4.YF6aMA.F2BmSblEUwimcguff0sRHol-Lvw')
