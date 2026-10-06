"""
Facebook Page / Instagram Business via Graph API, Pinterest via API v5 — lecture et publication.
Credentials dans .env (META_PAGE_ID, META_PAGE_ACCESS_TOKEN, META_IG_USER_ID, META_IG_ACCESS_TOKEN,
PINTEREST_ACCESS_TOKEN).

Pinterest — état au 2026-10-06 : l'app "Automatisation Maison Ombrel" (PINTEREST_APP_ID) est en
"Accès à trial en attente" chez Pinterest. Tant que ce statut n'est pas passé à approuvé :
  - PINTEREST_TEST_TOKEN (jeton "Production limitée", généré à la main dans le dashboard, valable
    24 h) suffit pour TOUTES les commandes pin-* de lecture ci-dessous (scopes pins:read,
    boards:read, user_accounts:read, ads:read, catalogs:read).
  - Les commandes d'écriture (pin-create-board, pin-create-pin, pin-create-video-pin) sont déjà
    câblées et prêtes, mais échoueront tant que l'app n'a pas un accès avec les scopes write
    (pins:write, boards:write) — ça nécessite l'approbation du Trial puis un jeton permanent
    obtenu par le flux OAuth complet (PINTEREST_ACCESS_TOKEN), pas le jeton de test 24 h.
  - Dès l'approbation : générer un jeton permanent via OAuth, le mettre dans PINTEREST_ACCESS_TOKEN,
    et toutes les commandes pin-* fonctionnent sans changement de code.

Lecture (toujours directe, sans risque) :
    python3 04-scripts-python/social_api.py fb-info
    python3 04-scripts-python/social_api.py fb-posts [--limit 10]
    python3 04-scripts-python/social_api.py fb-comments <post_id>
    python3 04-scripts-python/social_api.py fb-insights <post_id>
    python3 04-scripts-python/social_api.py fb-reel-insights <video_id>
    python3 04-scripts-python/social_api.py ig-info
    python3 04-scripts-python/social_api.py ig-media [--limit 10]
    python3 04-scripts-python/social_api.py ig-comments <media_id>
    python3 04-scripts-python/social_api.py ig-insights <media_id>
    python3 04-scripts-python/social_api.py ig-limit
    python3 04-scripts-python/social_api.py pin-info
    python3 04-scripts-python/social_api.py pin-boards [--limit 25]
    python3 04-scripts-python/social_api.py pin-board-pins <board_id> [--limit 25]
    python3 04-scripts-python/social_api.py pin-pin-info <pin_id>
    python3 04-scripts-python/social_api.py pin-analytics <pin_id> --debut 2026-09-01 --fin 2026-10-01

Écriture (publication, réponse à un commentaire) — RÈGLE FERME :
    Toutes les commandes d'écriture sont en PREVIEW par défaut : elles affichent
    exactement ce qui serait envoyé et n'appellent PAS l'API. Il faut relire ce
    preview au fondateur mot pour mot dans le chat, obtenir un accord explicite
    pour CE contenu précis, puis relancer la même commande avec --confirm pour
    l'envoyer réellement. Ne jamais ajouter --confirm sans avoir montré le
    preview et reçu un "oui" explicite pour ce contenu-là.

    python3 04-scripts-python/social_api.py fb-publish-text "texte du post" [--confirm]
    python3 04-scripts-python/social_api.py fb-publish-photo <chemin_ou_url_image> "légende" --ia non [--confirm]
    python3 04-scripts-python/social_api.py fb-publish-carousel "légende" <image1> <image2> ... --ia non [--confirm]
    python3 04-scripts-python/social_api.py fb-publish-reel <chemin_video.mp4> "légende" --ia non [--confirm]
    python3 04-scripts-python/social_api.py fb-reply-comment <comment_id> "réponse" [--confirm]
    python3 04-scripts-python/social_api.py ig-publish-photo <chemin_ou_url_image> "légende" --ia oui|non [--confirm]
    python3 04-scripts-python/social_api.py ig-publish-carousel "légende" <image1> <image2> ... --ia oui|non [--confirm]
    python3 04-scripts-python/social_api.py ig-publish-reel <chemin_ou_url_video> "légende" --ia oui|non [--cover <image>] [--trial] [--confirm]
    python3 04-scripts-python/social_api.py ig-reply-comment <comment_id> "réponse" [--confirm]
    python3 04-scripts-python/social_api.py pin-create-board "nom" "description" --privacy public|secret [--confirm]
    python3 04-scripts-python/social_api.py pin-create-pin <board_id> <image> "titre" "description" [--lien <url>] [--confirm]
    python3 04-scripts-python/social_api.py pin-create-video-pin <board_id> <video.mp4> <couverture.jpg> "titre" "description" [--lien <url>] [--confirm]

    Pinterest n'a aucun paramètre API pour une étiquette "contenu IA" (contrairement à Instagram) :
    si le visuel est généré/modifié par IA, le signaler manuellement dans la description du pin ou
    via les réglages de contenu de l'app Pinterest elle-même.

    --ia est obligatoire sur toute publication de média Facebook/Instagram : "oui" pour tout contenu
    généré ou modifié par IA (Higgsfield, Photos Bloc/...). Instagram pose alors
    l'étiquette "Infos IA" (paramètre is_ai_generated). Facebook n'a AUCUN
    paramètre API équivalent : les commandes fb-* refusent --ia oui, ces
    contenus se publient à la main sur Facebook (Meta Business Suite, réglage
    étiquette IA) ou pas du tout.

    --trial (Reels Instagram) : publie en "Essai" (Trial reel), montré d'abord
    aux non-abonnés ; le passage aux abonnés se fait à la main dans l'app.

    Médias locaux : Instagram exige une URL publique. Un chemin local est
    d'abord envoyé dans les Fichiers Shopify (seulement avec --confirm), puis
    son URL CDN est utilisée. Les images non JPEG sont converties en JPEG
    (Instagram n'accepte que le JPEG).

Lots hebdomadaires (validation par lot, voir organique/lots/README.md) :
    python3 04-scripts-python/social_api.py lot-preview <lot.json>
    python3 04-scripts-python/social_api.py lot-publish-due <lot.json> [--confirm]

    lot-publish-due ne publie que si le lot porte "valide_par_fondateur": true
    (posé uniquement après le "oui" explicite du fondateur sur le lot entier),
    et seulement les éléments dont l'heure est passée et le statut "a_publier".
    Le résultat de chaque envoi est réécrit dans le fichier du lot.
"""
import argparse
import datetime
import json
import os
import sys
import tempfile
import time

