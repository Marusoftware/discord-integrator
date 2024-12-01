from discord import Bot, ApplicationContext, Button, Message, Option, Intents, Interaction, Role
from discord.ui import button, View, Modal, InputText
from discord.abc import Mentionable
from tortoise import Tortoise, run_async
import os, logging, re
from github import get_username, send_invitation, get_token, get_devicecode, GITHUB_DEVICE_LOGIN
from db import User, Invitation as InvitationDB

logging.basicConfig(level=20)
logger = logging.getLogger("Main")

if "GITHUB_CLIENT_ID" not in os.environ:
    raise ValueError("GITHUB_CLIENT_ID is not present!")
GITHUB_CLIENT_ID=os.environ["GITHUB_CLIENT_ID"]
if "DISCORD_BOT_TOKEN" not in os.environ:
    raise ValueError("DISCORD_BOT_TOKEN is not present!")
DISCORD_BOT_TOKEN=os.environ["DISCORD_BOT_TOKEN"]
if "DATABASE_URL" not in os.environ:
    raise ValueError("DATABASE_URL is not present.")
DATABASE_URL=os.environ["DATABASE_URL"]
EMAIL_PATTERN=re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

import db
DB_CONFIG={
    "connections": {"default":DATABASE_URL},
    "apps": {
        "models": {
            "models": [db, "aerich.models"],
            "default_connection": "default",
        },
    },
}

bot=Bot(description="Discord Integration with something", intent=Intents.default())

@bot.event
async def on_ready():
    logger.info("Login")
    logger.info("Start resuming invitations...")
    async for invitation in InvitationDB.all():
        if invitation.discord_message_id is None:
            continue
        bot.add_view(GetInvitation(), message_id=invitation.discord_message_id)
    logger.info("Resuming invitations completed!")

class CompleteSignup(View):
    def __init__(self, device_code: str, context: str, timeout: float | None = 180, disable_on_timeout: bool = True):
        self.device_code=device_code
        self.context=context
        super().__init__(timeout=timeout, disable_on_timeout=disable_on_timeout)
    @button(label="Complete!")
    async def complete_signup(self, button, interaction: Interaction):
        try:
            access_token=(await get_token(GITHUB_CLIENT_ID, self.device_code))["access_token"]
            username=await get_username(access_token)
        except:
            await interaction.respond("Error!", ephemeral=True)
            return
        await User.create(access_token=access_token, discord_id=interaction.user.id, username=username, context=self.context)
        await interaction.respond(content="Signup successful!", ephemeral=True)

@bot.slash_command(description="Sign up to github")
async def signup(ctx: ApplicationContext, context: Option(str, default="default", description="gh account context(for multiple account)")): # type: ignore
    if await User.exists(discord_id=ctx.user.id, context=context):
        await ctx.respond('Already signed in with that context.', ephemeral=True)
        return
    res=await get_devicecode(GITHUB_CLIENT_ID)
    view=CompleteSignup(device_code=res["device_code"], context=context)
    await ctx.respond(f"Please access [here]({GITHUB_DEVICE_LOGIN}) and input this: `{res['user_code']}`.\nWhen it's done, please click 'Complete!' button.", view=view, ephemeral=True)

class Invitation(Modal):
    def __init__(self, invitation: InvitationDB, *args, **kwargs) -> None:
        super().__init__(title="Invitation", *args, **kwargs, timeout=None, custom_id="inv_modal")
        self.add_item(InputText(label="github Email or Username", required=True))
        self.invitation=invitation
    async def callback(self, interaction: Interaction):
        if await send_invitation(access_token=self.invitation.owner.access_token, repo=self.invitation.repo, user=self.children[0].value):
            await interaction.response.send_message("Invitation was sent!", ephemeral=True)
            self.invitation.count+=1
            await self.invitation.save()
        else:
            await interaction.response.send_message("Error!", ephemeral=True)

