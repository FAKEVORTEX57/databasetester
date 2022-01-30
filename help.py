from typing import Dict, NamedTuple, Optional
import nextcord
from nextcord.ext import commands
from nextcord.abc import GuildChannel
from nextcord import (
    Button,
    ButtonStyle,
    ChannelType,
    Colour,
    Embed,
    Forbidden,
    Guild,
    HTTPException,
    Interaction,
    Member,
    MessageType,
    Thread,
    ThreadMember,
    ui
)


HELP_CHANNEL_ID: int = 929022205982019664
HELP_LOGS_CHANNEL_ID: int = 929022227939196979
HELPER_ROLE_ID: int = 824766184389083226
HELP_MOD_ID: int = 398068173275922433
GUILD_ID: int = 823744695296852018
CUSTOM_ID_PREFIX: str = "help:"
NAME_TOPIC_REGEX: str = r"(^.*?) \((.*?[0-9]{4})\)$"
WAIT_FOR_TIMEOUT: int = 1800  # 30 minutes
timeout_message = "Estás atualmente em repouso, por favor aguarda até que termine antes de tentares novamente"
closing_message = ("Se a tua pergunta não foi corretamente respondida ou se o teu problema não ficou  "
                   "resolvido, nós sugerimos a utlização do site do  [EstudaFQ](https://estudafq.pt/) do professor Marco Pereira "
                   "para tentares questionar o problema com mais eficácia.")


async def get_thread_author(channel: Thread) -> Member:
    history = channel.history(oldest_first = True, limit = 1)
    history_flat = await history.flatten()
    user = history_flat[0].mentions[0]
    return user


async def close_help_thread(method: str, thread_channel, thread_author):
    """Fecha uma thread, pode ser chamado através do botão fechar ou do cmd !fechar

    """
    if not thread_channel.last_message or not thread_channel.last_message_id:
        _last_msg = ((await thread_channel.history(limit = 1)).flatten())[0]
    else:
        _last_msg = thread_channel.get_partial_message(thread_channel.last_message_id)

    thread_jump_url = _last_msg.jump_url

    dm_embed_thumbnail = thread_channel.guild.icon.url
    embed_reply = Embed(title="Este subcanal está agora fechado.",
                        description=closing_message,
                        colour=nextcord.Colour.teal())

    await thread_channel.send(embed=embed_reply)  # Send the closing message to the help thread
    await thread_channel.edit(locked = True, archived = True)  # Lock thread
    await thread_channel.guild.get_channel(HELP_LOGS_CHANNEL_ID).send(  # Send log
        content = f"Subcanal de ajuda {thread_channel.name[2:]} (criado por {thread_author.name}) foi fechado."
    )
    # Make some slight changes to the previous thread-closer embed
    # to send to the user via DM.
    embed_reply.title = "O teu subcanal de ajuda no servidor EstudaFQ foi fechado"
    embed_reply.description += (f"\n\nPodes usar [**este link**]({thread_jump_url}) para "
                                "acederes quando necessário ao subcanal arquivado")
    embed_reply.set_thumbnail(url=dm_embed_thumbnail)
    try:
        await thread_author.send(embed=embed_reply)
    except (HTTPException, Forbidden):
        pass

class HelpButton(ui.Button["HelpView"]):
    def __init__(self, help_type: str, *, style: ButtonStyle, custom_id: str):
        super().__init__(label = f"Ajuda em {help_type}", style = style, custom_id = f"{CUSTOM_ID_PREFIX}{custom_id}")
        self._help_type = help_type

    async def create_help_thread(self, interaction: Interaction) -> None:
        channel_type = ChannelType.private_thread if interaction.guild.premium_tier >= 2 else ChannelType.public_thread
        thread = await interaction.channel.create_thread(
            name = f"Ajuda em {self._help_type} ({interaction.user})",
            type = channel_type
        )

        await interaction.guild.get_channel(HELP_LOGS_CHANNEL_ID).send(
            content = f"Subcanal de ajuda para {self._help_type[2:]} criado por {interaction.user.mention}: {thread.mention}!"
        )
        close_button_view = ThreadCloseView()
        close_button_view._thread_author = interaction.user

        type_to_colour: Dict[str, Colour] = {
            "Física": Colour.red(),
            "Química": Colour.green()
        }

        em = Embed(
            title = f"Ajuda em {self._help_type[2:]} necessária!",
            description = f"Ok, agora que estamos todos aqui para te ajudar, em que é que precisas de ajuda?",
            colour = type_to_colour.get(self._help_type, Colour.blurple())
        )
        em.set_footer(text = "Tu e os ajudantes podem carregar neste botão para arquivar o subcanal.")

        msg = await thread.send(
            content = f"<@&{HELPER_ROLE_ID}> | {interaction.user.mention}",
            embed = em,
            view = ThreadCloseView()
        )
        await msg.pin(reason = "1ª msg de um subcanal de ajuda")

    async def callback(self, interaction: Interaction):
        confirm_view = ConfirmView()

        def disable_all_buttons():
            for _item in confirm_view.children:
                _item.disabled = True

        confirm_content = f"Tens a certeza que queres criar um subcanal de ajuda de **{self._help_type[2:]}**?"
        await interaction.response.send_message(content = confirm_content, ephemeral = True, view = confirm_view)
        await confirm_view.wait()
        if confirm_view.value is False or confirm_view.value is None:
            disable_all_buttons()
            content = "Ok, cancelado." if confirm_view.value is False else f"~~{confirm_content}~~ Pelos vistos não..."
            await interaction.edit_original_message(content = content, view = confirm_view)
        else:
            disable_all_buttons()
            await interaction.edit_original_message(content = "Criado!", view = confirm_view)
            await self.create_help_thread(interaction)