import requests
from dotenv import load_dotenv

load_dotenv()

FB_API = "https://graph.facebook.com/v26.0"
FB_RUPLOAD = "https://rupload.facebook.com/video-upload/v26.0"
IG_API = "https://graph.instagram.com/v26.0"

FB_PAGE_ID = os.getenv("META_PAGE_ID")
FB_TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN")
IG_USER_ID = os.getenv("META_IG_USER_ID")
IG_TOKEN = os.getenv("META_IG_ACCESS_TOKEN")

PIN_API = "https://api.pinterest.com/v5"
# Jeton permanent (OAuth complet, après approbation du Trial) en priorité ; sinon le jeton de
# test 24 h généré à la main dans le dashboard (lecture seule, scopes limités).
PIN_TOKEN = os.getenv("PINTEREST_ACCESS_TOKEN") or os.getenv("PINTEREST_TEST_TOKEN")

# Métriques vérifiées en v26.0 (les anciennes post_impressions / post_engaged_users sont refusées).
FB_POST_METRICS = ["post_media_view", "post_clicks", "post_reactions_by_type_total"]
FB_REEL_METRICS = ["blue_reels_play_count", "fb_reels_total_plays", "fb_reels_replay_count",
                   "post_impressions_unique", "post_video_avg_time_watched", "post_video_view_time",
                   "post_video_social_actions"]
IG_MEDIA_METRICS = ["views", "reach", "saved", "likes", "comments", "shares", "total_interactions"]
IG_REEL_EXTRA_METRICS = ["ig_reels_avg_watch_time", "ig_reels_video_view_total_time", "reels_skip_rate"]


class ApiError(Exception):
    pass


def _handle(r):
    try:
        data = r.json()
    except ValueError:
        raise ApiError(f"Réponse non-JSON (status {r.status_code}): {r.text[:300]}")
    if "error" in data:
        raise ApiError(json.dumps(data["error"], ensure_ascii=False))
    return data


CONNEXION = "CONNEXION"  # préfixe des erreurs réseau : l'élément reste à publier et sera retenté


def _requete(fn, *args, **kwargs):
    """Requête avec 4 essais espacés (30 s, 60 s, 90 s) : absorbe les courtes coupures du Wi-Fi."""
    for essai in range(4):
        try:
            return fn(*args, timeout=120, **kwargs)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if essai == 3:
                raise ApiError(f"{CONNEXION} : {type(e).__name__}")
            time.sleep(30 * (essai + 1))
        except requests.exceptions.RequestException as e:
            raise ApiError(f"{CONNEXION} : {type(e).__name__}")


def _get(url, params):
    return _handle(_requete(requests.get, url, params=params))


def _post(url, data=None, files=None, headers=None):
    return _handle(_requete(requests.post, url, data=data, files=files, headers=headers))


def _pin_auth():
    if not PIN_TOKEN:
        raise ApiError("Aucun jeton Pinterest disponible (PINTEREST_ACCESS_TOKEN ou PINTEREST_TEST_TOKEN manquant dans .env).")
    return {"Authorization": f"Bearer {PIN_TOKEN}"}


def _pin_get(path, params=None):
    return _handle(requests.get(f"{PIN_API}{path}", params=params, headers=_pin_auth()))


def _pin_post(path, json_body=None, headers=None):
    return _handle(requests.post(f"{PIN_API}{path}", json=json_body, headers={**_pin_auth(), **(headers or {})}))


def _pin_put(path, json_body=None):
    return _handle(requests.put(f"{PIN_API}{path}", json=json_body, headers=_pin_auth()))


def _is_url(path):
    return path.startswith("http://") or path.startswith("https://")


def _ia_flag(ia):
    return ia == "oui"


