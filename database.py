import os
import psycopg2
from psycopg2 import Error, sql
from datetime import datetime, timedelta  # این خط اضافه شد
import hashlib
import binascii

class Database:
    def __init__(self):
        self.db_url = os.environ.get('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable is not set")
    
    def get_connection(self):
        """ایجاد اتصال به پایگاه داده"""
        try:
            conn = psycopg2.connect(self.db_url)
            return conn
        except Error as e:
            print(f"Error connecting to database: {e}")
            raise
    
    def init_db(self):
        """ایجاد جداول در صورت عدم وجود"""
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            
            # جدول ادمین‌ها
            cur.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(80) UNIQUE NOT NULL,
                    password_hash VARCHAR(256) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # جدول اعضا
            cur.execute("""
                CREATE TABLE IF NOT EXISTS members (
                    id SERIAL PRIMARY KEY,
                    full_name VARCHAR(200) NOT NULL,
                    phone VARCHAR(20),
                    email VARCHAR(120),
                    address TEXT,
                    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            # جدول کتاب‌ها
            cur.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(200) NOT NULL,
                    author VARCHAR(200) NOT NULL,
                    isbn VARCHAR(20) UNIQUE,
                    publication_year INTEGER,
                    total_copies INTEGER DEFAULT 1,
                    available_copies INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # جدول امانت‌ها
            cur.execute("""
                CREATE TABLE IF NOT EXISTS borrowings (
                    id SERIAL PRIMARY KEY,
                    book_id INTEGER REFERENCES books(id) ON DELETE CASCADE,
                    member_id INTEGER REFERENCES members(id) ON DELETE CASCADE,
                    borrow_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    due_date TIMESTAMP NOT NULL,
                    return_date TIMESTAMP,
                    is_returned BOOLEAN DEFAULT FALSE
                )
            """)
            
            conn.commit()
            print("Database tables created successfully")
            
            # ایجاد کاربر ادمین پیش‌فرض
            self.create_default_admin()
            
            cur.close()
        except Error as e:
            print(f"Error initializing database: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def create_default_admin(self):
        """ایجاد کاربر ادمین پیش‌فرض"""
        admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            
            # بررسی وجود کاربر
            cur.execute("SELECT id FROM admins WHERE username = %s", (admin_username,))
            if cur.fetchone():
                print("Admin user already exists")
                return
            
            # هش کردن رمز عبور
            password_hash = self._hash_password(admin_password)
            
            cur.execute(
                "INSERT INTO admins (username, password_hash) VALUES (%s, %s)",
                (admin_username, password_hash)
            )
            
            conn.commit()
            print(f"Default admin user created: {admin_username}")
            cur.close()
        except Error as e:
            print(f"Error creating default admin: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def _hash_password(self, password):
        """هش کردن رمز عبور"""
        salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
        pwdhash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'), 
                                     salt, 100000)
        pwdhash = binascii.hexlify(pwdhash)
        return (salt + pwdhash).decode('ascii')
    
    def verify_password(self, stored_password, provided_password):
        """بررسی رمز عبور"""
        salt = stored_password[:64]
        stored_password = stored_password[64:]
        pwdhash = hashlib.pbkdf2_hmac('sha512', 
                                      provided_password.encode('utf-8'), 
                                      salt.encode('ascii'), 
                                      100000)
        pwdhash = binascii.hexlify(pwdhash).decode('ascii')
        return pwdhash == stored_password
    
    # متدهای کاربردی برای اعضا
    def get_all_members(self):
        """دریافت همه اعضا"""
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, full_name, phone, email, address, join_date, is_active 
                FROM members 
                WHERE is_active = TRUE 
                ORDER BY full_name
            """)
            members = cur.fetchall()
            cur.close()
            return members
        finally:
            conn.close()
    
    def add_member(self, full_name, phone, email, address):
        """افزودن عضو جدید"""
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO members (full_name, phone, email, address)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (full_name, phone, email, address))
            member_id = cur.fetchone()[0]
            conn.commit()
            cur.close()
            return member_id
        except Error as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def deactivate_member(self, member_id):
        """غیرفعال کردن عضو"""
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                UPDATE members 
                SET is_active = FALSE 
                WHERE id = %s
            """, (member_id,))
            conn.commit()
            cur.close()
        finally:
            conn.close()
    
    # متدهای کاربردی برای کتاب‌ها
    def get_all_books(self):
        """دریافت همه کتاب‌ها"""
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, title, author, isbn, publication_year, 
                       total_copies, available_copies, created_at
                FROM books 
                ORDER BY title
            """)
            books = cur.fetchall()
            cur.close()
            return books
        finally:
            conn.close()
    
    def get_book_by_id(self, book_id):
        """دریافت کتاب بر اساس ID"""
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, title, author, isbn, publication_year, 
                       total_copies, available_copies
                FROM books 
                WHERE id = %s
            """, (book_id,))
            book = cur.fetchone()
            cur.close()
            return book
        finally:
            conn.close()
    
    def add_book(self, title, author, isbn, publication_year, total_copies):
        """افزودن کتاب جدید"""
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO books (title, author, isbn, publication_year, 
                                 total_copies, available_copies)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (title, author, isbn, publication_year, total_copies, total_copies))
            book_id = cur.fetchone()[0]
            conn.commit()
            cur.close()
            return book_id
        except Error as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def delete_book(self, book_id):
        """حذف کتاب"""
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM books WHERE id = %s", (book_id,))
            conn.commit()
            cur.close()
        finally:
            conn.close()
    
    def search_books(self, search_type, keyword):
        """جستجوی کتاب"""
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            search_pattern = f"%{keyword}%"
            
            if search_type == 'title':
                query = """
                    SELECT id, title, author, available_copies
                    FROM books 
                    WHERE title ILIKE %s 
                    ORDER BY title
                """
            else:  # author
                query = """
                    SELECT id, title, author, available_copies
                    FROM books 
                    WHERE author ILIKE %s 
                    ORDER BY title
                """
            
            cur.execute(query, (search_pattern,))
            results = cur.fetchall()
            cur.close()
            return results
        finally:
            conn.close()
    
    # متدهای کاربردی برای امانت کتاب
    def borrow_book(self, book_id, member_id, days):
        """امانت دادن کتاب"""
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            
            # بررسی موجودی کتاب
            cur.execute("SELECT available_copies FROM books WHERE id = %s", (book_id,))
            book_info = cur.fetchone()
            
            if not book_info:
                raise ValueError("کتاب یافت نشد")
            
            if book_info[0] < 1:
                raise ValueError("کتاب موجود نیست")
            
            # محاسبه تاریخ سررسید
            due_date = datetime.now() + timedelta(days=days)
            
            # ثبت امانت
            cur.execute("""
                INSERT INTO borrowings (book_id, member_id, due_date)
                VALUES (%s, %s, %s)
            """, (book_id, member_id, due_date))
            
            # کاهش موجودی
            cur.execute("""
                UPDATE books 
                SET available_copies = available_copies - 1 
                WHERE id = %s
            """, (book_id,))
            
            conn.commit()
            cur.close()
            return due_date
        except Error as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def return_book(self, book_id):
        """بازگرداندن کتاب"""
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            
            # یافتن امانت فعال
            cur.execute("""
                SELECT id FROM borrowings 
                WHERE book_id = %s AND is_returned = FALSE
                ORDER BY borrow_date DESC LIMIT 1
            """, (book_id,))
            
            borrowing = cur.fetchone()
            if not borrowing:
                raise ValueError("هیچ امانت فعالی برای این کتاب یافت نشد")
            
            borrowing_id = borrowing[0]
            
            # به‌روزرسانی وضعیت بازگشت
            cur.execute("""
                UPDATE borrowings 
                SET is_returned = TRUE, return_date = CURRENT_TIMESTAMP 
                WHERE id = %s
            """, (borrowing_id,))
            
            # افزایش موجودی
            cur.execute("""
                UPDATE books 
                SET available_copies = available_copies + 1 
                WHERE id = %s
            """, (book_id,))
            
            conn.commit()
            cur.close()
        except Error as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def get_borrowed_books(self):
        """دریافت لیست کتاب‌های امانت‌رفته"""
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    borrowings.id as borrowing_id,
                    books.id as book_id,
                    books.title,
                    books.author,
                    members.id as member_id,
                    members.full_name,
                    borrowings.borrow_date,
                    borrowings.due_date,
                    CASE 
                        WHEN borrowings.due_date < CURRENT_DATE THEN 'معوقه'
                        ELSE 'در امانت'
                    END as status
                FROM borrowings
                JOIN books ON borrowings.book_id = books.id
                JOIN members ON borrowings.member_id = members.id
                WHERE borrowings.is_returned = FALSE
                ORDER BY borrowings.due_date
            """)
            borrowed = cur.fetchall()
            cur.close()
            return borrowed
        except Error as e:
            print(f"Error in get_borrowed_books: {e}")
            return []
        finally:
            conn.close()
    
    def get_available_books(self):
        """دریافت لیست کتاب‌های موجود"""
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, title, author 
                FROM books 
                WHERE available_copies > 0
                ORDER BY title
            """)
            books = cur.fetchall()
            cur.close()
            return books
        finally:
            conn.close()
    
    def get_active_members(self):
        """دریافت لیست اعضای فعال"""
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, full_name, phone 
                FROM members 
                WHERE is_active = TRUE
                ORDER BY full_name
            """)
            members = cur.fetchall()
            cur.close()
            return members
        finally:
            conn.close()
    
    # متدهای کاربردی برای آمار
    def get_stats(self):
        """دریافت آمار کلی"""
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            
            # تعداد کتاب‌ها
            cur.execute("SELECT COUNT(*) FROM books")
            total_books = cur.fetchone()[0]
            
            # تعداد اعضای فعال
            cur.execute("SELECT COUNT(*) FROM members WHERE is_active = TRUE")
            total_members = cur.fetchone()[0]
            
            # تعداد کتاب‌های امانت‌رفته
            cur.execute("SELECT COUNT(*) FROM borrowings WHERE is_returned = FALSE")
            total_borrowed = cur.fetchone()[0]
            
            # تعداد کتاب‌های معوقه
            cur.execute("""
                SELECT COUNT(*) FROM borrowings 
                WHERE is_returned = FALSE AND due_date < CURRENT_DATE
            """)
            overdue_books = cur.fetchone()[0]
            
            # کتاب‌های معوقه
            cur.execute("""
                SELECT 
                    books.title,
                    members.full_name,
                    borrowings.due_date
                FROM borrowings
                JOIN books ON borrowings.book_id = books.id
                JOIN members ON borrowings.member_id = members.id
                WHERE borrowings.is_returned = FALSE AND borrowings.due_date < CURRENT_DATE
                ORDER BY borrowings.due_date
                LIMIT 5
            """)
            overdue_list = cur.fetchall()
            
            cur.close()
            
            return {
                'total_books': total_books,
                'total_members': total_members,
                'total_borrowed': total_borrowed,
                'overdue_books': overdue_books,
                'overdue_list': overdue_list
            }
        except Error as e:
            print(f"Error getting stats: {e}")
            return {
                'total_books': 0,
                'total_members': 0,
                'total_borrowed': 0,
                'overdue_books': 0,
                'overdue_list': []
            }
        finally:
            conn.close()
    
    # متدهای احراز هویت
    def authenticate_admin(self, username, password):
        """احراز هویت ادمین"""
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, username, password_hash 
                FROM admins 
                WHERE username = %s
            """, (username,))
            
            admin = cur.fetchone()
            cur.close()
            
            if admin and self.verify_password(admin[2], password):
                return {'id': admin[0], 'username': admin[1]}
            return None
        except Error as e:
            print(f"Error authenticating admin: {e}")
            return None
        finally:
            conn.close()

# نمونه Singleton از کلاس دیتابیس
db = Database()