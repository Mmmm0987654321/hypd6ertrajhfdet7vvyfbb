#!/usr/bin/env python3
"""Patch ONLY the Accessibility permission setup path on original Andee v0.11.0.

The original AI/controller/gesture/typing app is preserved. This script does not
remove features, alter service flags, bypass Android Restricted Settings, or
change Google Play Protect. Android permission must be granted by the user.
"""
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

root = Path(sys.argv[1])
src = root / "app/src/main/java/net/kuafuai/andee"
assert src.exists(), "Expected upstream Andee v0.11.0 source"
self_check = src / "device/SelfCheck.kt"
original = self_check.read_text(encoding="utf-8")
assert 'fix = if (on) Fix.Nothing else Fix.Screen(Settings.ACTION_ACCESSIBILITY_SETTINGS),' in original, "Upstream permission row changed"
original = original.replace(
    'fix = if (on) Fix.Nothing else Fix.Screen(Settings.ACTION_ACCESSIBILITY_SETTINGS),',
    '''fix = if (on) Fix.Nothing else Fix.Screen(
                android.content.Intent.ACTION_MAIN,
                component = android.content.ComponentName(
                    context, net.kuafuai.andee.ui.AccessibilityPermissionGuideActivity::class.java
                ).flattenToString(),
            ),''',
    1
)
self_check.write_text(original, encoding="utf-8")

