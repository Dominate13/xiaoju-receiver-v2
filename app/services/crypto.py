import base64
import hashlib
import hmac
import json
from typing import Optional, Dict, Any

# 兼容不同 Python 版本的 Crypto 库导入
try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad, pad
except ImportError:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import unpad, pad


class CryptoUtil:
    """加解密工具"""
    
    @staticmethod
    def aes_decrypt(encrypted_data: str, key: str, iv: str) -> Optional[Dict[str, Any]]:
        """
        AES-128-CBC解密
        
        Args:
            encrypted_data: Base64编码的加密数据
            key: 密钥（32字符）
            iv: 初始向量（16字符）
        
        Returns:
            解密后的字典，失败返回None
        """
        try:
            encrypted_bytes = base64.b64decode(encrypted_data)
            cipher = AES.new(
                key.encode("utf-8"),
                AES.MODE_CBC,
                iv.encode("utf-8")
            )
            decrypted = unpad(cipher.decrypt(encrypted_bytes), AES.block_size)
            return json.loads(decrypted.decode("utf-8"))
        except Exception:
            return None
    
    @staticmethod
    def hmac_verify(data: str, signature: str, secret: str) -> bool:
        """
        HMAC-SHA256验签
        
        Args:
            data: 待验签数据（原始字符串）
            signature: 签名（Base64编码）
            secret: 密钥
        
        Returns:
            验签结果
        """
        try:
            expected_sig = hmac.new(
                secret.encode("utf-8"),
                data.encode("utf-8"),
                hashlib.sha256
            ).digest()
            
            expected_sig_b64 = base64.b64encode(expected_sig).decode("utf-8")
            
            return hmac.compare_digest(signature, expected_sig_b64)
        except Exception:
            return False
    
    @staticmethod
    def hmac_sign(data: str, secret: str) -> str:
        """
        HMAC-SHA256签名
        
        Args:
            data: 待签名数据
            secret: 密钥
        
        Returns:
            Base64编码的签名
        """
        sig = hmac.new(
            secret.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha256
        ).digest()
        return base64.b64encode(sig).decode("utf-8")


def aes_encrypt(data: str, key: str, iv: str) -> str:
    """AES 加密"""
    cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))
    padded_data = pad(data.encode('utf-8'), AES.block_size)
    encrypted = cipher.encrypt(padded_data)
    return base64.b64encode(encrypted).decode('utf-8')


def aes_decrypt(data: str, key: str, iv: str) -> str:
    """AES 解密"""
    cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))
    encrypted_data = base64.b64decode(data)
    decrypted = cipher.decrypt(encrypted_data)
    unpadded = unpad(decrypted, AES.block_size)
    return unpadded.decode('utf-8')


def hmac_md5_sign(sign_str: str, secret: str) -> str:
    """HMAC-MD5 签名"""
    h = hmac.new(secret.encode('utf-8'), sign_str.encode('utf-8'), hashlib.md5)
    return h.hexdigest().upper()


def verify_sig(operator_id, enc_data, timestamp, seq, sig, sig_secret) -> bool:
    """验证签名"""
    sign_str = f"{operator_id}{enc_data}{timestamp}{seq}"
    expected_sig = hmac_md5_sign(sign_str, sig_secret)
    return sig == expected_sig


def build_response_sig(ret, msg, enc_data, sig_secret) -> str:
    """构建响应签名"""
    sign_str = f"{ret}{msg}{enc_data}"
    return hmac_md5_sign(sign_str, sig_secret)
