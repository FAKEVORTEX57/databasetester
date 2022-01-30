import datetime

import nextcord
from nextcord.ext import commands
import json
class Avisos(commands.Cog, name='Avisos'):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    async def avisar(self, ctx, member: nextcord.Member, *, reason='Sem razão dada.'):
        """Avisa um membro de um determinado comportamento contra as regras do servidor.
        3 avisos = Mute de 3 dias"""
        if member.id in [ctx.author.id, self.bot.user.id]:
            return await ctx.send('Queres te auto avisar?')
        else:

            with open('warns.json') as json_file:
                data = json.load(json_file)
                ids_bad = [x['membro_id'] for x in data]
                ids = list(dict.fromkeys(ids_bad))
                for x in data:
                    if x['membro_id'] == member.id:
                        x['moderador_id'].append(ctx.author.id)
                        x['razao'].append(reason)
                        x['conta'] += 1
                        conta = x['conta']
                        if conta == 3:
                            razoes = ''
                            x['conta'] = 0
                            for r in list(dict.fromkeys(x['razao'])):
                                razoes += f'**{x["razao"].index(r) + 1}.** ' + r + '\n'
                            x['razao'] = []
                            x['moderador_id'] = []

                            await member.edit(timeout=nextcord.utils.utcnow() + datetime.timedelta(days=3))
                    else:
                        if member.id not in ids:
                            conta = 1
                            novo_avisado = {
                                'membro_id': member.id,
                                'razao': [reason],
                                'moderador_id': [],
                                'conta': 1
                             }

                            data.append(novo_avisado)
                            break

            with open('warns.json', 'w') as j:
                json.dump(data, j, indent=4)

            embed=nextcord.Embed(title=f"{member.name}#{member.discriminator} avisado.",
                                                description=f"**Razão**\n{reason}\n\n**Moderador**\n{ctx.author.mention}\n\n**Aviso nº**\n{conta}",color=nextcord.Colour.orange())
            if conta == 3:
                embed.add_field(name='Membro silenciado', value='Após levar 3 avisos pelas seguintes razões:\n '
                                                                f'\n{razoes}\nO utilizador **{member.name}#{member.discriminator}** foi silenciado por 3 dias.')
            embed.set_footer(text=f'Hoje às {str(nextcord.utils.utcnow())[11:16]}')
            embed.set_author(name='⚠❗', icon_url=member.default_avatar.url)

            await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def avisos(self, ctx, member: nextcord.Member):
        """ Mostra a quantidade de avisos que um utilizador recebeu."""
        with open('warns.json') as json_file:
            data = json.load(json_file)
            ids_bad = [x['membro_id'] for x in data]
            ids = list(dict.fromkeys(ids_bad))
            for x in data:
                if member.id == x['membro_id'] and x['conta'] > 0:
                    txt = ''
                    embed = nextcord.Embed(title=f'Avisos do membro {member.name}#{member.discriminator}({x["conta"]})')
                    for i in range(x['conta']):
                        txt += f"**{i + 1}.** {x['razao'][i]} \nPor: __<@{x['moderador_id'][i]}>__\n\n"
                    embed.description = txt
                    embed.colour = nextcord.Colour.orange()
                    if member.default_avatar.url is None:
                        embed.set_thumbnail(url='https://ecoregional.com.br/wp-content/uploads/2022/01/avisos-1.png')
                    else:
                        embed.set_thumbnail(url=member.default_avatar.url)
                    await ctx.send(embed=embed)
                    break
                elif member.id not in ids or x['conta'] == 0:
                    await ctx.send(embed=nextcord.Embed(title=f'O membro {member.name}#{member.discriminator} não recebeu avisos até agora.', color=nextcord.Color.orange()))








def setup(bot):
    bot.add_cog(Avisos(bot))
