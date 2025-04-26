from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from datetime import date
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)

NAME = 'guru'
PASSWORD = '123'
app.secret_key = 'supersecretkey'


@app.route('/')
def frontpage():
    return render_template('frontpage.html')


@app.route('/admin')
def admin():
    return render_template('admin.html')


@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if request.method == "POST":
        if request.form['name'] != NAME and request.form['password'] != PASSWORD:
            flash("Invalid username or password")
            return redirect(url_for('admin'))
        else:
            conn = sqlite3.connect('database.db')
            c = conn.cursor()
            today = date.today()
            c.execute("SELECT * from campaign "
                      "WHERE start_date<= ? AND "
                      "end_date>= ?", (today, today))
            ongoing_campaigns = c.fetchall()
            c.execute("SELECT * from sponsors WHERE flag='yes'")
            flag_sponsors = c.fetchall()
            c.execute("SELECT * from influencers WHERE flag='yes'")
            flag_influencers = c.fetchall()
            c.execute("SELECT * from campaign WHERE flag='yes'")
            flag_campaigns = c.fetchall()

            return render_template('admin_dashboard.html', name=request.form['name'],
                                   campaigns=ongoing_campaigns, flag_sponsors=flag_sponsors,
                                   flag_influencers=flag_influencers, flag_campaigns=flag_campaigns)
    else:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        today = date.today()
        c.execute("SELECT * from campaign "
                  "WHERE start_date<= ? AND "
                  "end_date>= ?", (today, today))
        ongoing_campaigns = c.fetchall()
        c.execute("SELECT * from sponsors WHERE flag='yes'")
        flag_sponsors = c.fetchall()
        c.execute("SELECT * from influencers WHERE flag='yes'")
        flag_influencers = c.fetchall()
        c.execute("SELECT * from campaign WHERE flag='yes'")
        flag_campaigns = c.fetchall()

        return render_template('admin_dashboard.html', name=NAME,
                               campaigns=ongoing_campaigns, flag_sponsors=flag_sponsors,
                               flag_influencers=flag_influencers, flag_campaigns=flag_campaigns)


@app.route('/user', methods=['GET', 'POST'])
def user():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(20) NOT NULL,
                role VARCHAR(20) NOT NULL,
                password VARCHAR(20) NOT NULL
            )
        ''')

    conn.commit()
    conn.close()
    return render_template('user.html')


@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        role = request.form['role']

        session['name'] = name
        session['password'] = password

        c.execute('SELECT * FROM users WHERE name = ? AND password = ? AND role = ?',
                  (name, password, role))
        user = c.fetchone()

        if user:
            if user[1] == name and user[3] == password and user[2] == role:
                session['user_id'] = user[0]
                session['name'] = user[1]
                session['role'] = user[2]

                if role == 'influencer':
                    c.execute('SELECT id from influencers WHERE name = ? AND password = ?',
                              (name, password))
                    influ_id = c.fetchone()
                    return redirect(url_for('influencer_dashboard',
                                            influ_id=influ_id[0], name=name, password=password))
                elif role == 'sponsor':
                    c.execute('SELECT id from sponsors WHERE name = ? AND password = ?',
                              (name, password))
                    spon_id = c.fetchone()
                    return redirect(url_for('sponsor_dashboard',
                                            spon_id=spon_id[0], name=name, password=password))
            else:
                flash('Incorrect username or password. Please try again.')
                return render_template('user_login.html')
        else:
            flash('User does not exist.')

        conn.commit()
        conn.close()
    return render_template('user_login.html')


@app.route('/influencer_registration', methods=['GET', 'POST'])
def influencer_registration():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
             CREATE TABLE IF NOT EXISTS influencers (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name VARCHAR(20) NOT NULL,
                 password VARCHAR(20) NOT NULL,
                 category VARCHAR(20) NOT NULL, 
                 niche VARCHAR(20) NOT NULL,
                 media VARCHAR(20) NOT NULL,
                 followers INTEGER NOT NULL
             )
         ''')
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        role = request.form['role']

        c.execute('SELECT * FROM users WHERE name = ? AND password = ?', (name, password))
        user = c.fetchone()

        if user is None:
            c.execute('INSERT INTO users (name, password,role) VALUES (?, ?, ?)',
                      (name, password, role))
        else:
            flash('Your name and password are already registered')
            return redirect(url_for('user_login'))
        conn.commit()
        conn.close()
        return render_template('influencer_registration.html')

    return render_template('influencer_registration.html')


