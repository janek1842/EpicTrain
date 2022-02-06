from __main__ import app, mysql, db
import random

from flask import render_template
import datetime
import math
from datetime import timedelta
from flask import render_template
import os
import MySQLdb
from werkzeug.urls import url_parse
from werkzeug.utils import secure_filename
from forms import LoginForm, RegistrationForm, AccountForm, OpinionForm
from flask import render_template, flash, redirect, url_for, request, session
from models import User
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from django.contrib.auth.decorators import user_passes_test
from datetime import *


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('/'))
    form = RegistrationForm(request.form)
    if request.method == 'POST' and form.validate():
        hashed_password = generate_password_hash(form.password.data, method='sha256')
        user = User(username=form.username.data,
                    email=form.email.data,
                    password=hashed_password,
                    )
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('views/register.html', title='Register', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not check_password_hash(user.password, form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('home')
        if user.is_banned:
            flash('Nie możesz się zalogować bo zostałeś zbanowany (zbananowany hahaha)')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        return redirect(next_page)
    return render_template('views/login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    session['logged_in'] = False
    return redirect(url_for('home'))


@app.route('/read_more')
def read_more():
    return render_template('views/read_more.html')


@app.route('/my_bookings', methods=['GET', 'POST'])
def my_bookings():
    if(request.values.get("id_to_delete") is not None):
        deleteReservation(int(request.values.get("id_to_delete")))
    return render_template('views/my_bookings.html', bookings=getMyBookings())


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg'}


@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    form = AccountForm(request.form)
    if request.method == 'POST':
        if 'avatar' in request.files:
            avatar = request.files['avatar']
        if avatar and allowed_file(avatar.filename):
            filename = secure_filename(avatar.filename)
            basedir = os.path.abspath(os.path.dirname(__file__))
            avatar.save(os.path.join(basedir, app.config['UPLOAD_FOLDER'], filename))
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute(
                'UPDATE users SET avatar=' + '"' + avatar.filename + '"' + ' WHERE user_id=' + str(
                    current_user.user_id))
            mysql.connection.commit()
            cursor.close()
        if form.validate():
            description = form.description.data
            discount = form.discount.data
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute(
                'UPDATE users SET description =' + '"' + description + '"' + ', discount =' + '"' + discount + '"' + ' WHERE user_id=' + str(
                    current_user.user_id))
            mysql.connection.commit()
            cursor.close()
        return redirect(url_for('home'))
    return render_template('views/account.html', title='Account', form=form)


@app.route('/delete_account', methods=['GET'])
@login_required
def delete_account():
    if current_user.is_authenticated:
        User.query.filter_by(user_id=current_user.user_id).delete()
        db.session.commit()
        session['logged_in'] = False
        return redirect(url_for('home'))
    return redirect(url_for('account'))

@app.route('/home', methods=['GET', 'POST'])
@login_required
def home():
    if request.method == "POST":
        doReservation(request.values.get("train"), request.values.get("date"), request.values.get("course_id"),
                      request.values.get("city1"), request.values.get("city2"),
                      convertSimonNames(request.values.get("std")))

        cursor = mysql.connection.cursor()
        cursor.execute('SELECT MAX(reservation_id) FROM reservations')
        reservation_id = cursor.fetchall()[0][0]

        doReservedServices(request.form.getlist('purchasedSer')[0], reservation_id)

    return render_template('views/main_panel.html')

@app.route('/', methods=['GET', 'POST'])
@app.route('/index')
def index():
    return render_template('views/index.html')


@app.route('/courses', methods=['GET', 'POST'])
@login_required
def courses():
    if request.method == 'POST' and request.values.get('start-city') is not None:
        startCity = request.values.get('start-city').replace("+", " ")
        endCity = request.values.get('end-city').replace("+", " ")
        hour = request.values.get('trip-start') + " 00:00:00"
        return render_template('views/course_search_engine.html', stations=getStations(),
                               courses=getConnectionsWithDetails(startCity, endCity, hour))
    else:
        return render_template('views/course_search_engine.html', stations=getStations(),
                               courses=getConnectionsWithDetails())


@app.route('/booking', methods=['GET', 'POST'])
def booking():
    freePlaces = getAmountofFreePlaces(request.values.get("NazwaPociagu"), request.values.get("date"),
                                       request.values.get("CourseId"), request.values.get("stacjaPoczatkowa"),
                                       request.values.get("stacjaKoncowa"))
    if request.method == 'POST':
        detailsDict = {"CzasOdjazdu": request.values.get('CzasOdjazdu'),
                       "CzasPrzyjazdu": request.values.get('CzasPrzyjazdu'),
                       "CalkowityDystans": request.values.get('CalkowityDystans')
            , "NazwaPociagu": request.values.get("NazwaPociagu"),
                       "stacjaPoczatkowa": request.values.get("stacjaPoczatkowa"),
                       "stacjaKoncowa": request.values.get("stacjaKoncowa"),
                       "CzasPodrozy": request.values.get("CzasPodrozy"), "CourseId": request.values.get("CourseId"),
                       "trainId": request.values.get("trainId"), "IdPocz": request.values.get("IdPocz"),
                       "IdKonc": request.values.get("IdKonc"),
                       "date": request.values.get("date"), "std": request.values.get("travel-standard")}

        purchasedSer = []

        if len(request.form.getlist('services')) > 0:
            purchasedSer = request.form.getlist('services')
        else:
            for i in range(0, len(getServices())):
                purchasedSer.append('')

        return render_template('views/booking_details.html', services=getServices(), course=detailsDict,
                               reqIDs_msgs_rcs=zip(getServices(), purchasedSer), places=freePlaces,
                               purchasedSer=purchasedSer,
                               price=str(getTravelPrice(float(request.values.get('CalkowityDystans').split()[0]),
                                                        request.values.get('travel-standard')) + getServicesPrices(
                                   request.form.getlist('services'))) + " PLN")


@app.route('/trains')
@login_required
def trains():
    return render_template('views/trains.html', trains=getTrains())


@app.route('/stations')
@login_required
def stations():
    return render_template('views/stations.html', stations=getStations())

@app.route('/services')
@login_required
def services():
    return render_template('views/services.html', services=getServices())


@app.route('/train_details/<string:train_id>', methods=['GET', 'POST'])
@login_required
def train_details(train_id):
    form = OpinionForm()
    if form.validate_on_submit():
        cursor = mysql.connection.cursor()
        insert_time = str(datetime.now())
        opinion = form.opinion.data
        rate = str(form.rate.data)
        user_id = str(current_user.user_id)
        cursor.execute(
            "INSERT INTO opinions(text, rate, insert_time, user_id, opinion_train_id) VALUES ('" + opinion + "','" + rate + "','" + insert_time + "','" + user_id + "','" + train_id + "')")
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('train_details', train_id=train_id))
    page = "trains"
    train = getTrainDetails(train_id)
    opinions = getOpinions(train_id, page)
    total_rate = 0
    for opinion in opinions:
        total_rate += opinion["rate"]
    if(len(opinions) != 0):
        total_rate /= len(opinions)
    else:
        total_rate = 0
    return render_template('views/train_details.html', train=train,
                           opinions=opinions, total_rate=round(float(total_rate),2), form=form)


@app.route('/train_details/<string:train_id>/opinion/<string:opinion_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_train_opinion(train_id, opinion_id):
    form = OpinionForm(request.form)
    if request.method == 'POST':
        if form.validate_on_submit():
            cursor = mysql.connection.cursor()
            cursor.execute("UPDATE opinions SET text='" + form.opinion.data + "',rate='" + str(
                form.rate.data) + "'WHERE opinion_id=" + opinion_id)
            mysql.connection.commit()
            cursor.close()
            return redirect(url_for('train_details', train_id=train_id))
    cursor = mysql.connection.cursor()
    cursor.execute(
        "SELECT opinions.user_id,username,avatar,text,rate,insert_time,opinion_id from opinions, users WHERE opinion_train_id=" + train_id + " AND opinions.opinion_id=" + opinion_id)
    op = cursor.fetchone()
    opinion = {}
    opinion["user_id"] = op[0]
    opinion["username"] = op[1]
    opinion["avatar"] = op[2]
    opinion["text"] = op[3]
    opinion["rate"] = op[4]
    opinion["insert_time"] = op[5]
    opinion["opinion_id"] = op[6]
    cursor.close()
    return render_template('views/opinion_edit.html', page='trains', opinion=opinion, train_id=train_id, form=form)


@app.route('/train_details/<string:train_id>/opinion/<string:opinion_id>/delete', methods=['GET', 'POST'])
@login_required
def delete_train_opinion(train_id, opinion_id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM opinions WHERE opinion_id=" + opinion_id)
    mysql.connection.commit()
    cursor.close()
    return redirect(url_for('train_details', train_id=train_id))


@app.route('/service_details/<string:service_id>/opinion/<string:opinion_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_service_opinion(service_id, opinion_id):
    form = OpinionForm(request.form)
    if request.method == 'POST':
        if form.validate_on_submit():
            cursor = mysql.connection.cursor()
            cursor.execute("UPDATE opinions SET text='" + form.opinion.data + "',rate='" + str(
                form.rate.data) + "'WHERE opinion_id=" + opinion_id)
            mysql.connection.commit()
            cursor.close()
            return redirect(url_for('service_details', service_id=service_id))
    cursor = mysql.connection.cursor()
    cursor.execute(
        "SELECT opinions.user_id,username,avatar,text,rate,insert_time,opinion_id from opinions, users WHERE opinion_service_id=" + service_id + " AND opinions.opinion_id=" + opinion_id)
    op = cursor.fetchone()
    opinion = {}
    opinion["user_id"] = op[0]
    opinion["username"] = op[1]
    opinion["avatar"] = op[2]
    opinion["text"] = op[3]
    opinion["rate"] = op[4]
    opinion["insert_time"] = op[5]
    opinion["opinion_id"] = op[6]
    cursor.close()
    return render_template('views/opinion_edit.html', page='services', opinion=opinion, service_id=service_id,
                           form=form)


@app.route('/service_details/<string:service_id>/opinion/<string:opinion_id>/delete', methods=['GET', 'POST'])
@login_required
def delete_service_opinion(service_id, opinion_id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM opinions WHERE opinion_id=" + opinion_id)
    mysql.connection.commit()
    cursor.close()
    return redirect(url_for('service_details', service_id=service_id))


@app.route('/station_details/<string:station_id>/opinion/<string:opinion_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_station_opinion(station_id, opinion_id):
    print("JESTEM")
    form = OpinionForm(request.form)
    if request.method == 'POST':
        if form.validate_on_submit():
            cursor = mysql.connection.cursor()
            cursor.execute("UPDATE opinions SET text='" + form.opinion.data + "',rate='" + str(
                form.rate.data) + "'WHERE opinion_id=" + opinion_id)
            mysql.connection.commit()
            cursor.close()
            return redirect(url_for('station_details', station_id=station_id))

    cursor = mysql.connection.cursor()
    cursor.execute(
        "SELECT opinions.user_id,username,avatar,text,rate,insert_time,opinion_id from opinions, users WHERE opinion_station_id=" + station_id + " AND opinions.opinion_id=" + opinion_id)
    op = cursor.fetchone()
    print("OTO nasze ",op)
    opinion = {}
    opinion["user_id"] = op[0]
    opinion["username"] = op[1]
    opinion["avatar"] = op[2]
    opinion["text"] = op[3]
    opinion["rate"] = op[4]
    opinion["insert_time"] = op[5]
    opinion["opinion_id"] = op[6]
    cursor.close()
    return render_template('views/opinion_edit.html', page='stations', opinion=opinion, station_id=station_id,
                           form=form)


@app.route('/station_details/<string:station_id>/opinion/<string:opinion_id>/delete', methods=['GET', 'POST'])
@login_required
def delete_station_opinion(station_id, opinion_id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM opinions WHERE opinion_id=" + opinion_id)
    mysql.connection.commit()
    cursor.close()
    return redirect(url_for('station_details', station_id=station_id))


@app.route('/service_details/<string:service_id>', methods=['GET', 'POST'])
@login_required
def service_details(service_id):
    form = OpinionForm()
    if form.validate_on_submit():
        cursor = mysql.connection.cursor()
        insert_time = str(datetime.now())
        opinion = form.opinion.data
        rate = str(form.rate.data)
        user_id = str(current_user.user_id)
        cursor.execute(
            "INSERT INTO opinions(text, rate, insert_time, user_id, opinion_service_id) VALUES ('" + opinion + "','" + rate + "','" + insert_time + "','" + user_id + "','" + service_id + "')")
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('service_details', service_id=service_id))
    page = "services"
    total_rate = 0
    service = getServiceDetails(service_id)
    opinions = getOpinions(service_id, page)
    for opinion in opinions:
        total_rate += opinion["rate"]
    if (len(opinions) != 0):
        total_rate /= len(opinions)
    else:
        total_rate = 0
    return render_template('views/service_details.html', service=service,
                           opinions=opinions, total_rate=round(float(total_rate),2), form=form)


@app.route('/station_details/<string:station_id>', methods=['GET', 'POST'])
@login_required
def station_details(station_id):
    form = OpinionForm()
    if form.validate_on_submit():
        cursor = mysql.connection.cursor()
        insert_time = str(datetime.now())
        opinion = form.opinion.data
        rate = str(form.rate.data)
        user_id = str(current_user.user_id)
        cursor.execute(
            "INSERT INTO opinions(text, rate, insert_time, user_id, opinion_station_id) VALUES ('" + opinion + "','" + rate + "','" + insert_time + "','" + user_id + "','" + station_id + "')")
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('station_details', station_id=station_id))
    page = "stations"
    station = getStationDetails(station_id)
    opinions = getOpinions(station_id, page)
    total_rate = 0
    for opinion in opinions:
        total_rate += opinion["rate"]
    if(len(opinions) != 0):
        total_rate /= len(opinions)
    else:
        total_rate = 0
    return render_template('views/station_details.html', station=station,
                           opinions=opinions, total_rate=round(float(total_rate),2), form=form)


@app.route('/admin_panel')
@login_required
def admin_panel():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT user_id,username,is_admin,is_banned from users WHERE is_admin != '1'")
    users = cursor.fetchall()
    userList = []
    for u in users:
        user = {}
        user['id'] = u[0]
        user['username'] = u[1]
        user['is_admin'] = u[2]
        user['is_banned'] = u[3]
        userList.append(user)
    print(users)
    cursor.close()
    return render_template('views/adminpanel.html', users = userList)


@app.route('/ban_user/<user_id>', methods=["POST"])
def ban_user(user_id):
    cursor = mysql.connection.cursor()
    cursor.execute('UPDATE users SET is_banned=1 WHERE user_id=' + user_id)
    mysql.connection.commit()
    cursor.close()
    return redirect(url_for('admin_panel'))


@app.route('/unban_user/<user_id>', methods=["POST"])
def unban_user(user_id):
    cursor = mysql.connection.cursor()
    cursor.execute('UPDATE users SET is_banned=0 WHERE user_id=' + user_id)
    mysql.connection.commit()
    cursor.close()
    return redirect(url_for('admin_panel'))


def getDistanceKM(city1="Szczecin", city2="Wrocław"):
    if (city1 == city2):
        return 0
    else:
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT x_coord,y_coord FROM stations where name = %s or name = %s', (city1, city2,))
        results = cursor.fetchall()

        xdiffDeg = ((int(str(results[0][0])[:2]) - int(str(results[1][0])[:2])) * 111)
        ydiffDeg = ((int(str(results[0][1])[:2]) - int(str(results[1][1])[:2])) * 111)

        xdiffMin = ((float(str(results[0][0])[2:4]) - float(str(results[1][0])[2:4])) * 111 / 60)
        ydiffMin = ((float(str(results[0][1])[2:4]) - float(str(results[1][1])[2:4])) * 111 / 60)

        xdiff = xdiffDeg + xdiffMin
        ydiff = ydiffDeg + ydiffMin

        totaldist = str(math.sqrt(math.pow(xdiff, 2) + math.pow(ydiff, 2)))
        return (totaldist)


def getCities(city1, city2):
    cursor = mysql.connection.cursor()

    # pobieranie id stacji docelowej i zrodlowej
    cursor.execute('SELECT station_id FROM stations where name = %s', (city1,))
    city1_id = cursor.fetchall()[0][0]

    cursor.execute('SELECT station_id FROM stations where name = %s', (city2,))
    city2_id = cursor.fetchall()[0][0]

    cursor.execute('SELECT station_id2 FROM tracks where station_id1 = %s', (city1_id,))
    subresult_1 = cursor.fetchall()

    cursor.execute('SELECT station_id1 FROM tracks where station_id2 = %s', (city1_id,))
    subresult_2 = cursor.fetchall()

    results = []

    try:
        for r in subresult_1:
            results.append(r[0])
    except Exception:
        pass

    try:
        for r in subresult_2:
            results.append(r[0])
    except Exception:
        pass

    for st in results:
        cities = (branchSearch(city1_id, st, city2_id))
        if (city2_id in cities):
            return list(cities)
        else:
            continue


def branchSearch(city1_id, city2_id, dst_id):
    temp_list = []
    temp_list.append(city1_id)
    temp_list.append(city2_id)
    cursor = mysql.connection.cursor()

    while (True):
        cursor.execute('SELECT station_id2 FROM tracks where station_id1 = %s', (city2_id,))
        subresult_1 = cursor.fetchall()
        cursor.execute('SELECT station_id1 FROM tracks where station_id2 = %s', (city2_id,))
        subresult_2 = cursor.fetchall()

        results = []
        try:
            for r in subresult_2:
                results.append(r[0])
        except Exception:
            pass

        try:
            for r in subresult_1:
                results.append(r[0])
        except Exception:
            pass

        if (dst_id in temp_list):
            if (len(temp_list) > 2):
                temp_list.append(dst_id)
            temp_list = list(dict.fromkeys(temp_list))
            return temp_list
        else:
            for r in results:
                if r in temp_list:
                    results.remove(r)

            if (len(results) == 1):
                city2_id = results[0]
                temp_list.append(city2_id)
                continue

            if (len(results) >= 2):
                for r in results:
                    if (dst_id in branchSearch(city2_id, r, dst_id)):
                        temp_list = temp_list + branchSearch(city2_id, r, dst_id)
                        temp_list = list(dict.fromkeys(temp_list))
                        return temp_list
                return temp_list

            if (len(results) == 0):
                return temp_list


def cities():
    return getCities("Kraków", "Lublin")


def getStationFromId(id1):
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT name FROM stations where station_id = %s', (str(id1),))
    return str(cursor.fetchone()[0])

def getIdFromStation(name):
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT station_id FROM stations where name = %s', (str(name),))
    return int(cursor.fetchone()[0])

def getTrainFromId(id1):
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT name FROM trains where train_id = %s', (str(id1),))
    return str(cursor.fetchone()[0])

def getTrains():
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT * FROM trains')
    temp = cursor.fetchall()
    trainList = []

    for train in temp:
        trains = {}
        trains["train_id"] = train[0]
        trains["stdEco_wagons_number"] = train[1]
        trains["stdPre_wagons_number"] = train[2]
        trains["stdVip_wagons_number"] = train[3]
        trains["speed"] = train[4]
        trains["description"] = train[5]
        trains["photo"] = train[6]
        trains["name"] = train[7]
        trainList.append(trains)

    return trainList


def getStations():
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT * FROM stations')
    temp = cursor.fetchall()
    stations = {}
    stationList = []

    for station in temp:
        stations = {}
        stations["station_id"] = station[0]
        stations["x_coord"] = station[1]
        stations["y_coord"] = station[2]
        stations["platform_number"] = station[3]
        stations["track_number"] = station[4]
        stations["ticket_office"] = station[5]
        stations["description"] = station[6]
        stations["opinion_id"] = station[7]
        stations["photo"] = station[8]
        stations["name"] = station[9]
        stationList.append(stations)

    return stationList


def getServices():
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT * FROM services')
    temp = cursor.fetchall()
    services = {}

    serviceList = []
    for service in temp:
        services = {}
        services["service_id"] = service[0]
        services["service_name"] = service[1]
        services["price"] = service[2]
        services["description"] = service[3]
        services["photo"] = service[4]
        serviceList.append(services)

    return serviceList


def getRides(st1="Olsztyn", st2="Opole", d1='2022-01-20 00:00:00'):
    d1 = datetime(int(d1.split('-')[0]), int(d1.split('-')[1]), int(d1.split('-')[2].split()[0]))
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT * FROM courses where validity_start <= %s and validity_end >=%s order by departure_time',
                   (d1, d1))
    results = list(cursor.fetchall())
    finalResult = []

    for r in results:
        course_result = getCities(getStationFromId(int(r[-2])), getStationFromId(int(r[-3])))
        for id in range(0, len(course_result)):
            if getIdFromStation(st1) == course_result[id]:
                if getIdFromStation(st2) in course_result[id:]:
                    finalResult.append(r)
    return finalResult


def getCourseTotalDist(st1, st2):
    distSum = 0
    cities = getCities(st1, st2)
    for id in range(0, len(cities) - 1):
        distSum = distSum + float(getDistanceKM(getStationFromId(cities[id]), getStationFromId(cities[id + 1])))
    if st1 == st2:
        return 0
    return distSum


def getCourseTimers(course, st1, st2):
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT speed FROM trains where train_id = %s', (course[-1],))
    speed = int(cursor.fetchone()[0])

    courseStartStation = getStationFromId(course[-2]).strip()

    startTimeDiff = getCourseTotalDist(courseStartStation, st1) / speed
    startTime = course[1] + timedelta(hours=startTimeDiff)

    endTimeDiff = getCourseTotalDist(st1, st2) / speed
    endTime = startTime + timedelta(hours=endTimeDiff)

    travelTime = str(timedelta(hours=endTimeDiff)).rsplit(':', 1)[0]
    return [startTime, endTime, travelTime]


def getTravelDetails(course, st1, st2, d1):
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT name FROM trains where train_id = %s', (course[-1],))
    trainName = str(cursor.fetchone()[0])

    totalDist = str(round(getCourseTotalDist(st1, st2), 2)) + " km"
    departureTime = getCourseTimers(course, st1, st2)[0].strftime("%H:%M")
    arrivalTime = getCourseTimers(course, st1, st2)[1].strftime("%H:%M")

    detailsDict = {"CzasOdjazdu": departureTime, "CzasPrzyjazdu": arrivalTime, "CalkowityDystans": totalDist
        , "NazwaPociagu": trainName, "stacjaPoczatkowa": st1, "stacjaKoncowa": st2,
                   "CzasPodrozy": getCourseTimers(course, st1, st2)[2], "CourseId": course[0], "trainId": course[-1],
                   "IdPocz": getIdFromStation(st1), "IdKonc": getIdFromStation(st2), "date": d1}

    return detailsDict


def getConnectionsWithDetails(st1="Warszawa", st2="Szczecin", d1="FalseFlag"):
    listOfConAndDetails = []
    if (d1 != "FalseFlag" and st1 != st2):
        courses = getRides(st1, st2, d1)
        for course in courses:
            listOfConAndDetails.append(getTravelDetails(course, st1, st2, d1))
        return listOfConAndDetails
    else:
        detailsDict = {"CzasOdjazdu": " ", "CzasPrzyjazdu": " ", "CalkowityDystans": " "
            , "NazwaPociagu": " ", "stacjaPoczatkowa": " ", "stacjaKoncowa": " ",
                       "CzasPodrozy": "FalseFlag", "CourseId": " ",
                       "trainId": " ", "IdPocz": " ", "IdKonc": " ",
                       "date": " "}
        listOfConAndDetails.append(detailsDict)
        return listOfConAndDetails


def getTravelPrice(totalDistance=2122.34, standard="basic"):
    userDiscount = float(getUserDiscount(current_user.user_id))

    scaler = 1
    if standard == "premium":
        scaler = 1.5
    elif standard == "vip":
        scaler = 2

    return ((round((1 - userDiscount) * (float(totalDistance) * 0.05) * scaler, 1)))


def getTrainDetails(train_id):
    cursor = mysql.connection.cursor()
    cursor.execute(
        'SELECT stdEco_wagons_number,stdPre_wagons_number,stdVip_wagons_number, speed, description, photo, name from trains where train_id=' + train_id)
    # nie wpisałam tutaj select * tylko kolejne nazwy żeby mieć pewność co do kolejności konkretnych kolumn
    train = cursor.fetchone()
    trainDict = {
        'id': train_id,
        'stdEco_wagons_number': train[0],
        'stdPre_wagons_number': train[1],
        'stdVip_wagons_number': train[2],
        'speed': train[3],
        'description': train[4],
        'photo': train[5],
        'name': train[6],
    }
    return trainDict


def getServiceDetails(service_id):
    cursor = mysql.connection.cursor()
    cursor.execute(
        'SELECT service_name,price,description,photo from services where service_id=' + service_id)
    service = cursor.fetchone()
    serviceDict = {
        'id': service_id,
        'name': service[0],
        'price': service[1],
        'description': service[2],
        'photo': service[3],
    }
    return serviceDict


def getStationDetails(station_id):
    cursor = mysql.connection.cursor()
    cursor.execute(
        'SELECT x_coord,y_coord,platform_number,track_number,ticket_office,description,opinion_id,photo,name from stations where station_id=' + station_id)
    station = cursor.fetchone()
    stationDict = {
        'id': station_id,
        'x_coord': station[0],
        'y_coord': station[1],
        'platform_number': station[2],
        'track_number': station[3],
        'ticket_office': station[4],
        'description': station[5],
        'opinion_id': station[6],
        'photo': station[7],
        'name': station[8],
    }
    return stationDict


def getOpinions(id, page):
    if page == 'trains':
        column = "opinion_train_id"
    elif page == 'stations':
        column = "opinion_station_id"
    if page == 'services':
        column = "opinion_service_id"

    cursor = mysql.connection.cursor()
    cursor.execute(
        "SELECT opinions.user_id,username,avatar,text,rate,insert_time,opinion_id from opinions, users WHERE " + column + "=" + id + " AND users.user_id=opinions.user_id")
    opinions = cursor.fetchall()

    opinionList = []
    for op in opinions:
        opinion = {}
        opinion["author_id"] = op[0]
        opinion["author"] = op[1]
        opinion["avatar"] = op[2]
        opinion["text"] = op[3]
        opinion["rate"] = op[4]
        opinion["insert_time"] = op[5]
        opinion["opinion_id"] = op[6]
        opinionList.append(opinion)

    return opinionList


def getStdFromPlace(placeNumber, trainName):
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT stdEco_wagons_number,stdPre_wagons_number,stdVip_wagons_number FROM trains where name = %s',
                   (trainName,))
    results = (cursor.fetchall()[0])

    stdVIPNominal = int(results[2]) * 10
    stdPremiumNominal = int(results[1]) * 20
    stdEcoNominal = int(results[0]) * 30

    if (placeNumber <= stdEcoNominal):
        return "Eco"
    elif (placeNumber <= (stdEcoNominal + stdPremiumNominal)):
        return "Premium"
    else:
        return "VIP"


def checkIfPlaceAvailable(city1, city2, cityReserved1, cityReserved2):
    if (getIdFromStation(city1) in getCities(getStationFromId(cityReserved1),
                                             getStationFromId(cityReserved2)) or
            getIdFromStation(city2)
            in getCities(getStationFromId(cityReserved1), getStationFromId(cityReserved2))
    ):
        return False
    elif (cityReserved1 in getCities(city1, city2) or cityReserved2 in getCities(city1, city2)):
        return False
    return True


def selectFreePlace(standard, train, date, course_id, city1, city2):
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT seat_number FROM reservations where course_id = %s and reservation_date = %s',
                   (course_id, date,))

    reservedSeats = []

    for seat in cursor.fetchall():
        reservedSeats.append(seat[0])

    cursor.execute('SELECT stdEco_wagons_number,stdPre_wagons_number,stdVip_wagons_number FROM trains where name = %s',
                   (train,))
    results = (cursor.fetchall()[0])

    stdVIP = int(results[2]) * 10
    stdPremium = int(results[1]) * 20
    stdEco = int(results[0]) * 30

    while (True):
        if (standard == "ECO"):
            seatNumber = random.randint(1, stdEco)
        elif (standard == "PREMIUM"):
            seatNumber = random.randint(stdEco + 1, stdEco + stdPremium)
        elif (standard == "VIP"):
            seatNumber = random.randint(stdEco + stdPremium + 1, stdEco + stdPremium + stdVIP)
        if (seatNumber not in reservedSeats):
            break
    return str(seatNumber)


def doReservation(train, date, course_id, city1, city2, standard):
    selectedPlace = selectFreePlace(standard, train, date, course_id, city1, city2)

    cursor = mysql.connection.cursor()
    cursor.execute('INSERT INTO reservations values (null,%s,%s,%s,%s,%s,%s)',
                   (selectedPlace, current_user.user_id, course_id, getIdFromStation(city1), getIdFromStation(city2),
                    date))
    mysql.connection.commit()

    cursor = mysql.connection.cursor()
    cursor.execute(
        'SELECT reservation_id from reservations where seat_number=%s and user_id=%s and course_id=%s and start_station_id=%s and end_station_id=%s and reservation_date=%s ',
        (selectedPlace, current_user.user_id, course_id, getIdFromStation(city1),
         getIdFromStation(city2),
         date))
    return str(cursor.fetchall()[0][0])


def getAmountofFreePlaces(train, date, course_id, city1, city2):
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT stdEco_wagons_number,stdPre_wagons_number,stdVip_wagons_number FROM trains where name = %s',
                   (train,))
    results = (cursor.fetchall()[0])

    cursor.execute('SELECT * FROM reservations where reservation_date = %s and course_id = %s', (date, course_id,))
    reserResults = (cursor.fetchall())

    ecoStd = 0
    preStd = 0
    vipStd = 0

    for reservation in reserResults:
        if (not checkIfPlaceAvailable(city1, city2, reservation[4], reservation[5])):
            if (getStdFromPlace(reservation[1], train) == "Eco"):
                ecoStd = ecoStd + 1
            if (getStdFromPlace(reservation[1], train) == "Premium"):
                preStd = preStd + 1
            if (getStdFromPlace(reservation[1], train) == "VIP"):
                vipStd = vipStd + 1

    stdVIP = int(results[2]) * 10 - vipStd
    stdPremium = int(results[1]) * 20 - preStd
    stdEco = int(results[0]) * 30 - ecoStd

    resultDict = {"ECO": stdEco, "VIP": stdVIP, "PREMIUM": stdPremium}
    return resultDict


def getUserDiscount(user_id=1):
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT discount FROM users WHERE user_id=%s ',
                   (user_id,))
    return str(float(cursor.fetchall()[0][0]) / 100)


def convertSimonNames(std):
    if std == "premium":
        return "PREMIUM"
    elif std == "vip":
        return "VIP"
    else:
        return "ECO"

def convertToSimonNames(std):
    if std == "PREMIUM":
        return "premium"
    elif std == "VIP":
        return "vip"
    else:
        return "basic"

def getServicesPrices(listOfServices):
    if listOfServices is not None:
        cursor = mysql.connection.cursor()
        sumPrice = 0

        for id in range(1, len(listOfServices) + 1):
            if (listOfServices[id - 1] != ''):
                amount = int(listOfServices[id - 1])
                cursor.execute('SELECT price FROM services where service_id = %s', (id,))
                result = int(cursor.fetchall()[0][0])
                sumPrice = sumPrice + amount * result
        return sumPrice
    else:
        return 0


def doReservedServices(orderedServices, reservationId):
    index = 1
    newList = orderedServices.replace('[', '').replace(']', '').replace(' ', '').split(',')
    newerList = []

    for new in newList:
        try:
            newerList.append(int(new[1:-1]))
        except:
            pass

    for order in newerList:
        if order != 0:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "INSERT INTO reserved_services(service_id,reservation_id,amount) VALUES ('" + str(index) + "','" + str(
                    reservationId) + "','" + str(order) + "') ")
            mysql.connection.commit()
        index = index + 1

