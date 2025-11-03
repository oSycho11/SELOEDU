from extensions import db

class Profile(db.Model):

    __tablename__ = 'profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    telefone = db.Column(db.String(20))
    instituicao = db.Column(db.String(100))
    cargo = db.Column(db.String(50))
    bio = db.Column(db.Text)
    foto = db.Column(db.String(200))
    foto_thumb = db.Column(db.String(200))

    user = db.relationship('User', back_populates='profile')