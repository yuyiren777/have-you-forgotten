"""AES 加密/解密工具 — 用于保护 API Key 等敏感配置"""
import base64
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# 固定密钥（基于机器名+固定盐生成，同一台机器上可解密）
def _get_machine_key() -> bytes:
    import socket
    raw = socket.gethostname().encode() + b'__schedule_assistant_salt__'
    return hashlib.sha256(raw).digest()

_AES_KEY = _get_machine_key()


def encrypt(plain_text: str) -> str:
    """AES-CBC 加密，返回 base64 字符串"""
    if not plain_text:
        return ''
    cipher = AES.new(_AES_KEY, AES.MODE_CBC)
    ct_bytes = cipher.encrypt(pad(plain_text.encode('utf-8'), AES.block_size))
    iv = base64.b64encode(cipher.iv).decode('utf-8')
    ct = base64.b64encode(ct_bytes).decode('utf-8')
    return f'{iv}:{ct}'


def decrypt(cipher_text: str) -> str:
    """AES-CBC 解密，返回明文"""
    if not cipher_text:
        return ''
    try:
        iv, ct = cipher_text.split(':')
        iv = base64.b64decode(iv)
        ct = base64.b64decode(ct)
        cipher = AES.new(_AES_KEY, AES.MODE_CBC, iv)
        pt = unpad(cipher.decrypt(ct), AES.block_size)
        return pt.decode('utf-8')
    except Exception:
        return cipher_text  # 解密失败返回原文（可能是未加密的旧数据）