@app.route('/influencer_dashboard/<int:influ_id>/<string:name>/<string:password>', methods=['GET', 'POST'])
def influencer_dashboard(influ_id, name, password):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM campaign WHERE status = 'active'")
    campaigns = c.fetchall()
    requested_ads = c.execute("""
            SELECT ads.ad_id, ads.name AS ad_name, ads.description AS ad_description, ads.payment,
                   ads.status AS ad_status,
                   campaign.camp_id , campaign.name AS campaign_name, campaign.description AS campaign_description
            FROM ads 
            JOIN campaign ON ads.camp_id = campaign.camp_id
            WHERE ads.status = 'sponsor_requested' AND ads.influ_id = ?
                   """, (influ_id,)).fetchall()

    if request.method == "POST":
        name = request.form['name']
        password = request.form['password']
        category = request.form['category']
        niche = request.form['niche']
        media = request.form.getlist('media')
        followers = request.form['reach']
        media = ",".join(media)
        flag='no'
        c.execute(
            'INSERT INTO influencers (name, password,category,niche,media,followers,flag) VALUES (?, ?,?,?,?,?,?)',
            (name, password, category, niche, media, followers,flag))

        flash('Registration successful!')

    today = date.today()
    c.execute("""
        UPDATE campaign
        SET status = CASE
            WHEN end_date <= ? THEN 'inactive'
            ELSE 'active'
        END
    """, (today,))
    c.execute('SELECT id FROM influencers WHERE name = ? and password = ?', (name, password,))
    influ_id = c.fetchone()[0]
    c.execute('SELECT name FROM influencers WHERE id = ?', (influ_id,))
    influ_name = c.fetchone()[0]

    conn.commit()
    conn.close()

    return render_template('influencer_dashboard.html', influ_id=influ_id, name=influ_name,
                           requested_ads=requested_ads, campaigns=campaigns, password=password)


