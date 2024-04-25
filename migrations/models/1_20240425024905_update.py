from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "invitation" ADD "count" SMALLINT NOT NULL  DEFAULT 0;
        ALTER TABLE "invitation" ALTER COLUMN "discord_message_id" SET NOT NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "invitation" DROP COLUMN "count";
        ALTER TABLE "invitation" ALTER COLUMN "discord_message_id" DROP NOT NULL;"""
