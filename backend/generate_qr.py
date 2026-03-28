import qrcode
import io
import base64

def generate_qr_base64(url):
    """生成二维码Base64"""
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode()

if __name__ == '__main__':
    url = 'weixin://wxpay/bizpayurl?pr=WQblilyz3'
    b64 = generate_qr_base64(url)
    print(f'Generated QR: {len(b64)} bytes')
