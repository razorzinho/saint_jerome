from __future__ import annotations

import discord


class VersePaginator(discord.ui.View):
    def __init__(self, embeds: list[discord.Embed]) -> None:
        super().__init__(timeout=120)
        self.embeds = embeds
        self.current_page = 0
        self._update_buttons()

    def _update_buttons(self) -> None:
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == len(self.embeds) - 1

    @discord.ui.button(label="Anterior", style=discord.ButtonStyle.secondary, emoji="⬅️")
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.current_page -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="Próximo", style=discord.ButtonStyle.secondary, emoji="➡️")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.current_page += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
