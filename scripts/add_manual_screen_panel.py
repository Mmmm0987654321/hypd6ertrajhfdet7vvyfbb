#!/usr/bin/env python3
"""Add explicit, one-action-at-a-time Android Accessibility screen controls.
This does not disable Play Protect or make a browser-downloaded APK installable.
The manual controls only exist after the user enables the Accessibility service.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1]) / "app/src/main/java/net/kuafuai/andee"
assert root.exists()
panel = root/"screen/ManualScreenControls.kt"
assert not panel.exists()
panel.write_text(r'''package net.kuafuai.andee.screen

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.content.Context
import android.graphics.Color
import android.graphics.Path
import android.graphics.PixelFormat
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.view.WindowManager
import android.view.accessibility.AccessibilityNodeInfo
import android.widget.Button
import android.widget.LinearLayout
import android.widget.Toast
import net.kuafuai.andee.ScreenBodyService

/**
 * Each button performs exactly one predefined action only when touched by user.
 * No LLM planning, no automatic taps, no background trigger.
 * TYPE_ACCESSIBILITY_OVERLAY is used only after user enables Android's service.
 * No SYSTEM_ALERT_WINDOW / Play Protect bypass.
 */
class ManualScreenControls(private val service: ScreenBodyService) {
    private val windowManager = service.getSystemService(Context.WINDOW_SERVICE) as WindowManager
    private var overlay: View? = null
    private val instructions = service.getSharedPreferences("andee_direct_commands", Context.MODE_PRIVATE)

    private fun toast(message: String) {
        Toast.makeText(service, message, Toast.LENGTH_SHORT).show()
    }

    private fun runManual(action: () -> Unit) {
        if (!ScreenAccessGate.allowed(service)) {
            toast("यह स्क्रीन सुरक्षित नहीं है या Accessibility consent बंद है")
            return
        }
        try {
            action()
        } catch (_: SecurityException) {
            toast("इस स्क्रीन पर control blocked है")
        } catch (_: Exception) {
            toast("Screen action उपलब्ध नहीं है")
        }
    }

    private fun button(row: LinearLayout, label: String, action: () -> Unit) {
        val b = Button(service)
        b.text = label
        b.isAllCaps = false
        b.textSize = 11f
        b.setOnClickListener { action() }
        row.addView(b, LinearLayout.LayoutParams(0, -2, 1f))
    }

    fun show() {
        if (overlay != null) return
        val consent = service.getSharedPreferences("andee_access_consent", Context.MODE_PRIVATE)
            .getBoolean("consent", false)
        if (!consent) {
            toast("Andee में पहले Accessibility disclosure स्वीकार करें")
            return
        }
        val layout = LinearLayout(service)
        layout.orientation = LinearLayout.VERTICAL
        layout.setPadding(4, 4, 4, 4)
        layout.setBackgroundColor(Color.argb(238, 28, 37, 52))
        val first = LinearLayout(service)
        first.orientation = LinearLayout.HORIZONTAL
        layout.addView(first, LinearLayout.LayoutParams(-1, -2))
        button(first, "← Back") {
            runManual { service.performGlobalAction(AccessibilityService.GLOBAL_ACTION_BACK) }
        }
        button(first, "⌂ Home") {
            runManual { service.performGlobalAction(AccessibilityService.GLOBAL_ACTION_HOME) }
        }
        button(first, "↑ Scroll") { runManual { scroll(down = false) } }
        button(first, "↓ Scroll") { runManual { scroll(down = true) } }

        val second = LinearLayout(service)
        second.orientation = LinearLayout.HORIZONTAL
        layout.addView(second, LinearLayout.LayoutParams(-1, -2))
        button(second, "Tap XY") { runManual { tapPrepared() } }
        button(second, "Type") { runManual { typePrepared() } }
        button(second, "× Close") { hide() }

        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
            PixelFormat.TRANSLUCENT
        )
        params.gravity = Gravity.TOP
        params.y = 80
        try {
            windowManager.addView(layout, params)
            overlay = layout
        } catch (_: Exception) {
            toast("Android ने Accessibility overlay उपलब्ध नहीं कराई")
        }
    }

    private fun tapPrepared() {
        val x = instructions.getInt("tap_x", -1)
        val y = instructions.getInt("tap_y", -1)
        if (x < 0 || y < 0) {
            toast("Andee में पहले 'tap 300 600' लिखें")
            return
        }
        // A prepared command is consumed after this one user button press.
        instructions.edit().remove("tap_x").remove("tap_y").apply()
        val width = service.resources.displayMetrics.widthPixels
        val height = service.resources.displayMetrics.heightPixels
        if (x >= width || y >= height) {
            toast("Coordinates स्क्रीन से बाहर हैं")
            return
        }
        val path = Path().apply { moveTo(x.toFloat(), y.toFloat()) }
        val stroke = GestureDescription.StrokeDescription(path, 0L, 90L)
        service.dispatchGesture(
            GestureDescription.Builder().addStroke(stroke).build(), null, null
        )
    }

    private fun scroll(down: Boolean) {
        val width = service.resources.displayMetrics.widthPixels
        val height = service.resources.displayMetrics.heightPixels
        val x = width * 0.75f
        val y1 = height * if (down) 0.72f else 0.32f
        val y2 = height * if (down) 0.32f else 0.72f
        val path = Path().apply { moveTo(x, y1); lineTo(x, y2) }
        service.dispatchGesture(
            GestureDescription.Builder()
                .addStroke(GestureDescription.StrokeDescription(path, 0L, 360L))
                .build(), null, null
        )
    }

    private fun typePrepared() {
        val text = instructions.getString("type_text", "") ?: ""
        if (text.isBlank() || text.length > 1000) {
            toast("Andee में पहले 'type hello' लिखें")
            return
        }
        val root = service.rootInActiveWindow ?: return
        val focused = try { root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT) }
            finally { @Suppress("DEPRECATION") root.recycle() }
        if (focused == null || focused.isPassword ||
            !focused.isEditable || !focused.isVisibleToUser) {
            @Suppress("DEPRECATION")
            focused?.recycle()
            toast("पहले गैर-संवेदनशील editable field चुनें")
            return
        }
        // Clearing the prepared value prevents unattended repeating/typing.
        instructions.edit().remove("type_text").apply()
        val args = Bundle().apply {
            putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, text)
        }
        val ok = try { focused.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args) }
            finally { @Suppress("DEPRECATION") focused.recycle() }
        toast(if (ok) "Text डाला गया" else "इस editor में direct type उपलब्ध नहीं")
    }

    fun hide() {
        val old = overlay ?: return
        overlay = null
        runCatching { windowManager.removeView(old) }
    }
}
''', encoding="utf-8")

service = root/"ScreenBodyService.kt"
code = service.read_text(encoding="utf-8")
assert "class ScreenBodyService : AccessibilityService() {" in code
code=code.replace(
    "import android.view.accessibility.AccessibilityEvent",
    "import android.view.accessibility.AccessibilityEvent\nimport net.kuafuai.andee.screen.ManualScreenControls",1
)
code=code.replace(
    "class ScreenBodyService : AccessibilityService() {",
    '''class ScreenBodyService : AccessibilityService() {
    private var manualScreenPanel: ManualScreenControls? = null

    /** Visible controls only after explicit user tap from Andee's own UI. */
    fun showManualScreenPanel() {
        if (manualScreenPanel == null) manualScreenPanel = ManualScreenControls(this)
        manualScreenPanel?.show()
    }
''',1)
assert "        BodyCoreService.get()?.detachScreen()" in code
code=code.replace("        BodyCoreService.get()?.detachScreen()",
                  "        manualScreenPanel?.hide()\n        manualScreenPanel = null\n        BodyCoreService.get()?.detachScreen()",1)
service.write_text(code,encoding="utf-8")

activity = root/"ui/InAppCompanionActivity.kt"
code=activity.read_text(encoding="utf-8")
button_marker='        button(p, "🔄  Permission status दोबारा जाँचें") {'
assert button_marker in code
code=code.replace(button_marker,'''        button(p, "🖐️  Manual Screen Control शुरू करें") {
            val active = net.kuafuai.andee.ScreenBodyService.get()
            if (active == null) {
                showResult("Android Accessibility Service को पहले Settings में enable करें")
            } else {
                active.showManualScreenPanel()
                showResult("Screen control toolbar दिखेगा। दूसरे app में जाएँ और action button दबाएँ। Tap/Type के लिए पहले नीचे command तैयार करें।")
            }
        }
''' + button_marker,1)
needle="        val lower = text.lowercase(Locale.ROOT)\n        when {"
assert needle in code
code=code.replace(needle,'''        val lower = text.lowercase(Locale.ROOT)
        // Deterministic one-step commands. No LLM/browser/network actions here.
        val xy = Regex("^(?:tap|click|टैप)\\\\s+(\\\\d{1,4})[,\\\\s]+(\\\\d{1,4})$", RegexOption.IGNORE_CASE).matchEntire(text)
        if (xy != null) {
            val x = xy.groupValues[1].toInt()
            val y = xy.groupValues[2].toInt()
            getSharedPreferences("andee_direct_commands", MODE_PRIVATE).edit()
                .putInt("tap_x", x).putInt("tap_y", y).apply()
            showResult("Tap $x, $y तैयार है। Manual Screen Control खोलकर दूसरे app में 'Tap XY' दबाएँ।")
            return
        }
        val typing = Regex("^(?:type|लिखो)\\\\s+(.+)$",
            setOf(RegexOption.IGNORE_CASE, RegexOption.DOT_MATCHES_ALL)).matchEntire(text)
        if (typing != null) {
            val value = typing.groupValues[1]
            if (value.length > 1000) { showResult("1000 characters तक ही लिख सकते हैं"); return }
            getSharedPreferences("andee_direct_commands", MODE_PRIVATE).edit()
                .putString("type_text", value).apply()
            showResult("Text तैयार है। दूसरे app के input field पर टैप करके Manual Screen Control में 'Type' दबाएँ। पासवर्ड या OTP न डालें।")
            return
        }
        when {''',1)
activity.write_text(code,encoding="utf-8")
print("Added user-driven Accessibility overlay and explicit tap/type/scroll/back/home")
