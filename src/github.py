from typing import TypedDict
import httpx, re, logging

logger=logging.getLogger("github")

class DeviceCode(TypedDict):
    device_code: str
    user_code: str
    verification_url: str
    expires_in: int
    interval: int

class Token(TypedDict):
    access_token: str
    token_type: str
    scope: str

GITHUB_GET_ME="https://api.github.com/user"
GITHUB_GET_USER="https://api.github.com/users/{username}"
GITHUB_CREATE_INVITATION="https://api.github.com/repos/{repo}/collaborators/{username}"
GITHUB_CREATE_ORG_INVITATION="https://api.github.com/orgs/{org}/invitations"
GITHUB_ACCEPT_INVITATION="/user/repository_invitations/{invitation_id}"
GITHUB_SEARCH="https://api.github.com/search/users"
GITHUB_DEVICE_OAUTH="https://github.com/login/device/code"
GITHUB_DEVICE_OAUTH_TOKEN="https://github.com/login/oauth/access_token"
GITHUB_DEVICE_LOGIN="https://github.com/login/device"
EMAIL_PATTERN=re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

async def get_token(client_id: str, device_code: str) -> Token:
    async with httpx.AsyncClient() as client:
        return (await client.post(GITHUB_DEVICE_OAUTH_TOKEN, json={
            "client_id": client_id,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code"
        }, headers={"Accept": "application/json"})).json()

async def get_devicecode(client_id: str) -> DeviceCode:
    async with httpx.AsyncClient() as client:
        return (await client.post(GITHUB_DEVICE_OAUTH, 
            json={"client_id": client_id},
            headers={"Accept": "application/json"})).json()

async def get_username(access_token:str) -> str:
    async with httpx.AsyncClient() as client:
        return (await client.get(GITHUB_GET_ME, headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer "+access_token
        })).json()["login"]

async def get_myuserid(access_token: str) -> str:
    async with httpx.AsyncClient() as client:
        return (await client.get(GITHUB_GET_ME, headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer "+access_token
        })).json()["id"]

async def get_userid(username:str) -> str:
    async with httpx.AsyncClient() as client:
        return (await client.get(GITHUB_GET_USER.replace("{username}", username), headers={
            "Accept": "application/vnd.github+json",
        })).json()["id"]

async def send_invitation(access_token:str, repo:str, user:str, auto_accept:bool=False) -> bool:
    async with httpx.AsyncClient() as client:
        try:
            if "/" not in repo:
                if EMAIL_PATTERN.fullmatch(user):
                    req={"email": user}
                else:
                    req={"invitee_id": await get_userid(user)}
                res=await client.post(GITHUB_CREATE_ORG_INVITATION.replace("{org}", repo), headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {access_token}"
                }, json=req)
                if res.status_code==201:
                    return True
                else:
                    return False
            else:
                if EMAIL_PATTERN.fullmatch(user):
                    res=(await client.get(GITHUB_SEARCH, params={"q": f"{user} in:email"}, headers={"Accept": "application/vnd.github+json"})).json()
                    if res["tortal_count"] != 1:
                        return False
                    user=res["items"][0]["login"]
                res=await client.post(GITHUB_CREATE_INVITATION.replace("{repo}", repo).replace("{username}", user), headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {access_token}"
                })
                if auto_accept:
                    accepted=await accept_invitation(access_token, res["id"])
                if res.status_code >= 200 and accepted:
                    return True
                else:
                    return False
        except Exception as e:
            logger.exception("send_invitation Error")
            return False

async def accept_invitation(access_token:str, invitation_id:str):
    async with httpx.AsyncClient() as client:
        res=await client.patch(GITHUB_ACCEPT_INVITATION.replace("{invitation_id}", invitation_id), headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}"
        })
    return res.status_code in (204, 304)
