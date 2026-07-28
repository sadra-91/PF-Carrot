[app]

title = PF-Carrot

package.name = pfcarrot
package.domain = org.test

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,db

version = 0.1

requirements = python3,kivy,requests,pyjnius,android

icon.filename = icon.png

orientation = portrait

osx.kivy_version = 2.2.0

fullscreen = 0

android.permissions = INTERNET

android.api = 34
android.minapi = 24
android.accept_sdk_license = True

android.archs = arm64-v8a,armeabi-v7a

android.allow_backup = True

[buildozer]

log_level = 2
warn_on_root = 1
