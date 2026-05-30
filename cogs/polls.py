import shlex

import discord
from discord import app_commands
from discord.ext import commands


YES_NO_OPTIONS = [("Yes", "👍"), ("No", "👎")]
CHOICE_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]


class PollsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _build_poll_embed(self, author, question, options):
        embed = discord.Embed(
            title="Poll",
            description=f"**{question}**",
            color=discord.Color.blurple(),
        )
        lines = [f"{emoji} {label}" for label, emoji in options]
        embed.add_field(name="Choices", value="\n".join(lines), inline=False)
        embed.set_footer(text=f"Poll by {author.display_name} • Vote with reactions")
        return embed

    async def _send_poll(self, channel, author, question, answers):
        question = (question or "").strip()
        answers = [answer.strip() for answer in answers if answer and answer.strip()]

        if not question:
            raise ValueError("Polls need a question.")
        if len(question) > 256:
            raise ValueError("Poll question is too long. Keep it under 256 characters.")
        if len(answers) > len(CHOICE_EMOJIS):
            raise ValueError(f"Too many choices. Max {len(CHOICE_EMOJIS)}.")
        if len(answers) == 1:
            raise ValueError("Use either no choices for Yes/No or at least two choices for multiple choice.")

        options = YES_NO_OPTIONS if not answers else list(zip(answers, CHOICE_EMOJIS))
        embed = self._build_poll_embed(author, question, options)
        message = await channel.send(embed=embed)

        for _, emoji in options:
            await message.add_reaction(emoji)

        return message

    @app_commands.command(name="poll", description="Create a SimplePoll-style reaction poll.")
    @app_commands.describe(
        question="The poll question",
        answer1="Optional answer choice. Leave blank for Yes/No.",
        answer2="Optional answer choice",
        answer3="Optional answer choice",
        answer4="Optional answer choice",
        answer5="Optional answer choice",
        answer6="Optional answer choice",
        answer7="Optional answer choice",
        answer8="Optional answer choice",
        answer9="Optional answer choice",
        answer10="Optional answer choice",
    )
    async def poll_slash(
        self,
        interaction: discord.Interaction,
        question: str,
        answer1: str = None,
        answer2: str = None,
        answer3: str = None,
        answer4: str = None,
        answer5: str = None,
        answer6: str = None,
        answer7: str = None,
        answer8: str = None,
        answer9: str = None,
        answer10: str = None,
    ):
        await interaction.response.defer()
        answers = [answer1, answer2, answer3, answer4, answer5, answer6, answer7, answer8, answer9, answer10]
        try:
            await self._send_poll(interaction.channel, interaction.user, question, answers)
            await interaction.followup.send("Poll created.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Could not create poll: `{e}`", ephemeral=True)

    @commands.command(name="poll")
    async def poll_prefix(self, ctx, *, text: str = ""):
        try:
            if '"' in text or "'" in text:
                parts = shlex.split(text)
            else:
                parts = [text.strip()] if text.strip() else []
        except ValueError:
            await ctx.send('Could not read that poll. Try `!poll "Question?" "Choice 1" "Choice 2"`.')
            return

        if not parts:
            await ctx.send('Usage: `!poll "Question?"` or `!poll "Question?" "Choice 1" "Choice 2"`.')
            return

        question = parts[0]
        answers = parts[1:]
        try:
            await self._send_poll(ctx.channel, ctx.author, question, answers)
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                pass
        except Exception as e:
            await ctx.send(f"Could not create poll: `{e}`")


async def setup(bot):
    await bot.add_cog(PollsCog(bot))
