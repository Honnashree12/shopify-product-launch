import urllib.request
import urllib.parse

prompt = "Ultra-realistic DSLR commercial photography of Indian children participating in a STEM satellite workshop, canon eos r5."
encoded_prompt = urllib.parse.quote(prompt)
url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"

print(f"Fetching: {url}")
try:
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        img_bytes = response.read()
        print(f"SUCCESS! Retrieved {len(img_bytes)} bytes of image.")
        with open("scratch/test_download.png", "wb") as f:
            f.write(img_bytes)
        print("Saved to scratch/test_download.png")
except Exception as e:
    print(f"FAILED to fetch image: {e}")
