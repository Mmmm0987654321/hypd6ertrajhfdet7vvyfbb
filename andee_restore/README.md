# Andee original v0.11.0 — Accessibility permission setup only

This is an **unofficial, debug-signed** personal test APK built directly from the original KUAFUAI Andee v0.11.0 sources. It is **not an official KUAFUAI release** and was not reviewed by Google Play.

**Direct Android ARM64 APK:** [Andee_Original_Permission_Guide_Arm64.apk](../downloads/Andee_Original_Permission_Guide_Arm64.apk)

**SHA-256:** `9580e2ad862e3f5be8a5eed345c697550b8deb29672787360459af830fb2953f`

## Exactly what was changed

The existing Android device health check's Accessibility setup button now opens a new `AccessibilityPermissionGuideActivity`. This guide displays:

- Open Andee App Info — the user may optionally choose Settings → Apps → Andee → three-dot menu → **Allow restricted settings**, when available on their device.
- Open Accessibility Settings — the user can enable Andee's Accessibility service themselves.
- Open floating-window settings if the original overlay remains unavailable.
- Check whether Accessibility is enabled and whether overlay permission is granted.
- An explicit explanation that Andee can read and control other apps, and that the device's protected permissions cannot be silently granted.

**All original Andee AI, voice, screen controller, gesture, typing, manifest permissions, backend configuration and app branding remain unchanged.** No manual-screen-only mode or AI screen-action block was added. Upstream Android target API 34 unchanged; not prepared for Google Play submission.

## Safety and limitations

This original version can request broad, sensitive permissions (including SMS and call log) and may handle on-screen data. Sensitive screen access could expose banking, passwords or OTPs if used in those apps. Grant only necessary permissions and do not use Accessibility around secrets. Disabling Google Play Protect increases risk and is not recommended. A build passing on GitHub does **not** prove device installation or functionality; OEM Restricted Settings and Play Protect remain controlled by Android.

Original source: https://github.com/kuafuai/andee/tree/v0.11.0

The original special license and attribution are preserved in [LICENSE.original](LICENSE.original). Modified app includes in-app permission setup guidance; not affiliated with KUAFUAI.