class GetInvitationStored(View):
    def __init__(self, invitation:InvitationDB, user:User, target:User|None, timeout: float | None = None):
        super().__init__(timeout=timeout)
        self.invitation=invitation
        self.user=user
        self.target=target
    @button(label="Yes, and please accept invitation too!", custom_id="get_inv_yes_accept")
    async def yes_accept(self, button:Button, interaction: Interaction):
        if self.target is None:
            await interaction.respond("Signup required!", ephemeral=True)
            return
        if await send_invitation(access_token=self.invitation.owner.access_token, repo=self.invitation.repo, user=self.user.username, auto_accept_token=self.target.access_token):
            await interaction.response.send_message("Invitation was sent!", ephemeral=True)
            self.invitation.count+=1
            await self.invitation.save()
        else:
            await interaction.response.send_message("Error!", ephemeral=True)
    @button(label="Yes", custom_id="get_inv_yes")
    async def yes(self, button:Button, interaction: Interaction):
        if await send_invitation(access_token=self.invitation.owner.access_token, repo=self.invitation.repo, user=self.user.username):
            await interaction.response.send_message("Invitation was sent!", ephemeral=True)
            self.invitation.count+=1
            await self.invitation.save()
        else:
            await interaction.response.send_message("Error!", ephemeral=True)
    @button(label="No", custom_id="get_inv_no")
    async def no(self, button:Button, interaction: Interaction):
        await interaction.response.send_modal(Invitation(self.invitation))

class GetInvitation(View):
    def __init__(self, timeout: float | None = None):
        super().__init__(timeout=timeout)
    @button(label="Get invitation", custom_id="get_invitation")
    async def get_invitation(self, button:Button, interaction: Interaction):
        user=await User.get_or_none(discord_id=interaction.user.id)
        invitation=await InvitationDB.get(discord_message_id=interaction.message.id).prefetch_related("owner")
        if invitation.is_role_perm:
            role=interaction.guild.get_role(invitation.permit_user)
            if not role:
                await interaction.respond("Error!", ephemeral=True)
                return
            if interaction.user not in role.members:
                await interaction.respond("Not permitted!", ephemeral=True)
                return
        else:
            if invitation.permit_user!=interaction.user.id:
                await interaction.respond("Not permitted!", ephemeral=True)
                return
        if user is None:
            if invitation.signup_required:
                await interaction.respond("Signup required!", ephemeral=True)
                return
            await interaction.response.send_modal(Invitation(invitation))
        else:
            await interaction.respond(f"Do you want to use already signed in github user '{user.username}'?", view=GetInvitationStored(invitation=invitation, user=user, target=user), ephemeral=True)

@bot.slash_command(description="Create invitation for specified user/role")
async def invite(ctx: ApplicationContext, user: Option(Mentionable, description="Who to create invitation"), # type: ignore
                repo: Option(str, description="Where repo to create invitation(only name of org also available)"), # type: ignore
                context: Option(str, default="default", description="gh account context(for multiple account)"), # type: ignore
                signup_required: Option(bool, default=False, description="is gh signup required?")): # type: ignore
    owner=await User.get_or_none(discord_id=ctx.user.id, context=context)
    if owner is None:
        await ctx.respond('Not signed! Please signup with /signup command!', ephemeral=True)
        return
    is_role_perm=isinstance(user, Role)
    msg=await (await ctx.respond(f'Hey {user.mention}!\nPlease click "Get invitation" button.', view=GetInvitation())).original_response()
    await InvitationDB.create(owner=owner, is_role_perm=is_role_perm, permit_user=user.id, discord_message_id=msg.id, repo=repo, signup_required=signup_required)

@bot.message_command(name="Cancel Invitation", description="Delete invitation on this message")
async def cancel_invite(ctx:ApplicationContext, message: Message):
    invitation=await InvitationDB.get_or_none(discord_message_id=message.id)
    if invitation is None:
        await ctx.respond("This message is not identified as invitation.", ephemeral=True)
        return
    await invitation.delete()
    await ctx.respond("Delete invitation!", ephemeral=True)
    await message.delete()

@bot.slash_command(description="Signout from github")
async def signout(ctx: ApplicationContext, context: Option(str, default="default", description="gh account context(for multiple account)")): # type: ignore
    user=await User.get_or_none(discord_id=ctx.user.id, context=context)
    if user is None:
        await ctx.respond('Not signed!', ephemeral=True)
        return
    await user.delete()
    await ctx.respond('Signed out!', ephemeral=True)

async def init():
    await Tortoise.init(DB_CONFIG)

if __name__ == "__main__":
    run_async(init())
    bot.run(DISCORD_BOT_TOKEN)