def _metrics(url, token, metrics):
    """Demande toutes les métriques d'un coup ; si l'API en refuse une, les reprend une par une
    pour ne perdre que celles qui ne sont pas disponibles (les noms changent selon les versions)."""
    try:
        data = _get(url, {"metric": ",".join(metrics), "access_token": token})
        data.pop("paging", None)  # les liens de pagination contiennent le jeton d'accès en clair
        return data
    except ApiError:
        ok, refused = [], {}
        for m in metrics:
            try:
                ok.extend(_get(url, {"metric": m, "access_token": token}).get("data", []))
            except ApiError as e:
                refused[m] = str(e)[:200]
        return {"data": ok, "metriques_refusees": refused}


# ---------- Hébergement dans les Fichiers Shopify (URL publique pour Instagram) ----------

STAGED_UPLOAD = """
mutation($input: [StagedUploadInput!]!) {
  stagedUploadsCreate(input: $input) {
    stagedTargets { url resourceUrl parameters { name value } }
    userErrors { field message }
  }
}
"""

FILE_CREATE = """
mutation($files: [FileCreateInput!]!) {
  fileCreate(files: $files) {
    files { id fileStatus }
    userErrors { field message }
  }
}
"""

FILE_STATUS = """
query($id: ID!) {
  node(id: $id) {
    ... on MediaImage { fileStatus image { url } }
    ... on Video { fileStatus originalSource { url } sources { url mimeType height } }
  }
}
"""


def _to_jpeg(path):
    if path.lower().endswith((".jpg", ".jpeg")):
        return path
    from PIL import Image
    out = os.path.join(tempfile.mkdtemp(), os.path.splitext(os.path.basename(path))[0] + ".jpg")
    Image.open(path).convert("RGB").save(out, "JPEG", quality=92)
    return out


def host_on_shopify(path, timeout=300):
    """Envoie un fichier local dans Fichiers Shopify et renvoie son URL CDN publique."""
    from shopify_helpers import gql

    if not os.path.isfile(path):
        raise ApiError(f"Fichier introuvable : {path}")
    is_video = path.lower().endswith((".mp4", ".mov"))
    if not is_video:
        path = _to_jpeg(path)
    name = os.path.basename(path)
    mime = ("video/quicktime" if name.lower().endswith(".mov") else "video/mp4") if is_video else "image/jpeg"
    size = os.path.getsize(path)

    staged = gql(STAGED_UPLOAD, {"input": [{
        "filename": name, "mimeType": mime, "httpMethod": "POST",
        "resource": "VIDEO" if is_video else "IMAGE", "fileSize": str(size),
    }]})["stagedUploadsCreate"]
    if staged["userErrors"]:
        raise ApiError(json.dumps(staged["userErrors"], ensure_ascii=False))
    target = staged["stagedTargets"][0]
    with open(path, "rb") as f:
        r = requests.post(target["url"], data={p["name"]: p["value"] for p in target["parameters"]},
                          files={"file": (name, f, mime)})
    if r.status_code not in (200, 201, 204):
        raise ApiError(f"Envoi Shopify refusé (status {r.status_code}): {r.text[:300]}")

    created = gql(FILE_CREATE, {"files": [{
        "originalSource": target["resourceUrl"], "contentType": "VIDEO" if is_video else "IMAGE", "alt": name,
    }]})["fileCreate"]
    if created["userErrors"]:
        raise ApiError(json.dumps(created["userErrors"], ensure_ascii=False))
    file_id = created["files"][0]["id"]

    deadline = time.time() + timeout
    while time.time() < deadline:
        node = gql(FILE_STATUS, {"id": file_id})["node"] or {}
        if node.get("fileStatus") == "READY":
            if is_video:
                return node["originalSource"]["url"]
            return node["image"]["url"]
        if node.get("fileStatus") == "FAILED":
            raise ApiError(f"Traitement Shopify échoué pour {name}")
        time.sleep(5)
    raise ApiError(f"Fichier Shopify toujours en traitement après {timeout} s : {name}")


def _public_url(path):
    return path if _is_url(path) else host_on_shopify(path)


# ---------- Lecture ----------

def fb_info():
    return _get(f"{FB_API}/{FB_PAGE_ID}", {
        "fields": "id,name,fan_count,link,about,followers_count",
        "access_token": FB_TOKEN,
    })


def fb_posts(limit=10):
    return _get(f"{FB_API}/{FB_PAGE_ID}/posts", {
        "fields": "id,message,created_time,permalink_url",
        "limit": limit,
        "access_token": FB_TOKEN,
    })


def fb_comments(post_id):
    return _get(f"{FB_API}/{post_id}/comments", {
        "fields": "id,message,from,created_time,like_count",
        "access_token": FB_TOKEN,
    })


def fb_insights(post_id):
    return _metrics(f"{FB_API}/{post_id}/insights", FB_TOKEN, FB_POST_METRICS)


def fb_reel_insights(video_id):
    return _metrics(f"{FB_API}/{video_id}/video_insights", FB_TOKEN, FB_REEL_METRICS)


def ig_info():
    return _get(f"{IG_API}/{IG_USER_ID}", {
        "fields": "id,username,followers_count,media_count",
        "access_token": IG_TOKEN,
    })


def ig_media(limit=10):
    return _get(f"{IG_API}/{IG_USER_ID}/media", {
        "fields": "id,caption,media_type,media_product_type,permalink,timestamp,like_count,comments_count",
        "limit": limit,
        "access_token": IG_TOKEN,
    })