class HelpView(ui.View):
    def __init__(self):
        super().__init__(timeout = None)
        self.add_item(HelpButton("🪂│Física", style = ButtonStyle.red, custom_id = "física"))
        self.add_item(HelpButton("🧪│Química", style = ButtonStyle.green, custom_id = "quíica"))
        self.add_item(HelpButton("📜│Exercício de Exame", style = ButtonStyle.blurple, custom_id = "exame"))
        self.add_item(HelpButton("🌈│3 Ciclo", style = ButtonStyle.secondary, custom_id = "3 ciclo"))



class ConfirmButton(ui.Button["ConfirmView"]):
    def __init__(self, label: str, style: ButtonStyle, *, custom_id: str):
        super().__init__(label = label, style = style, custom_id = f"{CUSTOM_ID_PREFIX}{custom_id}")

    async def callback(self, interaction: Interaction):
        self.view.value = True if self.custom_id == f"{CUSTOM_ID_PREFIX}confirm_button" else False
        self.view.stop()


class ConfirmView(ui.View):
    def __init__(self):
        super().__init__(timeout = 10.0)
        self.value = None
        self.add_item(ConfirmButton("Sim", ButtonStyle.green, custom_id = "confirm_button"))
        self.add_item(ConfirmButton("Não", ButtonStyle.red, custom_id = "decline_button"))


class ThreadCloseView(ui.View):
    def __init__(self):
        super().__init__(timeout = None)
        self._thread_author: Optional[Member] = None

    async def _get_thread_author(self, channel: Thread) -> None:
        self._thread_author = await get_thread_author(channel)

    @ui.button(label = "Close", style = ButtonStyle.red, custom_id = f"{CUSTOM_ID_PREFIX}thread_close")
    async def thread_close_button(self, button: Button, interaction: Interaction):
        if interaction.channel.archived:
            button.disabled = True
            await interaction.message.edit(view = self)
            return

        if not self._thread_author:
            await self._get_thread_author(interaction.channel)  # type: ignore
        
        await close_help_thread("BUTTON", interaction.channel, self._thread_author)
        button.disabled = True
        await interaction.message.edit(view = self)

    async def interaction_check(self, interaction: Interaction) -> bool:
        if not self._thread_author:
            await self._get_thread_author(interaction.channel)  # type: ignore

        # because we aren't assigning the persistent view to a message_id.
        if not isinstance(interaction.channel, Thread) or interaction.channel.parent_id != HELP_CHANNEL_ID:
            return False

        return interaction.user.id == self._thread_author.id or interaction.user.get_role(HELP_MOD_ID)


class HelpCog(commands.Cog, name='Subcanais'):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.create_views())

    async def create_views(self):
        if getattr(self.bot, "help_view_set", False) is False:
            self.bot.help_view_set = True
            self.bot.add_view(HelpView())
            self.bot.add_view(ThreadCloseView())

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id == HELP_CHANNEL_ID and message.type is MessageType.thread_created:
            await message.delete(delay = 5)
        if isinstance(message.channel, Thread) and \
                message.channel.parent_id == HELP_CHANNEL_ID and \
                message.type is MessageType.pins_add:
            await message.delete(delay = 10)

    @commands.Cog.listener()
    async def on_thread_member_remove(self, member: ThreadMember):
        thread = member.thread
        if thread.parent_id != HELP_CHANNEL_ID or thread.archived:
            return

        thread_author = await get_thread_author(thread)
        if member.id != thread_author.id:
            return

        await close_help_thread("EVENT", thread, thread_author)

    @commands.command()
    @commands.is_owner()
    async def menu(self, ctx):
        """Exibe a mensagem com o menu com as ligações para a criação de subcanais."""

        
        embed_dispo = nextcord.Embed(
                    description='\n Ao requisitares ajuda **deves**:\n\n• ** Fazer** a tua pergunta diretamente, não perguntar se alguém pode ajudar ou se há um perito no assunto.\n\n**•  Mostrar** o exercício (copia, tira printscreen, etc) e verifica que mandaste com boa qualidade para maximizar as chances de obteres uma boa resposta.\n\n**•  Explicar** o que esperas que aconteça e o que não entendes.',
                    colour = nextcord.Colour.green()
                )
        embed_dispo.set_author(name='Antes de criares um subcanal de ajuda, por favor lê o seguinte guião:', icon_url='https://raw.githubusercontent.com/python-discord/branding/main/icons/checkmark/green-question-mark-dist.png')
        embed_dispo.set_footer(text='Fazer/Mostrar/Explicar')
        await ctx.send(embed=embed_dispo)
        await ctx.send(':white_check_mark: **Se leste o guião, carrega num dos botões para criares um subcanal de ajuda!**', view=HelpView())
        

    @commands.command()
    async def fechar(self, ctx):
        """ Fecha um subcanal, só funciona dentro de subcanais."""
        if not isinstance(ctx.channel, Thread) or ctx.channel.parent_id != HELP_CHANNEL_ID:
            return
        thread_author = await get_thread_author(ctx.channel)
        await close_help_thread("COMMAND", ctx.channel, thread_author)

    @commands.command()
    @commands.has_role(HELP_MOD_ID)
    async def topic(self, ctx, *, topic):
        if not ctx.channel.type == ChannelType.private_thread:
            return await ctx.send("Este comando só pode ser usado em subcanais!")
        if ctx.message.channel.parent.id != HELP_CHANNEL_ID:
            return await ctx.send("Este comando só pode ser usado em subcanais!")
        author = await get_thread_author(ctx.channel)
        await ctx.channel.edit(name=f"{topic} ({author})")


def setup(bot):
    bot.add_cog(HelpCog(bot))