#!/usr/bin/env python3
"""Explicitly consented Accessibility integration for Andee v0.11.0.
Protect banks/payment apps by refusing screen reads and actions at the Android
controller boundary. No Play Protect bypass or auto-grant of Accessibility.
"""
from pathlib import Path
import sys

base=Path(sys.argv[1])
src=base/"app/src/main/java/net/kuafuai/andee"
assert src.exists()
guard=src/"screen/ScreenAccessGate.kt"
guard.write_text(r'''package net.kuafuai.andee.screen

import android.accessibilityservice.AccessibilityService
import android.view.accessibility.AccessibilityNodeInfo
import net.kuafuai.andee.device.DeviceState
import java.util.ArrayDeque
import java.util.Locale

/**
 * Defensive boundary for a user-enabled AccessibilityService.
 * No payment, banking or authentication window should be inspected or acted on.
 *
 * Package/visible-text checks are best-effort, NOT a formal security boundary.
 * User must keep this service disabled while handling financial/secret data.
 */
object ScreenAccessGate {
    private val restricted = listOf(
        "bank", "banking", "hdfc", "icici", "axisbank", "axis.bank",
        "kotak", "onlinesbi", "yono", "statebank", "sbi", "pnb",
        "bobworld", "barodabank", "canarabank", "idbibank", "unionbank",
        "indusind", "yesbank", "federalbank", "idfcfirst", "rblbank",
        "dbsbank", "hsbc", "standardchartered", "citi", "americanexpress",
        "paytm", "phonepe", "gpay", "google pay", "paisa.user", "npci",
        "bhim", "upi", "cred", "razorpay", "cashfree", "paypal",
        "payment", "payu", "mobikwik", "freecharge", "airtelmoney",
        "wallet", "metamask", "trustwallet", "phantom", "ledger",
        "binance", "coinbase", "coindcx", "wazirx", "bybit",
        "kucoin", "okx", "bitget", "cryptocom", "crypto.com",
        "trading", "zerodha", "groww", "upstox", "angelone",
        "fyers", "dhan", "stocks", "broker", "investing",
        "passwordmanager", "authenticator", "onepassword", "lastpass",
        "bitwarden", "dashlane", "keepass",
        "com.android.settings", "com.google.android.packageinstaller",
        "com.android.permissioncontroller", "com.google.android.permissioncontroller",
        "com.android.vending"
    )
    private val browsers = listOf("chrome", "firefox", "browser", "opera", "brave", "edge", "samsung.internet")
    private val sensitiveWeb = listOf(
        "internet banking", "netbanking", "mobile banking", "bank account",
        "enter your otp", "enter otp", "one time password", "account number",
        "card number", "cvv", "secure checkout", "make a payment",
        "beneficiary", "upi pin", "enter pin", "send money",
        "withdraw funds", "seed phrase", "secret recovery phrase",
        "private key", "wallet recovery", "payment gateway",
        "onlinesbi.sbi", "hdfcbank.com", "icicibank.com",
        "axisbank.com", "kotak.com", "bankofbaroda.in"
    )
    private fun lowered(value: String?) = (value ?: "").lowercase(Locale.ROOT)
    private fun risky(value: String) = restricted.any { value.contains(it) }

    fun isProtectedPackage(service: AccessibilityService, packageName: String?): Boolean {
        val pkg=lowered(packageName)
        if (pkg.isEmpty()) return true
        if (risky(pkg)) return true
        val label=runCatching {
            val pm=service.packageManager
            pm.getApplicationLabel(pm.getApplicationInfo(pkg, 0)).toString().lowercase(Locale.ROOT)
        }.getOrDefault("")
        return risky(label)
    }

    fun allowed(service: AccessibilityService): Boolean = try {
        requireAllowed(service)
        true
    } catch (_: SecurityException) { false } catch (_: Exception) { false }

    fun requireAllowed(service: AccessibilityService) {
        val consent=service.getSharedPreferences("andee_access_consent", android.content.Context.MODE_PRIVATE)
            .getBoolean("consent", false)
        if (!consent) throw SecurityException("User must read and accept the in-app Accessibility disclosure")
        val root=service.rootInActiveWindow
            ?: throw SecurityException("No readable application window: screen access denied")
        try {
            val current=lowered(root.packageName?.toString())
            val seen=lowered(DeviceState.foregroundPkg)
            if (isProtectedPackage(service,current) ||
                (seen.isNotBlank() && seen!=service.packageName && isProtectedPackage(service,seen))) {
                throw SecurityException("Banking, payment, trading, credentials or protected system app blocked")
            }
            // Browser apps can display banking sites. Fail closed when screen
            // contains strong banking/payment/credential signals.
            if (browsers.any { current.contains(it) || seen.contains(it) }) {
                val nodes=ArrayDeque<AccessibilityNodeInfo>()
                nodes.add(root)
                var examined=0
                var scanned=0
                val text=StringBuilder()
                while (!nodes.isEmpty() && examined++<230 && scanned<7000) {
                    val node=nodes.removeFirst()
                    if (node.isPassword) throw SecurityException("Password field on screen: refused")
                    val parts=listOfNotNull(node.text?.toString(),node.contentDescription?.toString(),
                        node.viewIdResourceName)
                    for (part in parts) {
                        if (scanned>=7000) break
                        val take=part.take(260)
                        text.append(' ').append(take)
                        scanned+=take.length
                    }
                    for (i in 0 until node.childCount) {
                        node.getChild(i)?.let { nodes.addLast(it) }
                    }
                }
                val loweredText=text.toString().lowercase(Locale.ROOT)
                if (sensitiveWeb.any { loweredText.contains(it) })
                    throw SecurityException("Sensitive banking/payment webpage detected: refused")
            }
        } finally {
            @Suppress("DEPRECATION")
            root.recycle()
        }
    }
}
''',encoding='utf-8')
print("Created bank/payment exclusion guard:",guard)

