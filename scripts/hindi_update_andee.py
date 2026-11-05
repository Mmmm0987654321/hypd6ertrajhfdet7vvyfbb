#!/usr/bin/env python3
"""Personal Hindi UI and safe permission-guidance patch for official Andee v0.11.0.
Retains Andee attribution and brand. Does not bypass Android security.
"""
from pathlib import Path
import re
import sys
import shutil

base=Path(sys.argv[1])
def edit(rel, fn):
    p=base/rel
    txt=p.read_text(encoding="utf-8")
    new=fn(txt)
    if new==txt: raise SystemExit("Required patch made no change: "+rel)
    p.write_text(new,encoding="utf-8")
    print("Modified:",rel)

def voice(s):
    s=s.replace('const val LANG_EN = "en"', 'const val LANG_EN = "en"\n        const val LANG_HI = "hi"')
    s=s.replace('if (saved == LANG_ZH) return LANG_ZH','if (saved == LANG_ZH) return LANG_ZH\n            if (saved == LANG_HI) return LANG_HI')
    s=s.replace('LANG_ZH -> return LANG_ZH\n            }', 'LANG_ZH -> return LANG_ZH\n                LANG_HI -> return LANG_HI\n            }')
    s=s.replace('return if (java.util.Locale.getDefault().language == "zh") LANG_ZH else LANG_EN',
                'return when (java.util.Locale.getDefault().language) {\n                "zh" -> LANG_ZH\n                "hi" -> LANG_HI\n                else -> LANG_EN\n            }')
    s=s.replace('uiLanguage(context) == LANG_EN) DEFAULT_LLM_BASE_URL_EN', 'uiLanguage(context) != LANG_ZH) DEFAULT_LLM_BASE_URL_EN')
    s=s.replace('uiLanguage(context) == LANG_EN) DEFAULT_LLM_MODEL_EN', 'uiLanguage(context) != LANG_ZH) DEFAULT_LLM_MODEL_EN')
    assert 'const val LANG_HI = "hi"' in s
    return s
edit("app/src/main/java/net/kuafuai/andee/config/VoiceConfig.kt",voice)
def languagepicker(s):
    s=s.replace('VoiceConfig.LANG_EN to "EN")', 'VoiceConfig.LANG_EN to "EN", VoiceConfig.LANG_HI to "हिं" )')
    assert 'VoiceConfig.LANG_HI' in s
    return s
edit("app/src/main/java/net/kuafuai/andee/ui/LangToggle.kt",languagepicker)
def settings(s):
    s=s.replace('english = saved["lang"] == VoiceConfig.LANG_EN', 'english = saved["lang"] != VoiceConfig.LANG_ZH')
    s=s.replace('VoiceConfig.LANG_EN to "EN",', 'VoiceConfig.LANG_EN to "EN",\n            VoiceConfig.LANG_HI to "हिं",')
    s=s.replace('picked = if (english) VoiceConfig.LANG_EN else VoiceConfig.LANG_ZH,',
                'picked = VoiceConfig.uiLanguage(context),')
    s=s.replace('english = lang == VoiceConfig.LANG_EN', 'english = lang != VoiceConfig.LANG_ZH')
    assert 'VoiceConfig.LANG_HI to "हिं"' in s
    return s
edit("app/src/main/java/net/kuafuai/andee/ui/SettingsUi.kt",settings)
def onboarding(s):
    s=s.replace('listOf(VoiceConfig.LANG_ZH to "中文", VoiceConfig.LANG_EN to "English")',
                'listOf(VoiceConfig.LANG_ZH to "中文", VoiceConfig.LANG_EN to "English", VoiceConfig.LANG_HI to "हिन्दी")')
    s=s.replace('if (code == VoiceConfig.LANG_ZH) "Chinese" else "英文"',
                'when (code) { VoiceConfig.LANG_ZH -> "Chinese"; VoiceConfig.LANG_HI -> "Hindi"; else -> "English" }')
    assert 'VoiceConfig.LANG_HI to "हिन्दी"' in s
    return s
edit("app/src/main/java/net/kuafuai/andee/ui/OnboardingUi.kt",onboarding)
def tts(s):
    s=s.replace('val lang = if (VoiceConfig.uiLanguage(context) == VoiceConfig.LANG_EN) {\n                Locale.US\n            } else {\n                Locale.SIMPLIFIED_CHINESE\n            }',
                'val lang = when (VoiceConfig.uiLanguage(context)) {\n                VoiceConfig.LANG_HI -> Locale.forLanguageTag("hi-IN")\n                VoiceConfig.LANG_ZH -> Locale.SIMPLIFIED_CHINESE\n                else -> Locale.US\n            }')
    assert 'Locale.forLanguageTag("hi-IN")' in s
    return s
edit("app/src/main/java/net/kuafuai/andee/tts/SystemTts.kt",tts)