def ig_comments(media_id):
    return _get(f"{IG_API}/{media_id}/comments", {
        "fields": "id,text,username,timestamp,like_count",
        "access_token": IG_TOKEN,
    })


def ig_insights(media_id):
    kind = _get(f"{IG_API}/{media_id}", {"fields": "media_product_type", "access_token": IG_TOKEN})
    metrics = IG_MEDIA_METRICS + (IG_REEL_EXTRA_METRICS if kind.get("media_product_type") == "REELS" else [])
    return _metrics(f"{IG_API}/{media_id}/insights", IG_TOKEN, metrics)


def ig_limit():
    return _get(f"{IG_API}/{IG_USER_ID}/content_publishing_limit", {
        "fields": "config,quota_usage",
        "access_token": IG_TOKEN,
    })


def pin_info():
    return _pin_get("/user_account")


def pin_boards(limit=25):
    return _pin_get("/boards", {"page_size": limit})


def pin_board_pins(board_id, limit=25):
    return _pin_get(f"/boards/{board_id}/pins", {"page_size": limit})


def pin_pin_info(pin_id):
    return _pin_get(f"/pins/{pin_id}")


def pin_analytics(pin_id, start_date, end_date):
    return _pin_get(f"/pins/{pin_id}/analytics", {
        "start_date": start_date,
        "end_date": end_date,
        "metric_types": "IMPRESSION,SAVE,PIN_CLICK,OUTBOUND_CLICK,ENGAGEMENT",
    })


# ---------- Écriture (preview par défaut, --confirm pour envoyer) ----------

def _refuse_fb_ia(ia, action):
    if _ia_flag(ia):
        raise ApiError(f"{action} : contenu IA. Facebook n'a pas de paramètre API pour l'étiquette IA : "
                       "publier à la main dans Meta Business Suite avec l'étiquette, ou ne pas publier sur Facebook.")


def fb_publish_text(message, confirm=False):
    preview = {"action": "fb-publish-text", "page": FB_PAGE_ID, "message": message}
    if not confirm:
        return {"PREVIEW_SEULEMENT": True, **preview}
    return _post(f"{FB_API}/{FB_PAGE_ID}/feed", data={"message": message, "access_token": FB_TOKEN})


def _fb_photo(image, published, caption=None):
    data = {"published": "true" if published else "false", "access_token": FB_TOKEN}
    if caption is not None:
        data["caption"] = caption
    if _is_url(image):
        return _post(f"{FB_API}/{FB_PAGE_ID}/photos", data={**data, "url": image})
    if not os.path.isfile(image):
        raise ApiError(f"Fichier introuvable : {image}")
    with open(image, "rb") as f:
        return _post(f"{FB_API}/{FB_PAGE_ID}/photos", data=data, files={"source": f})


def fb_publish_photo(image, caption, ia, confirm=False):
    preview = {"action": "fb-publish-photo", "page": FB_PAGE_ID, "image": image, "caption": caption, "ia": ia}
    _refuse_fb_ia(ia, "fb-publish-photo")
    if not confirm:
        return {"PREVIEW_SEULEMENT": True, **preview}
    return _fb_photo(image, published=True, caption=caption)


def fb_publish_carousel(caption, images, ia, confirm=False):
    preview = {"action": "fb-publish-carousel", "page": FB_PAGE_ID, "images": images, "caption": caption, "ia": ia}
    _refuse_fb_ia(ia, "fb-publish-carousel")
    if not 2 <= len(images) <= 10:
        raise ApiError("Un carrousel compte de 2 à 10 images.")
    if not confirm:
        return {"PREVIEW_SEULEMENT": True, **preview}
    ids = [_fb_photo(img, published=False)["id"] for img in images]
    data = {"message": caption, "access_token": FB_TOKEN}
    for i, media_id in enumerate(ids):
        data[f"attached_media[{i}]"] = json.dumps({"media_fbid": media_id})
    return _post(f"{FB_API}/{FB_PAGE_ID}/feed", data=data)


def fb_publish_reel(video, caption, ia, confirm=False):
    preview = {"action": "fb-publish-reel", "page": FB_PAGE_ID, "video": video, "caption": caption, "ia": ia}
    _refuse_fb_ia(ia, "fb-publish-reel")
    if not _is_url(video) and not os.path.isfile(video):
        raise ApiError(f"Fichier introuvable : {video}")
    if not confirm:
        return {"PREVIEW_SEULEMENT": True, **preview}
    start = _post(f"{FB_API}/{FB_PAGE_ID}/video_reels", data={"upload_phase": "start", "access_token": FB_TOKEN})
    video_id = start["video_id"]
    headers = {"Authorization": f"OAuth {FB_TOKEN}"}
    if _is_url(video):
        _post(f"{FB_RUPLOAD}/{video_id}", headers={**headers, "file_url": video})
    else:
        with open(video, "rb") as f:
            payload = f.read()
        _post(f"{FB_RUPLOAD}/{video_id}", data=payload,
              headers={**headers, "offset": "0", "file_size": str(len(payload))})
    finish = _post(f"{FB_API}/{FB_PAGE_ID}/video_reels", data={
        "upload_phase": "finish", "video_id": video_id, "video_state": "PUBLISHED",
        "description": caption, "access_token": FB_TOKEN,
    })
    return {"video_id": video_id, "finish": finish}