@app.route('/sponsor_registration', methods=['GET', 'POST'])
def sponsor_registration():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
                    CREATE TABLE IF NOT EXISTS sponsors (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(20) NOT NULL,
                        password VARCHAR(20) NOT NULL,
                        industry VARCHAR(20) NOT NULL, 
                        budget INTEGER NOT NULL,
                        flag VARCHAR(10)
                    )
                ''')
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        role = request.form['role']
        print(name, password)

        c.execute('SELECT * FROM users WHERE name = ? AND password = ?', (name, password))
        user = c.fetchone()

        if user is None:
                c.execute('INSERT INTO users (name, password,role) VALUES (?, ?, ?)',
                          (name, password, role))
        else:
            flash('Your name and password are already registered')
            return redirect(url_for('user_login'))
        conn.commit()
        conn.close()
        return render_template('sponsor_registration.html')


@app.route('/sponsor_dashboard/<int:spon_id>/<string:name>/<string:password>', methods=['GET', 'POST'])
def sponsor_dashboard(spon_id, name, password):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM campaign WHERE status = 'active'")
    campaigns = c.fetchall()
    requested_ads = c.execute("""
                SELECT ads.ad_id, ads.name AS ad_name, ads.description AS ad_description, ads.payment,
                       ads.status AS ad_status,
                       campaign.camp_id , campaign.name AS campaign_name, campaign.description AS campaign_description
                FROM ads 
                JOIN campaign ON ads.camp_id = campaign.camp_id
                WHERE ads.status = 'influ_requested' AND ads.spon_id = ?
                       """, (spon_id,)).fetchall()
    if request.method == 'POST':
        session['name'] = request.form['name']
        name = session.get('name')
        password = request.form['password']
        industry = request.form['industry']
        budget = request.form['budget']
        flag='no'
        c.execute(
            'INSERT INTO sponsors (name, password,industry,budget,flag) VALUES (?, ?,?,?,?)',
            (name, password, industry, budget,flag))
        flash('Registration successful!')

    today = date.today()
    c.execute("""
        UPDATE campaign
        SET status = CASE
            WHEN end_date <= ? THEN 'inactive'
            ELSE 'active'
        END
    """, (today,))

    c.execute('SELECT id FROM sponsors WHERE name = ? and password = ?', (name, password,))
    spon_id = c.fetchone()[0]
    c.execute('SELECT name FROM sponsors WHERE id = ?', (spon_id,))
    spon_name = c.fetchone()[0]
    conn.commit()
    conn.close()
    return render_template('sponsor_dashboard.html', name=spon_name, spon_id=spon_id,
                           campaigns=campaigns, requested_ads=requested_ads, password=password)


@app.route('/view_campaign/<int:camp_id>', methods=['POST', 'GET'])
def view_campaign(camp_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM campaign WHERE camp_id = ?", (camp_id,))
    campaign = c.fetchone()
    conn.commit()
    conn.close()
    return render_template('campaign_details.html', campaign=campaign)


@app.route('/influencer_view_campaign/<int:camp_id>', methods=['POST','GET'])
def influencer_view_campaign(camp_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM campaign WHERE camp_id = ?", (camp_id,))
    campaign = c.fetchone()
    conn.commit()
    conn.close()
    return render_template('influencer_view_campaign.html', campaign=campaign)


@app.route('/accept_ad/<int:ad_id>', methods=['POST'])
def accept_ad(ad_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("UPDATE ads SET status='accepted' WHERE ad_id=?", (ad_id,))
    c.execute("SELECT influ_id from ads WHERE ad_id=?",(ad_id,))
    influ_id = c.fetchone()
    c.execute("SELECT name from influencers WHERE id=?", (influ_id[0],))
    influ_name = c.fetchone()
    c.execute("SELECT password from influencers WHERE id=?", (influ_id[0],))
    password = c.fetchone()[0]
    conn.commit()
    conn.close()
    flash('Ad accepted successfully!')
    return redirect(url_for('influencer_dashboard',
                            influ_id=influ_id[0], name=influ_name[0], password=password))


@app.route('/sponsor_accept_ad/<int:ad_id>', methods=['POST'])
def sponsor_accept_ad(ad_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("UPDATE ads SET status='accepted' WHERE ad_id=?", (ad_id,))
    c.execute("SELECT spon_id from ads WHERE ad_id=?",(ad_id,))
    spon_id = c.fetchone()
    c.execute("SELECT name from sponsors WHERE id=?", (spon_id[0],))
    spon_name = c.fetchone()
    c.execute("SELECT password from sponsors WHERE id=?", (spon_id[0],))
    password = c.fetchone()[0]
    conn.commit()
    conn.close()
    flash('Ad accepted successfully!')
    return redirect(url_for('sponsor_dashboard',
                            spon_id=spon_id[0], name=spon_name[0], password=password))


@app.route('/reject_ad/<int:ad_id>', methods=['POST'])
def reject_ad(ad_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT influ_id from ads WHERE ad_id=?",(ad_id,))
    influ_id = c.fetchone()
    c.execute("SELECT name from influencers WHERE id=?", (influ_id[0],))
    influ_name = c.fetchone()
    c.execute("SELECT password from influencers WHERE id=?", (influ_id[0],))
    password = c.fetchone()[0]
    c.execute("UPDATE ads SET status='pending' WHERE ad_id=?", (ad_id,))
    c.execute("UPDATE ads SET influ_id=0 WHERE ad_id=?", (ad_id,))
    c.execute("UPDATE ads SET influ_name='none' WHERE ad_id=?",(ad_id,))
    conn.commit()
    conn.close()
    flash('Ad rejected successfully!')
    return redirect(url_for('influencer_dashboard',
                            influ_id=influ_id[0], name=influ_name[0], password=password))


@app.route('/sponsor_reject_ad/<int:ad_id>', methods=['POST'])
def sponsor_reject_ad(ad_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT spon_id from ads WHERE ad_id=?",(ad_id,))
    spon_id = c.fetchone()
    c.execute("SELECT name from sponsors WHERE id=?", (spon_id[0],))
    spon_name = c.fetchone()
    c.execute("SELECT password from sponsors WHERE id=?", (spon_id[0],))
    password = c.fetchone()[0]
    c.execute("UPDATE ads SET status='pending' WHERE ad_id=?", (ad_id,))
    c.execute("UPDATE ads SET influ_id=0 WHERE ad_id=?", (ad_id,))
    c.execute("UPDATE ads SET influ_name='none' WHERE ad_id=?", (ad_id,))
    conn.commit()
    conn.close()
    flash('Ad rejected successfully!')
    return redirect(url_for('sponsor_dashboard',
                            spon_id=spon_id[0], name=spon_name[0], password=password))


@app.route('/create_campaigns/<int:spon_id>', methods=['GET','POST'])
def create_campaigns(spon_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
                CREATE TABLE IF NOT EXISTS campaign (
                camp_id INTEGER PRIMARY KEY AUTOINCREMENT,
                spon_id INTEGER,
                influ_id INTEGER,
                name VARCHAR(20),
                description VARCHAR(20),
                start_date VARCHAR(15),
                end_date VARCHAR(15),
                budget INTEGER,
                visibility VARCHAR(20),
                goals VARCHAR(20),
                niche VARCHAR(20),
                status VARCHAR(20),
                flag VARCHAR(10)
                )
            ''')
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        budget = request.form['budget']
        visibility = request.form['visibility']
        goals = request.form['goals']
        niche = request.form['niche']
        status = 'waiting'
        flag='no'
        c.execute(
            'INSERT INTO campaign (spon_id,name, description,start_date,end_date,budget,'
            'visibility,goals,niche,status,flag) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
            (spon_id,name, description,start_date,end_date,budget,visibility,goals,niche,status,flag))

        conn.commit()
        flash('Campaign created successfully!')
    conn.close()
    return render_template('create_campaigns.html')


