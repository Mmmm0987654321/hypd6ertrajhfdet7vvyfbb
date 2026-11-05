# Andee Hindi: Play Protect installation block — release remediation

**Status (5 November 2026):** User reports the APK downloads successfully but Google Play Protect prevents installation in India. No bypass is attempted. **Not fixed on the phone.**

## Confirmed root cause

Google's enhanced fraud protection blocks many apps installed from browser/chat/file manager sources when they declare Android Accessibility access. The app legitimately declares BIND_ACCESSIBILITY_SERVICE for tap, read, type, scroll, screenshot-related functionality. It cannot keep the same Accessibility capability **and** be guaranteed to sideload on a protected device. Renaming APKs, changing browsers, signing again or wrapping in ZIP do not change the device-enforced policy.

Official Google explanation:
https://blog.google/intl/en-in/products/launching-enhanced-fraud-protection-pilot-in-india/
https://developers.google.com/android/play-protect/warning-dev-guidance

## Source audit of the published v0.11.0-derived APK

1. Original `kuafuai/andee v0.11.0` has `app/build.gradle` `compileSdk 34`, `targetSdk 34` and `agp 8.3.1`. New Google Play submissions must target **API 36** as of 2026-08-31. Changing just `targetSdk` is not enough; upgrade AGP, compileSdk, dependencies and test behavioral changes.
2. The currently distributed APK is debug-signed, not a release-signed AAB prepared through the Google Play Console.
3. This general-purpose AI agent includes autonomous multi-step phone control. Google Play policy prohibits non-accessibility-tool apps autonomously initiating, planning and executing actions/decisions through Accessibility API. Permission disclosure alone cannot fix this. A store-submittable design must scope automation to deterministic, user-defined routines (or meet genuine accessibility-tool eligibility), and undergo Google policy review.
4. Android services can access sensitive data. Existing heuristic bank/finance blocklists are **not** a complete security boundary (web pages and unrecognized packages may be missed). The app must not advertise itself as banking safe.
5. AI backend/LLM may receive on-screen content. Disclose this specifically to the user before permission consent, do not bundle secrets, and offer user-accessible control/revoke.
6. Source is a modified version of KUAFUAI's Andee and must include original branding, copyright, and their modified Apache-2.0 license.

## Compliant path

1. Finish a narrowly scoped, user-directed Accessibility app design, safety and privacy review (including data transmission); add opt-in and one-tap disable control.
2. Upgrade build toolchain and target to Android API 36, test on real Android 14/15/16 devices, resolve breaking runtime/permission changes, build a *release-signed AAB* with protected signing credentials. Do not commit keys.
3. Use the developer's **Google Play Console** account to create the app, complete privacy policy + Data Safety + Accessibility declaration (use cases/disclosure/demo video), upload AAB for an appropriate test track, and await review. Availability/approval not guaranteed.
4. For an erroneous classification of an otherwise compliant app, use Google's [Play Protect appeal](https://support.google.com/googleplay/android-developer/answer/2992033). Do not claim the block is erroneous unless substantiated.
5. Check the test device directly, with explicit user permission, after distribution. A successful Gradle build is not device installation confirmation.

Official policies:
- https://support.google.com/googleplay/android-developer/answer/10964491
- https://support.google.com/googleplay/android-developer/answer/11926878
- https://support.google.com/googleplay/android-developer/answer/9214102
- https://support.google.com/googleplay/android-developer/answer/2992033

## Work already performed on this isolated preparation branch

- Existing Accessibility consent checkbox and bank exclusion checks retained.
- Updated in-app disclosure to warn that screen content may be sent to the configured AI backend and that financial exclusion is not guaranteed.
- Added a clearly labelled **Stop Accessibility / revoke consent** control. This control revokes app consent immediately and asks Android to disable the currently running Accessibility service.
- Kept the production website's `main` branch and the previously published download APK unchanged.

**No APK currently installed on the user's device and no Play Console submission has happened.**