screen=src/"screen/ScreenController.kt"
content=screen.read_text(encoding="utf-8")
# Do not count app's system event note as a screen read. All public
# read/actuation entry points below are explicitly guarded.
methods=[
    'fun tapNorm(nx: Int, ny: Int, beforePx: FloatArray? = null): JSONObject {',
    'fun longPressNorm(nx: Int, ny: Int, durationMs: Long): JSONObject {',
    'fun tapLocated(nx: Int, ny: Int, target: String, long: Boolean): JSONObject {',
    'fun tapAim(on: String?, x: Int?, y: Int?, cell: String?, part: String?): JSONObject {',
    'fun zoomAim(cell: String, part: String?): JSONObject {',
    'fun tapByEid(eid: String): JSONObject {',
    'fun longPressByEid(eid: String, durationMs: Long): JSONObject {',
    'fun tap(x: Int, y: Int, snapFrame: FloatArray? = null): JSONObject {',
    'fun tapById(id: String): JSONObject {',
    'fun swipe(x1: Int, y1: Int, x2: Int, y2: Int, durationMs: Long, fling: Boolean): JSONObject {',
    'fun longPress(x: Int, y: Int, durationMs: Long): JSONObject {',
    'fun longPressById(id: String): JSONObject {',
    'fun typeText(text: String, id: String?, secret: Boolean): JSONObject {',
    'fun submitInput(id: String?): JSONObject {',
    'fun globalAction(action: String, actor: String = "brain"): JSONObject {',
    'fun screenshot(reason: String = "tool", grid: Boolean = true): JSONObject {',
    'fun lookRegion(nx: Int, ny: Int, w: Int, h: Int, mark: IntArray? = null): JSONObject {',
]
for signature in methods:
    assert content.count(signature)==1, "ScreenController signature changed: "+signature
    content=content.replace(signature,signature+"\n        ScreenAccessGate.requireAllowed(service)",1)
# Multiline signatures, inject after a unique first line that follows the opening brace.
markers=[
    ('fun longPressAim(', '        val a = resolveAim(on, x, y, cell, part)'),
    ('fun swipeNorm(', '        requireNorm(nx1, "x1"); requireNorm(ny1, "y1")'),
    ('fun dumpUiTree(', '        // Asking for the tree is the deliberate act of looking.'),
]
for function_name, first_line in markers:
    start=content.find('    '+function_name)
    assert start!=-1
    idx=content.find(first_line,start)
    assert idx>start and idx-start<900, ("cannot place guard",function_name)
    content=content[:idx]+"        ScreenAccessGate.requireAllowed(service)\n"+content[idx:]
# A number of methods call runGesture directly. Block at the very last
# boundary too, so new gesture code can't accidentally skip high-level guard.
signature='private fun runGesture(gesture: GestureDescription, timeoutMs: Long): JSONObject {'
assert content.count(signature)==1
content=content.replace(signature,signature+"\n        ScreenAccessGate.requireAllowed(service)",1)
signature='fun activeWindowVisible(): Boolean {'
assert content.count(signature)==1
content=content.replace(signature,signature+"\n        if (!ScreenAccessGate.allowed(service)) return false",1)
screen.write_text(content,encoding='utf-8')

body=src/"ScreenBodyService.kt"
text=body.read_text(encoding="utf-8")
text=text.replace("import android.view.accessibility.AccessibilityEvent",
                  "import android.view.accessibility.AccessibilityEvent\nimport net.kuafuai.andee.screen.ScreenAccessGate",1)
marker="        if (event == null) return\n        when (event.eventType) {"
assert marker in text
text=text.replace(marker,'''        if (event == null) return
        val currentPkg=event.packageName?.toString()
        if (currentPkg != null && ScreenAccessGate.isProtectedPackage(this,currentPkg)) {
            // Record that the bank is foreground so no stale previously allowed
            // app can be used as the target of a new gesture.
            net.kuafuai.andee.device.DeviceState.foregroundPkg=currentPkg
            return
        }
        when (event.eventType) {''',1)
body.write_text(text,encoding='utf-8')
print("Protected Android screen controller entry points and accessibility event path")

# Documentation available inside APK.
assets=base/"app/src/main/assets"
assets.mkdir(exist_ok=True,parents=True)
(assets/"SCREEN_ACCESS_NOTICE_HI.txt").write_text(
    "Andee personal modified build. Android Accessibility permission sirf user Settings "
    "mein enable kar sakta hai. Bank, payment, trading, wallets, secrets aur "
    "sensitive system apps screen-controller mein block kiye gaye hain. "
    "Browser ke andar sabhi banking pages ki detection guaranteed nahi hai. "
    "Sensitive transactions ke liye Accessibility OFF rakhein. "
    "Google Play Protect internet se install ko block kar sakta hai. "
    "Protection disable/bypass mat karein. "
    "Original Andee license and branding retained.\\n",encoding="utf-8"
)
# Static fail-fast checks on built source.
check=screen.read_text()
assert check.count('ScreenAccessGate.requireAllowed(service)')>=20
assert 'ScreenAccessGate.isProtectedPackage' in body.read_text()
print("Static checks: at least 20 guarded entry points")
