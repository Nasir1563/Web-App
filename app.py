import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Example settings data (you can replace this with database storage)
settings = {
    "site_name": "My Awesome Site",
    "site_description": "A simple website built with Flask and Supabase",
    "contact_email": "contact@myawesomesite.com",
    "support_phone": "+1234567890",
    "address": "1234 Main St, Anytown, USA"
}

@app.context_processor
def inject_settings():
    return dict(settings=settings)

@app.route('/')
def landing():
    if 'user' in session:
        return redirect(url_for('home'))
    return render_template('landing.html')

@app.route('/home')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('home.html')

@app.route('/user_settings', methods=['GET', 'POST'])
def user_settings():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        user_email = request.form['email']
        user_name = request.form['name']
        
        user_id = session['user_id']
        
        try:
            # Fetch existing user data
            user_data = supabase.from_('auth.users').select('raw_user_meta_data').eq('id', user_id).execute()
            print(f"User Data Fetch Response: {user_data}")
            if not user_data.data:
                flash('User not found.')
                return render_template('user_settings.html')
            
            current_meta_data = user_data.data[0]['raw_user_meta_data']
            updated_meta_data = current_meta_data.copy()
            updated_meta_data['name'] = user_name
            
            # Update raw_user_meta_data
            response = supabase.from_('auth.users').update({
                'email': user_email,
                'raw_user_meta_data': updated_meta_data
            }).eq('id', user_id).execute()
            
            print(f"Update Response: {response}")
            
            if response.status_code in [200, 204]:
                flash('User settings updated successfully.')
            else:
                flash(f'Failed to update user settings: {response.json()}')
        except Exception as e:
            print(f"An error occurred: {e}")  # Log the exception for debugging
            flash('An error occurred while updating settings.')
    
    return render_template('user_settings.html')

@app.route('/site_settings', methods=['GET', 'POST'])
def site_settings():
    if 'user' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        site_name = request.form['site_name']
        site_description = request.form['site_description']
        contact_email = request.form['contact_email']
        support_phone = request.form['support_phone']
        address = request.form['address']
        
        settings['site_name'] = site_name
        settings['site_description'] = site_description
        settings['contact_email'] = contact_email
        settings['support_phone'] = support_phone
        settings['address'] = address
        
        flash('Site settings updated successfully.')
    
    return render_template('site_settings.html', settings=settings)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']
        
        try:
            response = supabase.auth.sign_up({'email': email, 'password': password})
            print(f"Registration Response: {response}")
            
            if response.user:
                user_id = response.user.id
                
                # Update user metadata with name
                update_response = supabase.from_('auth.users').update({
                    'raw_user_meta_data': {
                        'name': name
                    }
                }).eq('id', user_id).execute()
                
                print(f"Update Response: {update_response}")
                
                if update_response.status_code in [200, 204]:
                    flash('Registration successful, please log in.')
                else:
                    flash(f'Failed to update user metadata: {update_response.json()}')
                return redirect(url_for('login'))
            else:
                flash('Registration failed.')
        except Exception as e:
            print(f"An error occurred during registration: {e}")  # Log the exception for debugging
            flash('An error occurred during registration.')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['identifier']
        password = request.form['password']
        
        # Authenticate with Supabase using email or name
        response = supabase.auth.sign_in_with_password({
            'email': identifier if '@' in identifier else None,
            'password': password
        })
        
        if response.user is None and '@' not in identifier:
            # If login with email failed, try login with name
            user_record = supabase.from_('auth.users').select('*').eq('raw_user_meta_data->>name', identifier).execute()
            if user_record and len(user_record.data) > 0:
                user_id = user_record.data[0]['id']
                email = user_record.data[0]['email']
                response = supabase.auth.sign_in_with_password({'email': email, 'password': password})
        
        if response.user:
            session['user'] = response.user.email
            session['user_id'] = response.user.id  # Assuming user ID is available
            session['user_role'] = 'admin' if response.user.email == 'admin@myawesomesite.com' else 'user'
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('user_id', None)
    session.pop('user_role', None)
    return redirect(url_for('login'))

@app.route('/sitemap.xml')
def sitemap():
    pages = []
    ten_days_ago = (datetime.now() - timedelta(days=10)).date().isoformat()

    for rule in app.url_map.iter_rules():
        if 'GET' in rule.methods and (rule.defaults is None or len(rule.defaults) >= len(rule.arguments)):
            pages.append([
                f"http://example.com{str(rule.rule)}",
                ten_days_ago
            ])

    sitemap_xml = render_template('sitemap_template.xml', pages=pages)
    response = make_response(sitemap_xml)
    response.headers["Content-Type"] = "application/xml"

    return response

if __name__ == '__main__':
    app.run(debug=True)
