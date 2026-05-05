import sys
import traceback
from urllib.parse import urljoin

BASE_URL = "https://jntuaceastudents.classattendance.in/"


def _looks_like_bot_block(text: str) -> bool:
    lowered = (text or "").lower()
    return "hello bot" in lowered or "inform the students access the actual website" in lowered


def _is_blocked_response(response) -> bool:
    return getattr(response, "status_code", None) == 403 or _looks_like_bot_block(
        getattr(response, "text", "")
    )


def main():
    print("Runtime diagnostic: curl_cffi availability and portal probe")

    # Plain requests
    try:
        import requests
        print("requests version:", getattr(requests, '__version__', 'unknown'))
        r = requests.get(BASE_URL, timeout=15)
        print("requests GET", r.status_code, "len=", len(getattr(r, 'text', '') or ""))
        if _is_blocked_response(r):
            print("requests: portal appears to be blocking automated requests (bot block detected)")
        else:
            print("requests: no bot block detected")
    except Exception:
        print("requests: failed to fetch")
        traceback.print_exc()

    # curl_cffi probe
    try:
        from curl_cffi import requests as br_requests
        print("curl_cffi is importable")
        try:
            s = br_requests.Session(impersonate="chrome")
            resp = s.get(BASE_URL, timeout=15)
            print("curl_cffi GET", resp.status_code, "len=", len(getattr(resp, 'text', '') or ""))
            if _is_blocked_response(resp):
                print("curl_cffi: portal still returns bot-block page")
            else:
                print("curl_cffi: portal responded without obvious bot-block text")
        except Exception:
            print("curl_cffi: request failed")
            traceback.print_exc()
    except Exception:
        print("curl_cffi is NOT importable in this runtime")
        traceback.print_exc()


if __name__ == '__main__':
    main()