activity = src / "ui/AccessibilityPermissionGuideActivity.kt"
assert not activity.exists(), "Do not overwrite existing upstream Activity"
activity.write_text(r'''package net.kuafuai.andee.ui

import android.app.Activity
import android.app.AlertDialog
import android.content.ComponentName
import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.provider.Settings
import android.text.method.ScrollingMovementMethod
import android.view.View
import android.widget.Button
import android.widget.CheckBox
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import net.kuafuai.andee.ScreenBodyService

/**
 * Guided, explicit and transparent setup for sideloaded Android 13+ apps.
 * Cannot toggle Android's restricted settings or enable Accessibility itself.
 * Original Andee AI, voice, overlays, typing and screen tools are unchanged.
 */
class AccessibilityPermissionGuideActivity : Activity() {
    private lateinit var status: TextView
    private lateinit var consent: CheckBox
    private lateinit var accessibilityButton: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val bg = Color.rgb(13, 22, 36)
        val fg = Color.WHITE
        val secondary = Color.rgb(205, 217, 230)
        val scroll = ScrollView(this)
        scroll.setBackgroundColor(bg)
        val panel = LinearLayout(this)
        panel.orientation = LinearLayout.VERTICAL
        val px = (16 * resources.displayMetrics.density).toInt()
        panel.setPadding(px, px, px, px)
        scroll.addView(panel)

        fun text(content: String, fontSize: Float, color: Int = secondary): TextView {
            val t = TextView(this)
            t.text = content
            t.textSize = fontSize
            t.setTextColor(color)
            t.setPadding(0, px / 3, 0, px / 3)
            panel.addView(t)
            return t
        }
        fun action(label: String, callback: () -> Unit): Button {
            val b = Button(this)
            b.text = label
            b.isAllCaps = false
            b.textSize = 15f
            b.setOnClickListener { callback() }
            panel.addView(b, LinearLayout.LayoutParams(-1, -2))
            return b
        }
        text("Andee • Original Screen Control", 22f, fg)
        text("Yeh original Andee hai: AI, voice, screen reading, tap, scroll aur typing features nahi hataye gaye hain.", 14f)
        status = text("", 16f, fg)
        text("Android 13+ par internet se install ki gayi app ke liye Restricted settings alag se allowed karni pad sakti hain.", 14f)
        text("STEP 1: Settings → Apps / App management → Andee → upar ⋮ (three dots) → Allow restricted settings. Yeh option sirf device par available ho to use karein. Screen lock PIN maang sakta hai.", 15f, fg)
        action("1. Andee App Info kholo") {
            val uri = Uri.fromParts("package", packageName, null)
            openSettings(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, uri))
        }
        text("STEP 2: Settings → Accessibility → Downloaded apps / Installed services → Andee → Use Andee ON. Realme phone par labels alag ho sakte hain.", 15f, fg)
        consent = CheckBox(this)
        consent.text = "Main samajhta/samajhti hoon: Andee Accessibility ke through doosri apps ki screen padh sakti hai, tap, scroll aur text type kar sakti hai. AI provider ko screen data bheja ja sakta hai. Bank, password, OTP aur wallet ke waqt ise band rakhna chahiye."
        consent.setTextColor(secondary)
        consent.textSize = 14f
        panel.addView(consent)
        accessibilityButton = action("2. Accessibility Settings kholo") {
            if (consent.isChecked) {
                openSettings(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
            }
        }
        accessibilityButton.isEnabled = false
        consent.setOnCheckedChangeListener { _, checked -> accessibilityButton.isEnabled = checked }
        text("STEP 3 (agar floating assistant nahi dikhta): Settings mein Display over other apps permission check karein. Android ki final permission user hi de sakta hai.", 14f)
        action("3. Floating window Settings kholo") {
            val uri = Uri.fromParts("package", packageName, null)
            openSettings(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, uri))
        }
        action("Permission status refresh karo") { updateStatus() }
        text("Security: Android/Google Play Protect disabled rakhna recommend nahi kiya jata. Accessibility enable karne se pehle app ke developer aur source par bharosa hona zaroori hai.", 12f)
        setContentView(scroll)
        updateStatus()
    }

    private fun openSettings(intent: Intent) {
        try {
            startActivity(intent)
        } catch (_: Exception) {
            AlertDialog.Builder(this)
                .setTitle("Settings nahi khul payi")
                .setMessage("Phone Settings ko manually kholkar Andee app select karein. Android ki protected setting ko app automatically ON nahi kar sakti.")
                .setPositiveButton("OK", null)
                .show()
        }
    }

    private fun updateStatus() {
        if (!::status.isInitialized) return
        val service = ComponentName(this, ScreenBodyService::class.java)
        val active = Settings.Secure.getString(
            contentResolver, Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
        ).orEmpty().split(':').any { ComponentName.unflattenFromString(it) == service }
        val overlay = Settings.canDrawOverlays(this)
        status.text = "Accessibility: " + (if (active) "ON ✓" else "OFF / Restricted") +
            "\nFloating window: " + (if (overlay) "ON ✓" else "OFF") +
            "\nYeh app Android ke restricted-settings allow state ko khud nahi badal sakti."
    }

    override fun onResume() {
        super.onResume()
        updateStatus()
    }
}
''', encoding="utf-8")

manifest = root/"app/src/main/AndroidManifest.xml"
tree = ET.parse(manifest)
ANDROID = '{http://schemas.android.com/apk/res/android}'
application = tree.getroot().find("application")
assert application is not None
assert not any(e.get(ANDROID+'name') == '.ui.AccessibilityPermissionGuideActivity'
    for e in application.findall("activity"))
entry = ET.SubElement(application, "activity")
entry.set(ANDROID+'name', ".ui.AccessibilityPermissionGuideActivity")
entry.set(ANDROID+'exported', "false")
entry.set(ANDROID+'label', "Andee • Accessibility Setup")
ET.indent(tree, space="    ")
tree.write(manifest, encoding="utf-8", xml_declaration=True)

# Feature integrity: this is only a settings/UI patch; don't change the AI
# controller, original gesture service or compile settings.
assert (src/"screen/ScreenController.kt").exists()
assert "ScreenBodyService" in (src/"ScreenBodyService.kt").read_text()
assert (root/"app/build.gradle").exists()
print("Original v0.11.0 preserved; new Accessibility setup activity + fix-button route only.")
print("No auto-grant, security bypass, forced Play Protect change, or feature removals.")
