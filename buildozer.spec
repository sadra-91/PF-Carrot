[app]

title = PF-Carrot
package.name = pfcarrot
package.domain = org.test

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,db

version = 0.1

requirements = python3,kivy,requests,pyjnius,python-bidi,arabic-reshaper
icon.filename = icon.png

orientation = portrait
fullscreen = 0

android.permissions = INTERNET

android.api = 34
android.minapi = 24

android.archs = armeabi-v7a,arm64-v8a

android.accept_sdk_license = True
android.allow_backup = True

[buildozer]

log_level = 2
warn_on_root = 1