def fb_reply_comment(comment_id, message, confirm=False):
    preview = {"action": "fb-reply-comment", "comment_id": comment_id, "message": message}
    if not confirm:
        return {"PREVIEW_SEULEMENT": True, **preview}
    return _post(f"{FB_API}/{comment_id}/comments", data={"message": message, "access_token": FB_TOKEN})


def _ig_wait(container_id, timeout=600):
    """Attend qu'un conteneur Instagram (vidéo surtout) soit prêt avant media_publish."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = _get(f"{IG_API}/{container_id}", {"fields": "status_code,status", "access_token": IG_TOKEN})
        if status.get("status_code") == "FINISHED":
            return status
        if status.get("status_code") in ("ERROR", "EXPIRED"):
            raise ApiError(f"Conteneur Instagram {container_id} : {status}")
        time.sleep(5)
    raise ApiError(f"Conteneur Instagram {container_id} toujours en traitement après {timeout} s")


def _ig_publish(container):
    creation_id = container["id"]
    _ig_wait(creation_id)
    published = _post(f"{IG_API}/{IG_USER_ID}/media_publish", data={
        "creation_id": creation_id, "access_token": IG_TOKEN,
    })
    permalink = _get(f"{IG_API}/{published['id']}", {"fields": "permalink", "access_token": IG_TOKEN})
    return {"container": container, "published": published, "permalink": permalink.get("permalink")}


def ig_publish_photo(image, caption, ia, confirm=False):
    preview = {"action": "ig-publish-photo", "account": IG_USER_ID, "image": image, "caption": caption,
               "is_ai_generated": _ia_flag(ia)}
    if not confirm:
        return {"PREVIEW_SEULEMENT": True, **preview}
    data = {"image_url": _public_url(image), "caption": caption, "access_token": IG_TOKEN}
    if _ia_flag(ia):
        data["is_ai_generated"] = "true"
    return _ig_publish(_post(f"{IG_API}/{IG_USER_ID}/media", data=data))


def ig_publish_carousel(caption, images, ia, confirm=False):
    preview = {"action": "ig-publish-carousel", "account": IG_USER_ID, "images": images, "caption": caption,
               "is_ai_generated": _ia_flag(ia)}
    if not 2 <= len(images) <= 10:
        raise ApiError("Un carrousel compte de 2 à 10 images.")
    if not confirm:
        return {"PREVIEW_SEULEMENT": True, **preview}
    children = []
    for img in images:
        child = _post(f"{IG_API}/{IG_USER_ID}/media", data={
            "image_url": _public_url(img), "is_carousel_item": "true", "access_token": IG_TOKEN,
        })
        _ig_wait(child["id"])
        children.append(child["id"])
    data = {"media_type": "CAROUSEL", "children": ",".join(children), "caption": caption, "access_token": IG_TOKEN}
    if _ia_flag(ia):
        data["is_ai_generated"] = "true"
    return _ig_publish(_post(f"{IG_API}/{IG_USER_ID}/media", data=data))


def ig_publish_reel(video, caption, ia, cover=None, trial=False, confirm=False):
    preview = {"action": "ig-publish-reel", "account": IG_USER_ID, "video": video, "cover": cover,
               "caption": caption, "is_ai_generated": _ia_flag(ia), "trial_reel": trial}
    if not _is_url(video) and not os.path.isfile(video):
        raise ApiError(f"Fichier introuvable : {video}")
    if not confirm:
        return {"PREVIEW_SEULEMENT": True, **preview}
    data = {"media_type": "REELS", "video_url": _public_url(video), "caption": caption,
            "share_to_feed": "true", "access_token": IG_TOKEN}
    if cover:
        data["cover_url"] = _public_url(cover)
    if _ia_flag(ia):
        data["is_ai_generated"] = "true"
    if trial:
        data["trial_params"] = json.dumps({"graduation_strategy": "MANUAL"})
    return _ig_publish(_post(f"{IG_API}/{IG_USER_ID}/media", data=data))


def ig_publish_story(media, confirm=False):
    """Story Instagram (image ou vidéo 9:16). L'API ne permet ni légende ni autocollant « Lien »."""
    is_video = (media.lower().split("?")[0]).endswith((".mp4", ".mov"))
    preview = {"action": "ig-publish-story", "account": IG_USER_ID, "media": media}
    if not _is_url(media) and not os.path.isfile(media):
        raise ApiError(f"Fichier introuvable : {media}")
    if not confirm:
        return {"PREVIEW_SEULEMENT": True, **preview}
    data = {"media_type": "STORIES", "access_token": IG_TOKEN}
    data["video_url" if is_video else "image_url"] = _public_url(media)
    return _ig_publish(_post(f"{IG_API}/{IG_USER_ID}/media", data=data))


def ig_reply_comment(comment_id, message, confirm=False):
    preview = {"action": "ig-reply-comment", "comment_id": comment_id, "message": message}
    if not confirm:
        return {"PREVIEW_SEULEMENT": True, **preview}
    return _post(f"{IG_API}/{comment_id}/replies", data={"message": message, "access_token": IG_TOKEN})