@app.route('/create_ad/<int:camp_id>', methods=['GET','POST'])
def create_ad(camp_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
                    CREATE TABLE IF NOT EXISTS ads (
                    ad_id integer PRIMARY KEY AUTOINCREMENT, 
                    camp_id integer,
                    spon_id integer,
                    influ_id integer,                    
                    name varchar(20),
                    description varchar(50),
                    terms varchar(30),
                    messages varchar(100),
                    payment integer,
                    status varchar(20),
                    influ_name varchar(20)
                    )
                ''')
    if request.method == 'POST':
        spon_id = session.get('sponsor_id')
        influ_id = 0
        name = request.form['name']
        description = request.form['description']
        terms = request.form['terms']
        messages = request.form['messages']
        payment = request.form['payment']
        status = 'pending'
        influ_name = 'none'
        c.execute(
            'INSERT INTO ads (camp_id,spon_id,influ_id,name,description,terms,messages,payment,status,influ_name) '
            'VALUES (?,?,?,?,?,?,?,?,?,?)',
            (camp_id, spon_id,influ_id, name, description, terms, messages, payment, status, influ_name))
        conn.commit()
        conn.close()
        flash('ad created successfully!')
    return render_template('create_ad.html')


@app.route('/campaigns/<int:spon_id>/<string:name>/<string:password>')
def campaigns(spon_id, name, password):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM campaign", )
    campaigns = c.fetchall()
    conn.commit()
    conn.close()
    return render_template('campaigns.html',
                           spon_id=spon_id, name=name, password=password, campaigns=campaigns)


@app.route('/ads_of_campaign/<int:camp_id>/<int:influ_id>/<string:name>/<string:password>', methods=['GET', 'POST'])
def ads_of_campaign(camp_id, influ_id, name, password):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM ads WHERE camp_id=?", (camp_id,))
    ads = c.fetchall()
    c.execute("SELECT name from campaign WHERE camp_id=?", (camp_id,))
    camp_name = c.fetchone()
    conn.commit()
    conn.close()
    return render_template('ads_of_campaign.html', ads=ads,
                           camp_name=camp_name[0], influ_id=influ_id, name=name, password=password)


@app.route('/influ_request_ad/<int:influ_id>/<string:name>/<string:password>', methods=['POST'])
def influ_request_ad(influ_id, name, password):
    ad_id = request.form['ad_id']
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("UPDATE ads SET status = 'influ_requested' WHERE ad_id = ?", (ad_id,))
    c.execute("SELECT name FROM influencers WHERE id=?", (influ_id,))
    influ_name = c.fetchone()
    c.execute("UPDATE ads SET influ_id = ? WHERE ad_id = ?", (influ_id, ad_id,))
    c.execute("UPDATE ads SET influ_name = ? WHERE ad_id = ?", (influ_name[0], ad_id,))
    conn.commit()
    conn.close()
    flash('Request sent successfully!')
    return redirect(url_for('influencer_find', influ_id=influ_id, name=name,
                            password=password))


@app.route('/ad_details/<int:influ_id>', methods=['GET', 'POST'])
def ad_details(influ_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM ads")
    ads = c.fetchall()
    conn.commit()
    conn.close()
    return render_template('ad_details.html', ads=ads, influ_id=influ_id)


@app.route('/request_ad/<int:influ_id>', methods=['POST'])
def request_ad(influ_id):
    ad_id = request.form['ad_id']
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("UPDATE ads SET status = 'sponsor_requested' WHERE ad_id = ?", (ad_id,))
    c.execute("SELECT name FROM influencers WHERE id=?", (influ_id,))
    influ_name = c.fetchone()
    c.execute("UPDATE ads SET influ_id = ? WHERE ad_id = ?", (influ_id, ad_id,))
    c.execute("UPDATE ads SET influ_name = ? WHERE ad_id = ?", (influ_name[0], ad_id,))
    conn.commit()
    conn.close()
    flash('Request sent successfully!')
    return redirect(url_for('ad_details', influ_id=influ_id))


@app.route('/admin_find')
def admin_find():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM sponsors where flag='no'")
    sponsors = c.fetchall()
    c.execute("SELECT * FROM influencers where flag='no'")
    influencers = c.fetchall()
    c.execute("SELECT * FROM campaign where flag='no'")
    campaigns = c.fetchall()
    conn.commit()
    conn.close()
    return render_template('admin_find.html', sponsors=sponsors,
                           influencers=influencers, campaigns=campaigns, name="GURU")


@app.route('/admin_view_sponsor/<int:spon_id>')
def admin_view_sponsor(spon_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM sponsors WHERE id = ?", (spon_id,))
    sponsor = c.fetchone()
    conn.commit()
    conn.close()
    return render_template('admin_view_sponsor.html', sponsor=sponsor)


@app.route('/admin_view_influencer/<int:influ_id>')
def admin_view_influencer(influ_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM influencers WHERE id = ?", (influ_id,))
    influencer = c.fetchone()
    conn.commit()
    conn.close()
    return render_template('admin_view_influencer.html', influencer=influencer)


@app.route('/search_influencers/<int:spon_id>/<string:name>/<string:password>', methods=['GET'])
def search_influencers(spon_id,name,password):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM influencers")
    influencers = c.fetchall()
    query = request.args.get('query', '').lower()
    matched_influencers = [inf for inf in influencers if query in inf[1].lower()]
    conn.commit()
    conn.close()
    return render_template('sponsor_find.html',spon_id=spon_id,
                           name=name, password=password, influencers=matched_influencers)


@app.route('/sponsor_find/<int:spon_id>/<string:name>/<string:password>')
def sponsor_find(spon_id, name, password):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM influencers")
    influencers = c.fetchall()
    conn.commit()
    conn.close()
    return render_template('sponsor_find.html', spon_id=spon_id,
                           name=name, password=password, influencers=influencers)


@app.route('/influencer_find/<int:influ_id>/<string:name>/<string:password>')
def influencer_find(influ_id,name,password):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM campaign")
    campaigns = c.fetchall()
    conn.commit()
    conn.close()
    return render_template('influencer_find.html', influ_id=influ_id,
                           name=name, password= password, campaigns=campaigns)


def create_pie_chart(data, labels, title):
    plt.figure(figsize=(6, 6))
    colormap = plt.get_cmap('Paired', len(data))
    colors = [colormap(i) for i in range(len(data))]
    plt.pie(data, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
    plt.title(title)
    plt.axis('equal')
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    return buf


def create_bar_chart(data, labels, title):
    plt.figure(figsize=(8, 6))
    colormap = plt.get_cmap('Paired', len(data))
    colors = [colormap(i) for i in range(len(data))]
    plt.bar(labels, data, color=colors)
    plt.title(title)
    plt.xlabel('Categories')
    plt.ylabel('Count')
    plt.xticks(rotation=45)
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    return buf


def get_base64_image(buf):
    return base64.b64encode(buf.getvalue()).decode('utf-8')


@app.route('/admin_stats')
def admin_stats():
    conn = sqlite3.connect('database.db')
    conn = conn.cursor()

    sponsors = conn.execute('SELECT * FROM sponsors').fetchall()
    influencers = conn.execute('SELECT * FROM influencers').fetchall()
    campaigns = conn.execute('SELECT * FROM campaign').fetchall()
    ads = conn.execute('SELECT * FROM ads').fetchall()

    flagged_users = conn.execute('''
            SELECT * FROM (
                SELECT id, name, "Sponsor" AS roll FROM sponsors WHERE flag = "yes"
                UNION ALL
                SELECT id, name, "Influencer" AS roll FROM influencers WHERE flag = "yes"
            ) AS flagged
        ''').fetchall()

    conn.close()
    sponsor_names = [sponsor[1] for sponsor in sponsors]
    sponsor_budgets = [sponsor[4] for sponsor in sponsors]

    influencer_names = [influencer[1] for influencer in influencers]
    follower_counts = [influencer[6] for influencer in influencers]

    campaign_names = [campaign[2] for campaign in campaigns]
    campaign_budgets = [campaign[6] for campaign in campaigns]

    ad_names = [ad[4] for ad in ads]
    ad_payments = [ad[8] for ad in ads]

    flagged_names = [user[1] for user in flagged_users]
    flagged_types = [user[2] for user in flagged_users]

    sponsor_chart = create_bar_chart(sponsor_budgets, sponsor_names, 'Sponsor Budgets')
    influencer_chart = create_bar_chart(follower_counts, influencer_names, 'Influencer Followers')
    campaign_chart = create_bar_chart(campaign_budgets, campaign_names, 'Campaign Budgets')
    ad_chart = create_bar_chart(ad_payments, ad_names, 'Ad Payments')
    flagged_chart = create_pie_chart([flagged_names.count(name) for name in flagged_names], flagged_names,
                                     'Flagged Users')

    return render_template('admin_stats.html',
                           sponsor_chart=get_base64_image(sponsor_chart),
                           influencer_chart=get_base64_image(influencer_chart),
                           campaign_chart=get_base64_image(campaign_chart),
                           ad_chart=get_base64_image(ad_chart),
                           flagged_chart=get_base64_image(flagged_chart))


@app.route('/sponsor_stats/<int:spon_id>/<string:name>/<string:password>')
def sponsor_stats(spon_id, name, password):
    conn = sqlite3.connect('database.db')
    conn = conn.cursor()
    campaigns = conn.execute('SELECT * FROM campaign WHERE spon_id = ?', (spon_id,)).fetchall()
    ads = conn.execute('SELECT * FROM ads WHERE spon_id = ?', (spon_id,)).fetchall()

    influencer_stats = conn.execute('''
            SELECT influencers.name, COUNT(ads.ad_id) AS ad_count
            FROM ads
            JOIN influencers ON ads.influ_id = influencers.id
            WHERE ads.spon_id = ?
            GROUP BY influencers.name
        ''', (spon_id,)).fetchall()

    conn.close()

    campaign_names = [campaign[2] for campaign in campaigns]
    campaign_budgets = [campaign[6] for campaign in campaigns]

    ad_names = [ad[4] for ad in ads]
    ad_payments = [ad[8] for ad in ads]

    influencer_names = [stat[0] for stat in influencer_stats]
    ad_counts = [stat[1] for stat in influencer_stats]
    print(campaign_budgets)
    campaign_chart = create_bar_chart(campaign_budgets, campaign_names, 'Campaign Budgets')
    ad_chart = create_bar_chart(ad_payments, ad_names, 'Ad Payments')
    influencer_chart = create_bar_chart(ad_counts, influencer_names, 'Ads per Influencer')

    return render_template('sponsor_stats.html',
                           campaign_chart=get_base64_image(campaign_chart),
                           ad_chart=get_base64_image(ad_chart),
                           influencer_chart=get_base64_image(influencer_chart),
                           spon_id=spon_id, name=name, password=password)


@app.route('/influencer_stats/<int:influ_id>/<string:name>/<string:password>')
def influencer_stats(influ_id, name, password):
    conn = sqlite3.connect('database.db')
    conn = conn.cursor()
    campaigns = conn.execute('''
            SELECT campaign.name, COUNT(ads.ad_id) AS ad_count, SUM(ads.payment) AS total_payment
            FROM campaign
            JOIN ads ON campaign.camp_id = ads.camp_id
            WHERE ads.influ_id = ?
            GROUP BY campaign.name
        ''', (influ_id,)).fetchall()

    conn.close()
    campaign_names = [campaign[0] for campaign in campaigns]
    ad_counts = [campaign[1] for campaign in campaigns]
    total_payments = [campaign[2] for campaign in campaigns]

    ad_count_chart = create_bar_chart(ad_counts, campaign_names, 'Ads per Campaign')
    payment_chart = create_bar_chart(total_payments, campaign_names, 'Total Payment per Campaign')

    return render_template('influencer_stats.html',
                           ad_count_chart=get_base64_image(ad_count_chart),
                           payment_chart=get_base64_image(payment_chart),
                           influ_id=influ_id, name=name, password=password)


@app.route('/influencer_details/<int:influ_id>', methods=['POST','GET'])
def influencer_details(influ_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM influencers WHERE id = ?", (influ_id,))
    influencer = c.fetchone()
    conn.commit()
    conn.close()
    return render_template('influencer_details.html', influencer=influencer)


@app.route('/flag_sponsor/<int:spon_id>')
def flag_sponsor(spon_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("UPDATE sponsors SET flag='yes' WHERE id=?", (spon_id,))
    flash('sponsor flaged successfully')
    conn.commit()
    conn.close()
    return redirect(url_for('admin_find'))


@app.route('/flag_campaign/<int:camp_id>')
def flag_campaign(camp_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("UPDATE campaign SET flag='yes' WHERE camp_id=?", (camp_id,))
    flash('campaign flaged successfully')
    conn.commit()
    conn.close()
    return redirect(url_for('admin_find'))


@app.route('/flag_influencer/<int:influ_id>')
def flag_influencer(influ_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("UPDATE influencers SET flag='yes' WHERE id=?", (influ_id,))
    flash('influencer flaged successfully')
    conn.commit()
    conn.close()
    return redirect(url_for('admin_find'))


@app.route('/remove_sponsor/<int:spon_id>')
def remove_sponsor(spon_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE from sponsors where id=?", (spon_id,))
    flash('sponsor removed successfully')
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))


@app.route('/remove_campaign/<int:camp_id>')
def remove_campaign(camp_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE from campaign where camp_id=?", (camp_id,))
    flash('campaign removed successfully')
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))


@app.route('/remove_influencer/<int:influ_id>')
def remove_influencer(influ_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE from influencers where id=?", (influ_id,))
    flash('influencer removed successfully')
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
