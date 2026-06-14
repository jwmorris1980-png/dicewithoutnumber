import discord
from discord import app_commands
from discord.ext import commands
import random
import re
import logging

logger = logging.getLogger(__name__)

async def dice_autocomplete_handler(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    """Autocomplete for dice expressions, providing common rolls and character-specific stats."""
    suggestions = []
    
    common_rolls = ["1d20", "2d6", "3d6", "1d8", "1d10", "1d12", "1d4", "1d100", "2d10", "4d6kh3", "3d6kh2"]
    for roll in common_rolls:
        if current.lower() in roll.lower():
            suggestions.append(app_commands.Choice(name=f"🎲 {roll}", value=roll))

    try:
        cog = interaction.client.get_cog("CharacterSheetCog")
        if cog:
            char_data = cog.bot.db.get_active_character(interaction.user.id)
            if char_data:
                if "weapons" in char_data:
                    for w in char_data["weapons"]:
                        w_name = w.get("name", "Unknown")
                        w_dmg = w.get("damage", "1d6")
                        label = f"⚔️ {w_name} ({w_dmg})"
                        if current.lower() in label.lower():
                            suggestions.append(app_commands.Choice(name=label, value=w_dmg))
                if "skills" in char_data:
                    for s_name, s_lvl in char_data["skills"].items():
                        label = f"📊 {s_name.capitalize()} (2d6+{s_lvl})"
                        val = f"2d6+{s_lvl}"
                        if current.lower() in label.lower():
                            suggestions.append(app_commands.Choice(name=label, value=val))
    except Exception:
        pass

    return suggestions[:25]

class DiceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def _find_exact_named_value(values, requested_name):
        """Return an exact case-insensitive sheet value without guessing."""
        if not isinstance(values, dict):
            return None
        requested = " ".join(str(requested_name or "").strip().lower().split())
        for name, value in values.items():
            normalized = " ".join(str(name).strip().lower().split())
            if normalized == requested:
                return str(name), value
        return None

    def _normalize_iterations(self, expression):
        suffix_match = re.match(
            r"^(?P<expr>.+?)\s+(?P<count>\d+)\s+times?(?P<rest>\s+target\b.*)?$",
            expression,
            flags=re.IGNORECASE,
        )
        if suffix_match:
            rest = suffix_match.group("rest") or ""
            return f"{suffix_match.group('count')}x {suffix_match.group('expr')}{rest}"

        prefix_match = re.match(
            r"^(?P<count>\d+)\s+times?\s+(?P<expr>.+)$",
            expression,
            flags=re.IGNORECASE,
        )
        if prefix_match:
            return f"{prefix_match.group('count')}x {prefix_match.group('expr')}"

        return expression

    def _extract_target(self, expression):
        match = re.search(
            r"\btarget\s+(?:(?P<direction1>high|higher|over|above|low|lower|under|below)\s+)?(?P<number>-?\d+)(?:\s+(?P<direction2>high|higher|over|above|low|lower|under|below))?\b",
            expression,
            flags=re.IGNORECASE,
        )
        if not match:
            return expression, None, "high"
        target = int(match.group("number"))
        direction_word = (match.group("direction1") or match.group("direction2") or "high").lower()
        direction = "low" if direction_word in {"low", "lower", "under", "below"} else "high"
        cleaned = (expression[:match.start()] + expression[match.end():]).strip()
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        return cleaned, target, direction

    def _format_target_result(self, total, target, direction="high"):
        if target is None:
            return ""
        success = total <= target if direction == "low" else total >= target
        label = "low target" if direction == "low" else "target"
        outcome = "Success" if success else "Failure"
        return f" vs {label} **{target}**: **{outcome}**"

    @app_commands.command(name="roll", description="Roll a dice expression (e.g. 1d20+5, 2d6+1d4, 4d6kh3)")
    @app_commands.describe(expression="Dice expression", comment="Optional comment", multiplier="Repeat roll")
    @app_commands.autocomplete(expression=dice_autocomplete_handler)
    async def roll_slash(self, interaction: discord.Interaction, expression: str, comment: str = None, multiplier: int = 1):
        if not interaction.response.is_done(): await interaction.response.defer()
        await self._perform_roll(interaction, expression, comment, multiplier)

    @commands.command(name="roll", aliases=["r"], help="Roll dice. Usage: !roll 1d20+5, !roll 3x 2d6")
    async def roll_prefix(self, ctx, *, expression: str):
        await self._perform_roll(ctx, expression, None, 1)

    @app_commands.command(name="gmroll", description="Perform a hidden GM roll (only visible to you).")
    @app_commands.describe(expression="Dice expression", comment="Optional comment", multiplier="Repeat roll")
    @app_commands.autocomplete(expression=dice_autocomplete_handler)
    async def gmroll_slash(self, interaction: discord.Interaction, expression: str, comment: str = None, multiplier: int = 1):
        if not interaction.response.is_done(): await interaction.response.defer(ephemeral=True)
        await self._perform_roll(interaction, expression, comment, multiplier, is_hidden=True)

    @commands.command(name="gmroll", aliases=["gr"], help="Hidden GM roll. Usage: !gmroll 1d20+5 (sent via DM)")
    async def gmroll_prefix(self, ctx, *, expression: str):
        await self._perform_roll(ctx, expression, None, 1, is_hidden=True)

    async def _perform_roll(self, target, expression, comment, multiplier, is_hidden=False):
        is_int = isinstance(target, discord.Interaction)
        user = target.user if is_int else target.author
        expression = self._normalize_iterations(expression)
        expression, target_number, target_direction = self._extract_target(expression)
        
        # Support comma-separated multi-rolls: !roll 1d20+5 Attack, 1d8+2 Damage
        sub_expressions = [s.strip() for s in expression.split(',')]
        
        if len(sub_expressions) > 5:
            send = target.followup.send if is_int else target.send
            await send("❌ Too many separate expressions! Max 5 per message.")
            return

        all_results_msg = ""
        
        for sub_expr in sub_expressions:
            # Initial parse to check for in-string multiples and errors
            _, _, err, in_string_repeats, end_idx = self.bot.dice_service.parse_and_roll(sub_expr)
            if err:
                all_results_msg += f"❌ `{sub_expr}`: {err}\n"
                continue

            repeat_match = re.match(r"^(?P<prefix>\d+\s*[x#]\s*)(?P<inner>.*)$", sub_expr)
            display_expr = repeat_match.group("inner") if repeat_match else sub_expr

            # Extract comment if not provided
            actual_comment = comment
            if not actual_comment:
                raw_comment = display_expr[end_idx:].strip()
                if raw_comment:
                    actual_comment = raw_comment

            total_executions = multiplier * in_string_repeats
            if total_executions > 20:
                all_results_msg += f"❌ `{sub_expr}`: Too many repeats!\n"
                continue

            dice_part = display_expr[:end_idx].strip()
            if repeat_match:
                dice_part = f"{in_string_repeats}x {dice_part}"
            header = f"🎲 **{dice_part}**"
            if actual_comment: header += f" *({actual_comment})*"
            
            msg = f"{header}\n"
            total_sum = 0
            for i in range(total_executions):
                total, details, _, _, _ = self.bot.dice_service.parse_and_roll(sub_expr)
                line = f"↳ Roll {i+1}: {details} = **{total}**\n" if total_executions > 1 else f"↳ Result: {details} = **{total}**\n"
                if target_number is not None:
                    line = line.rstrip() + self._format_target_result(total, target_number, target_direction) + "\n"
                msg += line
                total_sum += total
                
            if total_executions > 1: msg += f"↳ **Grand Total:** {total_sum}\n"
            all_results_msg += msg + "\n"

        display_name = discord.utils.escape_markdown(
            getattr(user, "display_name", getattr(user, "name", "Player"))
        )
        final_msg = f"**{display_name} rolled:**\n{all_results_msg.strip()}"
        
        send = target.followup.send if is_int else target.send
        # Roll output should never ping users or roles, including mentions in comments.
        kwargs = {"allowed_mentions": discord.AllowedMentions.none()}
        
        if is_hidden:
            if is_int:
                kwargs['ephemeral'] = True
                final_msg = f"🕵️ **GM Roll by {display_name}**\n{all_results_msg.strip()}"
            else:
                try:
                    await target.message.delete()
                except:
                    pass
                final_msg = f"🕵️ **GM Roll by {display_name}**\n|| {all_results_msg.strip()} ||\n_*(Note: Discord only allows 'hidden windows' for Slash Commands! Use `/gmroll` next time!)*_"

        await send(final_msg, **kwargs)


    @app_commands.command(name="multiroll")
    async def multiroll_slash(self, interaction: discord.Interaction, times: int, expression: str, comment: str = None):
        if not interaction.response.is_done(): await interaction.response.defer()
        await self._perform_roll(interaction, expression, comment, times)

    @commands.command(name="multiroll", aliases=["rr"])
    async def multiroll_prefix(self, ctx, times: int, expression: str, *, comment: str = None):
        await self._perform_roll(ctx, expression, comment, times)

    @app_commands.command(name="skill")
    async def skill_slash(self, interaction: discord.Interaction, name: str, attribute: str = None, bonus: int = 0):
        sheet_cog = self.bot.get_cog('CharacterSheetCog')
        char_data = await sheet_cog.get_active_character_data(interaction)
        if not char_data: return
        if not interaction.response.is_done(): await interaction.response.defer()
        await self._perform_skill(interaction, char_data, name, attribute, bonus)

    @commands.command(name="skill")
    async def skill_prefix(self, ctx, name: str, attribute: str = None, bonus: int = 0):
        sheet_cog = self.bot.get_cog('CharacterSheetCog')
        char_data = await sheet_cog.get_active_character_data(ctx)
        if char_data:
            await self._perform_skill(ctx, char_data, name, attribute, bonus)

    async def _perform_skill(self, target, char_data, name, attribute, bonus):
        is_int = isinstance(target, discord.Interaction)
        user = target.user if is_int else target.author

        skills = char_data.get('skills', {})
        matched_skill = self._find_exact_named_value(skills, name)
        if not matched_skill:
            if skills:
                available = ", ".join(sorted(str(skill) for skill in skills))
                message = (
                    f"I could not find the skill `{name}` on **{char_data['name']}**. "
                    "I will not guess or use a different skill.\n"
                    f"Skills on this sheet: {available[:1400]}"
                )
            else:
                message = (
                    f"**{char_data['name']}** has no skill values in the imported sheet, so I cannot "
                    f"safely roll `{name}`. I will not guess or automatically use `-1`.\n"
                    "Please re-import a sheet that includes its skills, or send "
                    "`ticket imported sheet has no skills` so we can fix the importer."
                )
            send = target.followup.send if is_int else target.send
            await send(message)
            return

        skill_name, skill_val = matched_skill
        try:
            skill_val = int(skill_val)
        except (TypeError, ValueError):
            send = target.followup.send if is_int else target.send
            await send(
                f"The imported value for `{skill_name}` on **{char_data['name']}** is not a valid "
                "number. I will not guess. Please send `ticket invalid skill value`."
            )
            return

        total_mod = bonus
        total_mod += skill_val
        if attribute:
            matched_attribute = self._find_exact_named_value(char_data.get('attributes', {}), attribute)
            if not matched_attribute:
                send = target.followup.send if is_int else target.send
                await send(
                    f"I could not find the attribute `{attribute}` on **{char_data['name']}**. "
                    "I will not guess or substitute another attribute."
                )
                return
            try:
                total_mod += int(matched_attribute[1])
            except (TypeError, ValueError):
                send = target.followup.send if is_int else target.send
                await send(
                    f"The imported value for `{matched_attribute[0]}` is not a valid number. "
                    "I will not guess."
                )
                return
            
        expression = f"2d6{total_mod:+d}"
        total, details, err, _, _ = self.bot.dice_service.parse_and_roll(expression)
        
        embed = discord.Embed(title=f"📊 Skill Check: {name.capitalize()}", color=discord.Color.green())
        embed.add_field(name="Result", value=f"**{total}**", inline=True)
        embed.add_field(name="Details", value=f"{details} = {total}", inline=False)
        embed.set_footer(text=f"Playing as {char_data['name']} | Rolled by {user.display_name}")
        
        send = target.followup.send if is_int else target.send
        await send(embed=embed)

    @app_commands.command(name="attack")
    async def attack_slash(self, interaction: discord.Interaction, weapon: str = None, bonus: int = 0):
        sheet_cog = self.bot.get_cog('CharacterSheetCog')
        char_data = await sheet_cog.get_active_character_data(interaction)
        if not char_data: return
        if not interaction.response.is_done(): await interaction.response.defer()
        await self._perform_attack(interaction, char_data, weapon, bonus)

    @commands.command(name="attack")
    async def attack_prefix(self, ctx, weapon: str = None, bonus: int = 0):
        sheet_cog = self.bot.get_cog('CharacterSheetCog')
        char_data = await sheet_cog.get_active_character_data(ctx)
        if char_data:
            await self._perform_attack(ctx, char_data, weapon, bonus)

    async def _perform_attack(self, target, char_data, weapon, bonus):
        is_int = isinstance(target, discord.Interaction)
        user = target.user if is_int else target.author
        
        total_mod = bonus
        w_name = "Manual Attack"
        if weapon:
            for w in char_data.get('weapons', []):
                if weapon.lower() in w['name'].lower():
                    total_mod += w.get('to_hit', 0)
                    w_name = w['name']
                    break
        else:
            total_mod += char_data.get('attack_bonus', 0)
            
        expression = f"1d20{total_mod:+d}"
        total, details, err, _, _ = self.bot.dice_service.parse_and_roll(expression)
        
        embed = discord.Embed(title=f"⚔️ Attack: {w_name}", color=discord.Color.red())
        embed.add_field(name="Result", value=f"**{total}**", inline=True)
        embed.add_field(name="Details", value=f"{details} = {total}", inline=False)
        embed.set_footer(text=f"Playing as {char_data['name']} | Rolled by {user.display_name}")
        
        send = target.followup.send if is_int else target.send
        await send(embed=embed)

async def setup(bot):
    await bot.add_cog(DiceCog(bot))
