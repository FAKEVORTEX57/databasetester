from typing import Dict, Optional
from asyncio import TimeoutError
from datetime import timedelta
from re import match

import nextcord
from nextcord.ext import commands, tasks
from nextcord import (
    Button,
    ButtonStyle,
    ChannelType,
    Colour,
    Embed,
    Forbidden,
    HTTPException,
    Interaction,
    Member,
    MessageType,
    Thread,
    ThreadMember,
    Message,
    ui,
    utils,
    AllowedMentions
)

HELP_CHANNEL_ID: int = 936663745034338314
HELP_LOGS_CHANNEL_ID: int = 929022227939196979
HELPER_ROLE_ID: int = 825201105188945941
HELP_MOD_ID: int = 825201105188945941
GUILD_ID: int = 823744695296852018
CUSTOM_ID_PREFIX: str = "help:"
NAME_TOPIC_REGEX: str = r"(^.*?) \((.*?[0-9]{4})\)$"
WAIT_FOR_TIMEOUT: int = 30  # 30 minutes
timeout_message = "Estás atualmente em repouso, por favor aguarda até que termine antes de tentares novamente"
closing_message = ("Se a tua pergunta não foi corretamente respondida ou se o teu problema não ficou  "
                   "resolvido, nós sugerimos a utlização do site do  [EstudaFQ](https://estudafq.pt/) do professor Marco Pereira "
                   "para tentares questionar o problema com mais eficácia.")


async def get_thread_author(channel: Thread) -> Member:
    history = channel.history(oldest_first=True, limit=1)
    history_flat = await history.flatten()
    user = history_flat[0].mentions[0]
    return user


async def close_help_thread(method: str, thread_channel, thread_author):
    """Fecha uma thread, pode ser chamado através do botão fechar ou do cmd !fechar

        """

    # no need to do any of this if the thread is already closed.
    if (thread_channel.locked or thread_channel.archived):
        return

    if not thread_channel.last_message or not thread_channel.last_message_id:
        _last_msg = (await thread_channel.history(limit=1).flatten())[0]
    else:
        _last_msg = thread_channel.get_partial_message(thread_channel.last_message_id)

    thread_jump_url = _last_msg.jump_url

    embed_reply = Embed(title="Este subcanal está agora fechado.",
                        description=closing_message,
                        colour=Colour.red())

    await thread_channel.send(embed=embed_reply)  # Send the closing message to the help thread
    await thread_channel.edit(locked=True, archived=True)  # Lock thread
    await thread_channel.guild.get_channel(HELP_LOGS_CHANNEL_ID).send(  # Send log
        content=f"Subcanal de ajuda {thread_channel.name[2:]} (criado por {thread_author.name}) foi fechado."
    )
    # Make some slight changes to the previous thread-closer embed
    # to send to the user via DM.
    embed_reply.title = "O teu subcanal de ajuda no servidor EstudaFQ foi fechado"
    embed_reply.description += (f"\n\nPodes usar [**este link**]({thread_jump_url}) para "
                                "acederes quando necessário ao subcanal arquivado")
    embed_reply.colour = Colour.green()
    if thread_channel.guild.icon:
        embed_reply.set_thumbnail(url=thread_channel.guild.icon.url)
    try:
        await thread_author.send(embed=embed_reply)
    except (HTTPException, Forbidden):
        pass


class HelpButton(ui.Button["HelpView"]):
    def __init__(self, help_type: str, *, style: ButtonStyle, custom_id: str):
        super().__init__(label=f"Ajuda em {help_type}", style=style, custom_id=f"{CUSTOM_ID_PREFIX}{custom_id}")
        self._help_type: str = help_type

    async def create_help_thread(self, interaction: Interaction) -> Thread:
        thread = await interaction.channel.create_thread(
            name=f"Ajuda em {self._help_type} ({interaction.user})",
            type=ChannelType.public_thread,
        )

        await interaction.guild.get_channel(HELP_LOGS_CHANNEL_ID).send(
            content=f"Subcanal de ajuda para {self._help_type[2:]} criado por {interaction.user.mention}: {thread.mention}!",
            allowed_mentions=AllowedMentions(users=False)
        )
        close_button_view = ThreadCloseView()
        close_button_view._thread_author = interaction.user

        type_to_colour: Dict[str, Colour] = {
            "Física": Colour.blurple(),
            "Química": Colour.green(),
            "exame": Colour.blurple(),
            "3 ciclo": Colour.random()
        }

        em = Embed(
            title=f"Ajuda em {self._help_type} necessária!",
            colour=type_to_colour.get(self._help_type, Colour.blurple()),
            description=(
                "Explica o teu problema em **pormenor**, os **ajudantes** responderão o mais rapidamente possível."
                "\nAntes de mais, envia a tua mensagem, de maneira a que possamos falar contigo."
                f"\n\nPara mais informações, consulta as nossas linhas de ajuda em <#{HELP_CHANNEL_ID}>"
            )
        )
        em.set_footer(text="Tu e os ajudantes podem carregar neste botão para arquivar o subcanal.")

        msg = await thread.send(
            content=interaction.user.mention,
            embed=em,
            view=ThreadCloseView()
        )
        await msg.pin(reason="1ª msg de um subcanal de ajuda")
        return thread

    async def __launch_wait_for_message(self, thread: Thread, interaction: Interaction) -> None:
        assert self.view is not None

        def is_allowed(message: Message) -> bool:
            return message.author.id == interaction.user.id and message.channel.id == thread.id and not thread.archived  # type: ignore

        try:
            await self.view.bot.wait_for("message", timeout=WAIT_FOR_TIMEOUT, check=is_allowed)
        except TimeoutError:
            await close_help_thread("TIMEOUT [launch_wait_for_message]", thread, interaction.user)
            return
        else:
            await thread.send(f"⬆⬆<@&{HELPER_ROLE_ID}>⬆⬆", delete_after=20)
            return

    async def callback(self, interaction: Interaction):
        confirm_view = ConfirmView()

        def disable_all_buttons():
            for _item in confirm_view.children:
                _item.disabled = True

        confirm_content = f"Tens a certeza que queres criar um subcanal de ajuda de **{self._help_type[2:]}**?"
        await interaction.send(content=confirm_content, ephemeral=True, view=confirm_view)
        await confirm_view.wait()
        if confirm_view.value is False or confirm_view.value is None:
            disable_all_buttons()
            content = "Ok, cancelado." if confirm_view.value is False else f"~~{confirm_content}~~ já vi que não..."
            await interaction.edit_original_message(content=content, view=confirm_view)
        else:
            disable_all_buttons()
            await interaction.edit_original_message(content="Criado!", view=confirm_view)
            created_thread = await self.create_help_thread(interaction)
            await self.__launch_wait_for_message(created_thread, interaction)