# Overlay is an Android user-controlled permission. Never grant it programmatically.
# Show an explanatory Hindi message on the launcher Activity, which works before
# the overlay is granted. Offer only standard App Info, not restricted-setting bypass.
def help_ui(s):
    s=s.replace('import android.provider.Settings','import android.provider.Settings\nimport android.app.AlertDialog')
    marker='    override fun onResume() {\n        super.onResume()'
    if marker not in s: raise SystemExit("SelfCheck onResume marker changed upstream")
    s=s.replace(marker, '    private var overlayHintShown = false\n\n'+marker+
      '\n        if (!overlayHintShown && !Settings.canDrawOverlays(this)) {\n'+
      '            overlayHintShown = true\n'+
      '            android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({\n'+
      '                if (isFinishing || isDestroyed || Settings.canDrawOverlays(this)) return@postDelayed\n'+
      '                AlertDialog.Builder(this)\n'+
      '                    .setTitle("Andee को स्क्रीन पर दिखाने की अनुमति नहीं मिली")\n'+
      '                    .setMessage("Android/realme ने Display over other apps की अनुमति रोकी है। यह फोन का सुरक्षा निर्णय है। ऐप अपने-आप इसे चालू नहीं कर सकता। केवल भरोसेमंद ऐप के लिए ही ऐप की जानकारी में जाकर अनुमतियाँ जाँचें। Play Protect बंद न करें। इस संस्करण में अन्य ऐप अपने-आप चलाने वाला Accessibility फ़ीचर शामिल नहीं है।")\n'+
      '                    .setPositiveButton("ऐप की जानकारी") { _, _ ->\n'+
      '                        val details = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,\n'+
      '                            Uri.parse("package:" + packageName))\n'+
      '                        startActivity(details)\n'+
      '                    }\n'+
      '                    .setNegativeButton("ठीक है", null)\n'+
      '                    .show()\n'+
      '            }, 450L)\n'+
      '        }\n')
    assert 'overlayHintShown = true' in s
    return s
edit("app/src/main/java/net/kuafuai/andee/ui/SelfCheckActivity.kt",help_ui)
src=base/"app/src/main/res/values-en/strings.xml"
dst=base/"app/src/main/res/values-hi/strings.xml"
dst.parent.mkdir(parents=True,exist_ok=True)
text=src.read_text(encoding="utf-8")
translations={
"onboarding_prelude_badge":"शुरू करने से पहले",
"onboarding_prelude_title":"आप मुझसे किस भाषा में बात करना चाहेंगे?",
"onboarding_prelude_body":"अपनी भाषा और आवाज़ का विकल्प चुनें। इसे बाद में सेटिंग्स में बदल सकते हैं।",
"onboarding_prelude_lang":"भाषा",
"onboarding_prelude_sound":"आवाज़",
"onboarding_prelude_sound_on":"आवाज़ चालू",
"onboarding_prelude_sound_on_note":"मैं अपने जवाब बोलकर सुनाऊँगा",
"onboarding_prelude_sound_off":"म्यूट",
"onboarding_prelude_sound_off_note":"सिर्फ टेक्स्ट",
"onboarding_prelude_next":"पूरा हुआ",
"onboarding_intro_badge":"नमस्ते, मैं Andee हूँ",
"onboarding_intro_title":"मैं आपके फ़ोन पर आपकी मदद करूँगा।",
"onboarding_permission_overlay_title":"स्क्रीन पर असिस्टेंट दिखाने की अनुमति",
"onboarding_permission_overlay_body":"दूसरे ऐप्स के ऊपर दिखाने की अनुमति केवल तभी दें जब आप इस ऐप पर भरोसा करते हैं। Android सुरक्षा के कारण यह अनुमति रोकी जा सकती है।",
"settings_title":"सेटिंग्स",
"common_cancel":"रद्द करें",
"common_save":"सेव करें",
"check_title_overlay":"दूसरे ऐप्स के ऊपर दिखाएँ",
"check_title_accessibility":"स्क्रीन कंट्रोल (इस सुरक्षित संस्करण में उपलब्ध नहीं)",
"onboarding_prelude_sound_on":"आवाज़ चालू",
"onboarding_prelude_sound_off":"आवाज़ बंद",
"onboarding_intro_chatbot_name":"चैटबॉट",
"onboarding_intro_agent_name":"एजेंट",
"onboarding_intro_me_name":"Andee",
"onboarding_intro_next":"आप क्या-क्या कर सकते हैं?",
"onboarding_setup_skip_note":"पहले से तैयार विकल्प छोड़ दिए जाएँगे",
}
count=0
for key,value in translations.items():
    pattern=r'(<string\s+name="'+re.escape(key)+r'"[^>]*>)([\s\S]*?)(</string>)'
    new, n=re.subn(pattern,lambda m: m.group(1)+value+m.group(3),text,count=1)
    if n:text=new;count+=1
dst.write_text(text,encoding="utf-8")
# Add explicit supported languages to Android's locale config (when present).
locales=base/"app/src/main/res/xml/locales_config.xml"
if locales.exists():
    s=locales.read_text(encoding="utf-8")
    if 'android:name="hi"' not in s:
        s=s.replace("</locale-config>",'    <locale android:name="hi" />\n</locale-config>')
        locales.write_text(s,encoding="utf-8")
print("Hindi string overrides:",count)
print("Hindi language selector, Android TTS locale and missing-overlay explanation added")
