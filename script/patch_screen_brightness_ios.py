#!/usr/bin/env python3
"""
Patch screen_brightness_ios so it compiles under Flutter 3.35+.

Flutter 3.35 removed the following from the iOS framework:
  - the FlutterSceneLifeCycleDelegate protocol
  - FlutterPluginRegistrar.addSceneDelegate(...)
  - FlutterPluginRegistrar.viewController

screen_brightness_ios 2.1.4 (the only published version) still uses all
three, so it fails to compile under Flutter 3.35 with:
  - Cannot find type 'FlutterSceneLifeCycleDelegate' in scope
  - Value of type 'any FlutterPluginRegistrar' has no member 'addSceneDelegate'
  - ... has no member 'viewController'

This is a transitive dependency pulled in by media_kit_video, so we cannot
just remove it. The patch strips the three removed usages. The scene
life-cycle callbacks (sceneWillResignActive / sceneDidBecomeActive /
sceneDidDisconnect) stay in the file as plain methods and simply stop being
invoked by Flutter, which is acceptable for a release build.

Run after `flutter pub get`, before `flutter build ios`.
"""
import glob
import os
import sys


def find_targets():
    roots = [
        os.path.expanduser("~/.pub-cache"),
        "/Users/runner/.pub-cache",
    ]
    pat = os.path.join(
        "{root}",
        "hosted/pub.dev/screen_brightness_ios-*/ios/screen_brightness_ios"
        "/Sources/screen_brightness_ios/ScreenBrightnessIosPlugin.swift",
    )
    found = []
    for r in roots:
        found.extend(glob.glob(pat.format(root=r)))
    return sorted(set(found))


def patch(text):
    # 1) drop the FlutterSceneLifeCycleDelegate conformance from the class
    text = text.replace(
        "FlutterPlugin, FlutterSceneLifeCycleDelegate", "FlutterPlugin"
    )
    # 2) drop registrar.addSceneDelegate(instance) call
    text = text.replace("        registrar.addSceneDelegate(instance)\n", "")
    # 3) replace registrar.viewController lookup with a connectedScenes lookup
    text = text.replace(
        "return registrar.viewController?.view.window?.windowScene?.screen",
        "return UIApplication.shared.connectedScenes"
        ".compactMap({ $0 as? UIWindowScene }).first?.screen",
    )
    return text


def main():
    targets = find_targets()
    if not targets:
        print(
            "screen_brightness_ios ScreenBrightnessIosPlugin.swift not found "
            "in pub-cache; nothing to patch.",
            file=sys.stderr,
        )
        return 1
    for f in targets:
        text = open(f, encoding="utf-8").read()
        new = patch(text)
        if new != text:
            open(f, "w", encoding="utf-8").write(new)
            print("patched: " + f)
        else:
            print("unchanged (already patched or pattern not matched): " + f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
