# seloedu/utils/uploads.py
import os
from uuid import uuid4
from pathlib import Path
from hashlib import md5

from flask import current_app
from werkzeug.utils import secure_filename

# Tentativa de importar Pillow; se não houver, funcionaremos sem thumbs
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

# ---------- auxiliares ----------

def initials_from_name(name, max_chars=2):
    if not name:
        return "?"
    parts = [p for p in name.strip().split() if p]
    if len(parts) == 1:
        return (parts[0][0:2].upper()).ljust(max_chars)[:max_chars]
    initials = (parts[0][0] + parts[-1][0]).upper()
    return initials[:max_chars]

def color_from_name(name):
    h = md5((name or "").encode("utf-8")).hexdigest()
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    def clamp(x, lo=40, hi=220):
        return max(lo, min(hi, x))
    return (clamp(r), clamp(g), clamp(b))

def _load_font_for_size(size):
    if not PIL_AVAILABLE:
        return None
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            try:
                return ImageFont.truetype(str(p), size=size)
            except Exception:
                pass
    return ImageFont.load_default()

# ---------- remoção segura de arquivo ----------

def remove_file_safe(filename):
    """
    Remove um arquivo dentro do UPLOAD_FOLDER de forma segura.
    Se filename for None ou vazio, não faz nada.
    """
    if not filename:
        return
    try:
        upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
    except Exception:
        # current_app não disponível (import/time), evitar crash
        return

    file_path = upload_folder / filename
    try:
        # garante que estamos removendo apenas arquivos dentro do upload_folder
        if file_path.exists() and upload_folder in file_path.parents:
            file_path.unlink()
    except Exception:
        current_app.logger.exception("Erro removendo arquivo %s", filename)

# ---------- gerar avatar com iniciais ----------

def create_initials_avatar(name, size=(200,200), filename=None, fg=(255,255,255)):
    """
    Gera e salva um PNG com as iniciais do nome.
    Retorna o filename (string) salvo dentro do UPLOAD_FOLDER.
    """
    if not PIL_AVAILABLE:
        # sem Pillow, não conseguimos gerar. Retornar None para sinalizar falha.
        return None

    upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
    upload_folder.mkdir(parents=True, exist_ok=True)

    initials = initials_from_name(name)
    bg = color_from_name(name)

    if filename is None:
        filename = f"initials_{uuid4().hex}.png"
    safe_name = secure_filename(filename)
    out_path = upload_folder / safe_name

    w, h = size
    img = Image.new("RGBA", (w, h), color=bg + (255,))
    draw = ImageDraw.Draw(img)

    font_size = int(h * 0.5)
    font = _load_font_for_size(font_size)
    if font is None:
        font = ImageFont.load_default()

    text_w, text_h = draw.textsize(initials, font=font)
    while (text_w > w * 0.85 or text_h > h * 0.7) and font_size > 10:
        font_size = int(font_size * 0.9)
        font = _load_font_for_size(font_size) or ImageFont.load_default()
        text_w, text_h = draw.textsize(initials, font=font)

    x = (w - text_w) / 2
    y = (h - text_h) / 2 - int(0.05 * h)
    shadow_color = (0, 0, 0, 100)
    draw.text((x+1, y+1), initials, font=font, fill=shadow_color)
    draw.text((x, y), initials, font=font, fill=fg + (255,))

    rgb = img.convert("RGB")
    rgb.save(out_path, format="PNG", optimize=True)
    return safe_name

# ---------- salvar imagem / criar thumbnail ----------

def save_image(file_storage=None, user_name=None):
    """
    Salva arquivo enviado (file_storage) e cria thumbnail se Pillow disponível.
    Se file_storage for None, gera avatar com iniciais baseado em user_name.
    Retorna tuple (filename, thumb_name). filename pode ser None se não houver original.
    """
    upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
    upload_folder.mkdir(parents=True, exist_ok=True)

    # Se houver upload de arquivo válido, salvar e criar thumbnail
    if file_storage:
        filename_ext = None
        try:
            filename_ext = secure_filename(file_storage.filename).rsplit(".", 1)[-1].lower()
        except Exception:
            filename_ext = "png"
        filename = f"{uuid4().hex}.{filename_ext}"
        filepath = upload_folder / filename

        try:
            file_storage.save(filepath)
        except Exception:
            # salvamento falhou
            return None, None

        thumb_name = None
        if PIL_AVAILABLE:
            try:
                img = Image.open(filepath)
                img = img.convert("RGB")
                img.thumbnail(current_app.config.get("THUMBNAIL_SIZE", (200,200)))
                thumb_name = f"thumb_{filename}"
                thumb_path = upload_folder / thumb_name
                img.save(thumb_path, optimize=True)
            except Exception:
                # falha criando thumb
                if thumb_name and (upload_folder / thumb_name).exists():
                    (upload_folder / thumb_name).unlink()
                thumb_name = None

        return filename, thumb_name

    # Sem upload: gerar avatar baseado no nome
    if user_name:
        if PIL_AVAILABLE:
            initials_filename = create_initials_avatar(user_name, size=current_app.config.get("THUMBNAIL_SIZE",(200,200)))
            return None, initials_filename
        else:
            return None, None

    return None, None