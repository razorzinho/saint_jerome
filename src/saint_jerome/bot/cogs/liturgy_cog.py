from __future__ import annotations

import logging
from datetime import UTC, datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks

from saint_jerome.bot.commands.liturgia import (
    build_liturgy_embeds,
    build_liturgy_period_embeds,
    get_embed_character_count,
)
from saint_jerome.bot.main import SaintJeromeBot
from saint_jerome.infra.clients.liturgy_api import LiturgyApiError

logger = logging.getLogger("saint_jerome.liturgy")
MAX_EMBEDS_PER_MESSAGE = 10
MAX_EMBED_CHARACTERS_PER_MESSAGE = 6000


class LiturgyCog(commands.Cog):
    def __init__(self, bot: SaintJeromeBot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        if not self.daily_dispatch_loop.is_running():
            self.daily_dispatch_loop.start()

    async def cog_unload(self) -> None:
        self.daily_dispatch_loop.cancel()

    @app_commands.command(
        name="liturgia_hoje",
        description="Exibe a Liturgia Diária de hoje.",
    )
    async def liturgia_hoje(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        try:
            liturgy = await self.bot.container.liturgy_service.get_today()
            embeds = build_liturgy_embeds(liturgy)
            await self._send_embeds(interaction.followup, embeds)
        except LiturgyApiError as exc:
            await interaction.followup.send(str(exc), ephemeral=True)

    @app_commands.command(
        name="liturgia_data",
        description="Exibe a Liturgia Diária de uma data específica.",
    )
    @app_commands.describe(
        dia="Dia da liturgia",
        mes="Mês da liturgia",
        ano="Ano da liturgia",
    )
    async def liturgia_data(
        self,
        interaction: discord.Interaction,
        dia: app_commands.Range[int, 1, 31],
        mes: app_commands.Range[int, 1, 12] | None = None,
        ano: app_commands.Range[int, 1900, 2100] | None = None,
    ) -> None:
        await interaction.response.defer()

        try:
            liturgy = await self.bot.container.liturgy_service.get_by_date(
                day=dia,
                month=mes,
                year=ano,
            )
            embeds = build_liturgy_embeds(liturgy)
            await self._send_embeds(interaction.followup, embeds)
        except (LiturgyApiError, ValueError) as exc:
            await interaction.followup.send(str(exc), ephemeral=True)

    @app_commands.command(
        name="liturgia_periodo",
        description="Exibe um resumo da Liturgia Diária dos próximos dias.",
    )
    @app_commands.describe(dias="Quantidade de dias (máximo 7)")
    async def liturgia_periodo(
        self,
        interaction: discord.Interaction,
        dias: app_commands.Range[int, 1, 7],
    ) -> None:
        await interaction.response.defer()

        try:
            liturgies = await self.bot.container.liturgy_service.get_period(dias)
            embeds = build_liturgy_period_embeds(liturgies)
            await self._send_embeds(interaction.followup, embeds)
        except LiturgyApiError as exc:
            await interaction.followup.send(str(exc), ephemeral=True)

    @app_commands.command(
        name="liturgia_configurar",
        description="Configura o envio automático da Liturgia Diária neste servidor.",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(
        canal="Canal onde a liturgia será enviada",
        hora="Hora local do envio (0-23)",
        minuto="Minuto do envio (0-59)",
        timezone="Timezone IANA, por exemplo America/Sao_Paulo",
        incluir_oracoes="Inclui coleta, oferendas e comunhão",
        incluir_antifonas="Inclui antífonas",
        incluir_extras="Inclui extras litúrgicos",
    )
    async def liturgia_configurar(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel,
        hora: app_commands.Range[int, 0, 23],
        minuto: app_commands.Range[int, 0, 59],
        timezone: str | None = None,
        incluir_oracoes: bool = True,
        incluir_antifonas: bool = True,
        incluir_extras: bool = True,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "Este comando só pode ser usado dentro de um servidor.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            subscription = await self.bot.container.guild_liturgy_service.configure(
                guild_id=interaction.guild.id,
                channel_id=canal.id,
                hour=hora,
                minute=minuto,
                timezone=timezone,
                include_prayers=incluir_oracoes,
                include_antiphons=incluir_antifonas,
                include_extras=incluir_extras,
            )
        except ValueError as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
            return

        await interaction.followup.send(
            "Configuração salva.\n"
            f"Canal: {canal.mention}\n"
            f"Horário: {subscription.post_hour:02d}:{subscription.post_minute:02d}\n"
            f"Timezone: {subscription.timezone}\n"
            f"Orações: {'sim' if subscription.include_prayers else 'não'}\n"
            f"Antífonas: {'sim' if subscription.include_antiphons else 'não'}\n"
            f"Extras: {'sim' if subscription.include_extras else 'não'}",
            ephemeral=True,
        )

    @app_commands.command(
        name="liturgia_status",
        description="Mostra a configuração automática da Liturgia Diária neste servidor.",
    )
    @app_commands.guild_only()
    async def liturgia_status(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "Este comando só pode ser usado dentro de um servidor.",
                ephemeral=True,
            )
            return

        subscription = await self.bot.container.guild_liturgy_service.get_subscription(
            interaction.guild.id
        )
        if subscription is None:
            await interaction.response.send_message(
                "Não há configuração salva para este servidor.",
                ephemeral=True,
            )
            return

        channel = interaction.guild.get_channel(subscription.channel_id)
        channel_display = (
            channel.mention if isinstance(channel, discord.TextChannel) else str(subscription.channel_id)
        )
        await interaction.response.send_message(
            f"Ativo: {'sim' if subscription.enabled else 'não'}\n"
            f"Canal: {channel_display}\n"
            f"Horário: {subscription.post_hour:02d}:{subscription.post_minute:02d}\n"
            f"Timezone: {subscription.timezone}\n"
            f"Orações: {'sim' if subscription.include_prayers else 'não'}\n"
            f"Antífonas: {'sim' if subscription.include_antiphons else 'não'}\n"
            f"Extras: {'sim' if subscription.include_extras else 'não'}\n"
            f"Último envio: {subscription.last_sent_date or 'nenhum'}",
            ephemeral=True,
        )

    @app_commands.command(
        name="liturgia_desativar",
        description="Desativa o envio automático da Liturgia Diária neste servidor.",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    async def liturgia_desativar(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "Este comando só pode ser usado dentro de um servidor.",
                ephemeral=True,
            )
            return

        await self.bot.container.guild_liturgy_service.disable(interaction.guild.id)
        await interaction.response.send_message(
            "Envio automático da liturgia desativado para este servidor.",
            ephemeral=True,
        )

    @tasks.loop(minutes=1)
    async def daily_dispatch_loop(self) -> None:
        await self.bot.wait_until_ready()

        due_subscriptions = await self.bot.container.guild_liturgy_service.get_due_subscriptions(
            now_utc=datetime.now(UTC)
        )
        if not due_subscriptions:
            return

        for subscription, local_date in due_subscriptions:
            try:
                channel = self.bot.get_channel(subscription.channel_id)
                if channel is None:
                    fetched = await self.bot.fetch_channel(subscription.channel_id)
                    channel = fetched if isinstance(fetched, discord.TextChannel) else None

                if not isinstance(channel, discord.TextChannel):
                    logger.warning(
                        "Channel %s for guild %s was not found or is not a text channel.",
                        subscription.channel_id,
                        subscription.guild_id,
                    )
                    continue

                liturgy = await self.bot.container.liturgy_service.get_today()
                embeds = build_liturgy_embeds(
                    liturgy,
                    include_prayers=subscription.include_prayers,
                    include_antiphons=subscription.include_antiphons,
                    include_extras=subscription.include_extras,
                )
                await self._send_embeds(channel, embeds)
                await self.bot.container.guild_liturgy_service.mark_sent(
                    subscription.guild_id,
                    local_date,
                )
            except Exception:
                logger.exception(
                    "Failed to dispatch daily liturgy for guild %s.",
                    subscription.guild_id,
                )

    async def _send_embeds(
        self,
        destination: discord.Webhook | discord.abc.Messageable,
        embeds: list[discord.Embed],
    ) -> None:
        batch: list[discord.Embed] = []
        batch_chars = 0

        for embed in embeds:
            embed_chars = get_embed_character_count(embed)
            would_exceed_count = len(batch) >= MAX_EMBEDS_PER_MESSAGE
            would_exceed_chars = batch_chars + embed_chars > MAX_EMBED_CHARACTERS_PER_MESSAGE

            if batch and (would_exceed_count or would_exceed_chars):
                await destination.send(embeds=batch)
                batch = []
                batch_chars = 0

            batch.append(embed)
            batch_chars += embed_chars

        if batch:
            await destination.send(embeds=batch)


async def setup(bot: SaintJeromeBot) -> None:
    await bot.add_cog(LiturgyCog(bot))
