"""ShopLite: a small built-in demo website with intentional bugs, so WebSentinel-AI can be demoed offline.

Version 2 simulates a UI redesign (renamed IDs, classes and button text) to demonstrate self-healing.
Intentional bugs: a broken 'Careers' link, missing email validation on the contact form, and a
server error when searching with a quote character.
"""

from html import escape

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter()
state = {"version": 1}

PRODUCTS = [
    ("Wireless Mouse", 1200),
    ("Mechanical Keyboard", 4500),
    ("USB-C Hub", 2300),
    ("Laptop Stand", 1800),
    ("Noise Cancelling Headphones", 7900),
    ("Webcam HD", 3100),
]

CSS = """
*{box-sizing:border-box}body{margin:0;font-family:system-ui,sans-serif;background:#f8fafc;color:#0f172a}
header{background:#0f172a;color:#fff;padding:14px 32px;display:flex;gap:24px;align-items:center}
header a{color:#cbd5e1;text-decoration:none}header a:hover{color:#fff}.brand{font-weight:700;color:#fff;margin-right:auto}
main{max-width:860px;margin:32px auto;padding:0 16px}.card{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:24px}
label{display:block;margin:12px 0 4px;font-weight:600}input,textarea{width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:8px}
.btn{margin-top:16px;padding:10px 18px;border:0;border-radius:8px;color:#fff;cursor:pointer}.btn-primary{background:#2563eb}.btn-accent{background:#7c3aed}
.error{color:#dc2626;margin-top:12px}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.price{color:#2563eb;font-weight:700}
.badge{font-size:12px;background:#fef3c7;padding:2px 8px;border-radius:99px;margin-left:8px}
"""


def v(v1: str, v2: str) -> str:
    return v1 if state["version"] == 1 else v2


def layout(title: str, body: str) -> HTMLResponse:
    badge = f"<span class='badge'>v{state['version']}</span>"
    return HTMLResponse(
        f"""<!doctype html><html><head><meta charset="utf-8"><title>{title} | ShopLite</title>
<style>{CSS}</style></head><body>
<header><a class="brand" href="/demo/">ShopLite{badge}</a>
<a href="/demo/products">Products</a><a href="/demo/about">About</a><a href="/demo/contact">Contact</a>
<a href="/demo/careers">Careers</a><a href="/demo/login">Login</a></header>
<main>{body}</main></body></html>"""
    )


@router.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    return layout(
        "Home",
        """<div class="card"><h1>Welcome to ShopLite</h1>
<p>Quality tech accessories at the best price in Bangladesh.</p>
<a href="/demo/products">Browse products &rarr;</a></div>""",
    )


@router.get("/about", response_class=HTMLResponse)
def about() -> HTMLResponse:
    return layout("About", "<div class='card'><h1>About us</h1><p>ShopLite is a demo store used by WebSentinel-AI.</p></div>")


@router.get("/products", response_class=HTMLResponse)
def products(q: str = "") -> HTMLResponse:
    if "'" in q:
        # Intentional bug: simulates an unescaped SQL query crashing on a quote.
        return HTMLResponse(
            "<h1>500 Internal Server Error</h1><pre>sqlite3.OperationalError: unrecognized token</pre>", status_code=500
        )
    items = [(n, p) for n, p in PRODUCTS if q.lower() in n.lower()]
    cards = "".join(f"<div class='card'><h3>{escape(n)}</h3><p class='price'>৳{p}</p></div>" for n, p in items)
    return layout(
        "Products",
        f"""<h1>Products</h1>
<form method="get" action="/demo/products">
<input id="{v("search", "product-search")}" name="q" type="search" placeholder="Search products" value="{escape(q)}">
<button id="{v("search-btn", "find-btn")}" class="btn {v("btn-primary", "btn-accent")}" type="submit">{v("Search", "Find")}</button>
</form><br><div class="grid">{cards or "<p>No products found.</p>"}</div>""",
    )


def login_page(error: str = "") -> HTMLResponse:
    err = f"<p class='error'>{error}</p>" if error else ""
    return layout(
        "Login",
        f"""<div class="card"><h1>Sign in</h1><form method="post" action="/demo/login">
<label for="{v("username", "user-login")}">Username</label>
<input id="{v("username", "user-login")}" name="username" placeholder="Username" required>
<label for="{v("password", "user-pass")}">Password</label>
<input id="{v("password", "user-pass")}" name="password" type="password" placeholder="Password" required>
<button id="{v("login-btn", "signin-submit")}" class="btn {v("btn-primary", "btn-accent")}" type="submit">{v("Sign in", "Log in")}</button>
{err}</form><p>Demo account: <code>demo</code> / <code>demo123</code></p></div>""",
    )


@router.get("/login", response_class=HTMLResponse)
def login_form() -> HTMLResponse:
    return login_page()


@router.post("/login", response_class=HTMLResponse)
def login(username: str = Form(""), password: str = Form("")):
    if username == "demo" and password == "demo123":
        return RedirectResponse("/demo/dashboard", status_code=303)
    return login_page("Invalid username or password.")


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> HTMLResponse:
    return layout("Dashboard", "<div class='card'><h1>Welcome back, demo!</h1><p>You have 2 orders in progress.</p></div>")


@router.get("/contact", response_class=HTMLResponse)
def contact_form() -> HTMLResponse:
    # Intentional bug: the email field is type="text" and the server never validates it.
    return layout(
        "Contact",
        f"""<div class="card"><h1>Contact us</h1><form method="post" action="/demo/contact">
<label for="{v("name", "full-name")}">Name</label><input id="{v("name", "full-name")}" name="name" placeholder="Your name" required>
<label for="{v("email", "mail")}">Email</label><input id="{v("email", "mail")}" name="email" type="text" placeholder="you@example.com" required>
<label for="{v("message", "msg")}">Message</label><textarea id="{v("message", "msg")}" name="message" rows="4" required></textarea>
<button id="{v("send-btn", "contact-submit")}" class="btn {v("btn-primary", "btn-accent")}" type="submit">{v("Send message", "Send")}</button>
</form></div>""",
    )


@router.post("/contact")
def contact(name: str = Form(""), email: str = Form(""), message: str = Form("")):
    if not name or not email or not message:
        return contact_form()
    return RedirectResponse("/demo/thank-you", status_code=303)


@router.get("/thank-you", response_class=HTMLResponse)
def thank_you() -> HTMLResponse:
    return layout("Thank you", "<div class='card'><h1>Thank you!</h1><p>We received your message.</p></div>")
