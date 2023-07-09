import pyshorteners

def shorten(url):
    s = pyshorteners.Shortener()
    shortened_url = s.tinyurl.short(url)
    return shortened_url

long_url = input("Enter the URL to shorten: ")
shortened_url = shorten(long_url)
print(f"Shortened URL: {shortened_url}")
