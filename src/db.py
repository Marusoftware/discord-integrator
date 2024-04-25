from tortoise import Model
from tortoise.fields import *

__all__=[
    "User",
    "Repo"
]

class User(Model):
    id=UUIDField(pk=True)
    context=CharField(max_length=1024, default="default")
    discord_id=BigIntField()
    access_token=CharField(max_length=1024)
    username=CharField(max_length=1024)
    invitations: ReverseRelation["Invitation"]
    
class Invitation(Model):
    id = UUIDField(pk=True)
    owner = ForeignKeyField("models.User", related_name="invitations", on_delete=CASCADE)
    is_role_perm = BooleanField()
    permit_user = BigIntField()
    discord_message_id = BigIntField(unique=True)
    count = SmallIntField(default=0)
    signup_required = BooleanField()
    repo = CharField(max_length=1024)