from flask import Blueprint, flash, render_template, request, redirect, url_for, session
from flask_login import login_required, login_user, logout_user, login_required
from flask_mail import Message
from models.user import User
from utils.token_utils import confirm_token, generate_token
from extensions import mail
from werkzeug.security import generate_password_hash
from extensions import db

def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")


        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Login realizado com sucesso!", "sucess")
            return redirect(url_for("dashboard"))
        else:
            flash("Credenciais inválidas.", "danger")
    
    return render_template("auth/login.html")

@login_required
def logout():
    logout_user()
    flash("Sessão encerrada.", "info")
    return redirect(url_for("auth.login"))

def forgot_password_request():
    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()

        if user:
            token = generate_token(email)

            reset_url = url_for('auth.reset_password', token=token, _external=True)

            msg = Message("Redefinição de Senha",
                          recipients=[email],
                          body=f'Clique no link  para redefinir sua senha: {reset_url}')
            mail.send(msg)

            return redirect(url_for("auth.login"))
        
    return render_template("auth/forgot_password.html")

def reset_password(token):
    email = confirm_token(token)

    if not email:
        flash("token inválido ou expirado.", "danger")
        return redirect(url_for("auth.login"))
    
    user = User.query.filter_by(email=email).first()
    if not user:
        flash("Usuário não encontrado", "danger")
        return redirect(url_for("auth.login"))
    
    if request.method == "POST":
        new_password = request.form.get("password")
        
        if len(new_password) < 6:
            flash("A senha deve ter pelo menos 6 caracteres.", "danger")
            return render_template("auth/reset_password.html", token=token)
        
        user.set_password(new_password)

        db.session.commit()

        flash("Sua senha foi atualizada com sucesso!", "success")
        return redirect(url_for("auth.login"))
        
    return render_template("auth/reset_password.html", token=token)