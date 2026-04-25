import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from bd_models.models import Ball, balls as countryballs
from settings.models import settings

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("ballsdex.packages.rarity")


class RarityView(discord.ui.View):
    """Pagination view for rarity list."""

    def __init__(self, pages: list[discord.Embed], timeout: float = 180.0):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.current_page = 0

    async def update_page(self, interaction: discord.Interaction):
        """Update the current page embed."""
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @discord.ui.button(label="<<", style=discord.ButtonStyle.secondary)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to first page."""
        self.current_page = 0
        await self.update_page(interaction)

    @discord.ui.button(label="<", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to previous page."""
        if self.current_page > 0:
            self.current_page -= 1
        await self.update_page(interaction)

    @discord.ui.button(label="...", style=discord.ButtonStyle.primary)
    async def skip_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Skip to a specific page."""
        modal = PageSkipModal(self.pages, self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label=">", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to next page."""
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
        await self.update_page(interaction)

    @discord.ui.button(label=">>", style=discord.ButtonStyle.secondary)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to last page."""
        self.current_page = len(self.pages) - 1
        await self.update_page(interaction)

    @discord.ui.button(label="Quit", style=discord.ButtonStyle.danger)
    async def quit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Quit the view."""
        await interaction.response.defer()
        self.stop()


class PageSkipModal(discord.ui.Modal, title="Skip to page"):
    """Modal for skipping to a specific page."""

    page_number = discord.ui.TextInput(label="Page number", placeholder="Enter page number...")

    def __init__(self, pages: list[discord.Embed], view: RarityView):
        super().__init__()
        self.pages = pages
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            page_num = int(self.page_number.value) - 1
            if 0 <= page_num < len(self.pages):
                self.view.current_page = page_num
                await interaction.response.edit_message(embed=self.pages[page_num], view=self.view)
            else:
                await interaction.response.send_message(
                    f"❌ Page must be between 1 and {len(self.pages)}", ephemeral=True
                )
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid number", ephemeral=True)


class Rarity(commands.Cog):
    """
    Rarity commands for viewing ball rarity tiers.
    """

    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot

    @app_commands.command()
    async def state_rarity(self, interaction: discord.Interaction["BallsDexBot"]):
        """
        View the rarity list of all available states.
        """
        await interaction.response.defer()

        # Get all enabled balls and group by rarity
        enabled_balls = [ball for ball in countryballs.values() if ball.enabled]
        
        if not enabled_balls:
            await interaction.followup.send("❌ No states available.", ephemeral=True)
            return

        # Sort by rarity (descending) then by name
        enabled_balls.sort(key=lambda b: (-b.rarity, b.country))

        # Group by rarity value
        rarity_groups: dict[float, list[Ball]] = {}
        for ball in enabled_balls:
            if ball.rarity not in rarity_groups:
                rarity_groups[ball.rarity] = []
            rarity_groups[ball.rarity].append(ball)

        # Sort rarity values in ascending order (smallest number = rarest first)
        sorted_rarities = sorted(rarity_groups.keys())

        # Create embed pages (max 5 rarity groups per page)
        pages: list[discord.Embed] = []
        current_embed = discord.Embed(
            title=f"{settings.collectible_name} Rarity List",
            color=discord.Colour.blurple(),
        )

        items_per_page = 5
        rarity_count = 0

        for rarity in sorted_rarities:
            balls_at_rarity = rarity_groups[rarity]
            # Format: ▶ Ball1, Ball2, Ball3 (with emojis)
            ball_names = []
            for ball in balls_at_rarity:
                emoji = self.bot.get_emoji(ball.emoji_id)
                if emoji:
                    ball_names.append(f"{emoji} {ball.country}")
                else:
                    ball_names.append(ball.country)

            rarity_text = f"**Rarity: {rarity}**\n" + ", ".join(ball_names)

            # Check if we need a new page
            if rarity_count >= items_per_page:
                pages.append(current_embed)
                current_embed = discord.Embed(
                    title=f"{settings.collectible_name} Rarity List",
                    color=discord.Colour.blurple(),
                )
                rarity_count = 0

            current_embed.add_field(name="\u200b", value=rarity_text, inline=False)
            rarity_count += 1

        # Add final page
        if current_embed.fields:
            pages.append(current_embed)

        # Add page counter to each embed
        for idx, page in enumerate(pages, 1):
            page.set_footer(text=f"Page {idx}/{len(pages)}")

        if not pages:
            await interaction.followup.send("❌ No states available.", ephemeral=True)
            return

        # Send first page with pagination view
        view = RarityView(pages)
        await interaction.followup.send(embed=pages[0], view=view)

