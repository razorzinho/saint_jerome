from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from saint_jerome.bot.commands.versiculo import build_verse_embeds
from saint_jerome.bot.main import SaintJeromeBot
from saint_jerome.bot.views.pagination import VersePaginator


class BibleCog(commands.Cog):
    def __init__(self, bot: SaintJeromeBot) -> None:
        self.bot = bot

    @app_commands.command(
        name="versiculo",
        description="Busca um versículo da Bíblia pela sua referência.",
    )
    @app_commands.describe(referencia="Ex: João 3:16 ou Sl 23:1-4")
    async def versiculo(self, interaction: discord.Interaction, referencia: str) -> None:
        await interaction.response.defer()
        
        try:
            embeds = await build_verse_embeds(self.bot.container, referencia)
            
            if len(embeds) == 1:
                await interaction.followup.send(embed=embeds[0])
            else:
                view = VersePaginator(embeds)
                await interaction.followup.send(embed=embeds[0], view=view)

        except ValueError as e:
            await interaction.followup.send(f"Erro: {e}")
        except LookupError as e:
            await interaction.followup.send(str(e))
        except Exception as e:
            await interaction.followup.send("Ocorreu um erro interno ao processar o seu pedido.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        if message.content.startswith(self.bot.command_prefix) or message.content.startswith("/"):
            return

        references = self.bot.container.parser.extract_all(message.content)
        if not references:
            return

        embed = discord.Embed(color=discord.Color.gold())
        combined_length = 0
        long_passages = []

        for ref in references:
            try:
                verses = await self.bot.container.bible_service.get_passage(ref)
                
                book_name = verses[0].book_name
                chapter = ref.chapter
                translation_id = verses[0].translation_id.upper()
                
                title = f"{book_name} {chapter}:{ref.verse_start}"
                if ref.verse_end and ref.verse_end != ref.verse_start:
                    title += f"-{ref.verse_end}"
                title += f" ({translation_id})"

                text = " ".join([f"**{v.verse}** {v.text}" for v in verses])

                if len(text) <= 1000 and combined_length + len(text) + len(title) < 5800 and len(embed.fields) < 25:
                    embed.add_field(name=title, value=text, inline=False)
                    combined_length += len(text) + len(title)
                else:
                    long_passages.append(ref)
                    
            except Exception:
                continue

        if len(embed.fields) > 0:
            await message.reply(embed=embed, mention_author=False)

        for long_ref in long_passages:
            embeds = await build_verse_embeds(self.bot.container, parsed_reference=long_ref)
            if len(embeds) == 1:
                await message.reply(embed=embeds[0], mention_author=False)
            else:
                view = VersePaginator(embeds)
                await message.reply(embed=embeds[0], view=view, mention_author=False)


async def setup(bot: SaintJeromeBot) -> None:
    await bot.add_cog(BibleCog(bot))