class HelpView(ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot: commands.Bot = bot

        self.add_item(HelpButton("🪂│Física", style=ButtonStyle.red, custom_id="física"))
        self.add_item(HelpButton("🧪│Química", style=ButtonStyle.green, custom_id="quíica"))
        self.add_item(HelpButton("📜│Exercício de Exame", style=ButtonStyle.blurple, custom_id="exame"))
        self.add_item(HelpButton("🌈│3 Ciclo", style=ButtonStyle.secondary, custom_id="3 ciclo"))

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.timeout is not None:
            await interaction.send(timeout_message, ephemeral=True)
            return False

        return await super().interaction_check(interaction)


class ConfirmButton(ui.Button["ConfirmView"]):
    def __init__(self, label: str, style: ButtonStyle, *, custom_id: str):
        super().__init__(label=label, style=style, custom_id=f"{CUSTOM_ID_PREFIX}{custom_id}")

    async def callback(self, interaction: Interaction):
        self.view.value = True if self.custom_id == f"{CUSTOM_ID_PREFIX}confirm_button" else False
        self.view.stop()


class ConfirmView(ui.View):
    def __init__(self):
        super().__init__(timeout=10.0)
        self.value = None
        self.add_item(ConfirmButton("Sim", ButtonStyle.green, custom_id="confirm_button"))
        self.add_item(ConfirmButton("Não", ButtonStyle.red, custom_id="decline_button"))


class ThreadCloseView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self._thread_author: Optional[Member] = None

    async def _get_thread_author(self, channel: Thread) -> None:
        self._thread_author = await get_thread_author(channel)

    @ui.button(label="Fechar", style=ButtonStyle.red, custom_id=f"{CUSTOM_ID_PREFIX}thread_close")
    async def thread_close_button(self, button: Button, interaction: Interaction):
        if interaction.channel.archived:
            button.disabled = True
            await interaction.response.edit_message(view=self)
            return

        if not self._thread_author:
            await self._get_thread_author(interaction.channel)  # type: ignore

        button.disabled = True
        await interaction.response.edit_message(view=self)
        await close_help_thread("BUTTON", interaction.channel, self._thread_author)

    async def interaction_check(self, interaction: Interaction) -> bool:
        if not self._thread_author:
            await self._get_thread_author(interaction.channel)  # type: ignore

        # because we aren't assigning the persistent view to a message_id.
        if not isinstance(interaction.channel, Thread) or interaction.channel.parent_id != HELP_CHANNEL_ID:
            return False

        if interaction.user.timeout is not None:
            await interaction.send(timeout_message, ephemeral=True)
            return False

        elif interaction.user.id != self._thread_author.id and not interaction.user.get_role(HELP_MOD_ID):
            await interaction.send("Não estás autorizado a fechar este subcanal.", ephemeral=True)
            return False

        return True


class HelpCog(commands.Cog, name='Subcanais'):
    def __init__(self, bot):
        self.bot = bot
        self.close_empty_threads.start()
        self.bot.loop.create_task(self.create_views())

    async def create_views(self):
        if getattr(self.bot, "help_view_set", False) is False:
            self.bot.help_view_set = True
            self.bot.add_view(HelpView(self.bot))
            self.bot.add_view(ThreadCloseView())

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id == HELP_CHANNEL_ID and message.type is MessageType.thread_created:
            await message.delete(delay=5)
        if isinstance(message.channel, Thread) and \
                message.channel.parent_id == HELP_CHANNEL_ID and \
                message.type is MessageType.pins_add:
            await message.delete(delay=10)

    @commands.Cog.listener()
    async def on_thread_member_remove(self, member: ThreadMember):
        thread = member.thread
        if thread.parent_id != HELP_CHANNEL_ID or thread.archived:
            return

        thread_author = await get_thread_author(thread)
        if member.id != thread_author.id:
            return

        await close_help_thread("EVENT", thread, thread_author)

    @tasks.loop(hours=24)
    async def close_empty_threads(self):
        await self.bot.wait_until_ready()

        guild = self.bot.get_guild(GUILD_ID)
        active_help_threads = [
            thread for thread in await guild.active_threads()
            if thread.parent_id == HELP_CHANNEL_ID and (not thread.locked and not thread.archived)
        ]

        thread: Thread
        for thread in active_help_threads:
            thread_created_at = utils.snowflake_time(thread.id)

            # We don't want to close it before the wait_for.
            if utils.utcnow() - timedelta(seconds=WAIT_FOR_TIMEOUT) <= thread_created_at:
                continue

            all_messages = [
                message for message in (await thread.history(limit=3, oldest_first=True).flatten())
                if message.type is MessageType.default
            ]
            # can happen, ignore.
            if not all_messages:
                continue

            thread_author = all_messages[0].mentions[0]
            if len(all_messages) >= 2:
                members = [x.id for x in await thread.fetch_members()]
                if all_messages[1].author == thread_author and members == [thread_author.id, guild.me.id]:
                    await thread.send(f"<@&{HELPER_ROLE_ID}>", delete_after=20)
                    continue
            else:
                await close_help_thread("TASK [close_empty_threads]", thread, thread_author)
                continue

    @commands.command()
    @commands.is_owner()
    async def menu(self, ctx):
        """Exibe a mensagem com o menu com as ligações para a criação de subcanais."""
        embed_dispo = nextcord.Embed(description='\n Ao requisitares ajuda **deves**:\n\n• ** Fazer** a tua pergunta diretamente, não perguntar se alguém pode ajudar ou se há um perito no assunto.\n\n**•  Mostrar** o exercício (copia, tira printscreen, etc) e verifica que mandaste com boa qualidade para maximizar as chances de obteres uma boa resposta.\n\n**•  Explicar** o que esperas que aconteça e o que não entendes.', color=Colour.green())
        embed_dispo.set_author(name='Antes de criares um subcanal de ajuda, por favor lê o seguinte guião:',
                               icon_url='https://raw.githubusercontent.com/python-discord/branding/main/icons/checkmark/green-question-mark-dist.png')
        embed_dispo.set_footer(text='Fazer/Mostrar/Explicar')

        await ctx.send(embed=embed_dispo)
        await ctx.send(
            content=':white_check_mark: **Se leste o guião, carrega num dos botões para criares um subcanal de ajuda!**',
            view=HelpView(self.bot)
        )

    @commands.command()
    async def close(self, ctx):
        if not isinstance(ctx.channel, Thread) or ctx.channel.parent_id != HELP_CHANNEL_ID:
            return

        thread_author = await get_thread_author(ctx.channel)
        await close_help_thread("COMMAND", ctx.channel, thread_author)

    @commands.command()
    @commands.has_role(HELP_MOD_ID)
    async def topico(self, ctx, *, topic: str):
        """Altera o nome/tópico de um subcanal
        Este comando só pode ser usado em subcanais"""

        if not (isinstance(ctx.channel, Thread) and ctx.channel.parent.id == HELP_CHANNEL_ID):  # type: ignore
            return await ctx.send("Este comando só pode ser usado em subcanais!")

        author = match(NAME_TOPIC_REGEX, ctx.channel.name).group(2)  # type: ignore
        await ctx.channel.edit(name=f"{topic} ({author})")

    @commands.command()
    @commands.has_role(HELP_MOD_ID)
    async def transferir(self, ctx, *, new_author: Member):
        """
        Este comando transfere um membro de um subcanal para outro.
        Só pode ser usado num subcanal e se o membro referido estiver num subcanal,
        que não seja o subcanal onde o comando está a ser utilizado.
            """
        if not (isinstance(ctx.channel, Thread) and ctx.channel.parent_id == HELP_CHANNEL_ID):  # type: ignore
            return await ctx.send("Este comando só pode ser usado em subcanais!")

        topic = match(NAME_TOPIC_REGEX, ctx.channel.name).group(1)  # type: ignore
        first_thread_message = (await ctx.channel.history(limit=1, oldest_first=True).flatten())[0]
        old_author = first_thread_message.mentions[0]

        await ctx.channel.edit(name=f"{topic} ({new_author})")
        await first_thread_message.edit(content=new_author.mention)
        await ctx.guild.get_channel(HELP_LOGS_CHANNEL_ID).send(  # Send log
            content=f"Subcanal {ctx.channel.mention} (criado por {old_author.mention}) " \
                    f"Foi transferido para {new_author.mention} por {ctx.author.mention}.",
        )


def setup(bot):
    bot.add_cog(HelpCog(bot))