import sqlite3
import time

# --- EXTENSIVE BLOCKLIST ---
DOMAINS = [
    # --- MAJOR TUBE SITES ---
    "pornhub.com", "xvideos.com", "xnxx.com", "xhamster.com", "xhamster1.com",
    "redtube.com", "youporn.com", "porn.com", "tube8.com", "spankbang.com",
    "youjizz.com", "beeg.com", "eporner.com", "hqporner.com", "thumbzilla.com",
    "motherless.com", "upornia.com", "vporn.com", "tnaflix.com", "drtuber.com",
    "nuvid.com", "cliphunter.com", "fuq.com", "porntrex.com", "keezmovies.com",
    "sunporno.com", "madthumbs.com", "txxx.com", "cumlouder.com", "porn300.com",
    "fapster.xxx", "gotporn.com", "pornhoarder.com", "pornerbros.com",
    "perfectgirls.net", "anysex.com", "bellesa.co", "scrolller.com",

    # --- CAM SITES ---
    "chaturbate.com", "livejasmin.com", "bongacams.com", "stripchat.com",
    "camsoda.com", "cam4.com", "myfreecams.com", "flirt4free.com",
    "streamate.com", "jerkmate.com", "cams.com", "imlive.com", "xlovecam.com",
    "adultwork.com", "skyprivate.com", "cherry.tv", "sakuralive.com",

    # --- FAN & SUBSCRIPTION SITES ---
    "onlyfans.com", "fansly.com", "loyalfans.com", "justfor.fans",
    "admireme.vip", "avn.com", "manyvids.com", "clips4sale.com",
    "iwantclips.com", "sextpanther.com", "fancentro.com", "unlockd.me",
    "my.club", "slushy.com", "4my.fans", "pocketstars.com",

    # --- MAJOR STUDIOS & PAYSITES ---
    "brazzers.com", "realitykings.com", "naughtyamerica.com", "bangbros.com",
    "mofos.com", "digitalplayground.com", "wicked.com", "evilangel.com",
    "hustler.com", "penthouse.com", "playboy.com", "twistys.com",
    "babes.com", "kink.com", "adulttime.com", "teamskeet.com",
    "fakehub.com", "metart.com", "hegre.com", "x-art.com",
    "blacked.com", "tushy.com", "vixen.com", "deeper.com",

    # --- HENTAI & COMICS ---
    "nhentai.net", "hanime.tv", "hentaihaven.xxx", "gelbooru.com",
    "rule34.xxx", "sankakucomplex.com", "fakku.net", "tsumino.com",
    "pururin.io", "hitomi.la", "luscious.net", "multporn.net",
    "8muses.com", "e-hentai.org", "hentai.tv",

    # --- DATING / HOOKUP / OTHERS ---
    "adultfriendfinder.com", "ashleymadison.com", "fetlife.com",
    "pure.app", "feeld.co", "alt.com", "fling.com", "escort alligator",
    "tnaboard.com", "listcrawler.com", "eros.com", "tryst.link",
    "megapersonals.eu", "skiipthegames.com"
]

def main():
    print(f"[*] Connecting to notifly.db...")
    try:
        conn = sqlite3.connect("notifly.db")
        cursor = conn.cursor()
        
        # Ensure table exists
        cursor.execute("CREATE TABLE IF NOT EXISTS nsfw_domains (domain TEXT PRIMARY KEY)")
        
        print(f"[*] Processing {len(DOMAINS)} domains...")
        
        added = 0
        skipped = 0
        
        for d in DOMAINS:
            try:
                # Clean the domain just in case
                clean_d = d.lower().strip()
                cursor.execute("INSERT INTO nsfw_domains (domain) VALUES (?)", (clean_d,))
                added += 1
            except sqlite3.IntegrityError:
                skipped += 1
        
        conn.commit()
        conn.close()
        
        print("\n" + "="*30)
        print(f"SUCCESS!")
        print(f"Added:   {added}")
        print(f"Skipped: {skipped} (Already existed)")
        print("="*30)
        
    except Exception as e:
        print(f"[!] Error: {e}")

if __name__ == "__main__":
    main()
