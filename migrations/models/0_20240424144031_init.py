from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "user" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "context" VARCHAR(1024) NOT NULL  DEFAULT 'default',
    "discord_id" BIGINT NOT NULL,
    "access_token" VARCHAR(1024) NOT NULL,
    "username" VARCHAR(1024) NOT NULL
);
CREATE TABLE IF NOT EXISTS "invitation" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "is_role_perm" BOOL NOT NULL,
    "permit_user" BIGINT NOT NULL,
    "discord_message_id" BIGINT  UNIQUE,
    "repo" VARCHAR(1024) NOT NULL,
    "owner_id" UUID NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
