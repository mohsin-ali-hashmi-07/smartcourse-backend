import aioboto3
from botocore.exceptions import ClientError
from app.core.settings import settings

_session = aioboto3.Session()

# ── bucket bootstrap ──────────────────────────────────────────────────────────

async def init_bucket() -> None:
    """Create the bucket if it doesn't already exist. Called once on startup."""
    async with _session.client(
        "s3",
        endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
    ) as client:
        try:
            await client.head_bucket(Bucket=settings.minio_bucket)
        except ClientError:
            await client.create_bucket(Bucket=settings.minio_bucket)


# ── upload ────────────────────────────────────────────────────────────────────

async def upload_file(object_key: str, data: bytes, content_type: str) -> str:
    """Upload bytes to MinIO and return the object key."""
    async with _session.client(
        "s3",
        endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
    ) as client:
        await client.put_object(
            Bucket=settings.minio_bucket,
            Key=object_key,
            Body=data,
            ContentType=content_type,
        )
    return object_key


# ── presigned URL ─────────────────────────────────────────────────────────────

async def get_presigned_url(object_key: str, expires_in: int = 3600) -> str:
    """Generate a temporary presigned download URL for an object."""
    async with _session.client(
        "s3",
        endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
    ) as client:
        url = await client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.minio_bucket, "Key": object_key},
            ExpiresIn=expires_in,
        )
    return url
