from flask_login import LoginManager, UserMixin
from database import db

class AdminUser(UserMixin):
    def __init__(self, user_id, username):
        self.id = user_id
        self.username = username
    
    def get_id(self):
        return str(self.id)
    
    @staticmethod
    def get(user_id):
        """دریافت کاربر از پایگاه داده بر اساس ID"""
        conn = db.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, username 
                FROM admins 
                WHERE id = %s
            """, (user_id,))
            
            user_data = cur.fetchone()
            cur.close()
            
            if user_data:
                return AdminUser(user_data[0], user_data[1])
            return None
        except Exception as e:
            print(f"Error loading user: {e}")
            return None
        finally:
            conn.close()
    
    @staticmethod
    def authenticate(username, password):
        """احراز هویت کاربر"""
        conn = db.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, username, password_hash 
                FROM admins 
                WHERE username = %s
            """, (username,))
            
            admin_data = cur.fetchone()
            cur.close()
            
            if admin_data and db.verify_password(admin_data[2], password):
                return AdminUser(admin_data[0], admin_data[1])
            return None
        except Exception as e:
            print(f"Error authenticating user: {e}")
            return None
        finally:
            conn.close()

# ایجاد مدیریت لاگین
login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    """لود کاربر از پایگاه داده"""
    try:
        user_id = int(user_id)
        return AdminUser.get(user_id)
    except (ValueError, TypeError):
        return None

@login_manager.unauthorized_handler
def unauthorized():
    """مدیریت دسترسی غیرمجاز"""
    from flask import redirect, url_for, flash
    flash('لطفاً برای دسترسی به این صفحه وارد سیستم شوید.', 'warning')
    return redirect(url_for('login'))