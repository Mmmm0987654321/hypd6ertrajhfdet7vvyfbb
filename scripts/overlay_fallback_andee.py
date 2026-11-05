#!/usr/bin/env python3
"""Provide Andee a Hindi, overlay-independent fallback Activity.

When the operating system denies 'Display over other apps', launch a visible
ordinary Activity rather than showing only a broken overlay-settings loop.
No OS security bypass, no unauthorized screen capture, and no external AI keys.
"""
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

base = Path(sys.argv[1])
rel = "app/src/main/java/net/kuafuai/andee/ui"
target = base / rel / "InAppCompanionActivity.kt"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(r'''package net.kuafuai.andee.ui

import android.app.Activity
import android.app.AlertDialog
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Bundle
import android.provider.Settings
import android.speech.RecognizerIntent
import android.speech.tts.TextToSpeech
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import java.net.URLEncoder
import java.util.Locale

/**
 * An ordinary Android activity works even when the OS refuses an overlay.
 * Limited on purpose: no Accessibility, no screen reading, no automatic Post.
 * The original Andee service is still available when Android allows it.
 */
class InAppCompanionActivity : Activity() {
    private val bg = Color.rgb(9, 16, 32)
    private val card = Color.rgb(23, 34, 53)
    private val accent = Color.rgb(88, 225, 205)
    private val white = Color.rgb(245, 248, 255)
    private val secondary = Color.rgb(180, 195, 215)
    private lateinit var output: TextView
    private lateinit var input: EditText
    private lateinit var permissionStatus: TextView
    private var tts: TextToSpeech? = null

    private fun dp(v: Int): Int = (v * resources.displayMetrics.density + 0.5f).toInt()
    private fun background(color: Int): GradientDrawable =
        GradientDrawable().apply {
            setColor(color)
            cornerRadius = dp(18).toFloat()
        }
    private fun line(parent: LinearLayout, value: String, size: Float, color: Int, weight: Boolean = false): TextView =
        TextView(this).also {
            it.text = value
            it.textSize = size
            it.setTextColor(color)
            if (weight) it.setTypeface(null, Typeface.BOLD)
            parent.addView(it)
        }
    private fun button(parent: LinearLayout, label: String, onclick: () -> Unit) {
        val b = Button(this)
        b.text = label
        b.isAllCaps = false
        b.textSize = 14f
        b.setTextColor(white)
        b.background = background(Color.rgb(44, 64, 88))
        b.setPadding(dp(9), dp(9), dp(9), dp(9))
        b.setOnClickListener { onclick() }
        val lp = LinearLayout.LayoutParams(-1, dp(52))
        lp.topMargin = dp(9)
        parent.addView(b, lp)
    }
    private fun gap(parent: LinearLayout, height: Int) = parent.addView(View(this), LinearLayout.LayoutParams(1, dp(height)))
    private fun panel(root: LinearLayout): LinearLayout =
        LinearLayout(this).also {
            it.orientation = LinearLayout.VERTICAL
            it.setPadding(dp(16), dp(16), dp(16), dp(16))
            it.background = background(card)
            val p = LinearLayout.LayoutParams(-1, -2)
            p.topMargin = dp(14)
            root.addView(it, p)
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = bg
        window.navigationBarColor = bg
        val scroll = ScrollView(this)
        scroll.setBackgroundColor(bg)
        val root = LinearLayout(this)
        root.orientation = LinearLayout.VERTICAL
        root.setPadding(dp(16), dp(20), dp(16), dp(35))
        scroll.addView(root)
        line(root, "ANDEE  •  हिंदी सहायता", 24f, white, true)
        gap(root, 5)
        line(root, "आपका निजी असिस्टेंट — जब floating window की अनुमति न मिले, तब भी यह स्क्रीन काम करती है।", 14f, secondary)

        val p = panel(root)
        permissionStatus = line(p, "", 16f, accent, true)
        gap(p, 8)
        line(p, "Floating window के लिए Android की अनुमति जरूरी है। ऐप यह अनुमति अपने आप नहीं दे सकता। Play Protect बंद न करें।", 13f, secondary)
        button(p, "📱  Android में Andee की अनुमतियाँ देखें") { openAppInfo() }
        button(p, "♿  Accessibility अनुमति की Settings खोलें") {
            // Explicit consent before visiting OS-controlled Accessibility settings.
            // Never toggle the system permission silently.
            val check = android.widget.CheckBox(this).apply {
                text = "मैं समझता/समझती हूँ कि Accessibility से Andee को दूसरी apps की स्क्रीन पढ़ने, लिखने, tap और scroll करने की अनुमति मिल सकती है। यह bank/payment apps को रोकने का प्रयास करेगा, लेकिन पूरी सुरक्षा की गारंटी नहीं है।"
                setTextColor(white)
                textSize = 14f
                setPadding(dp(12), dp(8), dp(12), dp(8))
                isChecked = false
            }
            val dialog = AlertDialog.Builder(this)
                .setTitle("Andee • Screen control permission")
                .setMessage("Andee के Accessibility access से स्क्रीन पर दिखने वाला टेक्स्ट, बटन और app activity पढ़ी जा सकती है। AI backend configure होने पर आपके निर्देश पूरे करने के लिए स्क्रीन की जानकारी उस backend/provider तक जा सकती है। बैंकिंग/भुगतान apps को रोकने के प्रयास किए गए हैं, पर पूर्ण सुरक्षा नहीं है। संवेदनशील जानकारी, password, OTP और वित्तीय स्क्रीन पर Accessibility बंद रखें। Android Settings में अंतिम अनुमति केवल आप दे सकते हैं।")
                .setView(check)
                .setPositiveButton("सहमत हूँ • Settings खोलें", null)
                .setNegativeButton("रद्द करें", null)
                .create()
            dialog.setOnShowListener {
                val yes = dialog.getButton(AlertDialog.BUTTON_POSITIVE)
                yes.isEnabled = false
                check.setOnCheckedChangeListener { _, checked -> yes.isEnabled = checked }
                yes.setOnClickListener {
                    getSharedPreferences("andee_access_consent", MODE_PRIVATE).edit()
                        .putBoolean("consent", true).apply()
                    dialog.dismiss()
                    startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
                }
            }
            dialog.show()
        }
        button(p, "🛑  Accessibility और screen control बंद करें") {
            // Always permit the user to revoke app-level consent immediately,
            // even when Android temporarily hides the Accessibility service.
            getSharedPreferences("andee_access_consent", MODE_PRIVATE).edit()
                .putBoolean("consent", false).apply()
            net.kuafuai.andee.ScreenBodyService.get()?.disableSelf()
            updatePermissionStatus()
            AlertDialog.Builder(this)
                .setTitle("स्क्रीन कंट्रोल बंद")
                .setMessage("Andee का in-app Accessibility consent वापस ले लिया गया है। Android service active हो तो उसे disable करने का अनुरोध भी किया गया है। Settings में इसकी स्थिति जाँच लें।")
                .setPositiveButton("Accessibility Settings") { _, _ ->
                    startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
                }
                .setNegativeButton("ठीक है", null).show()
        }
        button(p, "🔄  Permission status दोबारा जाँचें") {
            updatePermissionStatus()
            if (Settings.canDrawOverlays(this)) {
                AlertDialog.Builder(this).setTitle("अनुमति मिल गई")
                    .setMessage("अब आप मूल Andee interface खोल सकते हैं।")
                    .setPositiveButton("Andee खोलें") { _, _ -> openMainAndee() }
                    .setNegativeButton("यहीं रहें", null).show()
            }
        }
        button(p, "ℹ️  ऐप की सीमा और सुरक्षा") { explain() }

        val q = panel(root)
        line(q, "बोलकर या लिखकर शुरू करें", 17f, white, true)
        gap(q, 10)
        input = EditText(this)
        input.setTextColor(white)
        input.setHintTextColor(secondary)
        input.textSize = 16f
        input.hint = "जैसे: Twitter खोलो या Bitcoin news search करो"
        input.minLines = 2
        input.maxLines = 5
        input.setPadding(dp(12), dp(12), dp(12), dp(12))
        input.background = background(Color.rgb(14, 25, 43))
        q.addView(input, LinearLayout.LayoutParams(-1, -2))
        button(q, "➤  Command चलाएँ") { runCommand(input.text.toString()) }
        button(q, "🎙️  हिंदी में बोलें") { recognizeHindi() }
        output = line(q, "आपके निर्देश का नतीजा यहाँ दिखेगा।", 14f, white)
        output.setPadding(dp(9), dp(13), dp(9), dp(13))
        output.background = background(Color.rgb(15, 27, 44))

        val shortcuts = panel(root)
        line(shortcuts, "जल्दी शुरू करें", 17f, white, true)
        button(shortcuts, "X / Twitter खोलें") { openNamed("com.twitter.android", "https://x.com", "Twitter") }
        button(shortcuts, "Google पर खोजें") { webSearch(input.text.toString().ifBlank { "latest news today" }) }
        button(shortcuts, "ChatGPT खोलें") { openNamed("", "https://chatgpt.com", "ChatGPT") }
        button(shortcuts, "X पोस्ट का ड्राफ्ट साझा करें") { shareOnX(input.text.toString()) }
        gap(root, 14)
        line(root, "नोट: यह सामान्य in-app fallback है। Accessibility permission मिलने और AI backend configure होने पर गैर-वित्तीय apps का screen control उपलब्ध हो सकता है। Full Andee AI के लिए configured backend और Android permissions जरूरी हैं।", 12f, secondary)
        setContentView(scroll)

        tts = TextToSpeech(this) { status ->
            if (status == TextToSpeech.SUCCESS) {
                tts?.setLanguage(Locale.forLanguageTag("hi-IN"))
                tts?.setSpeechRate(0.85f)
            }
        }
        updatePermissionStatus()
    }

    private fun updatePermissionStatus() {
        if (!::permissionStatus.isInitialized) return
        permissionStatus.text = if (Settings.canDrawOverlays(this))
            "✓ Display over other apps की अनुमति चालू है"
        else "⚠ Android ने floating assistant को अनुमति नहीं दी"
    }
    override fun onResume() { super.onResume(); updatePermissionStatus() }
    private fun showResult(message: String, say: Boolean = false) {
        output.text = message
        if (say) tts?.speak(message, TextToSpeech.QUEUE_FLUSH, null, "andee-hi-fallback")
    }
    private fun openAppInfo() {
        try {
            startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                Uri.parse("package:" + packageName)))
        } catch (e: Exception) { showResult("Settings नहीं खुलीं: " + e.message) }
    }
    private fun openMainAndee() {
        val i = Intent(this, SelfCheckActivity::class.java)
        i.putExtra("skip_in_app_fallback", true)
        startActivity(i)
        finish()
    }
    private fun explain() {
        AlertDialog.Builder(this)
            .setTitle("Android की सुरक्षा")
            .setMessage("Andee का पुराना संस्करण Accessibility से अन्य apps के buttons पढ़कर click कर सकता है। इस संस्करण में Android की Accessibility अनुमति मिलने के बाद गैर-वित्तीय apps पर स्क्रीन कंट्रोल उपलब्ध हो सकता है। बैंकिंग ऐप को रोकने के लिए जाँचें जोड़ी गई हैं, पर सुरक्षा की पूर्ण गारंटी नहीं है। यह संस्करण सामान्य Android apps खोल सकता है, Google पर खोज सकता है और पोस्ट का ड्राफ्ट X तक साझा कर सकता है। Publish पर आखिरी पुष्टि आपको X में करनी होगी। Overlay permission की अंतिम अनुमति केवल Android देता है।")
            .setPositiveButton("समझ गया", null).show()
    }
    private fun recognizeHindi() {
        try {
            val i = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            i.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            i.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "hi-IN")
            i.putExtra(RecognizerIntent.EXTRA_PROMPT, "अपना निर्देश हिंदी में बोलें")
            startActivityForResult(i, 335)
        } catch (e: Exception) {
            showResult("इस फ़ोन पर voice recognition उपलब्ध नहीं है। आप नीचे लिख सकते हैं।")
        }
    }
    @Deprecated("Android legacy result API is compatible with minSdk 30")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == 335 && resultCode == RESULT_OK) {
            val list = data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
            val heard = list?.firstOrNull().orEmpty()
            input.setText(heard)
            runCommand(heard)
        }
    }
    private fun runCommand(raw: String) {
        val text = raw.trim()
        if (text.isEmpty()) { showResult("पहले अपना निर्देश बोलिए या लिखिए।", true); return }
        val lower = text.lowercase(Locale.ROOT)
        when {
            lower.contains("twitter") || lower.contains("ट्विटर") || lower == "x kholo" || lower.contains("एक्स खोल") ->
                if (lower.contains("post") || lower.contains("पोस्ट") || lower.contains("tweet"))
                    shareOnX(text.substringAfter(":", "").trim())
                else openNamed("com.twitter.android", "https://x.com", "Twitter")
            lower.contains("chatgpt") || lower.contains("चैटजीपीटी") || lower.contains("चैट जीपीटी") ->
                openNamed("", "https://chatgpt.com", "ChatGPT")
            lower.contains("whatsapp") || lower.contains("व्हाट्सएप") ->
                openNamed("com.whatsapp", "https://web.whatsapp.com", "WhatsApp")
            lower.contains("youtube") || lower.contains("यूट्यूब") ->
                openNamed("com.google.android.youtube", "https://youtube.com", "YouTube")
            lower.contains("chrome") || lower.contains("क्रोम") ->
                openNamed("com.android.chrome", "https://google.com", "Chrome")
            lower.contains("google") || lower.contains("गूगल") || lower.contains("search") ||
            lower.contains("खोज") || lower.contains("dhoond") || lower.contains("ढूंढ") ||
            lower.contains("news") || lower.contains("न्यूज़") ->
                webSearch(text)
            else -> showResult("यह सीमित offline screen है। मैं आपके फोन में app खोल सकती हूँ, X पर आपका लिखा post draft साझा कर सकती हूँ या Google search खोल सकती हूँ। सामान्य AI conversation के लिए Andee backend configuration चाहिए।", true)
        }
    }
    private fun openNamed(packageId: String, url: String, name: String) {
        try {
            val i = if (packageId.isNotBlank())
                packageManager.getLaunchIntentForPackage(packageId)
            else null
            startActivity(i ?: Intent(Intent.ACTION_VIEW, Uri.parse(url)))
            showResult(name + " खोल दिया।")
        } catch (e: Exception) { showResult(name + " अभी नहीं खुल सका: " + e.message) }
    }
    private fun webSearch(query: String) {
        try {
            val url = "https://www.google.com/search?q=" +
                URLEncoder.encode(query, "UTF-8")
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
            showResult("Google पर खोज खोल दी: " + query)
        } catch (e: Exception) { showResult("Google search नहीं खुली।") }
    }
    private fun shareOnX(post: String) {
        if (post.isBlank()) {
            showResult("X पर पोस्ट करने के लिए पहले post का text लिखो, फिर 'X पोस्ट का ड्राफ्ट साझा करें' दबाओ। मैं अपने-आप कोई पोस्ट publish नहीं करूँगी।", true)
            return
        }
        try {
            val intent = Intent(Intent.ACTION_SEND)
            intent.type = "text/plain"
            intent.putExtra(Intent.EXTRA_TEXT, post)
            intent.setPackage("com.twitter.android")
            try { startActivity(intent) } catch (e: Exception) {
                intent.setPackage(null)
                startActivity(Intent.createChooser(intent, "Post का draft कहाँ साझा करना है?"))
            }
            showResult("X post का draft share कर दिया। अंतिम Post करने से पहले review करें।")
        } catch (e: Exception) { showResult("X draft share नहीं हो पाया: " + e.message) }
    }
    override fun onDestroy() {
        tts?.stop()
        tts?.shutdown()
        super.onDestroy()
    }
}
''', encoding='utf-8')

