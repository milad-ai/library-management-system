import os
from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
from dotenv import load_dotenv


# بارگذاری متغیرهای محیطی
load_dotenv()

# ایجاد برنامه Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# ایمپورت کلاس دیتابیس و Auth
from database import db
from auth import AdminUser, login_manager

# مقداردهی اولیه LoginManager
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'لطفاً برای دسترسی به این صفحه وارد سیستم شوید.'

# ایجاد جداول دیتابیس در ابتدای اجرا
with app.app_context():
    db.init_db()

# Context processor برای افزودن متغیرهای عمومی به تمام templateها
@app.context_processor
def inject_now():
    """اضافه کردن تاریخ فعلی به تمام templateها"""
    return {'now': datetime.now(), 'current_date': datetime.now()}

# صفحات اصلی
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('لطفاً نام کاربری و رمز عبور را وارد کنید.', 'danger')
            return render_template('login.html')
        
        user = AdminUser.authenticate(username, password)
        if user:
            login_user(user, remember=True)
            session['user_id'] = user.id
            session['username'] = user.username
            flash('ورود موفقیت‌آمیز بود!', 'success')
            
            # ریدایرکت به صفحه‌ای که کاربر قصد دیدنش را داشت
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            flash('نام کاربری یا رمز عبور اشتباه است.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """خروج از سیستم"""
    # پاک کردن session
    session.clear()
    
    # logout از Flask-Login
    if current_user.is_authenticated:
        logout_user()
    
    flash('با موفقیت از سیستم خارج شدید.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    stats = db.get_stats()
    # ایجاد لیست فعالیت‌های اخیر (مثال)
    recent_activities = [
        {
            'title': 'کتاب جدید اضافه شد',
            'time': '5 دقیقه پیش',
            'description': 'کتاب "تاریخ ایران" توسط مدیر اضافه شد'
        },
        {
            'title': 'امانت کتاب',
            'time': '1 ساعت پیش',
            'description': 'کتاب "شاهنامه" به علی محمدی امانت داده شد'
        },
        {
            'title': 'عضویت جدید',
            'time': '2 ساعت پیش',
            'description': 'عضو جدید "مریم احمدی" ثبت نام کرد'
        }
    ]
    return render_template('dashboard.html', stats=stats, recent_activities=recent_activities)

# مدیریت کتاب‌ها
@app.route('/books')
@login_required
def books():
    books_list = db.get_all_books()
    return render_template('books.html', books=books_list)

@app.route('/books/add', methods=['GET', 'POST'])
@login_required
def add_book():
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        isbn = request.form.get('isbn') or None
        publication_year = request.form.get('publication_year')
        total_copies = request.form.get('total_copies', 1)
        
        # اعتبارسنجی داده‌ها
        if not title or len(title) < 2:
            flash('عنوان کتاب باید حداقل ۲ حرف باشد.', 'danger')
            return render_template('add_book.html')
        
        if not author or len(author) < 2:
            flash('نام نویسنده باید حداقل ۲ حرف باشد.', 'danger')
            return render_template('add_book.html')
        
        try:
            publication_year = int(publication_year) if publication_year else None
            total_copies = int(total_copies) if total_copies else 1
            
            book_id = db.add_book(title, author, isbn, publication_year, total_copies)
            flash(f'کتاب "{title}" با موفقیت اضافه شد. کد کتاب: {book_id}', 'success')
            return redirect(url_for('books'))
        except Exception as e:
            flash(f'خطا در افزودن کتاب: {str(e)}', 'danger')
    
    return render_template('add_book.html')

@app.route('/books/<int:book_id>/delete')
@login_required
def delete_book(book_id):
    try:
        book = db.get_book_by_id(book_id)
        if not book:
            flash('کتاب یافت نشد.', 'danger')
        elif book[6] != book[5]:  # اگر available_copies != total_copies
            flash('این کتاب در حال حاضر امانت است و قابل حذف نیست.', 'danger')
        else:
            db.delete_book(book_id)
            flash(f'کتاب "{book[1]}" با موفقیت حذف شد.', 'success')
    except Exception as e:
        flash(f'خطا در حذف کتاب: {str(e)}', 'danger')
    
    return redirect(url_for('books'))

# مدیریت اعضا
@app.route('/members')
@login_required
def members():
    members_list = db.get_all_members()
    return render_template('members.html', members=members_list)

@app.route('/members/add', methods=['GET', 'POST'])
@login_required
def add_member():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        phone = request.form.get('phone') or None
        email = request.form.get('email') or None
        address = request.form.get('address') or None
        
        # اعتبارسنجی داده‌ها
        if not full_name or len(full_name) < 2:
            flash('نام کامل باید حداقل ۲ حرف باشد.', 'danger')
            return render_template('add_member.html')
        
        try:
            member_id = db.add_member(full_name, phone, email, address)
            flash(f'عضو "{full_name}" با موفقیت اضافه شد. کد عضویت: {member_id}', 'success')
            return redirect(url_for('members'))
        except Exception as e:
            flash(f'خطا در افزودن عضو: {str(e)}', 'danger')
    
    return render_template('add_member.html')

@app.route('/members/<int:member_id>/deactivate')
@login_required
def deactivate_member(member_id):
    try:
        # بررسی اینکه عضو کتاب امانت داده دارد یا نه
        borrowed = db.get_borrowed_books()
        has_active_borrowings = False
        member_name = None
        
        for book in borrowed:
            if book[4] == member_id:  # member_id
                has_active_borrowings = True
                member_name = book[5]  # full_name
                break
        
        if has_active_borrowings:
            flash(f'عضو "{member_name}" کتاب‌های امانت داده دارد و قابل غیرفعال کردن نیست.', 'danger')
        else:
            # دریافت نام عضو قبل از غیرفعال کردن
            members = db.get_all_members()
            for member in members:
                if member[0] == member_id:
                    member_name = member[1]
                    break
            
            db.deactivate_member(member_id)
            flash(f'عضو "{member_name}" با موفقیت غیرفعال شد.', 'success')
    except Exception as e:
        flash(f'خطا در غیرفعال کردن عضو: {str(e)}', 'danger')
    
    return redirect(url_for('members'))

# مدیریت امانت کتاب
@app.route('/borrow', methods=['GET', 'POST'])
@login_required
def borrow_book():
    if request.method == 'POST':
        book_id = request.form.get('book_id')
        member_id = request.form.get('member_id')
        days = request.form.get('days', 14)
        
        # اعتبارسنجی داده‌ها
        if not book_id or not member_id:
            flash('لطفاً کتاب و عضو را انتخاب کنید.', 'danger')
            return redirect(url_for('borrow_book'))
        
        try:
            book_id = int(book_id)
            member_id = int(member_id)
            days = int(days)
            
            if days < 1:
                days = 14
            
            due_date = db.borrow_book(book_id, member_id, days)
            flash(f'کتاب با موفقیت امانت داده شد. موعد بازگشت: {due_date.strftime("%Y-%m-%d")}', 'success')
            return redirect(url_for('borrowed_books'))
        except ValueError as e:
            flash(str(e), 'danger')
        except Exception as e:
            flash(f'خطا در امانت دادن کتاب: {str(e)}', 'danger')
    
    # دریافت لیست‌ها برای فرم
    available_books = db.get_available_books()
    active_members = db.get_active_members()
    
    return render_template('borrow_book.html', 
                          available_books=available_books, 
                          active_members=active_members)

@app.route('/return', methods=['GET', 'POST'])
@login_required
def return_book():
    if request.method == 'POST':
        book_id = request.form.get('book_id')
        
        if not book_id:
            flash('لطفاً کتابی را انتخاب کنید.', 'danger')
            return redirect(url_for('return_book'))
        
        try:
            book_id = int(book_id)
            db.return_book(book_id)
            flash('کتاب با موفقیت بازگردانده شد.', 'success')
            return redirect(url_for('borrowed_books'))
        except ValueError as e:
            flash(str(e), 'danger')
        except Exception as e:
            flash(f'خطا در بازگرداندن کتاب: {str(e)}', 'danger')
    
    # دریافت کتاب‌های امانت داده شده
    borrowed_books = db.get_borrowed_books()
    book_choices = []
    for book in borrowed_books:
        if len(book) > 1:  # بررسی طول tuple
            book_choices.append((book[1], f"{book[2]} (نویسنده: {book[3]}) - کد: {book[1]}"))
    
    return render_template('return_book.html', book_choices=book_choices, borrowed_books=borrowed_books)

# جستجو
@app.route('/search', methods=['GET', 'POST'])
@login_required
def search_books():
    results = []
    
    if request.method == 'POST':
        search_type = request.form.get('search_type')
        keyword = request.form.get('keyword')
        
        if not search_type or not keyword:
            flash('لطفاً نوع جستجو و کلیدواژه را وارد کنید.', 'danger')
        elif len(keyword) < 2:
            flash('کلیدواژه باید حداقل ۲ حرف باشد.', 'danger')
        else:
            results = db.search_books(search_type, keyword)
            if not results:
                flash('نتیجه‌ای یافت نشد.', 'info')
    
    return render_template('search_books.html', results=results)

# وضعیت کتاب‌های امانت‌رفته
@app.route('/borrowed')
@login_required
def borrowed_books():
    borrowed_list = db.get_borrowed_books()
    return render_template('borrowed_books.html', borrowed_list=borrowed_list)

# تغییر رمز عبور
@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_password or not new_password or not confirm_password:
            flash('لطفاً تمام فیلدها را پر کنید.', 'danger')
            return render_template('change_password.html')
        
        if new_password != confirm_password:
            flash('رمز عبور جدید و تأیید آن مطابقت ندارند.', 'danger')
            return render_template('change_password.html')
        
        if len(new_password) < 6:
            flash('رمز عبور جدید باید حداقل ۶ حرف باشد.', 'danger')
            return render_template('change_password.html')
        
        # بررسی رمز عبور فعلی
        conn = db.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT password_hash 
                FROM admins 
                WHERE id = %s
            """, (current_user.id,))
            
            result = cur.fetchone()
            if not result:
                flash('کاربر یافت نشد.', 'danger')
                return render_template('change_password.html')
            
            current_hash = result[0]
            cur.close()
            
            if not db.verify_password(current_hash, current_password):
                flash('رمز عبور فعلی اشتباه است.', 'danger')
                return render_template('change_password.html')
            
            # به‌روزرسانی رمز عبور
            new_hash = db._hash_password(new_password)
            cur = conn.cursor()
            cur.execute("""
                UPDATE admins 
                SET password_hash = %s 
                WHERE id = %s
            """, (new_hash, current_user.id))
            
            conn.commit()
            cur.close()
            
            flash('رمز عبور با موفقیت تغییر کرد.', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            flash(f'خطا در تغییر رمز عبور: {str(e)}', 'danger')
            conn.rollback()
        finally:
            conn.close()
    
    return render_template('change_password.html')

# API برای آمار
@app.route('/api/stats')
@login_required
def get_stats():
    stats = db.get_stats()
    return jsonify({
        'total_books': stats['total_books'],
        'total_members': stats['total_members'],
        'total_borrowed': stats['total_borrowed'],
        'overdue_books': stats['overdue_books']
    })

# صفحه پروفایل کاربر
@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

# مدیریت خطاها
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

# همچنین می‌توانیم routeهای استاتیک برای خطاها اضافه کنیم
@app.route('/404')
def page_404():
    return render_template('404.html'), 404

@app.route('/500')
def page_500():
    return render_template('500.html'), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5500))
    app.run(host='0.0.0.0', port=port, debug=True)
