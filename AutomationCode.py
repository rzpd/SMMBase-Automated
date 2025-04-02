from playwright.sync_api import sync_playwright, Page, TimeoutError
import re

def open_browser_incognito():
    with sync_playwright() as p:
        # Use Chrome (Chromium) and launch it
        browser = p.chromium.launch(headless=False, channel="chrome")

        # Open incognito (aka a new context without cookies/cache)
        context = browser.new_context()

        # New tab (page) in incognito
        page = context.new_page()

        # Go to the website
        page.goto("https://smmbase.org")

        # Click "My account"
        page.click("a.account")

        # Wait for Sign In modal to load
        page.wait_for_selector('#loginWindow input[placeholder="Email"]')

        # Click the Sign Up link inside the modal
        page.click('div.register >> a[href="#registerWindow"]')

        # Fill form
        index = 1 # can be looped
        email = f"michael{index}@gmail.com"
        password = "TestPassword123!"

        # Wait for the Sign Up modal to appear
        page.wait_for_selector('#registerWindow input[placeholder="Email"]')

        # Fill form (scoped to Sign Up modal)
        human_type(page, '#registerWindow input[placeholder="Email"]', email)
        human_type(page, '#registerWindow input[placeholder="Password"]', password)
        human_type(page, '#registerWindow input[placeholder="Reapet the password"]', password)

        # Click Registration
        page.click('button:has-text("Registration")')

        print("Registration succeed!")

        # Wait for redirect to complete
        page.wait_for_url("https://smmbase.org/account-balance/")

        # Page 1: SMMBONUS
        page1 = context.new_page()
        apply_coupon_with_retry(page1, "SMMBONUS")

        # Page 2: SUPERFREE
        page2 = context.new_page()
        apply_coupon_with_retry(page2, "SUPERFREE")

        # Wait until it succeeds (no fixed time)
        wait_for_coupon_success(page2)

        # Open a new page for placing the order
        order_page = context.new_page()
        order_page.goto("https://smmbase.org/account-new-order/")
        wait_for_sufficient_balance(order_page)
        place_order_with_retry(order_page, "https://www.instagram.com/itsmichie_", "100")

        print("Finished!")

def human_type(page: Page, selector: str, text: str, delay: int = 100):
    """
    Types text into an input field with a delay between each keystroke (simulates human typing).
    """
    page.click(selector)
    page.keyboard.type(text, delay=delay)

def apply_coupon_with_retry(page, coupon_code):
    while True:
        page.goto("https://smmbase.org/account-promotion/")
        page.wait_for_selector('input.mycupon')

        page.click('input.mycupon')
        page.keyboard.type(coupon_code, delay=100)
        page.keyboard.press("Tab")
        page.wait_for_timeout(500)
        page.click('button.btn-activation')

        page.wait_for_timeout(1000)

        # Locate popup messages
        error_popup = page.locator("text=Enter coupon code!")
        not_found_popup = page.locator("text=Coupon not found")

        if error_popup.first.is_visible() or not_found_popup.first.is_visible():
            print(f"[{coupon_code}] ❌ Failed. Retrying...")
            page.click("text=Close")  # Close the popup
            page.wait_for_timeout(500)
        else:
            print(f"[{coupon_code}] ✅ Success!")
            break

def wait_for_coupon_success(page: Page, timeout: int = 180000):
    """
    Wait until the coupon popup appears with confirmation text.
    """
    print("🕐 Waiting for coupon to activate...")

    try:
        # Wait for any text inside this element that contains the popup confirmation
        popup = page.locator(".popup-thnk .text_preloader")

        # Use `wait_for` and check if text includes "Coupon activated"
        popup.wait_for(
            state="visible",
            timeout=timeout
        )

        # Optional: extract the message and log it
        print(f"✅ Coupon activated: {popup.inner_text()}")

        # Close the popup
        page.click("button.js-close-campaign")
        page.wait_for_timeout(5000)

        return True

    except TimeoutError:
        print("❌ Coupon activation did not complete within time.")
        return False
    
def wait_for_sufficient_balance(page: Page, minimum_balance: float = 1.0):
    """
    Wait until account balance is at least minimum_balance.
    If not, refreshes the page and rechecks.
    """
    while True:
        try:
            balance_locator = page.locator('div.balance').first
            page.wait_for_selector('div.balance', timeout=5000)

            balance_text = balance_locator.text_content()
            print(f"[Balance Check] Raw balance text: {balance_text!r}")  # Debugging print

            match = re.search(r"Balance:\s*([\d.]+)\s*\$", balance_text or "")
            if match:
                balance = float(match.group(1))
                print(f"[Balance Check] Current balance: ${balance}")
                if balance >= minimum_balance:
                    break
            else:
                print("[Balance Check] Regex failed to match balance.")
        except Exception as e:
            print(f"[Balance Check] Error: {e}")

        print("[Balance Check] Insufficient balance. Refreshing...")
        page.reload()
        page.wait_for_timeout(2000)

def place_order_with_retry(page: Page, instagram_url: str, quantity: str = "100"):
    success_locator = '#msgwnw .text'

    while True:
        try:
            # Refresh the page
            page.goto("https://smmbase.org/account-new-order/")
            page.wait_for_selector('input.profileUrl')

            # Fill Instagram profile URL
            page.click('input.profileUrl')
            page.keyboard.type(instagram_url, delay=100)

            # Fill quantity field like a human
            page.click('input.quantity')
            page.keyboard.press('Control+A')  # Select all
            page.keyboard.press('Backspace')  # Delete existing
            page.keyboard.type(quantity, delay=150)

            # Click outside to trigger recalculation
            page.click('div.total-price')
            page.wait_for_timeout(2000)

            # Click Order
            page.click('button.createOrder')

            # Wait for success popup (up to 5 sec)
            page.wait_for_selector(success_locator, timeout=5000)

            # Success!
            page.wait_for_timeout(2000)
            page.click('#msgwnw a[rel="modal:close"]')
            break

        except TimeoutError:
            print("❌ Order not confirmed. Retrying...")

            # Try closing popup (if it exists)
            try:
                page.click('#msgwnw a[rel="modal:close"]', timeout=1000)
            except:
                pass  # No modal

            page.wait_for_timeout(2000)


open_browser_incognito()
