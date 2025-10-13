from flask import render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from models.user import User
from models.profile import Profile
from forms.profile_form import ProfileForm
from utils.uploads import save_image, remove_file_safe
from extensions import db
from utils.uploads import save_image, remove_file_safe, create_initials_avatar


@login_required
def index():
    usuarios = User.query.all()
    return render_template("users/index.html", usuarios=usuarios)


@login_required
def create():
    if request.method == "POST":
        nome  = request.form.get("nome")
        email = request.form.get("email")
        role  = request.form.get("role", "aluno")
        senha = request.form.get("password")

        if current_user.role == "coordenador" and role == "coordenador":
            flash("Coordenador não pode criar outro coordenador.", "warning")
            # opcional: manter campos já preenchidos
            return render_template("users/form.html", form_data={"nome": nome, "email": email, "role": "aluno"})

        if not senha:
            flash("A senha é obrigatória!", "danger")
            return render_template("users/form.html", form_data={"nome": nome, "email": email, "role": role})

        user = User(nome=nome, email=email, role=role)
        user.set_password(senha)
        db.session.add(user)
        db.session.commit()

        # 🔹 Cria automaticamente o perfil vinculado
        profile = Profile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()

        flash("Usuário criado com sucesso!", "success")
        return redirect(url_for("users.index"))

    return render_template("users/form.html")


@login_required
def show(user_id):
    """Exibe os detalhes de um usuário"""
    user = User.query.get_or_404(user_id)
    return render_template("users/show.html", user=user)


@login_required
def edit(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        user.nome  = request.form.get("nome")
        user.email = request.form.get("email")
        novo_role  = request.form.get("role", user.role)

        if current_user.role == "coordenador" and novo_role == "coordenador":
            flash("Coordenador não pode atribuir papel de coordenador.", "warning")
            return render_template("users/form.html", user=user)

        nova_senha = request.form.get("password")
        if nova_senha:
            user.set_password(nova_senha)

        user.role = novo_role
        db.session.commit()
        flash("Usuário atualizado com sucesso!", "success")
        return redirect(url_for("users.index"))

    return render_template("users/form.html", user=user)


@login_required
def delete(user_id):
    """Remove um usuário"""
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash("Usuário removido!", "info")
    return redirect(url_for("users.index"))

def profile():
    form = ProfileForm()
    user = current_user
    profile = user.profile  # pode ser None

    # --- criar profile e avatar inicial se não existir (ajuda a evitar undefined no template) ---
    if profile is None:
        profile = Profile(user_id=user.id)
        db.session.add(profile)
        # cria avatar inicial e salva como foto_thumb
        try:
            initials_file = create_initials_avatar(user.nome, size=current_app.config.get("THUMBNAIL_SIZE", (200, 200)))
            profile.foto_thumb = initials_file
        except Exception:
            # se falhar ao gerar avatar, ignore (não bloqueia)
            current_app.logger.exception("Falha ao gerar avatar inicial")
        db.session.commit()

    # --- POST / salvar alterações ---
    if form.validate_on_submit():
        # atualizar campos do form
        profile.telefone = form.telefone.data
        profile.instituicao = form.instituicao.data
        profile.cargo = form.cargo.data
        profile.bio = form.bio.data

        # remover foto se checkbox enviado
        if request.form.get('remove_foto'):
            remove_file_safe(profile.foto)
            remove_file_safe(profile.foto_thumb)
            profile.foto = None
            profile.foto_thumb = None

        # processar novo upload (se houver)
        file_field = form.foto.data
        has_upload = False
        if file_field:
            # algumas vezes file_field existe mas sem filename (checagem defensiva)
            filename_attr = getattr(file_field, "filename", None)
            if filename_attr:
                has_upload = True

        if has_upload:
            try:
                new_filename, new_thumb = save_image(file_field, user_name=user.nome)
            except Exception:
                current_app.logger.exception("Erro salvando imagem enviada.")
                new_filename, new_thumb = None, None

            # remover antigos apenas se o novo foi gerado
            if new_filename or new_thumb:
                remove_file_safe(profile.foto)
                remove_file_safe(profile.foto_thumb)
                profile.foto = new_filename
                profile.foto_thumb = new_thumb

        # se não houve upload e não houver avatar, garantir avatar com iniciais
        if not profile.foto and not profile.foto_thumb:
            try:
                initials_file = create_initials_avatar(user.nome, size=current_app.config.get("THUMBNAIL_SIZE", (200, 200)))
                profile.foto_thumb = initials_file
            except Exception:
                current_app.logger.exception("Falha ao gerar avatar inicial")

        db.session.commit()
        flash("Perfil atualizado com sucesso.", "success")
        return redirect(url_for("users.profile"))

    # --- GET: preencher form com dados existentes ---
    if request.method == "GET" and profile:
        form.telefone.data = profile.telefone
        form.instituicao.data = profile.instituicao
        form.cargo.data = profile.cargo
        form.bio.data = profile.bio

    # --- construir URLs para template ---
    foto_url = None
    thumb_url = None
    if profile and profile.foto_thumb:
        thumb_url = url_for("static", filename=f"uploads/{profile.foto_thumb}")
    elif profile and profile.foto:
        foto_url = url_for("static", filename=f"uploads/{profile.foto}")

    return render_template(
        "users/profile.html",
        form=form,
        profile=profile,
        foto_url=foto_url,
        thumb_url=thumb_url
    )