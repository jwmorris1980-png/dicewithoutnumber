import discord
from discord import app_commands

def is_gm(interaction: discord.Interaction) -> bool:
    """
    Check if a user has GM permissions in the current context.
    GM permissions are granted if:
    1. User is a Server Administrator or has 'Manage Server' permission.
    2. User is the designated GM for the campaign (global).
    3. User has a specific 'GM Role' assigned to the current channel.
    """
    # 1. Server Admin Check
    if interaction.user.guild_permissions.administrator or interaction.user.guild_permissions.manage_guild:
        return True

    db = getattr(interaction.client, 'db', None)
    if not db:
        return False

    # 2. Campaign GM Check (Global for Guild)
    if interaction.guild:
        campaign = db.get_campaign(interaction.guild.id)
        if campaign and campaign.get('gm_id') == interaction.user.id:
            return True

    # 3. Channel-Specific GM Role Check
    if interaction.channel:
        gm_role_id = db.get_setting(interaction.channel.id, "gm_role")
        if gm_role_id:
            # Check if user has this role
            role = interaction.guild.get_role(int(gm_role_id))
            if role and role in interaction.user.roles:
                return True

    return False

def is_gm_check():
    """A decorator for app_commands to check for GM permissions."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if is_gm(interaction):
            return True
        
        # Localized error message (fallback to English)
        db = getattr(interaction.client, 'db', None)
        localizer = getattr(interaction.client, 'localizer', None)
        user_id = interaction.user.id
        locale = db.get_setting(user_id, "language", "en") if db else "en"
        
        msg = "❌ You do not have GM permissions in this channel."
        if localizer:
            msg = localizer.translate("errors.no_gm_permission", locale)
            
        await interaction.response.send_message(msg, ephemeral=True)
        return False
    
    return app_commands.check(predicate)