def getServiceFromId(service_id):
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT service_name FROM services where service_id = %s', (str(service_id)))
    return str(cursor.fetchall()[0][0])


def getServicesPricesFromDict(servicesDict):
    price = 0
    print(servicesDict)
    for k,v in servicesDict.items():
        cursor = mysql.connection.cursor()

        print("OTO",k)
        cursor.execute('SELECT price FROM services where service_name = %s', (str(k).strip(),))
        price = price + float(cursor.fetchall()[0][0])*v
    return price

def getMyBookings():
    try:
        user_id = current_user.user_id
    except:
        user_id = "7"

    cursor = mysql.connection.cursor()
    cursor.execute('SELECT * FROM reservations where user_id = %s',(user_id,))
    results = (cursor.fetchall())

    finalList = []

    for result in results:
        resultDict = {}
        resultDict["reservationId"] = int(result[0])
        resultDict["seatNumber"] = result[1]
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT train_id FROM courses where course_id = %s', (result[3],))
        trainID = (cursor.fetchall()[0][0])
        resultDict["standard"] = getStdFromPlace(int(result[1]),getTrainFromId(trainID))
        resultDict["trainName"] = getTrainFromId(trainID)
        resultDict["date"] = str(result[6]).split()[0]
        resultDict["startStation"] = getStationFromId(int(result[4]))
        resultDict["endStation"] = getStationFromId(int(result[5]))

        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM courses where course_id = %s', (result[3],))
        course = (cursor.fetchall()[0])
        resultDict["departureTime"]= getCourseTimers(course, resultDict["startStation"],resultDict["endStation"])[0].strftime("%H:%M")
        resultDict["courseId"] = getStationFromId(int(result[3]))
        resultDict["trainId"] = trainID

        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM reserved_services where reservation_id = %s', (result[0],))
        services = (cursor.fetchall())

        subDict = {}
        for service in services:
            subDict[getServiceFromId(service[0])] = service[2]

        resultDict["services"] = subDict
        resultDict["price"] = getTravelPrice(getDistanceKM((resultDict["startStation"]),(resultDict["endStation"])),convertToSimonNames(resultDict["standard"])) + getServicesPricesFromDict(subDict)

        finalList.append(resultDict)

    return finalList

def deleteReservation(reservation_id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM reservations WHERE reservation_id = %s ", ((reservation_id),))
    mysql.connection.commit()
    return "RESERVATION DELETED"