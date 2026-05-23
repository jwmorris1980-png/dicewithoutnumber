import discord
from discord import ui

class CharacterSelect(ui.Select):
    def __init__(self, char_names, placeholder="Choose a character..."):
        options = [
            discord.SelectOption(label=name, value=name)
            for name in char_names
        ]
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_value = self.values[0]
        await self.view.show_scope_selection(interaction)

class CharacterSelectorView(ui.View):
    def __init__(self, user_id, char_names, has_category=False, timeout=60):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.char_names = char_names
        self.has_category = has_category
        self.selected_value = None
        self.selected_scope = 'channel' # Default
        
        self.select_menu = CharacterSelect(char_names)
        self.add_item(self.select_menu)

    async def show_scope_selection(self, interaction: discord.Interaction):
        # Remove select menu and add scope buttons
        self.clear_items()
        
        channel_btn = ui.Button(label="Just this channel", style=discord.ButtonStyle.primary)
        channel_btn.callback = self.choose_channel
        self.add_item(channel_btn)
        
        if self.has_category:
            category_btn = ui.Button(label="Entire Folder (Category)", style=discord.ButtonStyle.success)
            category_btn.callback = self.choose_category
            self.add_item(category_btn)
            
        cancel_btn = ui.Button(label="Cancel", style=discord.ButtonStyle.secondary)
        cancel_btn.callback = self.cancel_selection
        self.add_item(cancel_btn)
        
        category_text = " (and its folder)" if self.has_category else ""
        await interaction.response.edit_message(
            content=f"✅ Selected **{self.selected_value}**. Where should I remember this?{category_text}",
            view=self
        )

    async def choose_channel(self, interaction: discord.Interaction):
        self.selected_scope = 'channel'
        self.stop()
        await interaction.response.defer()

    async def choose_category(self, interaction: discord.Interaction):
        self.selected_scope = 'category'
        self.stop()
        await interaction.response.defer()

    async def cancel_selection(self, interaction: discord.Interaction):
        self.selected_value = None
        self.stop()
        await interaction.response.edit_message(content="❌ Selection cancelled.", view=None)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return False
        return True
