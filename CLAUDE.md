# Wadsworth — Claude Notes

## Android Build & Deploy Sequence

After making changes, use this sequence to pull, build the APK, and stage the build artifacts:

```bash
git fetch && git pull && git add . && git commit -m "update" && git push && cd android && ./build-apk2.sh && cd .. && git add android/wadsworth-signed.apk android/wadsworth-signed.aab && git commit -m "build apk" && git push && exit
```

## Data Backup & Push Sequence

Pull first, then dump (pg_dump must run AFTER git pull or git pull will overwrite the fresh files):

```bash
git pull && sudo -u postgres pg_dump --clean --if-exists --no-owner --no-privileges wadsworth > wadsworth_backup.sql && sudo -u postgres pg_dump --clean --if-exists --no-owner --no-privileges reserve_banks > reserve_banks_backup.sql && git add wadsworth_backup.sql reserve_banks_backup.sql tick_state.txt && git commit -m "data backup $(date -u '+%Y-%m-%d %H:%M UTC')" && git push
```

## Cloudflare Tunnel

```bash
cloudflared tunnel run --token eyJhIjoiYWU3MmMxMWVlNGZlM2IwZDk0MWEzNDE4NGYyZTg0ZDkiLCJ0IjoiMGJjYTI0MTItYzU0Ni00NWU4LWI2ZGItMWU4ZDE4ODMzOGNmIiwicyI6Ik1EYzRZall6Tm1NdFlXRTVOaTAwTkdNM0xUbGpaamt0TTJlbE9XVm1Nelk0TlRRNSJ9
```