def pin_create_board(name, description, privacy="public", confirm=False):
    preview = {"action": "pin-create-board", "name": name, "description": description, "privacy": privacy}
    if not confirm:
        return {"PREVIEW_SEULEMENT": True, **preview}
    return _pin_post("/boards", {"name": name, "description": description, "privacy": privacy})


def pin_create_pin(board_id, image, title, description, link=None, confirm=False):
    preview = {"action": "pin-create-pin", "board_id": board_id, "image": image, "title": title,
               "description": description, "lien": link}
    if not confirm:
        return {"PREVIEW_SEULEMENT": True, **preview}
    body = {
        "board_id": board_id,
        "media_source": {"source_type": "image_url", "url": _public_url(image)},
        "title": title,
        "description": description,
    }
    if link:
        body["link"] = link
    return _pin_post("/pins", body)


def _pin_upload_video(upload_url, upload_parameters, video_path):
    with open(video_path, "rb") as f:
        r = requests.post(upload_url, data=upload_parameters, files={"file": (os.path.basename(video_path), f)})
    if r.status_code not in (200, 201, 204):
        raise ApiError(f"Envoi vidéo Pinterest refusé (status {r.status_code}): {r.text[:300]}")


def _pin_wait_media(media_id, timeout=600):
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = _pin_get(f"/media/{media_id}")
        if status.get("status") == "succeeded":
            return status
        if status.get("status") == "failed":
            raise ApiError(f"Media Pinterest {media_id} échoué : {status}")
        time.sleep(5)
    raise ApiError(f"Media Pinterest {media_id} toujours en traitement après {timeout} s")


def pin_create_video_pin(board_id, video, cover, title, description, link=None, confirm=False):
    preview = {"action": "pin-create-video-pin", "board_id": board_id, "video": video, "cover": cover,
               "title": title, "description": description, "lien": link}
    if not os.path.isfile(video):
        raise ApiError(f"Fichier introuvable : {video}")
    if not confirm:
        return {"PREVIEW_SEULEMENT": True, **preview}
    register = _pin_post("/media", {"media_type": "video"})
    _pin_upload_video(register["upload_url"], register["upload_parameters"], video)
    _pin_wait_media(register["media_id"])
    body = {
        "board_id": board_id,
        "media_source": {
            "source_type": "video_id",
            "media_id": register["media_id"],
            "cover_image_url": _public_url(cover),
        },
        "title": title,
        "description": description,
    }
    if link:
        body["link"] = link
    return _pin_post("/pins", body)


# ---------- Lots hebdomadaires ----------

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _abs(path):
    return path if (not path or _is_url(path) or os.path.isabs(path)) else os.path.join(ROOT, path)


def _publish_item(item, platform, confirm):
    kind, ia = item["type"], item["ia"]
    # Facebook accepte les liens cliquables dans le texte : légende dédiée si fournie.
    caption = item.get("legende_facebook", item["legende"]) if platform == "facebook" else item["legende"]
    medias = [_abs(m) for m in item["medias"]]
    if kind == "story":
        if platform != "instagram":
            raise ApiError("Stories : Instagram seulement par l'API.")
        return ig_publish_story(medias[0], confirm)
    if platform == "instagram":
        if kind == "reel":
            return ig_publish_reel(medias[0], caption, ia, cover=_abs(item.get("couverture")),
                                   trial=item.get("trial", False), confirm=confirm)
        if kind == "carrousel":
            return ig_publish_carousel(caption, medias, ia, confirm)
        return ig_publish_photo(medias[0], caption, ia, confirm)
    if platform == "facebook":
        if kind == "reel":
            return fb_publish_reel(medias[0], caption, ia, confirm)
        if kind == "carrousel":
            return fb_publish_carousel(caption, medias, ia, confirm)
        return fb_publish_photo(medias[0], caption, ia, confirm)
    raise ApiError(f"Plateforme inconnue : {platform}")


def _check_item(item):
    problems = []
    for key in ("id", "date", "type", "medias", "legende", "ia", "plateformes"):
        if key not in item:
            problems.append(f"champ manquant : {key}")
    if item.get("ia") not in ("oui", "non"):
        problems.append('"ia" doit valoir "oui" ou "non"')
    if item.get("type") not in ("reel", "carrousel", "photo", "story"):
        problems.append('"type" doit valoir reel, carrousel, photo ou story')
    for m in item.get("medias", []):
        if not _is_url(m) and not os.path.isfile(_abs(m)):
            problems.append(f"média introuvable : {m}")
    if item.get("ia") == "oui" and "facebook" in item.get("plateformes", []):
        problems.append("contenu IA : Facebook sera ignoré (pas d'étiquette IA par l'API), à publier à la main")
    return problems


def lot_preview(path):
    with open(path) as f:
        lot = json.load(f)
    out = {"lot": lot.get("lot"), "valide_par_fondateur": lot.get("valide_par_fondateur", False), "elements": []}
    for item in sorted(lot["items"], key=lambda i: i.get("date", "")):
        out["elements"].append({
            "id": item.get("id"), "date": item.get("date"), "type": item.get("type"),
            "plateformes": item.get("plateformes"), "ia": item.get("ia"), "trial": item.get("trial", False),
            "medias": item.get("medias"), "legende": item.get("legende"),
            "legende_facebook": item.get("legende_facebook"),
            "statut": item.get("statut", "a_publier"), "problemes": _check_item(item),
        })
    return out


