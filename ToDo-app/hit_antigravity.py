import requests
import urllib3

# Menonaktifkan insecure request warnings dari urllib3 saat mengakses self-signed certificate SSL lokal
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = "https://127.0.0.1:5000/antigravity"


def hit_antigravity():
    """
    Melakukan request ke endpoint lokal https://127.0.0.1:5000/antigravity
    dengan verify=False untuk mengabaikan error sertifikat SSL lokal.
    """
    print(f"[REQUEST] Mengirim request ke: {URL}")
    try:
        response = requests.get(URL, verify=False)
        print(f"[RESPONSE] Status Code: {response.status_code}")
        print("[RESPONSE] Body:")
        try:
            # Tampilkan formatted JSON jika respon berupa JSON
            import json
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        except Exception:
            print(response.text)
        return response
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Gagal melakukan request: {e}")
        return None


if __name__ == '__main__':
    hit_antigravity()
