#!/usr/bin/env python3
"""Prepare target SDK 36 for Google Play submission; never imply Play approval."""
from pathlib import Path
import sys
root=Path(sys.argv[1])
build=root/"app/build.gradle"
libs=root/"gradle/libs.versions.toml"
gradlew=root/"gradle/wrapper/gradle-wrapper.properties"
a=build.read_text(encoding="utf-8")
assert "compileSdk 34" in a and "targetSdk 34" in a
a=a.replace("compileSdk 34","compileSdk 36",1).replace("targetSdk 34","targetSdk 36",1)
build.write_text(a,encoding="utf-8")
b=libs.read_text(encoding="utf-8")
assert 'agp = "8.3.1"' in b
libs.write_text(b.replace('agp = "8.3.1"', 'agp = "8.13.0"'),encoding="utf-8")
c=gradlew.read_text(encoding="utf-8")
assert "gradle-8.4-bin.zip" in c
gradlew.write_text(c.replace("gradle-8.4-bin.zip","gradle-8.13-bin.zip"),encoding="utf-8")
print("Android SDK API 36 + AGP 8.13.0 + Gradle 8.13 target baseline")