def lot_publish_due(path, confirm=False, max_retard=None, max_envois=None):
    """max_retard (minutes) : un élément plus en retard que ça n'est pas publié (statut « en_retard ») — évite
    une rafale après une mise en veille. max_envois : nombre maximal d'éléments publiés par exécution.
    Avec --confirm, le fichier est réécrit après CHAQUE élément (jamais de double publication après un arrêt)."""
    with open(path) as f:
        lot = json.load(f)
    if not lot.get("valide_par_fondateur"):
        raise ApiError("Lot non validé : \"valide_par_fondateur\" doit être true (après le oui explicite du fondateur).")
    now = datetime.datetime.now()
    report = []
    envois = 0

    def sauver():
        if confirm:
            tmp = path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(lot, f, indent=2, ensure_ascii=False)
            os.replace(tmp, path)

    for item in sorted(lot["items"], key=lambda i: i["date"]):
        if item.get("statut", "a_publier") != "a_publier":
            continue
        quand = datetime.datetime.fromisoformat(item["date"])
        if quand > now:
            continue
        if max_retard is not None and (now - quand).total_seconds() > max_retard * 60:
            if confirm:
                item["statut"] = "en_retard"
                sauver()
            report.append({"id": item["id"], "statut": "en_retard", "prevu": item["date"]})
            continue
        if max_envois is not None and envois >= max_envois:
            break
        envois += 1
        problems = [p for p in _check_item(item) if not p.startswith("contenu IA")]
        if problems:
            item["statut"], item["erreur"] = "erreur", "; ".join(problems)
            report.append({"id": item["id"], "statut": "erreur", "problemes": problems})
            continue
        results = item.setdefault("resultats", {})
        for platform in item["plateformes"]:
            if platform in results and "erreur" not in results[platform]:
                continue
            if platform == "facebook" and item["ia"] == "oui":
                results[platform] = {"ignore": "contenu IA : à publier à la main sur Facebook"}
                continue
            try:
                results[platform] = _publish_item(item, platform, confirm)
            except (ApiError, requests.exceptions.RequestException, RuntimeError) as e:
                msg = str(e) if isinstance(e, ApiError) else f"{CONNEXION} : {type(e).__name__}"
                results[platform] = {"erreur": msg[:500]}
        if confirm:
            failed = [p for p, r in results.items() if "erreur" in r]
            passager = lambda m: m.startswith(CONNEXION) or m.startswith("Conteneur Instagram")
            if failed and all(passager(results[p]["erreur"]) for p in failed) and item.get("tentatives_reseau", 0) < 3:
                # coupure réseau ou traitement Instagram en échec (souvent passager) : l'élément reste à publier,
                # seules les plateformes en échec seront retentées au passage suivant (3 tentatives au plus)
                item.setdefault("tentatives_reseau", 0)
                item["tentatives_reseau"] += 1
                sauver()
                report.append({"id": item["id"], "resultats": results, "retente": True})
                break
            item["statut"] = "erreur" if failed else "publie"
            item["publie_le"] = datetime.datetime.now().isoformat(timespec="minutes")
            sauver()
        report.append({"id": item["id"], "resultats": results})
    return {"PREVIEW_SEULEMENT": not confirm, "maintenant": now.isoformat(timespec="minutes"), "envois": report}


