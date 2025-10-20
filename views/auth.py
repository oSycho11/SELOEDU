import token
from flask import current_app, render_template, redirect, url_for, request, flash
from flask import Blueprint, flash, render_template, request, redirect, url_for, session
from flask_mail import Message
from itsdangerous import SignatureExpired
from flask_login import login_required, login_user, logout_user

from models.user import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")


        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Login realizado com sucesso!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard"))
        else:
            flash("Credenciais inválidas.", "danger")
    
    return redirect(url_for("auth.login"))

def forgot_password():
    '''
    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()
        
        if user:
            reset_url = url_for('auth.reset_password', token=token, _external=True)

            try:
                msg = Message(
                    'Redefinição de Senha',
                    # O sender deve estar configurado no seu app Flask
                    sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@yourdomain.com'), 
                    recipients=[user.email]
                )
                msg.body = f"Olá,\n\nPara redefinir sua senha, clique no link a seguir (válido por 1 hora):\n{reset_url}\n\nSe você não solicitou esta redefinição, por favor, ignore este e-mail.\n"
                email.send(msg)

            except Exception as e:
                # Logar o erro em um sistema de produção
                print(f"Erro ao enviar email: {e}")
                flash("Ocorreu um erro ao tentar enviar o e-mail de redefinição. Tente novamente mais tarde.", "danger")
                return redirect(url_for("auth.forgot_password"))


        flash("Se um usuário com esse e-mail existir em nosso sistema, um link de redefinição de senha foi enviado.", "info")
        return redirect(url_for("auth.login"))

    '''

    return render_template("auth/forgot_password.html")

def reset_password(token): # <-- A função precisa receber o 'token' da URL
    try:
        email = request.form.get("email")
    except SignatureExpired:
        flash("O link de redefinição expirou. Por favor, solicite um novo.", "danger")
        return redirect(url_for("auth.forgot_password"))
    except Exception:
        flash("O link de redefinição é inválido.", "danger")
        return redirect(url_for("auth.forgot_password"))

    # 2. Encontrar o usuário pelo e-mail dentro do token
    user = User.query.filter_by(email=email).first()
    if not user:
        flash("Usuário não encontrado.", "danger")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        password = request.form.get("password")
        password_confirm = request.form.get("password_confirm") # É uma boa prática ter confirmação

        if not password or not password_confirm:
            flash("Por favor, preencha ambos os campos de senha.", "danger")
            return render_template("auth/reset_password.html", token=token)

        if password != password_confirm:
            flash("As senhas não coincidem.", "danger")
            return render_template("auth/reset_password.html", token=token)

        # 3. Atualizar a senha no banco
        # Assumindo que seu modelo User usa 'password_hash'
        # e o 'check_password' usa 'check_password_hash' do werkzeug
        db.session.commit()

        flash("Sua senha foi redefinida com sucesso! Você já pode fazer login.", "success")
        return redirect(url_for("auth.login"))

    # Se for um request GET, apenas mostramos o formulário
    return render_template("auth/reset_password.html", token=token)

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sessão encerrada.", "info")
    return redirect(url_for("auth.login"))