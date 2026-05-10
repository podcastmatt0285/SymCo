# Wadsworth — Claude Notes

## Android Build & Deploy Sequence

After making changes, use this sequence to pull, build the APK, and stage the build artifacts:

```bash
git fetch && git pull && git add . && git commit && git push && cd android && ./build-apk2.sh && cd .. && git add android/wadsworth-signed.apk android/wadsworth-signed.aab && exit
```