COMMANDS = {
    "fb-info": lambda a: fb_info(),
    "fb-posts": lambda a: fb_posts(a.limit),
    "fb-comments": lambda a: fb_comments(a.id),
    "fb-insights": lambda a: fb_insights(a.id),
    "fb-reel-insights": lambda a: fb_reel_insights(a.id),
    "ig-info": lambda a: ig_info(),
    "ig-media": lambda a: ig_media(a.limit),
    "ig-comments": lambda a: ig_comments(a.id),
    "ig-insights": lambda a: ig_insights(a.id),
    "ig-limit": lambda a: ig_limit(),
    "pin-info": lambda a: pin_info(),
    "pin-boards": lambda a: pin_boards(a.limit),
    "pin-board-pins": lambda a: pin_board_pins(a.id, a.limit),
    "pin-pin-info": lambda a: pin_pin_info(a.id),
    "pin-analytics": lambda a: pin_analytics(a.id, a.debut, a.fin),
    "fb-publish-text": lambda a: fb_publish_text(a.message, a.confirm),
    "fb-publish-photo": lambda a: fb_publish_photo(a.image, a.caption, a.ia, a.confirm),
    "fb-publish-carousel": lambda a: fb_publish_carousel(a.caption, a.images, a.ia, a.confirm),
    "fb-publish-reel": lambda a: fb_publish_reel(a.video, a.caption, a.ia, a.confirm),
    "fb-reply-comment": lambda a: fb_reply_comment(a.id, a.message, a.confirm),
    "ig-publish-photo": lambda a: ig_publish_photo(a.image, a.caption, a.ia, a.confirm),
    "ig-publish-carousel": lambda a: ig_publish_carousel(a.caption, a.images, a.ia, a.confirm),
    "ig-publish-reel": lambda a: ig_publish_reel(a.video, a.caption, a.ia, a.cover, a.trial, a.confirm),
    "ig-reply-comment": lambda a: ig_reply_comment(a.id, a.message, a.confirm),
    "pin-create-board": lambda a: pin_create_board(a.name, a.description, a.privacy, a.confirm),
    "pin-create-pin": lambda a: pin_create_pin(a.board_id, a.image, a.title, a.description, a.lien, a.confirm),
    "pin-create-video-pin": lambda a: pin_create_video_pin(
        a.board_id, a.video, a.cover, a.title, a.description, a.lien, a.confirm),
    "lot-preview": lambda a: lot_preview(a.lot),
    "lot-publish-due": lambda a: lot_publish_due(a.lot, a.confirm, a.max_retard, a.max_envois),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("fb-info", "ig-info", "ig-limit", "pin-info"):
        sub.add_parser(name)

    for name in ("fb-posts", "ig-media"):
        p = sub.add_parser(name)
        p.add_argument("--limit", type=int, default=10)

    p = sub.add_parser("pin-boards")
    p.add_argument("--limit", type=int, default=25)

    p = sub.add_parser("pin-board-pins")
    p.add_argument("id", help="board_id")
    p.add_argument("--limit", type=int, default=25)

    p = sub.add_parser("pin-pin-info")
    p.add_argument("id", help="pin_id")

    p = sub.add_parser("pin-analytics")
    p.add_argument("id", help="pin_id")
    p.add_argument("--debut", required=True, help="date de début AAAA-MM-JJ")
    p.add_argument("--fin", required=True, help="date de fin AAAA-MM-JJ")

    for name in ("fb-comments", "fb-insights", "fb-reel-insights", "ig-comments", "ig-insights"):
        p = sub.add_parser(name)
        p.add_argument("id", help="post_id / video_id (fb) ou media_id (ig)")

    p = sub.add_parser("fb-publish-text")
    p.add_argument("message")
    p.add_argument("--confirm", action="store_true")

    for name in ("fb-publish-photo", "ig-publish-photo"):
        p = sub.add_parser(name)
        p.add_argument("image", help="chemin local ou URL publique")
        p.add_argument("caption")
        p.add_argument("--ia", choices=["oui", "non"], required=True)
        p.add_argument("--confirm", action="store_true")

    for name in ("fb-publish-carousel", "ig-publish-carousel"):
        p = sub.add_parser(name)
        p.add_argument("caption")
        p.add_argument("images", nargs="+", help="2 à 10 chemins locaux ou URL publiques, dans l'ordre")
        p.add_argument("--ia", choices=["oui", "non"], required=True)
        p.add_argument("--confirm", action="store_true")

    for name in ("fb-publish-reel", "ig-publish-reel"):
        p = sub.add_parser(name)
        p.add_argument("video", help="chemin local .mp4 ou URL publique")
        p.add_argument("caption")
        p.add_argument("--ia", choices=["oui", "non"], required=True)
        p.add_argument("--confirm", action="store_true")
        if name == "ig-publish-reel":
            p.add_argument("--cover", help="image de couverture (chemin local ou URL)")
            p.add_argument("--trial", action="store_true", help="publier en Essai (Trial reel)")

    for name in ("fb-reply-comment", "ig-reply-comment"):
        p = sub.add_parser(name)
        p.add_argument("id", help="comment_id")
        p.add_argument("message")
        p.add_argument("--confirm", action="store_true")

    p = sub.add_parser("pin-create-board")
    p.add_argument("name")
    p.add_argument("description")
    p.add_argument("--privacy", choices=["public", "secret"], default="public")
    p.add_argument("--confirm", action="store_true")

    p = sub.add_parser("pin-create-pin")
    p.add_argument("board_id")
    p.add_argument("image", help="chemin local ou URL publique")
    p.add_argument("title")
    p.add_argument("description")
    p.add_argument("--lien", help="URL de destination (ex. fiche produit)")
    p.add_argument("--confirm", action="store_true")

    p = sub.add_parser("pin-create-video-pin")
    p.add_argument("board_id")
    p.add_argument("video", help="chemin local .mp4")
    p.add_argument("cover", help="image de couverture, chemin local ou URL publique")
    p.add_argument("title")
    p.add_argument("description")
    p.add_argument("--lien", help="URL de destination (ex. fiche produit)")
    p.add_argument("--confirm", action="store_true")

    p = sub.add_parser("lot-preview")
    p.add_argument("lot", help="fichier JSON du lot (organique/lots/...)")

    p = sub.add_parser("lot-publish-due")
    p.add_argument("lot", help="fichier JSON du lot (organique/lots/...)")
    p.add_argument("--confirm", action="store_true")
    p.add_argument("--max-retard", type=int, help="minutes : au-delà, l'élément passe en « en_retard » sans être publié")
    p.add_argument("--max-envois", type=int, help="nombre maximal d'éléments publiés par exécution")

    args = parser.parse_args()
    try:
        result = COMMANDS[args.command](args)
    except ApiError as e:
        print(f"Erreur : {e}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
