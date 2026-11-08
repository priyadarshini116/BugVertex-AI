def is_palindrome(s):
    t = "".join(c.lower() for c in s if c.isalnum())
    return t == t[::-1]
