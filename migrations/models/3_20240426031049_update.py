from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "invitation" ALTER COLUMN "owner_id" DROP NOT NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "invitation" ALTER COLUMN "owner_id" SET NOT NULL;"""