path = base/"app/src/main/java/net/kuafuai/andee/ui/SelfCheckActivity.kt"
code = path.read_text(encoding='utf-8')
marker = '        Theme.load(this)\n'
assert marker in code, 'SelfCheckActivity launcher marker missing'
code = code.replace(marker, marker + '''
        // Overlay is OS-protected: do not loop a disabled permission screen.
        // Keep a normal Hindi Activity usable until Android actually grants it.
        if ((!Settings.canDrawOverlays(this) ||
                !getSharedPreferences("andee_access_consent", MODE_PRIVATE).getBoolean("consent", false)) &&
            !intent.getBooleanExtra("skip_in_app_fallback", false)) {
            startActivity(Intent(this, InAppCompanionActivity::class.java))
            finish()
            return
        }
''', 1)
path.write_text(code, encoding='utf-8')

manifest = base/"app/src/main/AndroidManifest.xml"
tree = ET.parse(manifest)
ns = '{http://schemas.android.com/apk/res/android}'
app = tree.getroot().find('application')
assert app is not None
for node in app.findall('activity'):
    if node.get(ns+'name') == '.ui.InAppCompanionActivity':
        raise SystemExit('Duplicate fallback activity')
entry = ET.SubElement(app, 'activity')
entry.set(ns+'name','.ui.InAppCompanionActivity')
entry.set(ns+'exported','false')
entry.set(ns+'label','Andee • हिंदी')
ET.indent(tree, space='    ')
tree.write(manifest,encoding='utf-8',xml_declaration=True)

gradle = base/'app/build.gradle'
body=gradle.read_text(encoding='utf-8')
assert 'applicationId "net.kuafuai.andee"' in body
# Different debug package to avoid APK update-signature conflicts.
# Original application's branding and copyright are preserved.
body=body.replace('applicationId "net.kuafuai.andee"',
                  'applicationId "net.kuafuai.andee"\n        applicationIdSuffix ".accessv3"')
gradle.write_text(body,encoding='utf-8')
print('Added normal in-app Android Activity, Hindi commands, TTS, voice input.')
print('Manifest registered the fallback; package suffix avoids debug-signing collision.')
print('NO overlay, Accessibility or Play Protect bypass attempted.')
