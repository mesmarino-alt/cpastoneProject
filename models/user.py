from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash

from flask_login import UserMixin
from extensions import bcrypt  # import the bcrypt instance you initialized

class User(UserMixin):
    def __init__(self, id, name, student_id, email, password_hash,
                 profile_photo=None, created_at=None, active=True, role='user'):
        self.id = id
        self.name = name
        self.student_id = student_id
        self.email = email
        self.password_hash = password_hash
        self.profile_photo = profile_photo
        self.created_at = created_at
        self.active = active
        self.role = role

    @staticmethod
    def from_row(row: dict):
        if not row:
            return None
        return User(
            id=row.get('id'),
            name=row.get('name'),
            student_id=row.get('student_id'),
            email=row.get('email'),
            password_hash=row.get('password_hash'),
            profile_photo=row.get('profile_photo'),
            created_at=row.get('created_at'),
            active=row.get('active', True),
            role=row.get('role', 'user') 
        )

    # 🔐 Helpers using bcrypt
    def set_password(self, password: str):
        """Hash and set a new password with bcrypt."""
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password: str) -> bool:
        """Verify a password against the stored bcrypt hash."""
        if not self.password_hash:  # guard against empty values
            return False
        return bcrypt.check_password_hash(self.password_hash, password)

    # Flask-Login required methods
    def is_active(self):
        return bool(self.active)
    
    def is_admin(self):
        return self.role == 'admin'

    def get_id(self):
        return str(self.id)

    def __repr__(self):
        return f"<User id={self.id} email={self.email}>"


class LostItem:
    def __init__(self, id, user_id, name, category, description,
                 last_seen, last_seen_at, status, photo, reported_at):
        self.id = id
        self.user_id = user_id
        self.name = name
        self.category = category
        self.description = description
        self.last_seen = last_seen
        self.last_seen_at = last_seen_at
        self.status = status
        self.photo = photo
        self.reported_at = reported_at

    @staticmethod
    def from_row(row: dict):
        return LostItem(
            id=row.get('id'),
            user_id=row.get('user_id'),
            name=row.get('name'),
            category=row.get('category'),
            description=row.get('description'),
            last_seen=row.get('last_seen'),
            last_seen_at=row.get('last_seen_at'),
            status=row.get('status'),
            photo=row.get('photo'),
            reported_at=row.get('reported_at')
        )


class FoundItem:
    def __init__(self, id, user_id, name, category, description,
                 where_found, found_at, status, photo, reported_at):
        self.id = id
        self.user_id = user_id
        self.name = name
        self.category = category
        self.description = description
        self.where_found = where_found
        self.found_at = found_at
        self.status = status
        self.photo = photo
        self.reported_at = reported_at

    @staticmethod
    def from_row(row: dict):
        return FoundItem(
            id=row.get('id'),
            user_id=row.get('user_id'),
            name=row.get('name'),
            category=row.get('category'),
            description=row.get('description'),
            where_found=row.get('where_found'),
            found_at=row.get('found_at'),
            status=row.get('status'),
            photo=row.get('photo'),
            reported_at=row.get('reported_at')
        )


class Match:
    def __init__(self, id, lost_item_id, found_item_id, score, created_at):
        self.id = id
        self.lost_item_id = lost_item_id
        self.found_item_id = found_item_id
        self.score = score
        self.created_at = created_at

    @staticmethod
    def from_row(row: dict):
        if not row:
            return None
        return Match(
            id=row.get('id'),
            lost_item_id=row.get('lost_item_id'),
            found_item_id=row.get('found_item_id'),
            score=row.get('score'),
            created_at=row.get('created_at')
        )

    def __repr__(self):
        return f"<Match id={self.id} lost={self.lost_item_id} found={self.found_item_id} score={self.score}>"


class Claim:
    def __init__(self, id, match_id, lost_item_id, found_item_id,
                 user_id, status, justification, created_at):
        self.id = id
        self.match_id = match_id
        self.lost_item_id = lost_item_id
        self.found_item_id = found_item_id
        self.user_id = user_id
        self.status = status
        self.justification = justification
        self.created_at = created_at

    @staticmethod
    def from_row(row: dict):
        if not row:
            return None
        return Claim(
            id=row.get('id'),
            match_id=row.get('match_id'),
            lost_item_id=row.get('lost_item_id'),
            found_item_id=row.get('found_item_id'),
            user_id=row.get('user_id'),
            status=row.get('status'),
            justification=row.get('justification'),
            created_at=row.get('created_at')
        )

    def is_pending(self):
        return self.status == 'Pending'

    def is_approved(self):
        return self.status == 'Approved'

    def is_rejected(self):
        return self.status == 'Rejected'

    def __repr__(self):
        return f"<Claim id={self.id} match={self.match_id} status={self.status}>"
