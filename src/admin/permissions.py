from ..config import config

def is_admin(user_id: int) -> bool:
    """Check if user is authorized for admin commands"""
    return user_id == config.AUTHORIZED_USER_ID

async def admin_check(ctx) -> bool:
    """Admin authorization check with error message"""
    if not is_admin(ctx.author.id):
        await ctx.send(f"❌ **Access Denied**: Admin commands restricted.\nYour ID: {ctx.author.id}\nAuthorized ID: {config.AUTHORIZED_USER_ID}")
        return False
    return True