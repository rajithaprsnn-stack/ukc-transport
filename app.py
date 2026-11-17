from datetime import datetime, timedelta
import calendar
import io
from flask import (
    Flask,
    flash,
    redirect,
    render_template_string,
    request,
    session,
    url_for,
    send_file,
)
import sqlite3

app = Flask(__name__)
app.secret_key = "ukc_tours_ultimate_secret_key"


def get_db_connection():
  conn = sqlite3.connect("transport.db")
  conn.row_factory = sqlite3.Row
  return conn


def init_db():
  conn = get_db_connection()
  cursor = conn.cursor()

  cursor.execute(
      """CREATE TABLE IF NOT EXISTS vehicles (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          vehicle_no TEXT NOT NULL,
          model TEXT,
          current_mileage REAL,
          next_service_due REAL
      )"""
  )
  cursor.execute(
      """CREATE TABLE IF NOT EXISTS mileage (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          vehicle_id INTEGER,
          date TEXT,
          start_km REAL,
          end_km REAL,
          FOREIGN KEY(vehicle_id) REFERENCES vehicles(id)
      )"""
  )
  cursor.execute(
      """CREATE TABLE IF NOT EXISTS fuel (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          vehicle_id INTEGER,
          date TEXT,
          litres REAL,
          cost REAL,
          mileage_at_fill REAL,
          km_per_litre REAL,
          FOREIGN KEY(vehicle_id) REFERENCES vehicles(id)
      )"""
  )
  cursor.execute(
      """CREATE TABLE IF NOT EXISTS maintenance (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          vehicle_id INTEGER,
          date TEXT,
          type TEXT,
          description TEXT,
          cost REAL,
          mileage_at_service REAL,
          next_service_km REAL,
          parts_replaced TEXT,
          FOREIGN KEY(vehicle_id) REFERENCES vehicles(id)
      )"""
  )
  cursor.execute(
      """CREATE TABLE IF NOT EXISTS hires (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          vehicle_id INTEGER,
          customer_name TEXT,
          pickup TEXT,
          drop_loc TEXT,
          amount REAL,
          status TEXT,
          start_date TEXT,
          end_date TEXT,
          commission REAL,
          allocated_km REAL,
          extra_km_rate REAL,
          actual_km REAL,
          advance REAL,
          FOREIGN KEY(vehicle_id) REFERENCES vehicles(id)
      )"""
  )
  conn.commit()
  conn.close()


TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>UKC TOURS - Vehicle Management System</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0; padding: 20px; 
            background: linear-gradient(rgba(0,0,0,0.6), rgba(0,0,0,0.6)), url('https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=1920&q=80') no-repeat center center fixed; 
            background-size: cover;
            color: #333;
        }
        header { text-align: center; color: white; margin-bottom: 20px; text-shadow: 2px 2px 4px rgba(0,0,0,0.7); }
        header h1 { margin: 0; font-size: 32px; letter-spacing: 1px; }
        header p { margin: 5px 0 0 0; font-size: 16px; color: #ffc107; font-weight: bold; }
        
        .card-custom { background: rgba(255, 255, 255, 0.95); padding: 25px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); margin-bottom: 20px; }
        .sidebar-card { background: rgba(255, 255, 255, 0.95); padding: 20px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
        
        h2 { color: #0056b3; margin-top: 0; border-bottom: 2px solid #007bff; padding-bottom: 8px; font-size: 22px; }
        
        .cal-table { width: 100%; border-collapse: collapse; text-align: center; font-size: 13px; margin-top: 10px; background: white; }
        .cal-table th { background: #0056b3; color: white; padding: 6px; font-size: 11px; border: 1px solid #004085; }
        .cal-table td { padding: 8px; border: 1px solid #ddd; height: 35px; width: 35px; vertical-align: middle; }
        .day-booked { background-color: #ffc107 !important; font-weight: bold; color: #000; border-radius: 4px; }
        .day-today { border: 2px solid #28a745 !important; font-weight: bold; }
        .cal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; font-weight: bold; color: #0056b3; font-size: 15px; }
    </style>
</head>
<body>
    <header>
        <h1>UKC TOURS</h1>
        <p>Vehicle Management System — Explore Sri Lanka With Comfort</p>
    </header>

    {% if session.get('logged_in') %}
    <div class="container-fluid mb-4">
        <div class="bg-primary bg-opacity-75 p-3 rounded d-flex flex-wrap justify-content-between align-items: center shadow">
            <div class="d-flex flex-wrap gap-2">
                <a href="/" class="text-white text-decoration-none fw-bold px-3 py-1 rounded">Dashboard</a>
                <a href="/vehicles" class="text-white text-decoration-none fw-bold px-3 py-1 rounded">Vehicles</a>
                <a href="/mileage" class="text-white text-decoration-none fw-bold px-3 py-1 rounded">Daily Mileage</a>
                <a href="/fuel" class="text-white text-decoration-none fw-bold px-3 py-1 rounded">Fuel Records</a>
                <a href="/maintenance" class="text-white text-decoration-none fw-bold px-3 py-1 rounded">Service & Maint.</a>
                <a href="/hires" class="text-white text-decoration-none fw-bold px-3 py-1 rounded">Hires & Bookings</a>
                <a href="/pnl" class="text-dark bg-warning text-decoration-none fw-bold px-3 py-1 rounded">Profit & Loss (P&L)</a>
            </div>
            <div>
                <a href="/logout" class="btn btn-danger btn-sm fw-bold">Logout 🔒</a>
            </div>
        </div>
    </div>
    {% endif %}

    <div class="container-fluid">
        {% if not session.get('logged_in') %}
            <div class="row justify-content-center">
                <div class="col-md-5">
                    <div class="card-custom text-center">
                        <h2 class="mb-4">🔐 System Login</h2>
                        {% if error %}
                            <div class="alert alert-danger py-2">{{ error }}</div>
                        {% endif %}
                        <form method="POST" action="/login">
                            <div class="mb-3 text-start">
                                <label class="form-label fw-bold">Username</label>
                                <input type="text" name="username" class="form-control" placeholder="Enter username (admin)" required>
                            </div>
                            <div class="mb-3 text-start">
                                <label class="form-label fw-bold">Password</label>
                                <input type="password" name="password" class="form-control" placeholder="Enter password (ukc1234)" required>
                            </div>
                            <button type="submit" class="btn btn-primary w-100 fw-bold py-2">Login to System</button>
                        </form>
                    </div>
                </div>
            </div>
        {% else %}
            <div class="row">
                <div class="col-lg-8 mb-4">
                    <div class="card-custom">
                        {% block content %}{% endblock %}
                    </div>
                </div>
                <div class="col-lg-4 mb-4">
                    <div class="sidebar-card">
                        <h3 class="h5 text-primary fw-bold">📅 Booking Calendar</h3>
                        <div class="cal-header">
                            <span>{{ month_name }} {{ year }}</span>
                        </div>
                        
                        {{ calendar_html | safe }}

                        <h4 class="mt-4 pb-2 border-bottom fs-6 fw-bold text-secondary">Active / Pending Hires</h4>
                        <div style="max-height: 280px; overflow-y: auto; font-size: 13px;">
                            {% for ch in side_hires %}
                                <div class="bg-light p-2 mb-2 rounded border-start border-4 border-primary shadow-sm">
                                    <b>{{ ch['vehicle_no'] }}</b> ({{ ch['customer_name'] }})<br>
                                    <small>🗓️ {{ ch['start_date'] }} to {{ ch['end_date'] }}</small><br>
                                    <div class="d-flex justify-content-between align-items: center mt-1">
                                        <small>Status: <b class="text-dark">{{ ch['status'] }}</b></small>
                                        <a href="/invoice/{{ ch['id'] }}" target="_blank" class="btn btn-outline-dark btn-sm" style="font-size: 11px; padding: 1px 6px;">📄 Invoice</a>
                                    </div>
                                </div>
                            {% endfor %}
                        </div>
                    </div>
                </div>
            </div>
        {% endif %}
    </div>
</body>
</html>
"""


def render_with_calendar(template_string, **kwargs):
  if not session.get("logged_in"):
    return render_template_string(TEMPLATE, **kwargs)

  conn = get_db_connection()
  side_hires = conn.execute(
      """SELECT h.*, v.vehicle_no FROM hires h JOIN vehicles v ON h.vehicle_id = v.id WHERE h.status != 'Cancelled' ORDER BY h.start_date ASC"""
  ).fetchall()
  conn.close()

  now = datetime.now()
  year, month = now.year, now.month
  month_name = now.strftime("%B")

  booked_dates = set()
  for h in side_hires:
    try:
      s_date = datetime.strptime(h["start_date"], "%Y-%m-%d")
      e_date = datetime.strptime(h["end_date"], "%Y-%m-%d")
      curr = s_date
      while curr <= e_date:
        if curr.year == year and curr.month == month:
          booked_dates.add(curr.day)
        curr += timedelta(days=1)
    except:
      pass

  cal = calendar.Calendar(firstweekday=6)
  month_days = cal.monthdayscalendar(year, month)

  cal_html = '<table class="cal-table"><tr><th>Su</th><th>Mo</th><th>Tu</th><th>We</th><th>Th</th><th>Fr</th><th>Sa</th></tr>'
  for week in month_days:
    cal_html += "<tr>"
    for day in week:
      if day == 0:
        cal_html += '<td style="background: #f8f9fa;"></td>'
      else:
        is_booked = day in booked_dates
        is_today = day == now.day
        cls = []
        if is_booked:
          cls.append("day-booked")
        if is_today:
          cls.append("day-today")
        cls_str = " ".join(cls)
        cal_html += f'<td class="{cls_str}" title="Booked Date">{day}</td>'
    cal_html += "</tr>"
  cal_html += "</table>"

  return render_template_string(
      TEMPLATE + template_string,
      side_hires=side_hires,
      calendar_html=cal_html,
      month_name=month_name,
      year=year,
      **kwargs,
  )


@app.route("/login", methods=["POST"])
def login():
  username = request.form.get("username")
  password = request.form.get("password")
  if username == "admin" and password == "ukc1234":
    session["logged_in"] = True
    return redirect(url_for("index"))
  return render_with_calendar(
      "", error="Invalid Username or Password! Try admin / ukc1234"
  )


@app.route("/logout")
def logout():
  session.pop("logged_in", None)
  return redirect(url_for("index"))


@app.route("/")
def index():
  if not session.get("logged_in"):
    return render_with_calendar("")

  conn = get_db_connection()
  v_count = conn.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0]
  h_count = conn.execute(
      "SELECT COUNT(*) FROM hires WHERE status != 'Cancelled'"
  ).fetchone()[0]
  total_income = (
      conn.execute(
          "SELECT SUM(amount - COALESCE(commission, 0)) FROM hires WHERE status"
          " = 'Completed'"
      ).fetchone()[0]
      or 0
  )

  # Service Alerts check
  vehicles = conn.execute("SELECT * FROM vehicles").fetchall()
  alerts = []
  for v in vehicles:
    if v["current_mileage"] and v["next_service_due"]:
      diff = v["next_service_due"] - v["current_mileage"]
      if diff <= 1000:
        alerts.append(
            {
                "vehicle_no": v["vehicle_no"],
                "km_left": diff,
                "urgent": diff <= 0,
            }
        )
  conn.close()

  alerts_html = ""
  if alerts:
    alerts_html += """
        <div class="alert alert-warning mt-3 shadow-sm">
            <h5 class="alert-heading fw-bold fs-6">⚠️ Service Due Warnings!</h5>
            <ul class="mb-0 ps-3" style="font-size: 13px;">
        """
    for a in alerts:
      if a["urgent"]:
        alerts_html += f"<li class='text-danger fw-bold'>Vehicle <b>{a['vehicle_no']}</b> has exceeded service due by {abs(a['km_left'])} KM!</li>"
      else:
        alerts_html += f"<li>Vehicle <b>{a['vehicle_no']}</b> service due in <b>{a['km_left']} KM</b>.</li>"
    alerts_html += "</ul></div>"

  html = (
      """
    <h2>Dashboard Summary</h2>
    <div class="row g-3 mt-2">
        <div class="col-md-4">
            <div class="p-3 bg-light border rounded shadow-sm">
                <h5 class="text-muted fs-6">Total Vehicles</h5>
                <p class="fs-4 fw-bold text-primary mb-0">{{ v_count }}</p>
            </div>
        </div>
        <div class="col-md-4">
            <div class="p-3 bg-light border rounded shadow-sm">
                <h5 class="text-muted fs-6">Active / Completed Hires</h5>
                <p class="fs-4 fw-bold text-success mb-0">{{ h_count }}</p>
            </div>
        </div>
        <div class="col-md-4">
            <div class="p-3 bg-light border rounded shadow-sm">
                <h5 class="text-muted fs-6">Net Income (Completed)</h5>
                <p class="fs-4 fw-bold text-warning mb-0">Rs. {{ "%.2f"|format(total_income) }}</p>
            </div>
        </div>
    </div>
    """
      + alerts_html
  )
  return render_with_calendar(
      html, v_count=v_count, h_count=h_count, total_income=total_income
  )


@app.route("/vehicles", methods=["GET", "POST"])
def vehicles():
  if not session.get("logged_in"):
    return redirect(url_for("index"))
  conn = get_db_connection()
  if request.method == "POST":
    v_no = request.form["vehicle_no"]
    model = request.form["model"]
    mileage = float(request.form["mileage"] or 0)
    conn.execute(
        "INSERT INTO vehicles (vehicle_no, model, current_mileage, next_service_due) VALUES (?, ?, ?, ?)",
        (v_no, model, mileage, mileage + 5000),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("vehicles"))

  veh_list = conn.execute("SELECT * FROM vehicles").fetchall()
  conn.close()

  html = """
    <h2>Manage Vehicles</h2>
    <form method="POST" class="bg-light p-3 border rounded mb-4">
        <div class="mb-3"><input type="text" name="vehicle_no" class="form-control" placeholder="Vehicle Number (e.g., NC-0233)" required></div>
        <div class="mb-3"><input type="text" name="model" class="form-control" placeholder="Model / Type (Toyota Coaster)" required></div>
        <div class="mb-3"><input type="number" step="0.1" name="mileage" class="form-control" placeholder="Current Mileage (KM)" required></div>
        <button type="submit" class="btn btn-success w-100 fw-bold">Add Vehicle</button>
    </form>
    <h3>Vehicle Fleet List</h3>
    <div class="table-responsive">
        <table class="table table-bordered table-striped">
            <thead class="table-primary">
                <tr><th>Vehicle No</th><th>Model</th><th>Current KM</th><th>Next Service Due</th><th>Action</th></tr>
            </thead>
            <tbody>
                {% for v in veh_list %}
                <tr>
                    <td><b>{{ v['vehicle_no'] }}</b></td>
                    <td>{{ v['model'] }}</td>
                    <td>{{ v['current_mileage'] }} KM</td>
                    <td class="text-danger fw-bold">{{ v['next_service_due'] or '-' }} KM</td>
                    <td><a href="/vehicle/delete/{{ v['id'] }}" class="btn btn-danger btn-sm" onclick="return confirm('Delete vehicle?');">Delete</a></td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    """
  return render_with_calendar(html, veh_list=veh_list)


@app.route("/vehicle/delete/<int:id>")
def delete_vehicle(id):
  if not session.get("logged_in"):
    return redirect(url_for("index"))
  conn = get_db_connection()
  conn.execute("DELETE FROM vehicles WHERE id = ?", (id,))
  conn.commit()
  conn.close()
  return redirect(url_for("vehicles"))


@app.route("/mileage", methods=["GET", "POST"])
def mileage_page():
  if not session.get("logged_in"):
    return redirect(url_for("index"))
  conn = get_db_connection()
  if request.method == "POST":
    v_id = request.form["vehicle_id"]
    date = request.form["date"]
    start_km = float(request.form["start_km"])
    end_km = float(request.form["end_km"])
    conn.execute(
        "INSERT INTO mileage (vehicle_id, date, start_km, end_km) VALUES (?, ?, ?, ?)",
        (v_id, date, start_km, end_km),
    )
    conn.execute(
        "UPDATE vehicles SET current_mileage = ? WHERE id = ?", (end_km, v_id)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("mileage_page"))

  vehicles = conn.execute("SELECT * FROM vehicles").fetchall()
  mileages = conn.execute(
      """SELECT m.*, v.vehicle_no, (m.end_km - m.start_km) as total_run 
                  FROM mileage m JOIN vehicles v ON m.vehicle_id = v.id ORDER BY m.date DESC"""
  ).fetchall()
  conn.close()

  html = """
    <h2>Daily Mileage Tracking</h2>
    <form method="POST" class="bg-light p-3 border rounded mb-4">
        <div class="mb-3">
            <select name="vehicle_id" class="form-select" required>
                <option value="">Select Vehicle</option>
                {% for v in vehicles %}<option value="{{ v['id'] }}">{{ v['vehicle_no'] }} ({{ v['model'] }})</option>{% endfor %}
            </select>
        </div>
        <div class="row g-2 mb-3">
            <div class="col-md-4"><input type="date" name="date" class="form-control" required></div>
            <div class="col-md-4"><input type="number" step="0.1" name="start_km" class="form-control" placeholder="Start KM" required></div>
            <div class="col-md-4"><input type="number" step="0.1" name="end_km" class="form-control" placeholder="End KM" required></div>
        </div>
        <button type="submit" class="btn btn-success w-100 fw-bold">Save Mileage</button>
    </form>
    <h3>Mileage Logs</h3>
    <div class="table-responsive">
        <table class="table table-bordered table-striped">
            <thead class="table-primary">
                <tr><th>Vehicle</th><th>Date</th><th>Start KM</th><th>End KM</th><th>Total Run</th><th>Action</th></tr>
            </thead>
            <tbody>
                {% for m in mileages %}
                <tr>
                    <td>{{ m['vehicle_no'] }}</td>
                    <td>{{ m['date'] }}</td>
                    <td>{{ m['start_km'] }}</td>
                    <td>{{ m['end_km'] }}</td>
                    <td><b>{{ m['total_run'] }} KM</b></td>
                    <td><a href="/mileage/delete/{{ m['id'] }}" class="btn btn-danger btn-sm" onclick="return confirm('Delete record?');">Delete</a></td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    """
  return render_with_calendar(html, vehicles=vehicles, mileages=mileages)


@app.route("/mileage/delete/<int:id>")
def delete_mileage(id):
  if not session.get("logged_in"):
    return redirect(url_for("index"))
  conn = get_db_connection()
  conn.execute("DELETE FROM mileage WHERE id = ?", (id,))
  conn.commit()
  conn.close()
  return redirect(url_for("mileage_page"))


@app.route("/fuel", methods=["GET", "POST"])
def fuel_page():
  if not session.get("logged_in"):
    return redirect(url_for("index"))
  conn = get_db_connection()
  if request.method == "POST":
    v_id = int(request.form["vehicle_id"])
    date = request.form["date"]
    litres = float(request.form["litres"] or 0)
    cost = float(request.form["cost"] or 0)
    mileage_at_fill = float(request.form["mileage_at_fill"] or 0)

    prev_fuel = conn.execute(
        "SELECT mileage_at_fill FROM fuel WHERE vehicle_id = ? ORDER BY date DESC, id DESC LIMIT 1",
        (v_id,),
    ).fetchone()
    km_per_litre = 0
    if prev_fuel and mileage_at_fill > prev_fuel["mileage_at_fill"]:
      distance = mileage_at_fill - prev_fuel["mileage_at_fill"]
      if litres > 0:
        km_per_litre = round(distance / litres, 2)

    conn.execute(
        "INSERT INTO fuel (vehicle_id, date, litres, cost, mileage_at_fill, km_per_litre) VALUES (?, ?, ?, ?, ?, ?)",
        (v_id, date, litres, cost, mileage_at_fill, km_per_litre),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("fuel_page"))

  vehicles = conn.execute("SELECT * FROM vehicles").fetchall()
  fuels = conn.execute(
      "SELECT f.*, v.vehicle_no FROM fuel f JOIN vehicles v ON f.vehicle_id = v.id ORDER BY f.date DESC"
  ).fetchall()
  conn.close()

  html = """
    <h2>Fuel Records & Efficiency (KM/L)</h2>
    <form method="POST" class="bg-light p-3 border rounded mb-4">
        <div class="mb-3">
            <select name="vehicle_id" class="form-select" required>
                <option value="">Select Vehicle</option>
                {% for v in vehicles %}<option value="{{ v['id'] }}">{{ v['vehicle_no'] }} ({{ v['model'] }})</option>{% endfor %}
            </select>
        </div>
        <div class="row g-2 mb-3">
            <div class="col-md-4"><input type="date" name="date" class="form-control" required></div>
            <div class="col-md-4"><input type="number" step="0.01" name="litres" class="form-control" placeholder="Litres Pumped" required></div>
            <div class="col-md-4"><input type="number" step="0.01" name="cost" class="form-control" placeholder="Total Cost (Rs.)" required></div>
        </div>
        <div class="mb-3"><input type="number" step="0.1" name="mileage_at_fill" class="form-control" placeholder="Mileage at Fuel Fill (KM)" required></div>
        <button type="submit" class="btn btn-success w-100 fw-bold">Save Fuel Record</button>
    </form>
    <h3>Fuel Logs & Efficiency</h3>
    <div class="table-responsive">
        <table class="table table-bordered table-striped">
            <thead class="table-primary">
                <tr><th>Vehicle</th><th>Date</th><th>Litres</th><th>Cost</th><th>Mileage</th><th>Efficiency (KM/L)</th></tr>
            </thead>
            <tbody>
                {% for f in fuels %}
                <tr>
                    <td>{{ f['vehicle_no'] }}</td>
                    <td>{{ f['date'] }}</td>
                    <td>{{ f['litres'] }} L</td>
                    <td>Rs. {{ f['cost'] }}</td>
                    <td>{{ f['mileage_at_fill'] }} KM</td>
                    <td><span class="badge bg-success">{{ f['km_per_litre'] if f['km_per_litre'] > 0 else 'N/A' }} KM/L</span></td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    """
  return render_with_calendar(html, vehicles=vehicles, fuels=fuels)


@app.route("/maintenance", methods=["GET", "POST"])
def maintenance_page():
  if not session.get("logged_in"):
    return redirect(url_for("index"))
  conn = get_db_connection()
  if request.method == "POST":
    v_id = int(request.form["vehicle_id"])
    date = request.form["date"]
    m_type = request.form["type"]
    desc = request.form["description"]
    parts = request.form["parts_replaced"]
    m_at_serv = float(request.form["mileage_at_service"] or 0)
    next_serv = float(request.form["next_service_km"] or (m_at_serv + 5000))
    cost = float(request.form["cost"] or 0)

    conn.execute(
        """INSERT INTO maintenance (vehicle_id, date, type, description, parts_replaced, mileage_at_service, next_service_km, cost) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (v_id, date, m_type, desc, parts, m_at_serv, next_serv, cost),
    )
    conn.execute(
        "UPDATE vehicles SET current_mileage = ?, next_service_due = ? WHERE id = ?",
        (m_at_serv, next_serv, v_id),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("maintenance_page"))

  vehicles = conn.execute("SELECT * FROM vehicles").fetchall()
  maintenances = conn.execute(
      """SELECT m.*, v.vehicle_no FROM maintenance m JOIN vehicles v ON m.vehicle_id = v.id ORDER BY m.date DESC"""
  ).fetchall()
  conn.close()

  html = """
    <h2>Service & Maintenance Records</h2>
    <form method="POST" class="bg-light p-3 border rounded mb-4">
        <div class="mb-3">
            <select name="vehicle_id" class="form-select" required>
                <option value="">Select Vehicle</option>
                {% for v in vehicles %}<option value="{{ v['id'] }}">{{ v['vehicle_no'] }} ({{ v['model'] }})</option>{% endfor %}
            </select>
        </div>
        <div class="row g-2 mb-3">
            <div class="col-md-6"><input type="date" name="date" class="form-control" required></div>
            <div class="col-md-6">
                <select name="type" class="form-select" required>
                    <option value="Routine Service">Routine Service (Oil/Filters)</option>
                    <option value="Major Repair">Major Repair / Engine Work</option>
                    <option value="Tyre Change">Tyre Change / Alignment</option>
                    <option value="Other">Other Maintenance</option>
                </select>
            </div>
        </div>
        <div class="mb-3"><input type="text" name="description" class="form-control" placeholder="Work Description" required></div>
        <div class="mb-3"><input type="text" name="parts_replaced" class="form-control" placeholder="Parts Replaced"></div>
        <div class="row g-2 mb-3">
            <div class="col-md-6"><input type="number" step="0.1" name="mileage_at_service" class="form-control" placeholder="Mileage at Service (KM)" required></div>
            <div class="col-md-6"><input type="number" step="0.1" name="next_service_km" class="form-control" placeholder="Next Service Due KM (Default +5000)"></div>
        </div>
        <div class="mb-3"><input type="number" step="0.01" name="cost" class="form-control" placeholder="Total Cost (Rs.)" required></div>
        <button type="submit" class="btn btn-success w-100 fw-bold">Save Service Record</button>
    </form>
    <h3>Service History</h3>
    <div class="table-responsive">
        <table class="table table-bordered table-striped">
            <thead class="table-primary">
                <tr><th>Vehicle</th><th>Date</th><th>Type & Desc</th><th>Service KM</th><th>Next Due KM</th><th>Cost</th><th>Action</th></tr>
            </thead>
            <tbody>
                {% for m in maintenances %}
                <tr>
                    <td>{{ m['vehicle_no'] }}</td>
                    <td>{{ m['date'] }}</td>
                    <td><b>{{ m['type'] }}</b><br>{{ m['description'] }}</td>
                    <td>{{ m['mileage_at_service'] }} KM</td>
                    <td class="text-danger fw-bold">{{ m['next_service_km'] }} KM</td>
                    <td>Rs. {{ m['cost'] }}</td>
                    <td><a href="/maintenance/delete/{{ m['id'] }}" class="btn btn-danger btn-sm" onclick="return confirm('Delete record?');">Delete</a></td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    """
  return render_with_calendar(
      html, vehicles=vehicles, maintenances=maintenances
  )


@app.route("/maintenance/delete/<int:id>")
def delete_maintenance(id):
  if not session.get("logged_in"):
    return redirect(url_for("index"))
  conn = get_db_connection()
  conn.execute("DELETE FROM maintenance WHERE id = ?", (id,))
  conn.commit()
  conn.close()
  return redirect(url_for("maintenance_page"))


@app.route("/hires", methods=["GET", "POST"])
def hires_page():
  if not session.get("logged_in"):
    return redirect(url_for("index"))
  conn = get_db_connection()
  if request.method == "POST":
    v_id = request.form["vehicle_id"]
    c_name = request.form["customer_name"]
    pickup = request.form["pickup"]
    drop_loc = request.form["drop_loc"]
    start_date = request.form["start_date"]
    end_date = request.form["end_date"]
    amount = float(request.form["amount"] or 0)
    advance = float(request.form["advance"] or 0)
    commission = float(request.form["commission"] or 0)
    allocated_km = float(request.form["allocated_km"] or 0)
    extra_km_rate = float(request.form["extra_km_rate"] or 0)
    actual_km = float(request.form["actual_km"] or 0)
    status = request.form["status"]

    conn.execute(
        """INSERT INTO hires (vehicle_id, customer_name, pickup, drop_loc, start_date, end_date, amount, advance, commission, allocated_km, extra_km_rate, actual_km, status) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            v_id,
            c_name,
            pickup,
            drop_loc,
            start_date,
            end_date,
            amount,
            advance,
            commission,
            allocated_km,
            extra_km_rate,
            actual_km,
            status,
        ),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("hires_page"))

  vehicles = conn.execute("SELECT * FROM vehicles").fetchall()
  hires = conn.execute(
      """SELECT h.*, v.vehicle_no FROM hires h JOIN vehicles v ON h.vehicle_id = v.id ORDER BY h.start_date DESC"""
  ).fetchall()
  conn.close()

  html = """
    <h2>Hire & Booking Management</h2>
    <form method="POST" class="bg-light p-3 border rounded mb-4">
        <div class="mb-3">
            <select name="vehicle_id" class="form-select" required>
                <option value="">Select Vehicle</option>
                {% for v in vehicles %}<option value="{{ v['id'] }}">{{ v['vehicle_no'] }} ({{ v['model'] }})</option>{% endfor %}
            </select>
        </div>
        <div class="row g-2 mb-3">
            <div class="col-md-4"><input type="text" name="customer_name" class="form-control" placeholder="Customer Name & Phone" required></div>
            <div class="col-md-4"><input type="text" name="pickup" class="form-control" placeholder="Pickup Location" required></div>
            <div class="col-md-4"><input type="text" name="drop_loc" class="form-control" placeholder="Drop Location" required></div>
        </div>
        <div class="row g-2 mb-3">
            <div class="col-md-4"><label class="form-label small text-muted mb-1">Start Date:</label><input type="date" name="start_date" class="form-control" required></div>
            <div class="col-md-4"><label class="form-label small text-muted mb-1">End Date:</label><input type="date" name="end_date" class="form-control" required></div>
            <div class="col-md-4">
                <label class="form-label small text-muted mb-1">Status:</label>
                <select name="status" class="form-select" required>
                    <option value="Pending">Pending</option>
                    <option value="Ongoing">Ongoing</option>
                    <option value="Completed">Completed</option>
                    <option value="Cancelled">Cancelled</option>
                </select>
            </div>
        </div>
        <div class="row g-2 mb-3">
            <div class="col-md-4"><input type="number" step="0.01" name="amount" class="form-control" placeholder="Hire Amount (Rs.)" required></div>
            <div class="col-md-4"><input type="number" step="0.01" name="advance" class="form-control" placeholder="Advance Received (Rs.)"></div>
            <div class="col-md-4"><input type="number" step="0.01" name="commission" class="form-control" placeholder="Commission (Rs.)"></div>
        </div>
        <div class="row g-2 mb-3">
            <div class="col-md-4"><input type="number" step="0.1" name="allocated_km" class="form-control" placeholder="Allocated KM"></div>
            <div class="col-md-4"><input type="number" step="0.01" name="extra_km_rate" class="form-control" placeholder="Extra KM Rate"></div>
            <div class="col-md-4"><input type="number" step="0.1" name="actual_km" class="form-control" placeholder="Actual KM Traveled"></div>
        </div>
        <button type="submit" class="btn btn-success w-100 fw-bold">Save Hire Booking</button>
    </form>
    <h3>Hire History</h3>
    <div class="table-responsive">
        <table class="table table-bordered table-striped">
            <thead class="table-primary">
                <tr><th>Vehicle & Customer</th><th>Route / Dates</th><th>Financials</th><th>Status</th><th>Action</th></tr>
            </thead>
            <tbody>
                {% for h in hires %}
                <tr>
                    <td><b>{{ h['vehicle_no'] }}</b><br>{{ h['customer_name'] }}</td>
                    <td>{{ h['pickup'] }} -> {{ h['drop_loc'] }}<br><small>{{ h['start_date'] }} to {{ h['end_date'] }}</small></td>
                    <td>
                        Hire: Rs. {{ h['amount'] }}<br>
                        Adv: <span class="text-success fw-bold">Rs. {{ h['advance'] or 0 }}</span><br>
                        Bal: <b>Rs. {{ h['amount'] - (h['advance'] or 0) }}</b>
                    </td>
                    <td><b>{{ h['status'] }}</b></td>
                    <td>
                        <a href="/invoice/{{ h['id'] }}" target="_blank" class="btn btn-dark btn-sm mb-1">📄 PDF Invoice</a><br>
                        <a href="/hire/delete/{{ h['id'] }}" class="btn btn-danger btn-sm" onclick="return confirm('Delete record?');">Delete</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    """
  return render_with_calendar(html, vehicles=vehicles, hires=hires)


@app.route("/hire/delete/<int:id>")
def delete_hire(id):
  if not session.get("logged_in"):
    return redirect(url_for("index"))
  conn = get_db_connection()
  conn.execute("DELETE FROM hires WHERE id = ?", (id,))
  conn.commit()
  conn.close()
  return redirect(url_for("hires_page"))


@app.route("/invoice/<int:id>")
def generate_invoice(id):
  if not session.get("logged_in"):
    return redirect(url_for("index"))
  conn = get_db_connection()
  hire = conn.execute(
      """SELECT h.*, v.vehicle_no, v.model FROM hires h JOIN vehicles v ON h.vehicle_id = v.id WHERE h.id = ?""",
      (id,),
  ).fetchone()
  conn.close()

  if not hire:
    return "Invoice not found", 404

  balance = hire["amount"] - (hire["advance"] or 0)

  html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Invoice - #{hire['id']} - UKC TOURS</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 30px; color: #333; }}
            .invoice-box {{ max-width: 800px; margin: auto; padding: 30px; border: 1px solid #eee; box-shadow: 0 0 10px rgba(0, 0, 0, 0.15); }}
            .header {{ display: flex; justify-content: space-between; border-bottom: 2px solid #007bff; padding-bottom: 15px; margin-bottom: 20px; }}
            .header h1 {{ margin: 0; color: #0056b3; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ padding: 10px; border: 1px solid #ddd; text-align: left; }}
            th {{ background: #007bff; color: white; }}
            .total-section {{ text-align: right; margin-top: 20px; font-size: 16px; }}
            .footer {{ text-align: center; margin-top: 40px; font-size: 12px; color: #777; }}
        </style>
    </head>
    <body onload="window.print()">
        <div class="invoice-box">
            <div class="header">
                <div>
                    <h1>UKC TOURS</h1>
                    <p>Explore Sri Lanka With Comfort<br>Hotline: 0784441944 / 0704441944</p>
                </div>
                <div style="text-align: right;">
                    <h3>INVOICE</h3>
                    <p>Invoice #: UKC-{hire['id']}<br>Date: {datetime.now().strftime('%Y-%m-%d')}</p>
                </div>
            </div>
            
            <p><b>Customer Name:</b> {hire['customer_name']}</p>
            <p><b>Vehicle Assigned:</b> {hire['vehicle_no']} ({hire['model']})</p>
            
            <table>
                <tr><th>Description</th><th>Details</th></tr>
                <tr><td>Route</td><td>{hire['pickup']} -> {hire['drop_loc']}</td></tr>
                <tr><td>Hire Duration</td><td>{hire['start_date']} to {hire['end_date']}</td></tr>
                <tr><td>Allocated KM & Extra Rate</td><td>{hire['allocated_km'] or 'N/A'} KM (Rate: Rs. {hire['extra_km_rate'] or 0}/km)</td></tr>
                <tr><td>Actual KM Traveled</td><td>{hire['actual_km'] or 'N/A'} KM</td></tr>
            </table>
            
            <div class="total-section">
                <p><b>Total Amount:</b> Rs. {hire['amount']:.2f}</p>
                <p><b>Advance Received:</b> Rs. {hire['advance'] or 0:.2f}</p>
                <p style="font-size: 18px; color: #d9534f;"><b>Balance Due:</b> Rs. {balance:.2f}</p>
            </div>
            
            <div class="footer">
                <p>Thank you for travelling with UKC TOURS! Have a safe journey.</p>
            </div>
        </div>
    </body>
    </html>
    """
  return html_content


@app.route("/pnl")
def pnl_page():
  if not session.get("logged_in"):
    return redirect(url_for("index"))
  conn = get_db_connection()
  total_revenue = (
      conn.execute(
          "SELECT SUM(amount) FROM hires WHERE status = 'Completed'"
      ).fetchone()[0]
      or 0
  )
  total_commission = (
      conn.execute(
          "SELECT SUM(commission) FROM hires WHERE status = 'Completed'"
      ).fetchone()[0]
      or 0
  )
  total_fuel_cost = (
      conn.execute("SELECT SUM(cost) FROM fuel").fetchone()[0] or 0
  )
  total_maintenance_cost = (
      conn.execute("SELECT SUM(cost) FROM maintenance").fetchone()[0] or 0
  )
  conn.close()

  net_profit = (
      total_revenue - (total_commission + total_fuel_cost + total_maintenance_cost)
  )

  if net_profit >= 0:
    profit_color, profit_text = "text-success", f"Rs. {net_profit:.2f}"
  else:
    profit_color, profit_text = "text-danger", f"- Rs. {abs(net_profit):.2f}"

  html = f"""
    <h2>Profit & Loss Statement (P&L)</h2>
    <p class="text-muted">Financial summary of your transport business operations:</p>
    <div class="table-responsive">
        <table class="table table-bordered table-striped mt-3">
            <thead class="table-primary">
                <tr><th>Description</th><th>Amount (Rs.)</th></tr>
            </thead>
            <tbody>
                <tr><td><b>Total Gross Revenue (Completed Hires)</b></td><td class="text-success fw-bold">Rs. {total_revenue:.2f}</td></tr>
                <tr><td>Less: Total Commissions</td><td class="text-danger">- Rs. {total_commission:.2f}</td></tr>
                <tr><td>Less: Total Fuel Expenses</td><td class="text-danger">- Rs. {total_fuel_cost:.2f}</td></tr>
                <tr><td>Less: Total Maintenance & Repair Expenses</td><td class="text-danger">- Rs. {total_maintenance_cost:.2f}</td></tr>
                <tr class="table-info fs-5">
                    <td><b>Net Profit / (Loss)</b></td>
                    <td class="{profit_color} fw-bold">{profit_text}</td>
                </tr>
            </tbody>
        </table>
    </div>
    """
  return render_with_calendar(html)


if __name__ == "__main__":
  init_db()
  app.run(host="0.0.0.0", port=5000, debug=True)